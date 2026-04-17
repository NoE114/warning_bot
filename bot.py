import logging
import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("countdown-bot")


def get_env_int(name: str) -> int:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required env var: {name}")
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Env var {name} must be an integer") from exc


def get_env_date(name: str) -> date:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required env var: {name}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Env var {name} must be YYYY-MM-DD") from exc


TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = get_env_int("CHANNEL_ID")
TARGET_USER_ID = get_env_int("TARGET_USER_ID")
END_DATE = get_env_date("END_DATE")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")

if not TOKEN:
    raise ValueError("Missing required env var: DISCORD_TOKEN")

tz = ZoneInfo(TIMEZONE)

intents = discord.Intents.default()
bot = discord.Client(intents=intents)
scheduler = AsyncIOScheduler(timezone=tz)


def compute_days_left(today: date, end_date: date) -> int:
    return (end_date - today).days + 1


async def send_countdown() -> None:
    now = datetime.now(tz)
    today = now.date()

    if today > END_DATE:
        logger.info("End date passed; skipping message.")
        return

    days_left = compute_days_left(today, END_DATE)
    day_label = "day" if days_left == 1 else "days"
    message = f"<@{TARGET_USER_ID}> you have {days_left} {day_label} left"

    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(CHANNEL_ID)
        except discord.DiscordException as exc:
            logger.error("Failed to fetch channel %s: %s", CHANNEL_ID, exc)
            return

    try:
        await channel.send(message)
        logger.info("Sent message to channel %s", CHANNEL_ID)
    except discord.DiscordException as exc:
        logger.error("Failed to send message: %s", exc)


@bot.event
async def on_ready() -> None:
    logger.info("Logged in as %s", bot.user)
    if scheduler.running:
        return

    trigger = CronTrigger(hour=12, minute=0, timezone=tz)
    scheduler.add_job(send_countdown, trigger)
    scheduler.start()
    logger.info("Scheduler started for 12:00 %s", TIMEZONE)


if __name__ == "__main__":
    bot.run(TOKEN)
