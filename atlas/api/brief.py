"""
Morning Brief endpoint — GET /brief
Pulls goals, recent daily log, and key memories into a structured briefing.
"""
from datetime import date, timedelta
from fastapi import APIRouter
from atlas.db.vector_store import search, browse, search_recent
from atlas.services.groq_service import chat as groq_chat
from atlas.core.personality import HEIMDALL_BASE

router = APIRouter(prefix="/brief", tags=["brief"])

BRIEF_MODEL = "groq-llama4-scout"

MORNING_SYSTEM = HEIMDALL_BASE + """

CURRENT TASK: Deliver a morning briefing.
Be concise, sharp, and practical. Use Markdown.
Structure your response with these sections (only include sections that have content):

## Good morning, Nicholas
One sentence situational opener based on what you know.

## Today's Tasks
Bullet list of things the user said they needed to do — pulled from tasks/events/goals told to you in the last 48 hours. If something has a deadline today, flag it. If the list is empty, say so honestly.

## Goals in focus
Bullet list of active goals pulled from memory. Flag any that look stalled or unrealistic.

## Yesterday / Recent
What happened recently based on the daily log.

## On your mind
Ideas, plans, or things the user was thinking about recently.

## Gaps & Questions
What don't we know? What should the user clarify today?

## People
Any recent mentions of people worth keeping in mind.

Finish with one short, honest sentence — motivation without empty cheerleading. Keep the whole thing under 350 words."""

EVENING_SYSTEM = HEIMDALL_BASE + """

CURRENT TASK: Deliver an evening wrap-up brief.
Be reflective, honest, and grounding. Use Markdown.
Structure your response with these sections (only include sections that have content):

## Evening wrap-up
One sentence to close out the day.

## What happened today
Summary of today's activity, ingested content, and chat context.

## Progress on goals
How did today move the needle? What stalled?

## Things to carry forward
Unfinished items, open questions, or ideas worth noting for tomorrow.

## People & connections
Any people mentioned today worth following up on.

Finish with one honest reflection — not motivational fluff, just something true. Keep the whole thing under 300 words."""


@router.get("")
async def get_brief(type: str = "auto"):
    """
    type: "morning" | "evening" | "auto" (auto detects by server hour, UTC+8)
    """
    import asyncio
    from datetime import timezone, timedelta as td

    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    # Determine brief type
    if type == "auto":
        from datetime import datetime as dt
        utc_hour = dt.utcnow().hour
        sgt_hour = (utc_hour + 8) % 24
        # Evening = 17:00–03:59 SGT, Morning = 04:00–16:59 SGT
        brief_type = "evening" if sgt_hour >= 17 or sgt_hour < 4 else "morning"
    else:
        brief_type = type if type in ("morning", "evening") else "morning"

    system_prompt = MORNING_SYSTEM if brief_type == "morning" else EVENING_SYSTEM

    async def get_goals():
        try:
            return await search("vector_memory", "goal achieve want accomplish target", limit=5)
        except Exception:
            return []

    async def get_log_today():
        try:
            rows = await browse("vector_notes", limit=50)
            return [r for r in rows if today in r.get("source_path", "") or yesterday in r.get("source_path", "")]
        except Exception:
            return []

    async def get_people():
        try:
            return await search("vector_memory", "person friend colleague family", limit=4)
        except Exception:
            return []

    async def get_ideas():
        try:
            return await search("vector_memory", "idea plan project thinking about", limit=4)
        except Exception:
            return []

    async def get_preferences():
        try:
            return await search("vector_memory", "preference like dislike habit routine", limit=3)
        except Exception:
            return []

    async def get_recent_tasks():
        try:
            return await search_recent("vector_memory", "need to do task today tomorrow plan schedule", hours=48, limit=10)
        except Exception:
            return []

    async def get_calendar_events():
        try:
            from atlas.services.calendar_service import fetch_upcoming_events, enrich_event_with_pattern
            events = await fetch_upcoming_events(days_ahead=2)
            # Enrich with class patterns
            enriched = []
            for e in events:
                enriched.append(await enrich_event_with_pattern(e))
            return enriched
        except Exception:
            return []

    goals, log, people, ideas, prefs, recent_tasks, cal_events = await asyncio.gather(
        get_goals(), get_log_today(), get_people(), get_ideas(), get_preferences(), get_recent_tasks(), get_calendar_events()
    )

    def _fmt_cal_event(e):
        base = f"- {e.get('enriched_summary', e['summary'])} @ {e['start'][:16].replace('T', ' ')}"
        if e.get('location'):
            base += f" | Room: {e['location']}"
        if e.get('enriched_context'):
            base += f" | {e['enriched_context']}"
        elif e.get('class_code') and not e.get('enriched_context'):
            base += f" | [Unknown class: teach me what {e['class_code']} is]"
        return base

    sections = []
    if cal_events:
        sections.append("CALENDAR / SCHOOL SCHEDULE (next 2 days):\n" + "\n".join(_fmt_cal_event(e) for e in cal_events))
    if recent_tasks:
        sections.append("TASKS TOLD TO ME (last 48h):\n" + "\n".join(f"- {t['text']} [stored: {t.get('created_at', 'unknown')}]" for t in recent_tasks))
    if goals:
        sections.append("GOALS:\n" + "\n".join(f"- {g['text']}" for g in goals))
    if log:
        sections.append("RECENT ACTIVITY LOG:\n" + "\n".join(f"- {l['text']}" for l in log[-10:]))
    if people:
        sections.append("PEOPLE:\n" + "\n".join(f"- {p['text']}" for p in people))
    if ideas:
        sections.append("IDEAS & PLANS:\n" + "\n".join(f"- {i['text']}" for i in ideas))
    if prefs:
        sections.append("PREFERENCES:\n" + "\n".join(f"- {p['text']}" for p in prefs))

    context = "\n\n".join(sections) if sections else "No memories stored yet. This is a fresh start."

    user_msg = (
        f"Today is {today}. Here is my memory context:\n\n{context}\n\n"
        f"Generate my {'morning' if brief_type == 'morning' else 'evening'} brief."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]

    try:
        brief_text = await groq_chat(messages, model=BRIEF_MODEL)
    except Exception as e:
        brief_text = f"Could not generate brief: {e}"

    return {
        "date": today,
        "brief": brief_text,
        "brief_type": brief_type,
        "context_counts": {
            "goals": len(goals),
            "log_entries": len(log),
            "people": len(people),
            "ideas": len(ideas),
            "recent_tasks": len(recent_tasks),
            "calendar_events": len(cal_events),
        }
    }
