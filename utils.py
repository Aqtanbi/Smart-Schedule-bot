"""
utils.py — Reusable helper / formatting utilities.
Demonstrates: generators (yield), list comprehension, string formatting.
"""

from __future__ import annotations
from models import Schedule, Subject, DAYS


# ---------------------------------------------------------------------------
# Generator (advanced topic: iterators/generators)
# ---------------------------------------------------------------------------

def upcoming_today(schedule: Schedule, current_hour: int, current_minute: int):
    """
    Generator: yields subjects from today that haven't started yet.
    Demonstrates the 'yield' keyword (iterator/generator advanced topic).
    """
    for subject in schedule.get_today():
        h, m = map(int, subject.start_time.split(":"))
        if (h, m) > (current_hour, current_minute):
            yield subject


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_day_schedule(subjects: list[Subject], day: str) -> str:
    """Return a formatted Markdown block for one day's subjects."""
    if not subjects:
        return f"📅 *{day}*\n_No classes._"

    lines = [f"📅 *{day}*", ""]
    for i, s in enumerate(subjects, 1):
        line = f"{i}. ⏰ `{s.start_time}` — *{s.name}*"
        if s.room:
            line += f" (Room {s.room})"
        if s.teacher:
            line += f"\n    👨‍🏫 _{s.teacher}_"
        lines.append(line)
    return "\n".join(lines)


def format_full_week(schedule: Schedule) -> str:
    """Return a Markdown overview of the entire week."""
    if len(schedule) == 0:
        return "📭 Your schedule is empty. Use /add to add subjects."

    blocks: list[str] = []
    for day in DAYS:
        subjects = schedule.get_by_day(day)
        if subjects:
            blocks.append(format_day_schedule(subjects, day))

    return "\n\n".join(blocks)


def format_subject_list(subjects: list[Subject], header: str = "") -> str:
    """Short numbered list of subjects — used in search results."""
    if not subjects:
        return "_No subjects found._"

    lines = ([f"*{header}*", ""] if header else [])
    for s in subjects:
        line = f"• `{s.id}` *{s.name}* — {s.day} {s.start_time}"
        lines.append(line)
    return "\n".join(lines)


def format_today(schedule: Schedule) -> str:
    """Return today's schedule as a Markdown string."""
    from datetime import datetime
    today = datetime.now().strftime("%A")
    subjects = schedule.get_today()
    return format_day_schedule(subjects, f"Today ({today})")


def build_inline_keyboard_days(schedule: Schedule) -> list[dict]:
    """
    Return a list of dicts representing inline keyboard buttons for each day
    that has at least one subject. Used in bot.py to build aiogram keyboards.
    """
    return [
        {"text": day, "callback_data": f"day:{day}"}
        for day in schedule.unique_days()
    ]
