# Smart Schedule Bot 🗓

A Telegram bot that manages your class schedule and sends automatic reminders before each lesson.

## Features
- ➕ Add subjects step-by-step or with a quick one-liner
- 📅 View today's classes or the full week
- 🔍 Search and filter by day or subject name
- ✏️ Edit or delete any subject
- ⏰ Automatic reminders (default: 15 min before class)
- 📊 Export schedule to CSV
- 🔁 Recurring subject support

## Project Structure
```
smart_schedule_bot/
├── bot.py          # Telegram bot, all handlers, FSM dialogs
├── models.py       # Subject, RecurringSubject, Schedule (OOP + inheritance)
├── storage.py      # JSON persistence + CSV export
├── scheduler.py    # APScheduler — background reminder engine
├── validators.py   # Regex-based input validation
├── utils.py        # Generators, formatting helpers
├── data/
│   └── users.json  # Auto-created, stores all user schedules
├── tests/
│   └── test_models.py  # Unit tests (unittest)
├── requirements.txt
└── .env.example
```

## Setup

### 1. Clone and install dependencies
```bash
pip install -r requirements.txt
```

### 2. Create your bot
- Open Telegram → search **@BotFather**
- Send `/newbot` and follow the steps
- Copy the token

### 3. Configure environment
```bash
cp .env.example .env
# Open .env and paste your token:
# BOT_TOKEN=123456789:AAF...
```

### 4. Run the bot
```bash
python bot.py
```

### 5. Run tests
```bash
python -m pytest tests/ -v
```

## Bot Commands
| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | Command reference |
| `/add` | Add subject (wizard) |
| `/quick` | Quick add: `Name - Day - HH:MM` |
| `/today` | Today's classes |
| `/week` | Full week view |
| `/day` | Browse by weekday |
| `/search` | Search by name |
| `/remove` | Delete a subject |
| `/edit` | Edit a subject field |
| `/reminder` | Change reminder time |
| `/export` | Download CSV |

## Course Topics Covered
| Requirement | Where |
|-------------|-------|
| Variables, I/O, arithmetic/comparison | All files |
| Conditionals, loops | `bot.py`, `scheduler.py`, `utils.py` |
| Lists, tuples, sets, dicts | `models.py`, `validators.py` |
| File I/O (JSON + CSV) | `storage.py` |
| Functions and modules | All files |
| OOP: classes, inheritance, polymorphism | `models.py` — `Subject → RecurringSubject` |
| Exception handling + validation | `validators.py`, `storage.py`, `bot.py` |
| Advanced topic: APScheduler / asyncio | `scheduler.py` |
| Advanced topic: Regular expressions | `validators.py` |
| Advanced topic: Generators | `utils.py` — `upcoming_today()` |
| Unit testing | `tests/test_models.py` |
