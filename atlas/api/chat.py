import asyncio
import json
import logging
import os
import subprocess
import sys
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from atlas.services.ollama_service import chat as ollama_chat, chat_stream as ollama_stream
from atlas.services.deepseek_service import chat as deepseek_chat, chat_stream as deepseek_stream
from atlas.services.groq_service import chat as groq_chat, chat_stream as groq_stream
from atlas.db.vector_store import search, search_all, store
from atlas.core.indexer import run_indexer
from atlas.core.planner import plan as make_plan
from atlas.core.personality import get_system_prompt
from atlas.services.calendar_service import (
    fetch_upcoming_events,
    index_calendar_event_with_pattern,
    _extract_class_code,
)

INBOX_DIR = os.getenv("VAULT_PATH", "/opt/heimdall/vault") + "/inbox"
INBOX_SCRIPT = os.path.join(os.path.dirname(__file__), "../../scripts/process_inbox.py")
PYTHON = sys.executable


async def _run_inbox_processor() -> str:
    """Run process_inbox.py as a subprocess and return a summary."""
    import asyncio
    from pathlib import Path

    inbox = Path(INBOX_DIR)
    if not inbox.exists() or not list(inbox.rglob("*.md")):
        return "Inbox is empty — nothing to process. Drop `.md` files into `/opt/heimdall/vault/inbox/` first."

    file_count = len(list(inbox.rglob("*.md")))

    try:
        proc = await asyncio.create_subprocess_exec(
            PYTHON, os.path.abspath(INBOX_SCRIPT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=300)
        output = stdout.decode(errors="replace")

        # Parse summary from last lines
        lines = [l for l in output.splitlines() if l.strip()]
        summary_lines = [l for l in lines if any(k in l for k in ["INSERT", "UPDATE", "SKIP", "MOVE", "Done:", "Error"])]
        brief = "\n".join(summary_lines[-10:]) if summary_lines else output[-500:]

        if proc.returncode == 0:
            return f"Ingested {file_count} file(s) from inbox.\n\n```\n{brief}\n```"
        else:
            return f"Inbox processor finished with errors.\n\n```\n{brief}\n```"
    except asyncio.TimeoutError:
        return "Inbox processor timed out after 5 minutes — check logs."
    except Exception as e:
        return f"Failed to run inbox processor: {e}"

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

_PROVIDER_MAP = {
    "deepseek": (deepseek_chat, deepseek_stream),
    "groq":     (groq_chat,     groq_stream),
}


def _get_provider(model: str):
    for prefix, fns in _PROVIDER_MAP.items():
        if model.startswith(prefix):
            return fns
    return (ollama_chat, ollama_stream)


async def _fetch_context(plan: dict, message: str) -> list[dict]:
    """Search only the memory tables specified in the plan."""
    tables = plan.get("memory_tables", [])
    query = plan.get("memory_query") or message
    if not tables:
        return []
    results = []
    for table in tables:
        try:
            results += await search(table, query, limit=3)
        except Exception:
            pass
    results.sort(key=lambda r: r.get("distance", 1))
    return results[:5]


async def _fetch_calendar(days: int = 2) -> list[dict]:
    """Fetch upcoming calendar events."""
    try:
        events = await fetch_upcoming_events(days_ahead=days)
        # Format events for context
        formatted = []
        for e in events:
            text = f"Calendar: '{e['summary']}' on {e['start'][:10]}"
            if e.get("location"):
                text += f" at {e['location']}"
            if e.get("description"):
                text += f" — {e['description'][:100]}"
            formatted.append({"text": text, "source": "calendar", "uid": e["uid"]})
        return formatted[:8]  # Limit to 8 upcoming events
    except Exception:
        return []


async def _handle_class_pattern_learning(message: str) -> Optional[str]:
    """
    Detect if user is teaching Heimdall about a class code pattern.
    Returns confirmation message if pattern was learned, None otherwise.
    """
    import re
    
    # Look for patterns like "EGE301 is Communication & Workplace Success" 
    # or "EGE322 stands for Embedded System Design"
    patterns = [
        r'([A-Z]{2,4}\d{3})\s+(?:is|stands for|means?)\s+(.+?)(?:\.|$)',
        r'([A-Z]{2,4}\d{3})\s+(?:is|stands for|means?)\s+(.+?)(?:\n|$)',
        r'teach\s+(?:me\s+)?(?:that\s+)?([A-Z]{2,4}\d{3})\s+(?:is|stands for|means?)\s+(.+?)(?:\.|$)',
        r'([A-Z]{2,4}\d{3})\s+(?:is|stands for|means?)\s+(.+?)(?:\.|$)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            class_code = match.group(1).upper()
            description = match.group(2).strip()
            
            # Create a mock event for pattern storage
            mock_event = {
                "uid": f"chat-learned-{class_code}",
                "summary": f"{class_code} class",
                "start": "2026-05-13T12:00:00",
                "location": "",
                "description": "",
            }
            
            try:
                result = await index_calendar_event_with_pattern(mock_event, context_note=description)
                if result.get("pattern_stored"):
                    return f"Got it! I've learned that **{class_code}** is: {description}"
            except Exception as e:
                logger.warning(f"Failed to store class pattern from chat: {e}")
    
    return None


def _build_messages(message: str, history: list[dict], context_results: list[dict], calendar_results: list[dict] | None = None) -> list[dict]:
    sections = []
    has_calendar = bool(calendar_results and len(calendar_results) > 0)
    has_memory = bool(context_results and len(context_results) > 0)
    
    if calendar_results:
        calendar_text = "\n".join(f"- {r['text']}" for r in calendar_results)
        sections.append(f"Upcoming calendar events:\n{calendar_text}")
    
    if context_results:
        context_text = "\n".join(f"- {r['text']}" for r in context_results)
        sections.append(f"Relevant context from memory:\n{context_text}")
    
    context_section = ""
    if sections:
        context_section = "\n\n" + "\n\n".join(sections)

    system_prompt = get_system_prompt(
        context=context_section,
        with_memory=has_memory,
        with_calendar=has_calendar
    )
    messages = [{"role": "system", "content": system_prompt}]
    messages += history
    messages.append({"role": "user", "content": message})
    return messages


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    model: str | None = None        # None = let the planner decide
    store_in_memory: bool = False   # manual override; planner also decides


class ChatResponse(BaseModel):
    reply: str
    model: str
    plan: dict = {}
    context_used: list[dict] = []


@router.post("", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest, background_tasks: BackgroundTasks):
    # ── Class pattern learning dispatch ───────────────────────────────────
    pattern_result = await _handle_class_pattern_learning(req.message)
    if pattern_result:
        return ChatResponse(reply=pattern_result, model="tool/pattern", plan={}, context_used=[])
    
    routing_plan = await make_plan(req.message)
    model = req.model or routing_plan["model"]
    caps = routing_plan.get("capabilities", [])

    # ── Ingest tool dispatch (with guardrail) ──────────────────────────────
    # Only trigger ingest if message explicitly mentions inbox/file processing
    INGEST_KEYWORDS = ["ingest", "process my inbox", "process inbox", "import", "index files", "process files", "import files", "process notes"]
    if "ingest" in caps and any(k in req.message.lower() for k in INGEST_KEYWORDS):
        reply = await _run_inbox_processor()
        return ChatResponse(reply=reply, model="tool/inbox", plan=routing_plan, context_used=[])

    # ── Calendar tool dispatch ─────────────────────────────────────────────
    calendar_results = []
    if "calendar" in caps:
        # Determine days based on query
        days = 2
        msg_lower = req.message.lower()
        if "week" in msg_lower or "next 7" in msg_lower:
            days = 7
        elif "today" in msg_lower or "schedule" in msg_lower:
            days = 1
        elif "tomorrow" in msg_lower:
            days = 2
        elif "month" in msg_lower:
            days = 30
        calendar_results = await _fetch_calendar(days=days)

    context_results = await _fetch_context(routing_plan, req.message)
    messages = _build_messages(req.message, req.history, context_results, calendar_results)
    chat_fn, _ = _get_provider(model)

    try:
        reply = await chat_fn(messages, model=model)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    should_store = req.store_in_memory or routing_plan.get("store", False)
    if should_store:
        await store("vector_memory", req.message, source_type="chat_input", source_path="chat")

    background_tasks.add_task(run_indexer, req.message, reply)
    combined_context = context_results + calendar_results
    return ChatResponse(reply=reply, model=model, plan=routing_plan, context_used=combined_context)


@router.post("/stream")
async def chat_stream_endpoint(req: ChatRequest):
    # ── Class pattern learning dispatch (streaming) ────────────────────────
    pattern_result = await _handle_class_pattern_learning(req.message)
    if pattern_result:
        async def event_generator():
            yield f"data: {json.dumps({'type': 'token', 'data': pattern_result})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'model': 'tool/pattern', 'plan': {}})}\n\n"
        return StreamingResponse(event_generator(), media_type="text/event-stream")
    
    routing_plan = await make_plan(req.message)
    model = req.model or routing_plan["model"]
    caps = routing_plan.get("capabilities", [])

    # ── Calendar tool dispatch ─────────────────────────────────────────────
    calendar_results = []
    if "calendar" in caps:
        days = 2
        msg_lower = req.message.lower()
        if "week" in msg_lower or "next 7" in msg_lower:
            days = 7
        elif "today" in msg_lower or "schedule" in msg_lower:
            days = 1
        elif "tomorrow" in msg_lower:
            days = 2
        elif "month" in msg_lower:
            days = 30
        calendar_results = await _fetch_calendar(days=days)

    context_results = await _fetch_context(routing_plan, req.message)
    messages = _build_messages(req.message, req.history, context_results, calendar_results)
    _, stream_fn = _get_provider(model)

    async def event_generator():
        full_reply = []
        try:
            yield f"data: {json.dumps({'type': 'plan', 'data': routing_plan})}\n\n"

            # ── Ingest tool dispatch (streaming) ──────────────────────────
            INGEST_KEYWORDS = ["ingest", "process my inbox", "process inbox", "import", "index files", "process files", "import files", "process notes"]
            if "ingest" in caps and any(k in req.message.lower() for k in INGEST_KEYWORDS):
                yield f"data: {json.dumps({'type': 'token', 'data': 'Processing inbox...'})}\n\n"
                result = await _run_inbox_processor()
                yield f"data: {json.dumps({'type': 'token', 'data': result})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'model': 'tool/inbox', 'plan': routing_plan})}\n\n"
                return

            combined_context = context_results + calendar_results
            yield f"data: {json.dumps({'type': 'context', 'data': combined_context})}\n\n"
            async for token in stream_fn(messages, model=model):
                full_reply.append(token)
                yield f"data: {json.dumps({'type': 'token', 'data': token})}\n\n"
            reply_text = "".join(full_reply)
            should_store = req.store_in_memory or routing_plan.get("store", False)
            if should_store:
                await store("vector_memory", req.message, source_type="chat_input", source_path="chat")
            asyncio.ensure_future(run_indexer(req.message, reply_text))
            yield f"data: {json.dumps({'type': 'done', 'model': model, 'plan': routing_plan})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/plan")
async def plan_only(req: ChatRequest):
    """Debug endpoint — returns the plan without calling the LLM."""
    routing_plan = await make_plan(req.message)
    return {"message": req.message, "plan": routing_plan}
