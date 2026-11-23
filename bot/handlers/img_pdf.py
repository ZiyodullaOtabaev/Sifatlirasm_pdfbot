"""
Image to PDF handler with strict sequential ordering (by message_id) and multi-photo batch support.
"""
import os
import time
import asyncio
import logging
from typing import Dict, List, Tuple

from aiogram import Router, Bot
from aiogram.types import Message, FSInputFile

from bot.config import DOWNLOAD_DIR, MAX_FILE_SIZE
from bot.database import upsert_user, inc_uses_and_log, get_user_language
from bot.i18n import t
from bot.states import get_state, set_state, STATE_WAIT_IMG_PDF, STATE_NONE
from bot.utils.pdf import images_to_pdf
from bot.utils.helpers import safe_remove, user_pdf_filename
from bot.handlers.menu import enforce_subscription, show_main_menu

logger = logging.getLogger(__name__)
router = Router(name="img_pdf")

# Per-user buffers: user_id -> List[(message_id, file_path)]
MEDIA_BUFFER: Dict[int, List[Tuple[int, str]]] = {}
MEDIA_TASK: Dict[int, asyncio.Task] = {}
ACTIVE_DOWNLOADS: Dict[int, int] = {}
LAST_LIMIT_WARN: Dict[int, float] = {}


@router.message(lambda msg: msg.photo and get_state(msg.from_user.id) == STATE_WAIT_IMG_PDF)
async def handle_img_pdf(message: Message, bot: Bot):
    """Handle photo(s) for image-to-PDF conversion in exact message_id order."""
    user = message.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user_id) or "uz"

    # Only run subscription/limit check if no batch is currently being collected for this user
    if user_id not in MEDIA_BUFFER and ACTIVE_DOWNLOADS.get(user_id, 0) == 0:
        now_ts = time.time()
        if now_ts - LAST_LIMIT_WARN.get(user_id, 0) < 3.0:
            return
        if not await enforce_subscription(bot, user_id, lang):
            LAST_LIMIT_WARN[user_id] = now_ts
            return

    photo = message.photo[-1]

    # File size check
    if photo.file_size and photo.file_size > MAX_FILE_SIZE:
        await message.answer(
            t("err_file_too_large", lang, max_mb=MAX_FILE_SIZE // (1024 * 1024)),
            parse_mode="HTML",
        )
        return

    # Cancel pending finalizer while a new photo is arriving/downloading
    old_task = MEDIA_TASK.get(user_id)
    if old_task and not old_task.done():
        old_task.cancel()

    ACTIVE_DOWNLOADS[user_id] = ACTIVE_DOWNLOADS.get(user_id, 0) + 1
    file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{message.message_id}_{photo.file_unique_id}.jpg")
    try:
        file = await bot.get_file(photo.file_id)
        await bot.download_file(file.file_path, file_path)
        MEDIA_BUFFER.setdefault(user_id, []).append((message.message_id, file_path))
    except Exception as dl_err:
        logger.error(f"Error downloading image for user {user_id}: {dl_err}")
        safe_remove(file_path)
    finally:
        ACTIVE_DOWNLOADS[user_id] = max(0, ACTIVE_DOWNLOADS.get(user_id, 1) - 1)

    # Restart debounce task so all photos in the batch/album finish downloading
    old_task = MEDIA_TASK.get(user_id)
    if old_task and not old_task.done():
        old_task.cancel()

    async def finalize_group():
        await asyncio.sleep(1.8)
        # Wait until any in-flight downloads for this user complete
        while ACTIVE_DOWNLOADS.get(user_id, 0) > 0:
            await asyncio.sleep(0.4)
        # Extra small settle delay in case another download just finished
        await asyncio.sleep(0.3)
        if ACTIVE_DOWNLOADS.get(user_id, 0) > 0:
            return

        items = MEDIA_BUFFER.pop(user_id, [])
        MEDIA_TASK.pop(user_id, None)
        ACTIVE_DOWNLOADS.pop(user_id, None)
        if not items:
            return

        # Sort strictly by Telegram message_id ascending so order matches user's exact upload sequence
        items.sort(key=lambda x: x[0])
        paths = [p for _, p in items]

        status = await bot.send_message(user_id, t("img_pdf_generating", lang))
        pdf_path = os.path.join(DOWNLOAD_DIR, f"images_{user_id}_{int(time.time())}.pdf")
        try:
            images_to_pdf(paths, pdf_path)
            doc = FSInputFile(pdf_path, filename=user_pdf_filename(user))
            caption = f"{t('img_pdf_ready', lang)} ({len(paths)})" if len(paths) > 1 else t("img_pdf_ready", lang)
            await bot.send_document(user_id, doc, caption=caption, parse_mode="HTML")
            inc_uses_and_log(user_id, "img_pdf")
            logger.info(f"User {user_id}: img_pdf ({len(paths)} images in strict order)")
        except Exception as e:
            logger.error(f"Img PDF error for user {user_id}: {e}")
            from bot.utils.helpers import friendly_error
            await bot.send_message(user_id, friendly_error(e, lang), parse_mode="HTML")
        finally:
            for p in paths:
                safe_remove(p)
            safe_remove(pdf_path)
            try:
                await status.delete()
            except Exception:
                pass
        set_state(user_id, STATE_NONE)
        await show_main_menu(bot, user_id)

    MEDIA_TASK[user_id] = asyncio.create_task(finalize_group())