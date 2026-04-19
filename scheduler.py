"""
scheduler.py — Background reminder engine.
Advanced topic: async scheduling with APScheduler + asyncio.
"""

import logging
from datetime import datetime, timedelta
from typing import Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """
    Runs a background job every minute.
    For each user, checks whether any subject starts in ~REMINDER_MINUTES minutes
    and sends a Telegram notification if so.

    Demonstrates: asyncio, APScheduler, dependency injection (bot + loader).
    """

    DEFAULT_MINUTES: int = 15

    def __init__(self, bot, schedule_loader: Callable, timezone: str = "Asia/Almaty") -> None:
        """
        Args:
            bot:             aiogram Bot instance used to send messages.
            schedule_loader: zero-arg callable that returns dict[int, Schedule].
            timezone:        timezone string for the scheduler.
        """
        self._bot = bot
        self._loader = schedule_loader
        self._reminder_minutes: int = self.DEFAULT_MINUTES
        self._scheduler = AsyncIOScheduler(timezone=timezone)

    # ------------------------------------------------------------------ #
    # Public controls                                                      #
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        self._scheduler.add_job(
            self._tick,
            trigger=CronTrigger(minute="*"),   # runs every minute
            id="reminder_tick",
            replace_existing=True,
            misfire_grace_time=30,
        )
        self._scheduler.start()
        logger.info("ReminderScheduler started (lead time: %d min)", self._reminder_minutes)

    def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        logger.info("ReminderScheduler stopped")

    def set_reminder_minutes(self, minutes: int) -> None:
        """Change lead time globally. Raises ValueError for out-of-range input."""
        if not 5 <= minutes <= 60:
            raise ValueError("Reminder lead time must be between 5 and 60 minutes.")
        self._reminder_minutes = minutes
        logger.info("Reminder lead time updated to %d min", minutes)

    @property
    def reminder_minutes(self) -> int:
        return self._reminder_minutes

    # ------------------------------------------------------------------ #
    # Internal tick                                                        #
    # ------------------------------------------------------------------ #

    async def _tick(self) -> None:
        """Called every minute by the scheduler."""
        now = datetime.now()
        today = now.strftime("%A")

        try:
            schedules = self._loader()
        except Exception as exc:
            logger.error("Could not load schedules: %s", exc)
            return

        for user_id, schedule in schedules.items():
            for subject in schedule.get_by_day(today):
                h, m = map(int, subject.start_time.split(":"))
                class_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
                diff_minutes = (class_dt - now).total_seconds() / 60

                # Fire when the class is within the target window (±30 seconds)
                if self._reminder_minutes - 0.5 <= diff_minutes <= self._reminder_minutes + 0.5:
                    await self._send_reminder(user_id, subject)

    async def _send_reminder(self, user_id: int, subject) -> None:
        """Build and send the reminder message."""
        lines = [
            f"⏰ *Reminder — {self._reminder_minutes} min to go!*",
            "",
            f"📚 *{subject.name}* starts at *{subject.start_time}*",
        ]
        if subject.room:
            lines.append(f"🚪 Room: {subject.room}")
        if subject.teacher:
            lines.append(f"👨‍🏫 {subject.teacher}")
        lines.append("\nGood luck! 🍀")

        try:
            await self._bot.send_message(user_id, "\n".join(lines), parse_mode="Markdown")
            logger.debug("Reminder sent → user %s, subject '%s'", user_id, subject.name)
        except Exception as exc:
            logger.warning("Failed to send reminder to %s: %s", user_id, exc)
