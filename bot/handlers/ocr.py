"""
OCR handler — extract text from images using Replicate API.
Lightweight: no PyTorch/EasyOCR dependency.
"""
import os
import asyncio
import logging

import httpx
from aiogram import Router, Bot
from aiogram.types import Message, BufferedInputFile

from bot.config import DOWNLOAD_DIR, MAX_FILE_SIZE, REPLICATE_API_TOKEN
from bot.database import upsert_user, inc_uses_and_log
from bot.states import get_state, STATE_WAIT_OCR
from bot.utils.helpers import safe_remove, friendly_error
from bot.handlers.menu import enforce_subscription, show_main_menu

logger = logging.getLogger(__name__)
router = Router(name="ocr")


async def _ocr_via_replicate(image_path: str) -> str:
    """Run OCR via Replicate API (abiruyt/text-extract-ocr)."""
    with open(image_path, "rb") as f:
        image_data = f.read()

    headers = {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
        "Prefer": "wait",
    }

    async with httpx.AsyncClient(timeout=120) as client:
        # Upload file
        upload_resp = await client.post(
            "https://api.replicate.com/v1/files",
            headers={"Authorization": f"Bearer {REPLICATE_API_TOKEN}"},
            files={"content": ("image.jpg", image_data, "image/jpeg")},
        )
        upload_resp.raise_for_status()
        file_url = upload_resp.json()["urls"]["get"]

        # Create prediction
        predict_resp = await client.post(
            "https://api.replicate.com/v1/models/abiruyt/text-extract-ocr/predictions",
            headers=headers,
            json={"input": {"image": file_url}},
        )
        predict_resp.raise_for_status()
        prediction = predict_resp.json()

        # If Prefer: wait worked
        if prediction.get("status") == "succeeded":
            output = prediction.get("output", "")
            return output if isinstance(output, str) else str(output)

        # Poll for completion
        poll_url = prediction["urls"]["get"]
        for _ in range(60):
            await asyncio.sleep(1.5)
            poll_resp = await client.get(
                poll_url,
                headers={"Authorization": f"Bearer {REPLICATE_API_TOKEN}"},
            )
            poll_resp.raise_for_status()
            data = poll_resp.json()
            if data["status"] == "succeeded":
                output = data.get("output", "")
                return output if isinstance(output, str) else str(output)
            elif data["status"] in ("failed", "canceled"):
                raise RuntimeError(f"OCR failed: {data.get('error', '')}")

    raise RuntimeError("OCR timeout")


@router.message(lambda msg: msg.document and get_state(msg.from_user.id) == STATE_WAIT_OCR)
async def handle_ocr_document_error(message: Message, bot: Bot):
    """Reject documents in OCR mode — need a photo."""
    from bot.keyboards import kb_cancel
    await message.answer("❌ Rasm yuboring, fayl emas.\n"
                         "💡 Rasmni siqmay (photo sifatida) yuboring.", reply_markup=kb_cancel())


@router.message(lambda msg: msg.photo and get_state(msg.from_user.id) == STATE_WAIT_OCR)
async def handle_ocr(message: Message, bot: Bot):
    """Handle photo for OCR text extraction via Replicate."""
    user = message.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)

    if not await enforce_subscription(bot, user_id):
        return

    if not REPLICATE_API_TOKEN:
        await message.answer("❌ OCR xizmati hozir mavjud emas.")
        return

    photo = message.photo[-1]

    if photo.file_size and photo.file_size > MAX_FILE_SIZE:
        await message.answer(f"❌ Fayl hajmi juda katta (max {MAX_FILE_SIZE // (1024*1024)}MB).")
        return

    file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{photo.file_id}_ocr.jpg")
    file = await bot.get_file(photo.file_id)
    await bot.download_file(file.file_path, file_path)

    status = await message.answer("📖 Matn ajratilmoqda...")
    try:
        text = await _ocr_via_replicate(file_path)

        if not text.strip():
            await message.answer("❌ Rasmda matn topilmadi.")
        elif len(text) <= 4000:
            await bot.send_message(
                user_id,
                f"📖 <b>Topilgan matn:</b>\n\n<code>{text}</code>",
                parse_mode="HTML"
            )
        else:
            doc = BufferedInputFile(text.encode('utf-8'), filename="extracted_text.txt")
            await bot.send_document(user_id, doc, caption="📖 Topilgan matn (fayl)")

        inc_uses_and_log(user_id, "ocr")
        logger.info(f"User {user_id}: ocr ({len(text)} chars)")
    except Exception as e:
        logger.error(f"OCR error for user {user_id}: {e}")
        await message.answer(friendly_error(e))
    finally:
        safe_remove(file_path)
        try:
            await status.delete()
        except Exception:
            pass
    await show_main_menu(bot, message.chat.id)
