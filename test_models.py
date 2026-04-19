"""
tests/test_models.py — Unit tests.
Advanced topic: basic unit testing with unittest.

Run with:  python -m pytest tests/ -v
       or: python -m unittest discover tests
"""

import unittest
from models import Subject, RecurringSubject, Schedule, DAYS
from validators import (
    validate_time,
    validate_day,
    validate_name,
    parse_quick_add,
    validate_reminder_minutes,
)


# ===========================================================================
# Subject tests
# ===========================================================================

class TestSubject(unittest.TestCase):

    def setUp(self) -> None:
        self.subject = Subject("Math", "Monday", "10:00", "A101", "Dr. Smith")

    def test_creation(self) -> None:
        self.assertEqual(self.subject.name, "Math")
        self.assertEqual(self.subject.day, "Monday")
        self.assertEqual(self.subject.start_time, "10:00")
        self.assertIsNotNone(self.subject.id)
        self.assertEqual(len(self.subject.id), 8)

    def test_get_time(self) -> None:
        from datetime import time
        self.assertEqual(self.subject.get_time(), time(10, 0))

    def test_to_dict_and_from_dict(self) -> None:
        d = self.subject.to_dict()
        restored = Subject.from_dict(d)
        self.assertEqual(restored.name, self.subject.name)
        self.assertEqual(restored.id,   self.subject.id)
        self.assertEqual(restored.day,  self.subject.day)

    def test_equality(self) -> None:
        same = Subject("Math", "Monday", "10:00")
        different = Subject("Physics", "Monday", "10:00")
        self.assertEqual(self.subject, same)
        self.assertNotEqual(self.subject, different)

    def test_hash_in_set(self) -> None:
        same = Subject("Math", "Monday", "10:00")
        s = {self.subject, same}
        self.assertEqual(len(s), 1)

    def test_repr(self) -> None:
        r = repr(self.subject)
        self.assertIn("Math", r)
        self.assertIn("Monday", r)


# ===========================================================================
# RecurringSubject tests  (inheritance + polymorphism)
# ===========================================================================

class TestRecurringSubject(unittest.TestCase):

    def test_is_subclass(self) -> None:
        self.assertTrue(issubclass(RecurringSubject, Subject))

    def test_recurring_fields(self) -> None:
        rs = RecurringSubject("English", "Tuesday", "14:00", weeks=16)
        self.assertEqual(rs.weeks, 16)
        self.assertEqual(rs.subject_type, "recurring")

    def test_serialization_round_trip(self) -> None:
        rs = RecurringSubject("English", "Tuesday", "14:00", "B202", "Ms. Lee", weeks=14)
        d = rs.to_dict()
        restored = RecurringSubject.from_dict(d)
        self.assertEqual(restored.weeks, 14)
        self.assertEqual(restored.teacher, "Ms. Lee")
        self.assertEqual(restored.id, rs.id)

    def test_format_display_contains_weeks(self) -> None:
        rs = RecurringSubject("English", "Tuesday", "14:00", weeks=16)
        display = rs.format_display()
        self.assertIn("16", display)
        self.assertIn("week", display.lower())


# ===========================================================================
# Schedule tests
# ===========================================================================

class TestSchedule(unittest.TestCase):

    def setUp(self) -> None:
        self.schedule = Schedule(user_id=123)
        self.s1 = Subject("Math",    "Monday",    "10:00")
        self.s2 = Subject("English", "Tuesday",   "14:00")
        self.s3 = Subject("Physics", "Monday",    "12:00")

    def test_add_and_len(self) -> None:
        self.schedule.add_subject(self.s1)
        self.assertEqual(len(self.schedule), 1)

    def test_duplicate_raises(self) -> None:
        self.schedule.add_subject(self.s1)
        dup = Subject("Math", "Monday", "10:00")
        with self.assertRaises(ValueError):
            self.schedule.add_subject(dup)

    def test_remove(self) -> None:
        self.schedule.add_subject(self.s1)
        result = self.schedule.remove_subject(self.s1.id)
        self.assertTrue(result)
        self.assertEqual(len(self.schedule), 0)

    def test_remove_nonexistent(self) -> None:
        result = self.schedule.remove_subject("fakeid")
        self.assertFalse(result)

    def test_get_by_day_sorted(self) -> None:
        self.schedule.add_subject(self.s3)  # Monday 12:00
        self.schedule.add_subject(self.s1)  # Monday 10:00
        subjects = self.schedule.get_by_day("Monday")
        self.assertEqual(subjects[0].start_time, "10:00")
        self.assertEqual(subjects[1].start_time, "12:00")

    def test_get_by_name(self) -> None:
        self.schedule.add_subject(self.s1)
        self.schedule.add_subject(self.s2)
        results = self.schedule.get_by_name("mat")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Math")

    def test_get_by_id(self) -> None:
        self.schedule.add_subject(self.s1)
        found = self.schedule.get_by_id(self.s1.id)
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "Math")

    def test_get_by_id_missing(self) -> None:
        self.assertIsNone(self.schedule.get_by_id("nope"))

    def test_get_all_sorted_order(self) -> None:
        self.schedule.add_subject(self.s2)  # Tuesday
        self.schedule.add_subject(self.s3)  # Monday 12:00
        self.schedule.add_subject(self.s1)  # Monday 10:00
        sorted_list = self.schedule.get_all_sorted()
        self.assertEqual(sorted_list[0].day, "Monday")
        self.assertEqual(sorted_list[0].start_time, "10:00")
        self.assertEqual(sorted_list[-1].day, "Tuesday")

    def test_unique_days(self) -> None:
        self.schedule.add_subject(self.s1)
        self.schedule.add_subject(self.s2)
        self.schedule.add_subject(self.s3)
        days = self.schedule.unique_days()
        self.assertIn("Monday",  days)
        self.assertIn("Tuesday", days)
        self.assertNotIn("Friday", days)

    def test_iteration(self) -> None:
        self.schedule.add_subject(self.s1)
        self.schedule.add_subject(self.s2)
        names = [s.name for s in self.schedule]
        self.assertIn("Math",    names)
        self.assertIn("English", names)

    def test_serialization_round_trip(self) -> None:
        self.schedule.add_subject(self.s1)
        self.schedule.add_subject(RecurringSubject("Art", "Friday", "09:00", weeks=8))
        d = self.schedule.to_dict()
        restored = Schedule.from_dict(d)
        self.assertEqual(len(restored), 2)
        recurring = [s for s in restored if s.subject_type == "recurring"]
        self.assertEqual(len(recurring), 1)
        self.assertEqual(recurring[0].weeks, 8)


