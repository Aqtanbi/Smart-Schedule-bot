"""
models.py — Core OOP layer: Subject, RecurringSubject, Schedule
Demonstrates: classes, inheritance, polymorphism, dunder methods,
              data structures (list, dict, set, tuple)
"""

from __future__ import annotations
import uuid
from datetime import datetime, time
from typing import Optional

# Ordered list of weekdays (used for sorting)
DAYS: list[str] = [
    "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday", "Saturday", "Sunday"
]


# ---------------------------------------------------------------------------
# Base entity: Subject
# ---------------------------------------------------------------------------

class Subject:
    """Represents one class/lesson in a schedule."""

    def __init__(
        self,
        name: str,
        day: str,
        start_time: str,
        room: str = "",
        teacher: str = "",
    ) -> None:
        self.id: str = str(uuid.uuid4())[:8]
        self.name: str = name
        self.day: str = day          # e.g. "Monday"
        self.start_time: str = start_time  # e.g. "10:00"
        self.room: str = room
        self.teacher: str = teacher
        self.subject_type: str = "regular"

    # ---- time helpers ----

    def get_time(self) -> time:
        """Return start_time as a datetime.time object for easy comparison."""
        h, m = map(int, self.start_time.split(":"))
        return time(h, m)

    # ---- serialization ----

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subject_type": self.subject_type,
            "name": self.name,
            "day": self.day,
            "start_time": self.start_time,
            "room": self.room,
            "teacher": self.teacher,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Subject:
        obj = cls(
            data["name"],
            data["day"],
            data["start_time"],
            data.get("room", ""),
            data.get("teacher", ""),
        )
        obj.id = data["id"]
        return obj

    # ---- display ----

    def format_display(self) -> str:
        """Human-readable block for Telegram (Markdown)."""
        lines = [
            f"📚 *{self.name}*",
            f"🗓 {self.day}  |  ⏰ {self.start_time}",
        ]
        if self.room:
            lines.append(f"🚪 Room: {self.room}")
        if self.teacher:
            lines.append(f"👨‍🏫 {self.teacher}")
        lines.append(f"🆔 `{self.id}`")
        return "\n".join(lines)

    # ---- dunder methods ----

    def __repr__(self) -> str:
        return f"Subject(id={self.id!r}, name={self.name!r}, day={self.day!r}, time={self.start_time!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Subject):
            return NotImplemented
        return (
            self.name.lower() == other.name.lower()
            and self.day == other.day
            and self.start_time == other.start_time
        )

    def __hash__(self) -> int:
        return hash((self.name.lower(), self.day, self.start_time))


# ---------------------------------------------------------------------------
# Derived entity: RecurringSubject  (demonstrates inheritance + polymorphism)
# ---------------------------------------------------------------------------

class RecurringSubject(Subject):
    """
    A subject that explicitly spans N weeks of a semester.
    Overrides format_display() — polymorphism in action.
    """

    def __init__(
        self,
        name: str,
        day: str,
        start_time: str,
        room: str = "",
        teacher: str = "",
        weeks: int = 16,
    ) -> None:
        super().__init__(name, day, start_time, room, teacher)
        self.weeks: int = weeks
        self.subject_type = "recurring"

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["weeks"] = self.weeks
        return d

    @classmethod
    def from_dict(cls, data: dict) -> RecurringSubject:
        obj = cls(
            data["name"],
            data["day"],
            data["start_time"],
            data.get("room", ""),
            data.get("teacher", ""),
            data.get("weeks", 16),
        )
        obj.id = data["id"]
        return obj

    def format_display(self) -> str:          # polymorphic override
        base = super().format_display()
        return base + f"\n🔁 Every week ({self.weeks} wks)"


# ---------------------------------------------------------------------------
# Aggregate: Schedule
# ---------------------------------------------------------------------------

class Schedule:
    """
    Manages all subjects for one Telegram user.
    Uses: list (ordered subjects), set (duplicate detection), dict (serialization)
    """

    def __init__(self, user_id: int) -> None:
        self.user_id: int = user_id
        self._subjects: list[Subject] = []

    # ---- mutation ----

    def add_subject(self, subject: Subject) -> None:
        """Add a subject; raise ValueError on duplicate."""
        existing: set[tuple] = {
            (s.name.lower(), s.day, s.start_time) for s in self._subjects
        }
        key = (subject.name.lower(), subject.day, subject.start_time)
        if key in existing:
            raise ValueError(
                f"'{subject.name}' already exists on {subject.day} at {subject.start_time}"
            )
        self._subjects.append(subject)

    def remove_subject(self, subject_id: str) -> bool:
        """Remove by short ID. Returns True if something was deleted."""
        before = len(self._subjects)
        self._subjects = [s for s in self._subjects if s.id != subject_id]
        return len(self._subjects) < before

    def update_subject(self, subject_id: str, **kwargs) -> bool:
        """Update fields of an existing subject by ID."""
        subject = self.get_by_id(subject_id)
        if subject is None:
            return False
        allowed = {"name", "day", "start_time", "room", "teacher"}
        for key, value in kwargs.items():
            if key in allowed:
                setattr(subject, key, value)
        return True

    # ---- queries ----

    def get_by_id(self, subject_id: str) -> Optional[Subject]:
        for s in self._subjects:
            if s.id == subject_id:
                return s
        return None

    def get_by_day(self, day: str) -> list[Subject]:
        """Return subjects for a specific weekday, sorted by time."""
        return sorted(
            [s for s in self._subjects if s.day.lower() == day.lower()],
            key=lambda s: s.get_time(),
        )

    def get_today(self) -> list[Subject]:
        today = datetime.now().strftime("%A")
        return self.get_by_day(today)

    def get_by_name(self, keyword: str) -> list[Subject]:
        return [s for s in self._subjects if keyword.lower() in s.name.lower()]

    def get_all_sorted(self) -> list[Subject]:
        """Return all subjects sorted by weekday order then by time."""
        day_index: dict[str, int] = {d: i for i, d in enumerate(DAYS)}
        return sorted(
            self._subjects,
            key=lambda s: (day_index.get(s.day, 99), s.get_time()),
        )

    def unique_days(self) -> list[str]:
        """Return days that have at least one subject, in weekday order."""
        day_set: set[str] = {s.day for s in self._subjects}
        return [d for d in DAYS if d in day_set]

    # ---- serialization ----

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "subjects": [s.to_dict() for s in self._subjects],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Schedule:
        schedule = cls(data["user_id"])
        for sd in data.get("subjects", []):
            if sd.get("subject_type") == "recurring":
                schedule._subjects.append(RecurringSubject.from_dict(sd))
            else:
                schedule._subjects.append(Subject.from_dict(sd))
        return schedule

    # ---- dunder methods ----

    def __len__(self) -> int:
        return len(self._subjects)

    def __iter__(self):
        return iter(self._subjects)

    def __repr__(self) -> str:
        return f"Schedule(user_id={self.user_id}, subjects={len(self._subjects)})"
