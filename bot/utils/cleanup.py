"""
Temporary file cleanup worker.
"""
import os
import time
import asyncio
import logging

from bot.config import DOWNLOAD_DIR, CLEANUP_MAX_AGE_SECONDS, CLEANUP_INTERVAL_SECONDS

logger = logging.getLogger(__name__)


def cleanup_download_dir_once():
    """Remove old files from download directory."""
    try:
        now = time.time()
        for name in os.listdir(DOWNLOAD_DIR):
            path = os.path.join(DOWNLOAD_DIR, name)
            if not os.path.isfile(path):
                continue
            try:
                if now - os.path.getmtime(path) > CLEANUP_MAX_AGE_SECONDS:
                    os.remove(path)
            except Exception:
                pass
    except Exception:
        pass


async def cleanup_worker():
    """Background task that periodically cleans old files."""
    while True:
        cleanup_download_dir_once()
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)


# ========================
# RETENTION WORKER
# ========================

# Reminder messages for different inactivity periods
REMINDER_24H = (
    "👋 Salom! Sizni sog'indik.\n\n"
    "🛠 Bizning xizmatlarimiz sizni kutmoqda:\n"
    "• PDF yaratish va siqish\n"
    "• AI rasm sifat oshirish\n"
    "• Rasmdan matn ajratish\n\n"
    "⬇️ /start bosing va davom eting!"
)

REMINDER_72H = (
    "🔔 3 kundan beri ko'rishmagandik!\n\n"
    "Bilasizmi? Yangi imkoniyatlar qo'shildi:\n"
    "• ✦ AI rasm yaratish\n"
    "• 🎨 Fon olib tashlash\n"
    "• 🗜 PDF siqish\n\n"
    "Bepul foydalaning → /start"
)


async def retention_worker(bot):
    """
    Background task — checks for inactive users and sends reminders.
    Runs every 6 hours.
    """
    from bot.database import get_inactive_users, was_reminder_sent, mark_reminder_sent

    await asyncio.sleep(60)  # Wait 1 min after bot start

    while True:
        try:
            # 72-hour inactive users (first reminder)
            users_72h = get_inactive_users(72)
            sent_24 = 0
            for u in users_72h:
                uid = u["user_id"]
                if was_reminder_sent(uid, "72h"):
                    continue
                try:
                    await bot.send_message(uid, REMINDER_24H)
                    mark_reminder_sent(uid, "72h")
                    sent_24 += 1
                    await asyncio.sleep(0.5)  # Rate limit
                except Exception:
                    mark_reminder_sent(uid, "72h")

            # 216-hour (9 days) inactive users (second reminder)
            users_216h = get_inactive_users(216)
            sent_72 = 0
            for u in users_216h:
                uid = u["user_id"]
                if was_reminder_sent(uid, "216h"):
                    continue
                try:
                    await bot.send_message(uid, REMINDER_72H)
                    mark_reminder_sent(uid, "216h")
                    sent_72 += 1
                    await asyncio.sleep(0.5)
                except Exception:
                    mark_reminder_sent(uid, "216h")

            if sent_24 or sent_72:
                logger.info(f"Retention: sent {sent_24} 72h reminders, {sent_72} 216h reminders")

        except Exception as e:
            logger.error(f"Retention worker error: {e}")

        # Run every 12 hours
        await asyncio.sleep(12 * 3600)


# ========================
# BOT PROFILE DESCRIPTION WORKER
# ========================

async def update_bot_description_worker(bot):
    """
    Periodically update bot name, description and short_description without user counts.
    """
    from bot.i18n import t

    try:
        desc = t("bot_description", "uz")
        short_desc = t("bot_short_description", "uz")

        await bot.set_my_name(name="PDF & AI Video Bot")
        await bot.set_my_description(description=desc)
        await bot.set_my_short_description(short_description=short_desc)
        logger.info("Updated bot profile name and description cleanly (removed user count)")
    except Exception as e:
        logger.warning(f"Could not update bot profile description: {e}")

