"""
Capability Planner — analyses each incoming message and returns a structured
plan: which model to use, which capabilities are needed, and what memory
context to inject.

Uses groq-llama3-8b (fastest, cheapest) for the planning step itself.
The plan is a lightweight JSON object consumed by the chat endpoint.

Plan schema:
{
  "model":    "groq-llama4-scout",   # model ID to use for the response
  "capabilities": ["retrieval"],     # list of active capabilities
  "memory_tables": ["vector_memory"],# which tables to search for context
  "memory_query":  "...",            # refined query for memory search (may differ from raw message)
  "store":    true,                  # whether this turn should be indexed
  "reasoning": "one sentence"        # why this plan was chosen (debug)
}
"""

import json
import logging
import re
from atlas.services.groq_service import chat as groq_chat
from atlas.core.personality import HEIMDALL_BASE

logger = logging.getLogger(__name__)

# The model used to do the planning — must be fast and cheap
PLANNER_MODEL = "groq-llama3-8b"

# ── Model routing rules ──────────────────────────────────────────────────────
# Ordered by capability. The planner picks the first that fits.
# local-fast  = qwen3:1.7b   (instant, free, weak)
# local       = qwen3:8b     (slow, free, decent)
# scout       = groq-llama4-scout  (fast, free tier, good)
# flash       = deepseek-flash     (fast, $0.14/M, excellent)
# pro         = deepseek-pro       (slow, $1.74/M, best reasoning)

MODEL_ROUTING = {
    "quick":     "groq-llama4-scout",   # greetings, simple Q&A, short factual
    "retrieval": "groq-llama4-scout",   # memory search + answer
    "calendar":  "groq-llama4-scout",   # fetch calendar events + answer
    "writing":   "deepseek-flash",      # drafting, summarising, journal
    "reasoning": "deepseek-flash",      # multi-step analysis, plans, math
    "code":      "deepseek-flash",      # code generation / debugging
    "complex":   "deepseek-pro",        # deep reasoning, long-form research
    "local":     "qwen3:1.7b",          # explicit offline/local request
    "ingest":    "groq-llama4-scout",   # process inbox / ingest files
}

CAPABILITY_LIST = list(MODEL_ROUTING.keys())

