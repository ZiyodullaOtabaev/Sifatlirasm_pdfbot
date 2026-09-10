"""
3x4 Passport and Document Photo Maker Handler (100% free & offline).
- Aligns portrait to standard 3x4 ratio on clean white background
- Creates 10x15 cm 6-photo printable sheet (JPG and PDF) + 1 single 3x4 HD photo
"""
import os
import io
import asyncio
import logging
from typing import Tuple

from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from PIL import Image, ImageDraw

from bot.config import DOWNLOAD_DIR, MAX_FILE_SIZE
from bot.database import (
    upsert_user,
    inc_uses_and_log,
    get_user_language
)
from bot.i18n import t
from bot.keyboards import kb_cancel
from bot.states import get_state, set_state, STATE_WAIT_PASSPORT_PHOTO, STATE_NONE
from bot.utils.helpers import safe_remove
from bot.handlers.menu import enforce_subscription, show_main_menu

logger = logging.getLogger(__name__)
router = Router(name="passport_photo")

async def _safe_answer(call: CallbackQuery):
    try:
        await call.answer()
    except Exception:
        pass


def _process_passport_images(img_bytes: bytes) -> Tuple[bytes, bytes, bytes]:
    """
    Process transparent or cutout portrait into:
    1. single_3x4_jpg: (600x800 px)
    2. sheet_10x15_jpg: (1800x1200 px at 300 DPI, 6 photos with exact symmetry)
    3. sheet_10x15_pdf: (10x15 cm printable PDF)
    """
    im = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    w, h = im.size

    # Target aspect ratio 3:4 (0.75)
    target_ratio = 3.0 / 4.0
    current_ratio = w / float(h)

    if current_ratio > target_ratio:
        # Too wide, crop width
        new_w = int(h * target_ratio)
        offset = (w - new_w) // 2
        im_cropped = im.crop((offset, 0, offset + new_w, h))
    else:
        # Too tall, crop height centered naturally for head and shoulders
        new_h = int(w / target_ratio)
        top_offset = int((h - new_h) * 0.10)
        top_offset = max(0, min(top_offset, h - new_h))
        im_cropped = im.crop((0, top_offset, w, top_offset + new_h))

    # Single 3x4 photo (600 x 800 px)
    single_photo = Image.new("RGB", (600, 800), (255, 255, 255))
    im_resized = im_cropped.resize((600, 800), Image.Resampling.LANCZOS)
    if im_resized.mode == "RGBA":
        single_photo.paste(im_resized, (0, 0), im_resized)
    else:
        single_photo.paste(im_resized, (0, 0))

    single_buf = io.BytesIO()
    single_photo.save(single_buf, format="JPEG", quality=95)

    # 10x15 cm sheet at 300 DPI (1800 x 1200 px)
    sheet = Image.new("RGB", (1800, 1200), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)

    # 6 photos in 2 rows of 3 (each photo 420 x 560 px exact 3:4 ratio)
    p_w, p_h = 420, 560
    im_grid_photo = single_photo.resize((p_w, p_h), Image.Resampling.LANCZOS)

    start_x = 135
    spacing_x = 135
    start_y = 25
    spacing_y = 30

    for row in range(2):
        for col in range(3):
            px = start_x + col * (p_w + spacing_x)
            py = start_y + row * (p_h + spacing_y)
            sheet.paste(im_grid_photo, (px, py))
            # Thin border for cutting
            draw.rectangle([px, py, px + p_w, py + p_h], outline=(200, 200, 200), width=1)

    sheet_buf = io.BytesIO()
    sheet.save(sheet_buf, format="JPEG", quality=95)

    pdf_buf = io.BytesIO()
    sheet.save(pdf_buf, format="PDF", resolution=300.0)

    return single_buf.getvalue(), sheet_buf.getvalue(), pdf_buf.getvalue()


