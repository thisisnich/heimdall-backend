"""
Apple Calendar (iCloud CalDAV) integration service.
Fetches upcoming events, compares against stored memory, identifies unknown ones.
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

CALDAV_URL = os.getenv("CALDAV_URL", "https://caldav.icloud.com")
CALDAV_USERNAME = os.getenv("CALDAV_USERNAME", "")
CALDAV_PASSWORD = os.getenv("CALDAV_PASSWORD", "")  # Apple app-specific password

# Comma-separated list of calendar names to include. Empty = all calendars.
_RAW_ALLOWED = os.getenv("CALDAV_CALENDARS", "")
CALDAV_ALLOWED = {c.strip().lower() for c in _RAW_ALLOWED.split(",") if c.strip()}


def _get_client():
    import caldav
    return caldav.DAVClient(
        url=CALDAV_URL,
        username=CALDAV_USERNAME,
        password=CALDAV_PASSWORD,
    )


def _parse_event(event) -> Optional[dict]:
    """Extract useful fields from a caldav event object (caldav 3.x / icalendar)."""
    try:
        from icalendar import Calendar as iCal
        raw = event.data if isinstance(event.data, str) else event.data.decode("utf-8", errors="replace")
        cal = iCal.from_ical(raw)

        for component in cal.walk():
            if component.name != "VEVENT":
                continue

            summary = str(component.get("SUMMARY", "Untitled"))
            uid = str(component.get("UID", ""))
            location = str(component.get("LOCATION", ""))
            description = str(component.get("DESCRIPTION", ""))

            dtstart = component.get("DTSTART")
            dtend = component.get("DTEND")

            def _to_dt(val):
                if val is None:
                    return None
                v = val.dt if hasattr(val, "dt") else val
                if isinstance(v, datetime):
                    if v.tzinfo is None:
                        v = v.replace(tzinfo=timezone.utc)
                    return v
                # date only
                return datetime.combine(v, datetime.min.time()).replace(tzinfo=timezone.utc)

            start_dt = _to_dt(dtstart)
            end_dt = _to_dt(dtend)

            return {
                "uid": uid,
                "summary": summary,
                "start": start_dt.isoformat() if start_dt else None,
                "end": end_dt.isoformat() if end_dt else None,
                "location": location,
                "description": description,
            }
    except Exception as e:
        logger.warning(f"Failed to parse event: {e}")
    return None


async def fetch_upcoming_events(days_ahead: int = 7) -> list[dict]:
    """
    Fetch upcoming calendar events from iCloud CalDAV.
    Returns a list of event dicts for the next `days_ahead` days.
    """
    import asyncio

    def _sync_fetch():
        try:
            client = _get_client()
            principal = client.principal()
            calendars = principal.calendars()

            now = datetime.now(timezone.utc)
            end = now + timedelta(days=days_ahead)
            events = []
            for cal in calendars:
                cal_name = cal.get_display_name() or ""
                if CALDAV_ALLOWED and cal_name.lower().strip() not in CALDAV_ALLOWED:
                    logger.debug(f"Skipping calendar: {cal_name}")
                    continue
                try:
                    cal_events = cal.date_search(start=now, end=end, expand=True)
                    for e in cal_events:
                        parsed = _parse_event(e)
                        if parsed:
                            parsed["calendar"] = cal_name
                            events.append(parsed)
                except Exception as ce:
                    logger.warning(f"Calendar {cal_name} error: {ce}")
            events.sort(key=lambda e: e["start"] or "")
            return events
        except Exception as ex:
            logger.error(f"CalDAV fetch failed: {ex}")
            raise

    return await asyncio.get_event_loop().run_in_executor(None, _sync_fetch)


async def find_unindexed_events(events: list[dict]) -> list[dict]:
    """
    Compare calendar events against vector_memory.
    Returns events that don't have a matching memory entry (by UID or summary).
    """
    from atlas.db.vector_store import browse

    existing = await browse("vector_memory", limit=500)
    indexed_texts = {e["text"].lower() for e in existing}
    indexed_paths = {e.get("source_path", "") for e in existing}

    unindexed = []
    for event in events:
        uid_path = f"calendar/{event['uid']}"
        summary_lower = event["summary"].lower()
        already_stored = (
            uid_path in indexed_paths
            or any(summary_lower in t for t in indexed_texts)
        )
        if not already_stored:
            unindexed.append(event)
    return unindexed


async def index_calendar_event(event: dict, context_note: str = "") -> str:
    """
    Store a calendar event into vector_memory with source_path=calendar/<uid>.
    Optionally append a context note (from user clarification).
    """
    from atlas.db.vector_store import store

    text = f"Calendar event: '{event['summary']}' on {event['start']}"
    if event.get("location"):
        text += f" at {event['location']}"
    if context_note:
        text += f". Context: {context_note}"

    entry_id = await store(
        "vector_memory",
        text,
        source_type="event",
        source_path=f"calendar/{event['uid']}",
    )
    return entry_id


def _extract_class_code(summary: str) -> Optional[str]:
    """
    Extract class code from summary like 'EGE353 LABE2 S.436' -> 'EGE353'.
    Looks for uppercase letter followed by digits at the start.
    """
    import re
    if not summary:
        return None
    # Match patterns like EGE353, CS101, MAT-202 at the start
    match = re.match(r'^([A-Z]{2,4}\d{3}[A-Z]?)', summary.strip())
    return match.group(1) if match else None


async def store_class_pattern(class_code: str, context: str) -> str:
    """
    Store a class code pattern mapping (e.g., EGE353 -> Digital Signal Processing).
    This allows future events with the same code to be auto-enriched.
    """
    from atlas.db.vector_store import store, search

    # Check if pattern already exists
    try:
        existing = await search("vector_memory", f"class code {class_code} pattern", limit=5)
        for e in existing:
            if class_code.lower() in e.get("text", "").lower() and e.get("source_type") == "class_pattern":
                # Update: we'll store a new version with more context
                pass
    except Exception:
        pass

    text = f"Class code {class_code}: {context}"
    entry_id = await store(
        "vector_memory",
        text,
        source_type="class_pattern",
        source_path=f"pattern/{class_code}",
    )
    logger.info(f"Stored class pattern: {class_code} -> {context[:60]}")
    return entry_id


async def get_class_pattern(class_code: str) -> Optional[str]:
    """
    Retrieve stored context for a class code.
    Returns the full text if found, None otherwise.
    """
    from atlas.db.vector_store import search

    if not class_code:
        return None
    try:
        results = await search("vector_memory", f"class code {class_code}", limit=5)
        for r in results:
            if r.get("source_type") == "class_pattern" and class_code.lower() in r.get("text", "").lower():
                # Extract just the context part after the colon
                text = r.get("text", "")
                if ":" in text:
                    return text.split(":", 1)[1].strip()
                return text
    except Exception as e:
        logger.warning(f"Failed to get class pattern for {class_code}: {e}")
    return None


async def enrich_event_with_pattern(event: dict) -> dict:
    """
    Enrich a calendar event with stored class pattern context if available.
    Adds 'enriched_context' field to the event dict.
    """
    class_code = _extract_class_code(event.get("summary", ""))
    if class_code:
        pattern = await get_class_pattern(class_code)
        if pattern:
            event["class_code"] = class_code
            event["enriched_context"] = pattern
            event["enriched_summary"] = f"{event['summary']} ({pattern})"
        else:
            event["class_code"] = class_code
            event["enriched_context"] = None
    return event


async def index_calendar_event_with_pattern(event: dict, context_note: str = "") -> dict:
    """
    Store a calendar event and extract/store class pattern if context provided.
    Returns dict with entry_id and whether a pattern was extracted.
    """
    # Extract and store pattern if this is a class event
    class_code = _extract_class_code(event.get("summary", ""))
    pattern_stored = False

    if class_code and context_note:
        # Store the pattern for future use
        await store_class_pattern(class_code, context_note)
        pattern_stored = True

    # Store the individual event
    entry_id = await index_calendar_event(event, context_note)

    return {
        "entry_id": entry_id,
        "class_code": class_code,
        "pattern_stored": pattern_stored,
    }


async def get_all_class_patterns() -> list[dict]:
    """
    Retrieve all stored class code patterns.
    """
    from atlas.db.vector_store import browse, search

    try:
        # Search for class_pattern source_type
        results = await search("vector_memory", "class code pattern", limit=50)
        patterns = []
        for r in results:
            if r.get("source_type") == "class_pattern":
                text = r.get("text", "")
                if text.startswith("Class code ") and ":" in text:
                    code = text[11:text.find(":")].strip()
                    context = text[text.find(":")+1:].strip()
                    patterns.append({
                        "class_code": code,
                        "context": context,
                        "stored_at": r.get("created_at"),
                    })
        return patterns
    except Exception as e:
        logger.warning(f"Failed to get class patterns: {e}")
        return []
