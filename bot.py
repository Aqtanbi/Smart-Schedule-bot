"""
bot.py — Telegram bot entry point.
Uses aiogram 3.x with FSM (Finite State Machine) for multi-step dialogs.

Commands:
    /start    — Welcome message
    /help     — Command reference
    /add      — Add a subject (step-by-step wizard)
    /quick    — Quick add: Name - Day - HH:MM [- Room [- Teacher]]
    /today    — Today's schedule
    /week     — Full week schedule
    /day      — Browse by weekday
    /search   — Search by subject name
    /remove   — Remove a subject by ID
    /edit     — Edit a subject field
    /reminder — Change reminder lead time
    /export   — Download schedule as CSV
"""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import storage as db
from models import RecurringSubject, Subject
from scheduler import ReminderScheduler
from utils import format_full_week, format_today, format_subject_list, format_day_schedule
from validators import (
    parse_quick_add,
    validate_day,
    validate_name,
    validate_reminder_minutes,
    validate_time,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FSM state groups
# ---------------------------------------------------------------------------

class AddSubjectSG(StatesGroup):
    name       = State()
    day        = State()
    start_time = State()
    room       = State()
    teacher    = State()
    recurring  = State()
    weeks      = State()


class EditSubjectSG(StatesGroup):
    subject_id = State()
    field      = State()
    value      = State()


class RemoveSG(StatesGroup):
    subject_id = State()


class ReminderSG(StatesGroup):
    minutes = State()


class SearchSG(StatesGroup):
    keyword = State()


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = Router()


# ---- /start ----

@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 *Welcome to Smart Schedule Bot!*\n\n"
        "I keep your class schedule and remind you *15 minutes* before each lesson.\n\n"
        "Use /help to see all commands.",
        parse_mode=ParseMode.MARKDOWN,
    )


# ---- /help ----

@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    text = (
        "*📖 Commands*\n\n"
        "/add — Add a subject (step-by-step)\n"
        "/quick — Quick add: `Name - Day - HH:MM`\n"
        "/today — Today's classes\n"
        "/week — Full week schedule\n"
        "/day — Browse by weekday\n"
        "/search — Search by name\n"
        "/remove — Remove a subject\n"
        "/edit — Edit a subject\n"
        "/reminder — Change reminder time\n"
        "/export — Download schedule as CSV"
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


# ================================================================
# /add — step-by-step wizard
# ================================================================

@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext) -> None:
    await state.set_state(AddSubjectSG.name)
    await message.answer(
        "➕ *Add a new subject*\n\nStep 1/5 — Enter the *subject name*:",
        parse_mode=ParseMode.MARKDOWN,
    )


@router.message(AddSubjectSG.name)
async def add_name(message: Message, state: FSMContext) -> None:
    ok, result = validate_name(message.text or "")
    if not ok:
        await message.answer(result, parse_mode=ParseMode.MARKDOWN)
        return
    await state.update_data(name=result)
    await state.set_state(AddSubjectSG.day)
    await message.answer(
        "Step 2/5 — Enter the *day of the week*:\n_e.g. Monday or Mon_",
        parse_mode=ParseMode.MARKDOWN,
    )


@router.message(AddSubjectSG.day)
async def add_day(message: Message, state: FSMContext) -> None:
    ok, result = validate_day(message.text or "")
    if not ok:
        await message.answer(result, parse_mode=ParseMode.MARKDOWN)
        return
    await state.update_data(day=result)
    await state.set_state(AddSubjectSG.start_time)
    await message.answer(
        "Step 3/5 — Enter *start time* in HH:MM format:\n_e.g. 09:00_",
        parse_mode=ParseMode.MARKDOWN,
    )


