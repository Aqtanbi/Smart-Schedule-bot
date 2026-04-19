"""
validators.py — Input validation and parsing.
Demonstrates: regular expressions, tuples, early-return pattern.
"""

import re
from models import DAYS

# ---------------------------------------------------------------------------
# Pre-compiled regex patterns (advanced topic: regular expressions)
# ---------------------------------------------------------------------------

TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")
NAME_RE = re.compile(r"^[\w\s\-\.\,]{2,60}$", re.UNICODE)

# Map common short forms → canonical day name
DAY_ALIASES: dict[str, str] = {
    alias: day
    for day in DAYS
    for alias in (day.lower(), day[:3].lower())
}

# ---------------------------------------------------------------------------
# Individual field validators
# (each returns a (success: bool, result: str) tuple)
# ---------------------------------------------------------------------------

def validate_time(raw: str) -> tuple[bool, str]:
    """
    Validate and normalise a time string.
    Returns (True, "HH:MM") or (False, error_message).
    """
    m = TIME_RE.match(raw.strip())
    if not m:
        return False, "⚠️ Invalid time. Use HH:MM — e.g. *09:00* or *14:30*"
    h, mn = int(m.group(1)), int(m.group(2))
    if not (0 <= h <= 23 and 0 <= mn <= 59):
        return False, "⚠️ Time out of range. Hours 0–23, minutes 0–59."
    return True, f"{h:02d}:{mn:02d}"


def validate_day(raw: str) -> tuple[bool, str]:
    """
    Validate and normalise a day string (accepts full name or 3-letter abbr).
    Returns (True, "Monday") or (False, error_message).
    """
    canonical = DAY_ALIASES.get(raw.strip().lower())
    if not canonical:
        abbrs = ", ".join(d[:3] for d in DAYS)
        return False, f"⚠️ Invalid day. Use full name or abbreviation:\n{abbrs}"
    return True, canonical


def validate_name(raw: str) -> tuple[bool, str]:
    """
    Validate a subject / teacher / room name.
    Returns (True, cleaned_name) or (False, error_message).
    """
    cleaned = raw.strip()
    if not NAME_RE.match(cleaned):
        return False, "⚠️ Name must be 2–60 characters (letters, digits, spaces, - . ,)"
    return True, cleaned


def validate_weeks(raw: str) -> tuple[bool, int]:
    """
    Validate the number of weeks for a recurring subject.
    Returns (True, weeks_int) or (False, error_message).
    """
    try:
        weeks = int(raw.strip())
        if not 1 <= weeks <= 52:
            raise ValueError
        return True, weeks
    except ValueError:
        return False, "⚠️ Weeks must be a number between 1 and 52."   # type: ignore[return-value]


def validate_reminder_minutes(raw: str) -> tuple[bool, int]:
    """
    Validate reminder lead time in minutes.
    Returns (True, minutes_int) or (False, error_message).
    """
    try:
        mins = int(raw.strip())
        if not 5 <= mins <= 60:
            raise ValueError
        return True, mins
    except ValueError:
        return False, "⚠️ Please enter a number between 5 and 60."   # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Quick-add parser
# ---------------------------------------------------------------------------

def parse_quick_add(text: str) -> tuple[bool, dict | str]:
    """
    Parse the quick-add shorthand:
        Name - Day - HH:MM [- Room [- Teacher]]

    Returns:
        (True,  {"name": ..., "day": ..., "start_time": ..., "room": ..., "teacher": ...})
        (False, error_message)
    """
    parts = [p.strip() for p in text.split("-")]
    if len(parts) < 3:
        return (
            False,
            "⚠️ Minimum format:\n`Name - Day - HH:MM`\n\nExample:\n`Math - Monday - 10:00`",
        )

    ok, name = validate_name(parts[0])
    if not ok:
        return False, name

    ok, day = validate_day(parts[1])
    if not ok:
        return False, day

    ok, t = validate_time(parts[2])
    if not ok:
        return False, t

    room = parts[3].strip() if len(parts) > 3 else ""
    teacher = parts[4].strip() if len(parts) > 4 else ""

    return True, {
        "name": name,
        "day": day,
        "start_time": t,
        "room": room,
        "teacher": teacher,
    }
