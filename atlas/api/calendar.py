"""
Calendar API — GET /calendar/upcoming, POST /calendar/sync
Pulls Apple iCloud events, finds unknown ones, asks user to clarify + indexes them.
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from atlas.services.calendar_service import (
    fetch_upcoming_events,
    find_unindexed_events,
    index_calendar_event,
    index_calendar_event_with_pattern,
    get_all_class_patterns,
    _extract_class_code,
    get_class_pattern,
    enrich_event_with_pattern,
)
from atlas.services.groq_service import chat as groq_chat
from atlas.core.personality import HEIMDALL_BASE

router = APIRouter(prefix="/calendar", tags=["calendar"])
logger = logging.getLogger(__name__)


class ClarifyRequest(BaseModel):
    event_uid: str
    event_summary: str
    event_start: str
    context: str


class SyncResponse(BaseModel):
    total_events: int
    already_known: int
    new_events: list[dict]
    questions: list[str]


@router.get("/calendars")
async def list_calendars():
    """List all available iCloud calendars and which ones Heimdall is currently reading."""
    import os
    from atlas.services.calendar_service import _get_client, CALDAV_ALLOWED

    def _sync():
        client = _get_client()
        cals = client.principal().calendars()
        result = []
        for c in cals:
            name = c.get_display_name() or ""
            enabled = (not CALDAV_ALLOWED) or (name.lower().strip() in CALDAV_ALLOWED)
            result.append({"name": name, "enabled": enabled})
        return result

    import asyncio
    try:
        cals = await asyncio.get_event_loop().run_in_executor(None, _sync)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CalDAV error: {e}")

    return {
        "calendars": cals,
        "filter_active": bool(CALDAV_ALLOWED),
        "hint": "Edit CALDAV_CALENDARS in .env (comma-separated names) to control which calendars Heimdall reads. Empty = all."
    }


@router.get("/upcoming")
async def get_upcoming(days: int = 7):
    """Fetch upcoming calendar events without syncing to memory. Enriches with learned patterns."""
    try:
        events = await fetch_upcoming_events(days_ahead=days)
        # Enrich events with learned patterns
        enriched = []
        for e in events:
            enriched.append(await enrich_event_with_pattern(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CalDAV error: {e}")
    return {"events": enriched, "count": len(enriched)}


@router.post("/sync", response_model=SyncResponse)
async def sync_calendar(days: int = 7):
    """
    Pull calendar events, find ones Heimdall doesn't know about,
    generate clarifying questions for each unknown event, and auto-index
    events that are self-explanatory (have a description or clear summary).
    For school schedules: extracts class codes and checks if we already know them.
    """
    try:
        events = await fetch_upcoming_events(days_ahead=days)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CalDAV error: {e}")

    unindexed = await find_unindexed_events(events)
    already_known = len(events) - len(unindexed)

    questions = []
    auto_indexed = []

    for event in unindexed:
        has_description = bool(event.get("description", "").strip())
        class_code = _extract_class_code(event.get("summary", ""))

        # Check if we already know this class pattern
        if class_code:
            pattern = await get_class_pattern(class_code)
            if pattern:
                # Auto-index with known pattern context
                try:
                    await index_calendar_event(event, context_note=pattern)
                    auto_indexed.append(event["uid"])
                    continue
                except Exception as e:
                    logger.warning(f"Pattern auto-index failed for {event['summary']}: {e}")

        if has_description:
            # Auto-index: enough context already
            try:
                await index_calendar_event(event, context_note=event["description"])
                auto_indexed.append(event["uid"])
            except Exception as e:
                logger.warning(f"Auto-index failed for {event['summary']}: {e}")
        else:
            # Generate a clarifying question
            try:
                messages = [
                    {"role": "system", "content": HEIMDALL_BASE + "\nYou help the user clarify calendar events for your memory. Ask ONE short question to understand the purpose or importance of this event. Be direct and conversational. Max 1 sentence."},
                    {"role": "user", "content": f"I have a calendar event: '{event['summary']}' on {event['start']}. What should I ask to understand it better?"},
                ]
                question = await groq_chat(messages, model="groq-llama3-8b")
                # Include class code hint if detected
                hint = f" [Class code: {class_code}]" if class_code else ""
                questions.append(f"**{event['summary']}** ({event['start']}): {question.strip()}{hint}")
            except Exception as e:
                hint = f" [Class code: {class_code}]" if class_code else ""
                questions.append(f"**{event['summary']}** ({event['start']}): What's this event about?{hint}")

    return SyncResponse(
        total_events=len(events),
        already_known=already_known,
        new_events=[e for e in unindexed if e["uid"] not in auto_indexed],
        questions=questions,
    )


@router.post("/clarify")
async def clarify_event(req: ClarifyRequest):
    """
    User has answered a clarifying question about a calendar event.
    Store the event + context into memory, and extract/store class pattern if applicable.
    """
    event = {
        "uid": req.event_uid,
        "summary": req.event_summary,
        "start": req.event_start,
        "location": "",
        "description": "",
    }
    try:
        result = await index_calendar_event_with_pattern(event, context_note=req.context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store event: {e}")

    response = {"status": "indexed", "entry_id": result["entry_id"], "event": req.event_summary}
    if result.get("pattern_stored"):
        response["pattern_learned"] = f"Class code '{result['class_code']}' now maps to: {req.context}"
    return response


@router.get("/brief-context")
async def calendar_brief_context(days: int = 2):
    """
    Returns upcoming events for the next N days formatted for the morning brief.
    Called by the brief endpoint to enrich context with calendar data.
    Enriches events with known class patterns.
    """
    from atlas.services.calendar_service import enrich_event_with_pattern
    try:
        events = await fetch_upcoming_events(days_ahead=days)
        # Enrich each event with pattern context
        enriched = []
        for e in events:
            enriched.append(await enrich_event_with_pattern(e))
    except Exception:
        return {"events": [], "error": "Calendar unavailable"}
    return {"events": enriched}


@router.get("/class-patterns")
async def list_class_patterns():
    """
    List all learned class code patterns (e.g., EGE353 -> Digital Signal Processing).
    """
    patterns = await get_all_class_patterns()
    return {
        "patterns": patterns,
        "count": len(patterns),
        "hint": "Teach Heimdall a new class by POSTing to /calendar/clarify with a class event."
    }
