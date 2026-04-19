"""
storage.py — JSON persistence layer.
Demonstrates: file I/O, exception handling, pathlib, CSV export.
"""

import csv
import io
import json
import logging
from pathlib import Path

from models import Schedule, Subject

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
USERS_FILE = DATA_DIR / "users.json"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not USERS_FILE.exists():
        USERS_FILE.write_text("{}", encoding="utf-8")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_all_schedules() -> dict[int, Schedule]:
    """Load every user's schedule from JSON. Returns empty dict on error."""
    _ensure_data_dir()
    try:
        raw: dict = json.loads(USERS_FILE.read_text(encoding="utf-8"))
        return {int(uid): Schedule.from_dict(data) for uid, data in raw.items()}
    except json.JSONDecodeError as exc:
        logger.error("JSON decode error: %s", exc)
        return {}
    except (KeyError, TypeError) as exc:
        logger.error("Data structure error: %s", exc)
        return {}


def save_all_schedules(schedules: dict[int, Schedule]) -> None:
    """Persist all schedules to JSON. Raises OSError on failure."""
    _ensure_data_dir()
    try:
        raw = {str(uid): sched.to_dict() for uid, sched in schedules.items()}
        USERS_FILE.write_text(
            json.dumps(raw, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.error("Failed to write schedules: %s", exc)
        raise


def load_schedule(user_id: int) -> Schedule:
    """Load a single user's schedule (returns empty Schedule if not found)."""
    return load_all_schedules().get(user_id, Schedule(user_id))


def save_schedule(schedule: Schedule) -> None:
    """Save / update a single user's schedule."""
    schedules = load_all_schedules()
    schedules[schedule.user_id] = schedule
    save_all_schedules(schedules)


# ---------------------------------------------------------------------------
# CSV export (bonus feature)
# ---------------------------------------------------------------------------

def export_schedule_csv(schedule: Schedule) -> str:
    """
    Return the schedule as a CSV string.
    Uses csv.writer to handle commas/quotes in field values correctly.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Day", "Time", "Room", "Teacher", "Type"])
    for subject in schedule.get_all_sorted():
        writer.writerow([
            subject.name,
            subject.day,
            subject.start_time,
            subject.room,
            subject.teacher,
            subject.subject_type,
        ])
    return output.getvalue()


def export_schedule_json(schedule: Schedule) -> str:
    """Return the schedule as a pretty-printed JSON string."""
    return json.dumps(schedule.to_dict(), indent=2, ensure_ascii=False)
