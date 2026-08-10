"""
Image to PDF handler with media group support.
"""
import os
import time
import asyncio
import logging
from typing import Dict, List, Tuple

from aiogram import Router, Bot
from aiogram.types import Message, FSInputFile

from bot.config import DOWNLOAD_DIR, MAX_FILE_SIZE
from bot.database import (
    upsert_user, inc_uses_and_log, get_user_language,
    get_user_img_pdf_count, inc_user_img_pdf_count, has_active_img_pdf_pass
)
from bot.i18n import t
from bot.states import get_state, set_state, STATE_WAIT_IMG_PDF, STATE_NONE
from bot.keyboards import kb_top_up_img_pdf
from bot.utils.pdf import images_to_pdf
from bot.utils.helpers import safe_remove, user_pdf_filename
from bot.handlers.menu import enforce_subscription, show_main_menu

logger = logging.getLogger(__name__)
router = Router(name="img_pdf")

# Media group buffers
MEDIA_BUFFER: Dict[Tuple[int, str], List[str]] = {}
MEDIA_TASK: Dict[Tuple[int, str], asyncio.Task] = {}


@router.message(lambda msg: msg.photo and get_state(msg.from_user.id) == STATE_WAIT_IMG_PDF)
async def handle_img_pdf(message: Message, bot: Bot):
    """Handle photo for image-to-PDF conversion."""
    user = message.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user_id) or "uz"

    if not await enforce_subscription(bot, user_id, lang):
        return

    has_pass = has_active_img_pdf_pass(user_id)
    cnt = get_user_img_pdf_count(user_id)

    if not has_pass and cnt >= 50:
        if lang == "ru":
            limit_msg = (
                "🖼 <b>Фото ➡️ PDF (Безлимит на 1 год)</b>\n\n"
                "📌 Вы использовали все <b>50 бесплатных</b> конвертаций.\n\n"
                "Чтобы использовать эту функцию <b>БЕЗЛИМИТНО в течение 1 ГОДА (365 дней)</b>, оплатите <b>5 000 сум (или ⭐️ 50 Stars)</b> 👇"
            )
        elif lang == "en":
            limit_msg = (
                "🖼 <b>Image ➡️ PDF (1-Year Unlimited Pass)</b>\n\n"
                "📌 You have used all <b>50 free</b> conversions.\n\n"
                "To use this feature <b>UNLIMITED for 1 YEAR (365 days)</b>, purchase the pass for <b>5,000 UZS (or ⭐️ 50 Stars)</b> 👇"
            )
        else:
            limit_msg = (
                "🖼 <b>Rasm ➡️ PDF (1 Yillik Cheksiz Pass)</b>\n\n"
                "📌 Siz dastlabki <b>50 ta bepul</b> rasmni PDF qilish limitidan to'liq foydalandingiz.\n\n"
                "Buyog'iga ushbu xizmatni <b>1 YIL (365 kun) davomida BUTUNLAY CHEKSIZ</b> ishlatish uchun <b>5 000 so'm (yoki ⭐️ 50 Stars)</b> to'lov qiling 👇"
            )

        await message.answer(limit_msg, parse_mode="HTML", reply_markup=kb_top_up_img_pdf(lang))
        set_state(user_id, STATE_NONE)
        return

    photo = message.photo[-1]

    # File size check
    if photo.file_size and photo.file_size > MAX_FILE_SIZE:
        await message.answer(f"❌ Fayl hajmi juda katta (max {MAX_FILE_SIZE // (1024*1024)}MB).")
        return

    file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{photo.file_id}.jpg")
    file = await bot.get_file(photo.file_id)
    await bot.download_file(file.file_path, file_path)

    # Media group handling
    if message.media_group_id:
        key = (user_id, message.media_group_id)
        MEDIA_BUFFER.setdefault(key, []).append(file_path)
        old_task = MEDIA_TASK.get(key)
        if old_task and not old_task.done():
            old_task.cancel()

        async def finalize_group():
            await asyncio.sleep(1.5)
            paths = MEDIA_BUFFER.pop(key, [])
            MEDIA_TASK.pop(key, None)
            if not paths:
                return
            status = await bot.send_message(user_id, t("img_pdf_generating", lang))
            pdf_path = os.path.join(DOWNLOAD_DIR, f"images_{user_id}_{int(time.time())}.pdf")
            try:
                images_to_pdf(paths, pdf_path)
                doc = FSInputFile(pdf_path, filename=user_pdf_filename(user))
                inc_user_img_pdf_count(user_id)
                current_cnt = get_user_img_pdf_count(user_id)
                if has_pass:
                    tag = "💎 1-Годовой VIP Pass" if lang == "ru" else "💎 1-Year VIP Pass" if lang == "en" else "💎 1 Yillik VIP Pass faol"
                else:
                    tag = f"🎁 Лимит: {current_cnt}/50" if lang == "ru" else f"🎁 Free: {current_cnt}/50" if lang == "en" else f"🎁 Bepul limit: {current_cnt}/50"
                await bot.send_document(user_id, doc, caption=f"{t('img_pdf_ready', lang)} ({len(paths)})\n<i>{tag}</i>", parse_mode="HTML")
                inc_uses_and_log(user_id, "img_pdf")
                logger.info(f"User {user_id}: img_pdf ({len(paths)} images)")
            except Exception as e:
                logger.error(f"Img PDF group error for user {user_id}: {e}")
                from bot.utils.helpers import friendly_error
                await bot.send_message(user_id, friendly_error(e))
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

        MEDIA_TASK[key] = asyncio.create_task(finalize_group())
        return

    # Single image
    status = await message.answer(t("img_pdf_generating", lang))
    pdf_path = os.path.join(DOWNLOAD_DIR, f"image_{user_id}_{int(time.time())}.pdf")
    try:
        images_to_pdf([file_path], pdf_path)
        doc = FSInputFile(pdf_path, filename=user_pdf_filename(user))
        inc_user_img_pdf_count(user_id)
        current_cnt = get_user_img_pdf_count(user_id)
        if has_pass:
            tag = "💎 1-Годовой VIP Pass" if lang == "ru" else "💎 1-Year VIP Pass" if lang == "en" else "💎 1 Yillik VIP Pass faol"
        else:
            tag = f"🎁 Лимит: {current_cnt}/50" if lang == "ru" else f"🎁 Free: {current_cnt}/50" if lang == "en" else f"🎁 Bepul limit: {current_cnt}/50"
        await bot.send_document(user_id, doc, caption=f"{t('img_pdf_ready', lang)}\n<i>{tag}</i>", parse_mode="HTML")
        inc_uses_and_log(user_id, "img_pdf")
        logger.info(f"User {user_id}: img_pdf (1 image)")
    except Exception as e:
        logger.error(f"Img PDF error for user {user_id}: {e}")
        from bot.utils.helpers import friendly_error
        await message.answer(friendly_error(e))
    finally:
        safe_remove(file_path)
        safe_remove(pdf_path)
        try:
            await status.delete()
        except Exception:
            pass
    set_state(user_id, STATE_NONE)
    await show_main_menu(bot, message.chat.id)