PLAN_SYSTEM = HEIMDALL_BASE + """

CURRENT TASK: Routing planner.
Given a user message, return a JSON plan. Be decisive. No explanation, no markdown — JSON only.

Schema:
{
  "model": "<model_id>",
  "capabilities": ["<cap1>", ...],
  "memory_tables": ["<table1>", ...],
  "memory_query": "<refined search query or empty string>",
  "store": true|false,
  "reasoning": "<one sentence>"
}

Model IDs (pick exactly one):
- "qwen3:1.7b"          — trivial/offline only
- "groq-llama4-scout"   — quick answers, retrieval, short tasks
- "deepseek-flash"      — writing, code, reasoning, analysis
- "deepseek-pro"        — genuinely hard reasoning or research only (use sparingly)

Capabilities (pick all that apply):
- "quick"      — simple greeting or one-liner fact
- "retrieval"  — needs to search past memories/notes
- "calendar"   — needs to fetch upcoming calendar events (schedule, appointments, "what's on", "do I have", etc.)
- "writing"    — drafting, editing, summarising text
- "reasoning"  — analysis, plans, step-by-step thinking
- "code"       — programming tasks
- "complex"    — very hard reasoning, research-level
- "ingest"     — user EXPLICITLY wants to ingest/process files/notes. Only include if message contains: "ingest", "process my inbox", "import", "index files", "process files". NEVER for todos, shopping lists, or reminders.

Memory tables (pick relevant ones, or empty list if no retrieval needed):
- "vector_memory"        — personal facts, goals, people, preferences
- "vector_notes"         — daily logs, journal entries
- "vector_chat_summaries"— past conversation summaries
- "vector_code_chunks"   — indexed code

memory_query: rewrite the user message as an optimal semantic search query.
  If no retrieval needed, set to "".

store: true if this message contains facts worth remembering. false for greetings,
  test messages, or purely computational tasks.

Examples:
User: "hey how are you"
→ {"model":"groq-llama4-scout","capabilities":["quick"],"memory_tables":[],"memory_query":"","store":false,"reasoning":"Simple greeting, no retrieval or storage needed."}

User: "what was that project i mentioned last week"
→ {"model":"groq-llama4-scout","capabilities":["retrieval"],"memory_tables":["vector_memory","vector_notes"],"memory_query":"project mentioned last week","store":false,"reasoning":"Needs memory retrieval across personal facts and journal."}

User: "what was that goal i mentioned about my PC build"
→ {"model":"groq-llama4-scout","capabilities":["retrieval"],"memory_tables":["vector_memory"],"memory_query":"PC build goal","store":false,"reasoning":"Simple retrieval from personal memory, no complex reasoning needed."}

User: "write a cover letter for a software engineering internship"
→ {"model":"deepseek-flash","capabilities":["writing"],"memory_tables":["vector_memory"],"memory_query":"job internship career goals","store":false,"reasoning":"Writing task, DeepSeek Flash best for long-form drafting."}

User: "i just got a new job at Google starting June"
→ {"model":"groq-llama4-scout","capabilities":["quick"],"memory_tables":[],"memory_query":"","store":true,"reasoning":"Contains a personal fact worth storing."}

User: "my favourite programming language is Python"
→ {"model":"groq-llama4-scout","capabilities":["quick"],"memory_tables":[],"memory_query":"","store":true,"reasoning":"Explicit personal preference — should be stored."}

User: "I prefer dark mode on all my apps"
→ {"model":"groq-llama4-scout","capabilities":["quick"],"memory_tables":[],"memory_query":"","store":true,"reasoning":"Personal preference worth storing."}

User: "I'm studying computer science at NTU"
→ {"model":"groq-llama4-scout","capabilities":["quick"],"memory_tables":[],"memory_query":"","store":true,"reasoning":"Personal fact about education."}

User: "ingest my inbox"
→ {"model":"groq-llama4-scout","capabilities":["ingest"],"memory_tables":[],"memory_query":"","store":false,"reasoning":"User wants to process inbox files."}

User: "process my notes / import my vault"
→ {"model":"groq-llama4-scout","capabilities":["ingest"],"memory_tables":[],"memory_query":"","store":false,"reasoning":"File ingestion request."}

User: "what's on my schedule today"
→ {"model":"groq-llama4-scout","capabilities":["calendar"],"memory_tables":[],"memory_query":"","store":false,"reasoning":"User is asking about today's calendar events."}

User: "do I have any meetings tomorrow"
→ {"model":"groq-llama4-scout","capabilities":["calendar"],"memory_tables":[],"memory_query":"","store":false,"reasoning":"User is checking for calendar events tomorrow."}

User: "what's happening this week"
→ {"model":"groq-llama4-scout","capabilities":["calendar"],"memory_tables":[],"memory_query":"","store":false,"reasoning":"User wants to see this week's calendar schedule."}

User: "when is my next doctor appointment"
→ {"model":"groq-llama4-scout","capabilities":["calendar","retrieval"],"memory_tables":["vector_memory"],"memory_query":"doctor appointment medical","store":false,"reasoning":"User is asking about a specific calendar event, also retrieve any stored medical context."}
"""


def _extract_json(raw: str) -> dict:
    """Extract the first balanced JSON object from a string."""
    raw = raw.strip()
    # Strip markdown code fences
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    # Find the first '{' and walk to its matching '}' (brace counting)
    start = raw.find("{")
    if start == -1:
        raise ValueError("No JSON object found")
    depth = 0
    for i, ch in enumerate(raw[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(raw[start : i + 1])
    raise ValueError("Unbalanced braces in JSON response")


_FALLBACK_PLAN = {
    "model": "groq-llama4-scout",
    "capabilities": ["quick"],
    "memory_tables": ["vector_memory"],
    "memory_query": "",
    "store": False,
    "reasoning": "Fallback plan — planner failed.",
}


def _validate(result: dict, message: str) -> dict:
    """Fill missing keys with safe defaults."""
    result.setdefault("model", _FALLBACK_PLAN["model"])
    result.setdefault("capabilities", ["quick"])
    result.setdefault("memory_tables", [])
    result.setdefault("memory_query", message)
    result.setdefault("store", False)
    result.setdefault("reasoning", "")
    return result


async def plan(message: str) -> dict:
    """
    Analyse a user message and return a routing plan.
    Retries once on parse failure before falling back to defaults.
    """
    messages = [
        {"role": "system", "content": PLAN_SYSTEM},
        {"role": "user", "content": message},
    ]
    last_err = None
    for attempt in range(2):
        try:
            raw = await groq_chat(messages, model=PLANNER_MODEL)
            if not raw or not raw.strip():
                raise ValueError("Empty response from planner LLM")
            result = _validate(_extract_json(raw), message)
            logger.debug(f"Plan: model={result['model']} caps={result['capabilities']} store={result['store']}")
            return result
        except Exception as e:
            last_err = e
            if attempt == 0:
                logger.debug(f"Planner attempt 1 failed ({e}), retrying...")

    logger.warning(f"Planner failed after retry ({last_err}), using fallback plan")
    fallback = dict(_FALLBACK_PLAN)
    fallback["memory_query"] = message
    return fallback
