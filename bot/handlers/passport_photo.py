"""
3x4 Passport and Document Photo Maker Handler.
- Removes background using AI (Bria)
- Aligns portrait to standard 3x4 ratio on clean white background
- Creates 10x15 cm 6-photo printable sheet (JPG and PDF) + 1 single 3x4 HD photo
- 3 Free generations per user, then 2 credits (1,000 UZS / 10 Stars)
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

from bot.config import DOWNLOAD_DIR, MAX_FILE_SIZE, REPLICATE_API_TOKEN
from bot.database import (
    upsert_user,
    inc_uses_and_log,
    get_user_language,
    get_user_balance,
    deduct_user_balance,
    get_user_passport_photo_count,
    inc_user_passport_photo_count
)
from bot.i18n import t
from bot.keyboards import kb_cancel, kb_top_up
from bot.states import get_state, set_state, STATE_WAIT_PASSPORT_PHOTO, STATE_NONE
from bot.utils.helpers import safe_remove
from bot.handlers.menu import enforce_subscription, show_main_menu

logger = logging.getLogger(__name__)
router = Router(name="passport_photo")

PASSPORT_FREE_LIMIT = 3
PASSPORT_PHOTO_COST = 2


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


async def _remove_background(in_path: str) -> bytes:
    """Remove background using Bria AI via Replicate API."""
    import httpx

    with open(in_path, "rb") as f:
        image_data = f.read()

    headers = {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
        "Prefer": "wait",
    }

    async with httpx.AsyncClient(timeout=120) as client:
        upload_resp = await client.post(
            "https://api.replicate.com/v1/files",
            headers={"Authorization": f"Bearer {REPLICATE_API_TOKEN}"},
            files={"content": ("image.jpg", image_data, "image/jpeg")},
        )
        upload_resp.raise_for_status()
        file_url = upload_resp.json()["urls"]["get"]

        predict_resp = await client.post(
            "https://api.replicate.com/v1/models/bria/remove-background/predictions",
            headers=headers,
            json={"input": {"image": file_url}},
        )

        if predict_resp.status_code == 404:
            predict_resp = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers=headers,
                json={
                    "version": "4f622503f07c88e8c1e0f3af8b2b0e3e3e1e3b5a7b2f7e2f3c4d5e6f7a8b9c0d",
                    "input": {"image": file_url},
                },
            )

        predict_resp.raise_for_status()
        prediction = predict_resp.json()

        if prediction.get("status") == "succeeded":
            output = prediction["output"]
            img_url = output if isinstance(output, str) else output[0] if output else None
            if img_url:
                r = await client.get(img_url, timeout=60)
                return r.content

        # Poll if not completed immediately
        pred_id = prediction.get("id")
        for _ in range(30):
            await asyncio.sleep(2)
            poll_resp = await client.get(
                f"https://api.replicate.com/v1/predictions/{pred_id}",
                headers={"Authorization": f"Bearer {REPLICATE_API_TOKEN}"},
            )
            poll_data = poll_resp.json()
            if poll_data.get("status") == "succeeded":
                output = poll_data["output"]
                img_url = output if isinstance(output, str) else output[0] if output else None
                if img_url:
                    r = await client.get(img_url, timeout=60)
                    return r.content
            elif poll_data.get("status") == "failed":
                raise RuntimeError(poll_data.get("error", "AI background removal failed"))

    raise RuntimeError("AI background removal timed out")


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

    used_count = get_user_passport_photo_count(user_id)
    is_free = used_count < PASSPORT_FREE_LIMIT
    balance = get_user_balance(user_id)

    if not is_free and balance < PASSPORT_PHOTO_COST:
        msg_text = (
            f"👔 <b>3x4 Hujjat Rasmi Yaratish (Pullik Xizmat)</b>\n\n"
            f"📌 Narxi: <b>{PASSPORT_PHOTO_COST} kredit (1 000 so'm yoki ⭐️ 10 Stars)</b>\n"
            f"💰 Sizning balansingiz: <b>{balance} kredit</b>\n\n"
            f"❌ Balansingizda kredit yetarli emas.\n"
            f"Quyidagi tugmalar orqali hisobingizni to'ldirishingiz mumkin 👇"
        )
        if lang == "ru":
            msg_text = (
                f"👔 <b>Создание Фото 3x4 на Документы (Платная услуга)</b>\n\n"
                f"📌 Стоимость: <b>{PASSPORT_PHOTO_COST} кредита (1 000 сум или ⭐️ 10 Stars)</b>\n"
                f"💰 Ваш баланс: <b>{balance} кредитов</b>\n\n"
                f"❌ На вашем балансе недостаточно кредитов.\n"
                f"Пополните баланс ниже 👇"
            )
        elif lang == "en":
            msg_text = (
                f"👔 <b>3x4 Passport Photo Generator (Paid Service)</b>\n\n"
                f"📌 Price: <b>{PASSPORT_PHOTO_COST} credits (1,000 UZS or ⭐️ 10 Stars)</b>\n"
                f"💰 Your balance: <b>{balance} credits</b>\n\n"
                f"❌ Insufficient credits on your balance.\n"
                f"Top up below 👇"
            )
        await bot.send_message(user_id, msg_text, parse_mode="HTML", reply_markup=kb_top_up(lang))
        return

    set_state(user_id, STATE_WAIT_PASSPORT_PHOTO)
    free_info = f"\n\n🎁 <b>(Sizda {PASSPORT_FREE_LIMIT - used_count} ta bepul qoldi)</b>" if is_free else ""
    await bot.send_message(
        user_id,
        t("passport_photo_prompt", lang) + free_info,
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

    used_count = get_user_passport_photo_count(user_id)
    is_free = used_count < PASSPORT_FREE_LIMIT
    balance = get_user_balance(user_id)

    if not is_free and balance < PASSPORT_PHOTO_COST:
        await message.answer(
            f"❌ Balansingizda kredit yetarli emas ({balance}/{PASSPORT_PHOTO_COST} kredit).",
            reply_markup=kb_top_up(lang)
        )
        return

    set_state(user_id, STATE_WAIT_PASSPORT_PHOTO)
    free_info = f"\n\n🎁 <b>(Sizda {PASSPORT_FREE_LIMIT - used_count} ta bepul qoldi)</b>" if is_free else ""
    await message.answer(
        t("passport_photo_prompt", lang) + free_info,
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

    used_count = get_user_passport_photo_count(user_id)
    is_free = used_count < PASSPORT_FREE_LIMIT
    balance = get_user_balance(user_id)

    if not is_free and balance < PASSPORT_PHOTO_COST:
        await message.answer("❌ Kredit yetarli emas.", reply_markup=kb_top_up(lang))
        set_state(user_id, STATE_NONE)
        await show_main_menu(bot, message.chat.id, lang=lang)
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

        # 1. AI Background Removal
        if REPLICATE_API_TOKEN:
            try:
                cutout_bytes = await _remove_background(in_path)
            except Exception as e:
                logger.warning(f"Bria BG removal failed, fallback to original: {e}")
                with open(in_path, "rb") as f:
                    cutout_bytes = f.read()
        else:
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

        # Update stats and deduct
        inc_user_passport_photo_count(user_id)
        inc_uses_and_log(user_id, "passport_photo")
        if not is_free:
            deduct_user_balance(user_id, PASSPORT_PHOTO_COST)
            rem = get_user_balance(user_id)
            await message.answer(f"💰 Hisobingizdan {PASSPORT_PHOTO_COST} kredit yechildi. Qoldiq: <b>{rem} kredit</b>", parse_mode="HTML")

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
