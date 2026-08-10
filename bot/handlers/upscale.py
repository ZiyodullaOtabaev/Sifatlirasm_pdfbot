"""
Image upscale handler — AI-powered via Replicate API.
"""
import os
import logging

from aiogram import Router, Bot
from aiogram.types import Message, FSInputFile

from bot.config import DOWNLOAD_DIR, MAX_FILE_SIZE
from bot.database import upsert_user, inc_uses_and_log, get_user_language
from bot.i18n import t
from bot.states import get_state, set_state, STATE_WAIT_UPSCALE, STATE_NONE
from bot.utils.image import ai_upscale
from bot.utils.helpers import safe_remove
from bot.handlers.menu import enforce_subscription, show_main_menu

logger = logging.getLogger(__name__)
router = Router(name="upscale")


@router.message(lambda msg: msg.document and get_state(msg.from_user.id) == STATE_WAIT_UPSCALE)
async def handle_upscale_document_error(message: Message, bot: Bot):
    """Reject documents in upscale mode — need a photo."""
    lang = get_user_language(message.from_user.id) or "uz"
    from bot.keyboards import kb_cancel
    await message.answer("❌ Iltimos, fayl emas, rasm yuboring.", reply_markup=kb_cancel(lang))


@router.message(lambda msg: msg.photo and get_state(msg.from_user.id) == STATE_WAIT_UPSCALE)
async def handle_upscale(message: Message, bot: Bot):
    """Handle photo for AI upscaling."""
    user = message.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user_id) or "uz"

    if not await enforce_subscription(bot, user_id, lang):
        return

    photo = message.photo[-1]

    # File size check
    if photo.file_size and photo.file_size > MAX_FILE_SIZE:
        await message.answer(f"❌ Fayl hajmi juda katta (max {MAX_FILE_SIZE // (1024*1024)}MB).")
        return

    file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{photo.file_id}.jpg")
    file = await bot.get_file(photo.file_id)
    await bot.download_file(file.file_path, file_path)

    status = await message.answer(t("upscale_generating", lang))
    out_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{photo.file_id}_up.jpg")
    try:
        await ai_upscale(file_path, out_path)

        photo_file = FSInputFile(out_path)
        await bot.send_photo(user_id, photo_file, caption=t("upscale_ready", lang), parse_mode="HTML")
        inc_uses_and_log(user_id, "upscale")
        logger.info(f"User {user_id}: ai_upscale success")
    except Exception as e:
        logger.error(f"AI Upscale error for user {user_id}: {e}")
        from bot.utils.helpers import friendly_error
        await message.answer(friendly_error(e))
    finally:
        safe_remove(file_path)
        safe_remove(out_path)
        try:
            await status.delete()
        except Exception:
            pass
    set_state(user_id, STATE_NONE)
    await show_main_menu(bot, message.chat.id)