@router.message(AddSubjectSG.start_time)
async def add_time(message: Message, state: FSMContext) -> None:
    ok, result = validate_time(message.text or "")
    if not ok:
        await message.answer(result, parse_mode=ParseMode.MARKDOWN)
        return
    await state.update_data(start_time=result)
    await state.set_state(AddSubjectSG.room)
    await message.answer(
        "Step 4/5 — Enter *room/location* (or send `-` to skip):",
        parse_mode=ParseMode.MARKDOWN,
    )


@router.message(AddSubjectSG.room)
async def add_room(message: Message, state: FSMContext) -> None:
    room = "" if (message.text or "").strip() == "-" else (message.text or "").strip()
    await state.update_data(room=room)
    await state.set_state(AddSubjectSG.teacher)
    await message.answer(
        "Step 5/5 — Enter *teacher name* (or send `-` to skip):",
        parse_mode=ParseMode.MARKDOWN,
    )


@router.message(AddSubjectSG.teacher)
async def add_teacher(message: Message, state: FSMContext) -> None:
    teacher = "" if (message.text or "").strip() == "-" else (message.text or "").strip()
    await state.update_data(teacher=teacher)
    await state.set_state(AddSubjectSG.recurring)

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔁 Recurring (every week)", callback_data="recurring:yes"),
        InlineKeyboardButton(text="📌 One-time",               callback_data="recurring:no"),
    ]])
    await message.answer("Is this subject recurring or one-time?", reply_markup=kb)


