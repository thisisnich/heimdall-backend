"""
Date normalization utility — converts relative date terms to actual dates.
"""
import re
from datetime import date, timedelta

# Map of relative terms to days offset
RELATIVE_TERMS = {
    "tmr": 1,
    "tmrw": 1,
    "tomorrow": 1,
    "today": 0,
    "tonight": 0,
    "yesterday": -1,
    "next week": 7,
    "in a week": 7,
    "this week": 0,
}

DAY_TERMS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def normalize_date_terms(text: str, reference_date: date | None = None) -> str:
    """
    Replace relative date terms with actual ISO dates.
    
    Examples:
        "meet john tmr" -> "meet john 2026-05-13" (if today is 2026-05-12)
        "deadline tomorrow" -> "deadline 2026-05-13"
        "today's task" -> "2026-05-12 task"
    """
    if reference_date is None:
        reference_date = date.today()
    
    result = text
    text_lower = text.lower()
    
    # Handle relative terms (tmr, tomorrow, today, etc.)
    for term, days_offset in RELATIVE_TERMS.items():
        # Match whole word only (with word boundaries)
        pattern = r'\b' + re.escape(term) + r'\b'
        if re.search(pattern, text_lower):
            target_date = reference_date + timedelta(days=days_offset)
            date_str = target_date.isoformat()
            # Replace all occurrences case-insensitively
            result = re.sub(pattern, date_str, result, flags=re.IGNORECASE)
    
    # Handle "next <day>" pattern (e.g., "next monday")
    for day_name, day_num in DAY_TERMS.items():
        pattern = rf'\bnext {re.escape(day_name)}\b'
        if re.search(pattern, text_lower):
            # Calculate days until next occurrence
            today_num = reference_date.weekday()  # 0=Monday
            days_until = (day_num - today_num) % 7
            if days_until == 0:
                days_until = 7  # If today is that day, "next" means next week
            target_date = reference_date + timedelta(days=days_until)
            result = re.sub(pattern, target_date.isoformat(), result, flags=re.IGNORECASE)
    
    return result


def extract_date(text: str) -> date | None:
    """
    Extract a date from text containing relative terms.
    Returns the first date found, or None if no relative terms present.
    """
    text_lower = text.lower()
    
    for term, days_offset in RELATIVE_TERMS.items():
        if term in text_lower:
            return date.today() + timedelta(days=days_offset)
    
    for day_name, day_num in DAY_TERMS.items():
        if f"next {day_name}" in text_lower:
            today_num = date.today().weekday()
            days_until = (day_num - today_num) % 7
            if days_until == 0:
                days_until = 7
            return date.today() + timedelta(days=days_until)
    
    return None