async def trigger_passport_photo_flow(event: CallbackQuery | Message, bot: Bot):
    """Handle 3x4 Passport Photo initiation flow."""
    if isinstance(event, CallbackQuery):
        await _safe_answer(event)
    user = event.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user_id) or "uz"

    if not await enforce_subscription(bot, user_id, lang=lang):
        return

    set_state(user_id, STATE_WAIT_PASSPORT_PHOTO)
    await bot.send_message(
        user_id,
        t("passport_photo_prompt", lang),
        parse_mode="HTML",
        reply_markup=kb_cancel(lang)
    )


@router.callback_query(F.data == "act_passport_photo")
async def cb_passport_photo_prompt(call: CallbackQuery, bot: Bot):
    """Handle 3x4 Passport Photo button click."""
    await trigger_passport_photo_flow(call, bot)


@router.message(Command("passport"))
async def cmd_passport_photo(message: Message, bot: Bot):
    """Handle /passport command."""
    user = message.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user_id) or "uz"

    if not await enforce_subscription(bot, user_id, lang=lang):
        return

    set_state(user_id, STATE_WAIT_PASSPORT_PHOTO)
    await message.answer(
        t("passport_photo_prompt", lang),
        parse_mode="HTML",
        reply_markup=kb_cancel(lang)
    )


@router.message(F.photo)
async def handle_passport_photo_input(message: Message, bot: Bot):
    """Handle incoming photo for 3x4 passport creation."""
    user = message.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user_id) or "uz"

    if get_state(user_id) != STATE_WAIT_PASSPORT_PHOTO:
        return

    if not await enforce_subscription(bot, user_id, lang=lang):
        return

    status = await message.answer(t("passport_photo_generating", lang))

    photo = message.photo[-1]
    if photo.file_size and photo.file_size > MAX_FILE_SIZE:
        await status.edit_text("❌ Rasm hajmi juda katta (max 20 MB).")
        return

    file_info = await bot.get_file(photo.file_id)
    in_path = os.path.join(DOWNLOAD_DIR, f"pass_in_{user_id}_{photo.file_unique_id}.jpg")

    try:
        await bot.download_file(file_info.file_path, in_path)

        # 1. Rasmni o'qish (lokal qayta ishlash)
        with open(in_path, "rb") as f:
            cutout_bytes = f.read()

        # 2. Process into 3x4 single, 10x15 cm sheet JPG, and 10x15 cm PDF
        loop = asyncio.get_event_loop()
        single_bytes, sheet_bytes, pdf_bytes = await loop.run_in_executor(
            None, _process_passport_images, cutout_bytes
        )

        # Send results
        sheet_photo = BufferedInputFile(sheet_bytes, filename="3x4_chop_etish_varagi_10x15.jpg")
        sheet_pdf = BufferedInputFile(pdf_bytes, filename="3x4_chop_etish_varagi_10x15.pdf")
        single_doc = BufferedInputFile(single_bytes, filename="3x4_pasport_rasm_HD.jpg")

        await bot.send_photo(
            message.chat.id,
            sheet_photo,
            caption=t("passport_photo_ready", lang),
            parse_mode="HTML"
        )
        await bot.send_document(
            message.chat.id,
            sheet_pdf,
            caption="📄 <b>10x15 sm 6 talik chop etish uchun PDF varaq</b>",
            parse_mode="HTML"
        )
        await bot.send_document(
            message.chat.id,
            single_doc,
            caption="👤 <b>1 dona 3x4 HD hujjat rasmi</b>",
            parse_mode="HTML"
        )

        # Update stats
        inc_uses_and_log(user_id, "passport_photo")

        try:
            await status.delete()
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Passport photo processing error: {e}", exc_info=True)
        await status.edit_text(t("passport_photo_error", lang))
    finally:
        safe_remove(in_path)
        set_state(user_id, STATE_NONE)
        await show_main_menu(bot, message.chat.id, lang=lang)