@router.callback_query(AddSubjectSG.recurring, F.data.startswith("recurring:"))
async def add_recurring_choice(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    choice = call.data.split(":")[1]
    await state.update_data(recurring=choice)

    if choice == "yes":
        await state.set_state(AddSubjectSG.weeks)
        await call.message.answer(
            "How many weeks does this subject last? _(1–52)_",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await _finish_add(call.message, state)


@router.message(AddSubjectSG.weeks)
async def add_weeks(message: Message, state: FSMContext) -> None:
    try:
        weeks = int((message.text or "").strip())
        if not 1 <= weeks <= 52:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Please enter a number between 1 and 52.")
        return
    await state.update_data(weeks=weeks)
    await _finish_add(message, state)


async def _finish_add(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()

    user_id = message.chat.id
    schedule = db.load_schedule(user_id)

    try:
        if data.get("recurring") == "yes":
            subject = RecurringSubject(
                data["name"], data["day"], data["start_time"],
                data.get("room", ""), data.get("teacher", ""),
                data.get("weeks", 16),
            )
        else:
            subject = Subject(
                data["name"], data["day"], data["start_time"],
                data.get("room", ""), data.get("teacher", ""),
            )
        schedule.add_subject(subject)
        db.save_schedule(schedule)

        await message.answer(
            f"✅ *Subject added!*\n\n{subject.format_display()}",
            parse_mode=ParseMode.MARKDOWN,
        )
    except ValueError as exc:
        await message.answer(f"⚠️ {exc}", parse_mode=ParseMode.MARKDOWN)


# ================================================================
# /quick — one-line add
# ================================================================

@router.message(Command("quick"))
async def cmd_quick(message: Message) -> None:
    text = (message.text or "").removeprefix("/quick").strip()
    if not text:
        await message.answer(
            "📝 Usage:\n`/quick Name - Day - HH:MM [- Room [- Teacher]]`\n\n"
            "Example:\n`/quick Math - Monday - 10:00 - A201 - Dr. Smith`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    ok, result = parse_quick_add(text)
    if not ok:
        await message.answer(result, parse_mode=ParseMode.MARKDOWN)
        return

    user_id = message.chat.id
    schedule = db.load_schedule(user_id)

    try:
        subject = Subject(**result)
        schedule.add_subject(subject)
        db.save_schedule(schedule)
        await message.answer(
            f"✅ *Subject added!*\n\n{subject.format_display()}",
            parse_mode=ParseMode.MARKDOWN,
        )
    except ValueError as exc:
        await message.answer(f"⚠️ {exc}", parse_mode=ParseMode.MARKDOWN)


# ================================================================
# /today  /week
# ================================================================

@router.message(Command("today"))
async def cmd_today(message: Message) -> None:
    schedule = db.load_schedule(message.chat.id)
    await message.answer(format_today(schedule), parse_mode=ParseMode.MARKDOWN)


@router.message(Command("week"))
async def cmd_week(message: Message) -> None:
    schedule = db.load_schedule(message.chat.id)
    await message.answer(format_full_week(schedule), parse_mode=ParseMode.MARKDOWN)


# ================================================================
# /day — browse by weekday via inline keyboard
# ================================================================

@router.message(Command("day"))
async def cmd_day(message: Message) -> None:
    from models import DAYS
    buttons = [
        [InlineKeyboardButton(text=day, callback_data=f"day:{day}")]
        for day in DAYS
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Choose a day:", reply_markup=kb)


@router.callback_query(F.data.startswith("day:"))
async def cb_day(call: CallbackQuery) -> None:
    await call.answer()
    day = call.data.split(":")[1]
    schedule = db.load_schedule(call.from_user.id)
    subjects = schedule.get_by_day(day)
    await call.message.answer(
        format_day_schedule(subjects, day),
        parse_mode=ParseMode.MARKDOWN,
    )


# ================================================================
# /search
# ================================================================

@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext) -> None:
    await state.set_state(SearchSG.keyword)
    await message.answer("🔍 Enter a keyword to search for a subject:")


@router.message(SearchSG.keyword)
async def do_search(message: Message, state: FSMContext) -> None:
    await state.clear()
    keyword = (message.text or "").strip()
    schedule = db.load_schedule(message.chat.id)
    results = schedule.get_by_name(keyword)
    await message.answer(
        format_subject_list(results, header=f'Results for "{keyword}"'),
        parse_mode=ParseMode.MARKDOWN,
    )


# ================================================================
# /remove
# ================================================================

@router.message(Command("remove"))
async def cmd_remove(message: Message, state: FSMContext) -> None:
    schedule = db.load_schedule(message.chat.id)
    if len(schedule) == 0:
        await message.answer("📭 Your schedule is empty.")
        return
    await state.set_state(RemoveSG.subject_id)
    listing = format_subject_list(schedule.get_all_sorted(), header="Your subjects")
    await message.answer(
        f"{listing}\n\n🗑 Send the *ID* of the subject to remove:",
        parse_mode=ParseMode.MARKDOWN,
    )


@router.message(RemoveSG.subject_id)
async def do_remove(message: Message, state: FSMContext) -> None:
    await state.clear()
    subject_id = (message.text or "").strip()
    schedule = db.load_schedule(message.chat.id)
    if schedule.remove_subject(subject_id):
        db.save_schedule(schedule)
        await message.answer(f"✅ Subject `{subject_id}` removed.", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.answer(f"⚠️ No subject with ID `{subject_id}` found.", parse_mode=ParseMode.MARKDOWN)


# ================================================================
# /edit
# ================================================================

EDITABLE_FIELDS: dict[str, str] = {
    "name": "Subject name",
    "day": "Day",
    "start_time": "Start time (HH:MM)",
    "room": "Room",
    "teacher": "Teacher",
}


@router.message(Command("edit"))
async def cmd_edit(message: Message, state: FSMContext) -> None:
    schedule = db.load_schedule(message.chat.id)
    if len(schedule) == 0:
        await message.answer("📭 Your schedule is empty.")
        return
    await state.set_state(EditSubjectSG.subject_id)
    listing = format_subject_list(schedule.get_all_sorted(), header="Your subjects")
    await message.answer(
        f"{listing}\n\nEnter the *ID* of the subject to edit:",
        parse_mode=ParseMode.MARKDOWN,
    )


@router.message(EditSubjectSG.subject_id)
async def edit_choose_field(message: Message, state: FSMContext) -> None:
    subject_id = (message.text or "").strip()
    schedule = db.load_schedule(message.chat.id)
    subject = schedule.get_by_id(subject_id)
    if subject is None:
        await message.answer(f"⚠️ No subject with ID `{subject_id}`.", parse_mode=ParseMode.MARKDOWN)
        return

    await state.update_data(subject_id=subject_id)
    await state.set_state(EditSubjectSG.field)

    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"editfield:{key}")]
        for key, label in EDITABLE_FIELDS.items()
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        f"Editing *{subject.name}*. Which field?",
        reply_markup=kb,
        parse_mode=ParseMode.MARKDOWN,
    )


@router.callback_query(EditSubjectSG.field, F.data.startswith("editfield:"))
async def edit_choose_value(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    field = call.data.split(":")[1]
    await state.update_data(field=field)
    await state.set_state(EditSubjectSG.value)
    prompt = EDITABLE_FIELDS.get(field, field)
    await call.message.answer(f"Enter new value for *{prompt}*:", parse_mode=ParseMode.MARKDOWN)


@router.message(EditSubjectSG.value)
async def edit_apply(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()

    field = data["field"]
    new_value = (message.text or "").strip()

    # Validate depending on field
    if field == "day":
        ok, new_value = validate_day(new_value)
    elif field == "start_time":
        ok, new_value = validate_time(new_value)
    elif field == "name":
        ok, new_value = validate_name(new_value)
    else:
        ok = True  # room / teacher: free text

    if not ok:
        await message.answer(new_value, parse_mode=ParseMode.MARKDOWN)
        return

    schedule = db.load_schedule(message.chat.id)
    if schedule.update_subject(data["subject_id"], **{field: new_value}):
        db.save_schedule(schedule)
        await message.answer(f"✅ *{field}* updated to `{new_value}`.", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.answer("⚠️ Subject not found.", parse_mode=ParseMode.MARKDOWN)


# ================================================================
# /reminder — change lead time
# ================================================================

@router.message(Command("reminder"))
async def cmd_reminder(message: Message, state: FSMContext) -> None:
    await state.set_state(ReminderSG.minutes)
    await message.answer(
        "⏰ How many minutes *before* each class should I remind you? (5–60)",
        parse_mode=ParseMode.MARKDOWN,
    )


@router.message(ReminderSG.minutes)
async def do_set_reminder(message: Message, state: FSMContext) -> None:
    await state.clear()
    ok, result = validate_reminder_minutes(message.text or "")
    if not ok:
        await message.answer(result, parse_mode=ParseMode.MARKDOWN)
        return

    # Access bot-level scheduler stored in dispatcher workflow data
    reminder_scheduler: ReminderScheduler = message.bot.reminder_scheduler  # type: ignore[attr-defined]
    reminder_scheduler.set_reminder_minutes(result)
    await message.answer(
        f"✅ I'll remind you *{result} minutes* before each class.",
        parse_mode=ParseMode.MARKDOWN,
    )


# ================================================================
# /export
# ================================================================

@router.message(Command("export"))
async def cmd_export(message: Message) -> None:
    schedule = db.load_schedule(message.chat.id)
    if len(schedule) == 0:
        await message.answer("📭 Your schedule is empty.")
        return

    csv_data = db.export_schedule_csv(schedule).encode("utf-8")
    file = BufferedInputFile(csv_data, filename="my_schedule.csv")
    await message.answer_document(file, caption="📊 Here's your schedule as CSV.")


# ================================================================
# Main entry point
# ================================================================

async def main() -> None:
    token = "8784972658:AAFDwzvnKzxmlpFaOqLEGkyJycoAqzUWGIE"

    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    # Attach scheduler to bot so handlers can access it
    reminder_scheduler = ReminderScheduler(
        bot=bot,
        schedule_loader=db.load_all_schedules,
        timezone="Asia/Almaty",
    )
    bot.reminder_scheduler = reminder_scheduler  # type: ignore[attr-defined]
    reminder_scheduler.start()

    logger.info("Bot starting...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        reminder_scheduler.stop()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