# ===========================================================================
# Validator tests
# ===========================================================================

class TestValidateTime(unittest.TestCase):

    def test_valid_times(self) -> None:
        cases = [
            ("09:00", "09:00"),
            ("9:00",  "09:00"),
            ("23:59", "23:59"),
            ("00:00", "00:00"),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                ok, result = validate_time(raw)
                self.assertTrue(ok)
                self.assertEqual(result, expected)

    def test_invalid_times(self) -> None:
        for raw in ("25:00", "10:60", "abc", "10", "10:0a"):
            with self.subTest(raw=raw):
                ok, _ = validate_time(raw)
                self.assertFalse(ok)


class TestValidateDay(unittest.TestCase):

    def test_full_names(self) -> None:
        for day in DAYS:
            ok, result = validate_day(day)
            self.assertTrue(ok)
            self.assertEqual(result, day)

    def test_abbreviations(self) -> None:
        ok, result = validate_day("mon")
        self.assertTrue(ok)
        self.assertEqual(result, "Monday")

    def test_case_insensitive(self) -> None:
        ok, result = validate_day("FRIDAY")
        self.assertTrue(ok)
        self.assertEqual(result, "Friday")

    def test_invalid(self) -> None:
        ok, _ = validate_day("Funday")
        self.assertFalse(ok)


class TestValidateName(unittest.TestCase):

    def test_valid(self) -> None:
        for name in ("Math", "English 101", "Dr. Smith", "Info-Tech"):
            ok, _ = validate_name(name)
            self.assertTrue(ok, f"Expected valid: {name!r}")

    def test_too_short(self) -> None:
        ok, _ = validate_name("X")
        self.assertFalse(ok)


class TestParseQuickAdd(unittest.TestCase):

    def test_minimal(self) -> None:
        ok, data = parse_quick_add("Math - Monday - 10:00")
        self.assertTrue(ok)
        self.assertEqual(data["name"],       "Math")
        self.assertEqual(data["day"],        "Monday")
        self.assertEqual(data["start_time"], "10:00")
        self.assertEqual(data["room"],       "")
        self.assertEqual(data["teacher"],    "")

    def test_full(self) -> None:
        ok, data = parse_quick_add("Physics - Friday - 14:00 - Lab3 - Prof. Lee")
        self.assertTrue(ok)
        self.assertEqual(data["room"],    "Lab3")
        self.assertEqual(data["teacher"], "Prof. Lee")

    def test_missing_parts(self) -> None:
        ok, _ = parse_quick_add("Math - Monday")
        self.assertFalse(ok)

    def test_invalid_day(self) -> None:
        ok, _ = parse_quick_add("Math - Funday - 10:00")
        self.assertFalse(ok)

    def test_invalid_time(self) -> None:
        ok, _ = parse_quick_add("Math - Monday - 99:00")
        self.assertFalse(ok)


class TestValidateReminderMinutes(unittest.TestCase):

    def test_valid(self) -> None:
        for val in ("5", "15", "30", "60"):
            ok, result = validate_reminder_minutes(val)
            self.assertTrue(ok)
            self.assertEqual(result, int(val))

    def test_out_of_range(self) -> None:
        for val in ("4", "61", "0", "-1"):
            ok, _ = validate_reminder_minutes(val)
            self.assertFalse(ok)

    def test_non_numeric(self) -> None:
        ok, _ = validate_reminder_minutes("abc")
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
