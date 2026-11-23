"""
Temporary file cleanup worker and 3-language retention/description workers.
"""
import os
import time
import shutil
import asyncio
import logging

from bot.config import DOWNLOAD_DIR, CLEANUP_MAX_AGE_SECONDS, CLEANUP_INTERVAL_SECONDS

logger = logging.getLogger(__name__)


def cleanup_download_dir_once():
    """Remove old files and stale temp subdirectories from download directory."""
    try:
        now = time.time()
        for name in os.listdir(DOWNLOAD_DIR):
            path = os.path.join(DOWNLOAD_DIR, name)
            try:
                if now - os.path.getmtime(path) <= CLEANUP_MAX_AGE_SECONDS:
                    continue
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path) and name.startswith("office_"):
                    shutil.rmtree(path, ignore_errors=True)
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
# RETENTION WORKER (3-Language)
# ========================

REMINDERS_72H = {
    "uz": (
        "👋 Salom! Sizni sog'indik.\n\n"
        "🛠 Bizning tezkor PDF & Ofis xizmatlarimiz sizni kutmoqda:\n"
        "• 🖼 Rasm → sifatli PDF\n"
        "• 📝 PDF → Word (.docx) va 📄 Word/PPT → PDF\n"
        "• 📎 PDF birlashtirish va siqish\n\n"
        "⬇️ /start bosing va davom eting!"
    ),
    "ru": (
        "👋 Здравствуйте! Мы скучали по вам.\n\n"
        "🛠 Наши быстрые PDF и Офис инструменты ждут вас:\n"
        "• 🖼 Фото → качественный PDF\n"
        "• 📝 PDF → Word (.docx) и 📄 Word/PPT → PDF\n"
        "• 📎 Объединение и сжатие PDF\n\n"
        "⬇️ Нажмите /start и продолжайте работу!"
    ),
    "en": (
        "👋 Hello! We missed you.\n\n"
        "🛠 Our fast PDF & Office tools are ready for you:\n"
        "• 🖼 Image → high-quality PDF\n"
        "• 📝 PDF → Word (.docx) & 📄 Word/PPT → PDF\n"
        "• 📎 Merge & compress PDF files\n\n"
        "⬇️ Tap /start to continue!"
    ),
}

REMINDERS_216H = {
    "uz": (
        "🔔 Ko'rishmaganimizga ancha bo'ldi!\n\n"
        "Barcha qulay PDF va Ofis asboblar bitta botda:\n"
        "• 📝 PDF → Word (.docx) va 📄 Word/Excel/PPT → PDF\n"
        "• 🖼 Rasm → PDF va PDF → Rasm\n"
        "• 📎 PDF birlashtirish va 🗜 sifatli siqish\n\n"
        "Foydalanish uchun → /start"
    ),
    "ru": (
        "🔔 Давно не виделись!\n\n"
        "Все удобные PDF и офисные инструменты в одном боте:\n"
        "• 📝 PDF → Word (.docx) и 📄 Word/Excel/PPT → PDF\n"
        "• 🖼 Фото → PDF и PDF → Фото\n"
        "• 📎 Объединение и 🗜 сжатие PDF\n\n"
        "Чтобы начать → /start"
    ),
    "en": (
        "🔔 Long time no see!\n\n"
        "All handy PDF & Office tools in one bot:\n"
        "• 📝 PDF → Word (.docx) & 📄 Word/Excel/PPT → PDF\n"
        "• 🖼 Image → PDF & PDF → Images\n"
        "• 📎 Merge & 🗜 compress PDF files\n\n"
        "Tap → /start to begin"
    ),
}


async def retention_worker(bot):
    """
    Background task — checks for inactive users and sends localized reminders.
    Runs every 12 hours.
    """
    from bot.database import get_inactive_users, was_reminder_sent, mark_reminder_sent, get_user_language

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
                    u_lang = get_user_language(uid) or "uz"
                    await bot.send_message(uid, REMINDERS_72H.get(u_lang, REMINDERS_72H["uz"]))
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
                    u_lang = get_user_language(uid) or "uz"
                    await bot.send_message(uid, REMINDERS_216H.get(u_lang, REMINDERS_216H["uz"]))
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
    Set bot name and 3-language descriptions (uz default, ru, en).
    """
    from bot.i18n import t

    try:
        await bot.set_my_name(name="Sifatli PDF Bot")
        await bot.set_my_description(description=t("bot_description", "uz"))
        await bot.set_my_short_description(short_description=t("bot_short_description", "uz"))
        for lc in ("ru", "en"):
            try:
                await bot.set_my_description(description=t("bot_description", lc), language_code=lc)
                await bot.set_my_short_description(short_description=t("bot_short_description", lc), language_code=lc)
            except Exception:
                pass
        logger.info("Updated bot profile name and 3-language descriptions cleanly")
    except Exception as e:
        logger.warning(f"Could not update bot profile description: {e}")

