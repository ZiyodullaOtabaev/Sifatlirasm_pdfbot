"""
Background remove handler — AI-powered via Replicate API.
"""
import os
import io
import asyncio
import logging

from aiogram import Router, Bot
from aiogram.types import Message, BufferedInputFile

from bot.config import DOWNLOAD_DIR, MAX_FILE_SIZE, REPLICATE_API_TOKEN
from bot.database import upsert_user, inc_uses_and_log
from bot.states import get_state, STATE_WAIT_BG_REMOVE
from bot.utils.helpers import safe_remove
from bot.handlers.menu import enforce_subscription, show_main_menu

logger = logging.getLogger(__name__)
router = Router(name="bg_remove")


async def _remove_background(in_path: str) -> bytes:
    """Remove background using Replicate API (direct HTTP with version)."""
    import httpx

    with open(in_path, "rb") as f:
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

        # Try official model endpoint first (bria/remove-background)
        predict_resp = await client.post(
            "https://api.replicate.com/v1/models/bria/remove-background/predictions",
            headers=headers,
            json={"input": {"image": file_url}},
        )

        if predict_resp.status_code == 404:
            # Fallback: use version-based prediction
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

        # If "Prefer: wait" worked, result is already here
        if prediction.get("status") == "succeeded":
            output = prediction["output"]
            img_url = output if isinstance(output, str) else output[0] if output else None
            if img_url:
                img_resp = await client.get(img_url, follow_redirects=True)
                img_resp.raise_for_status()
                return img_resp.content

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
            status = data["status"]
            if status == "succeeded":
                output = data["output"]
                img_url = output if isinstance(output, str) else output[0] if output else None
                if not img_url:
                    raise RuntimeError("No output from model")
                img_resp = await client.get(img_url, follow_redirects=True)
                img_resp.raise_for_status()
                return img_resp.content
            elif status in ("failed", "canceled"):
                raise RuntimeError(f"Model {status}: {data.get('error', '')}")

    raise RuntimeError("Timeout waiting for background removal")


from bot.config import DOWNLOAD_DIR, MAX_FILE_SIZE, REPLICATE_API_TOKEN
from bot.database import upsert_user, inc_uses_and_log, get_user_language
from bot.i18n import t
from bot.states import get_state, set_state, STATE_WAIT_BG_REMOVE, STATE_NONE
from bot.utils.helpers import safe_remove
from bot.handlers.menu import enforce_subscription, show_main_menu

logger = logging.getLogger(__name__)
router = Router(name="bg_remove")


@router.message(lambda msg: msg.document and get_state(msg.from_user.id) == STATE_WAIT_BG_REMOVE)
async def handle_bg_remove_document_error(message: Message, bot: Bot):
    """Reject documents in bg_remove mode — need a photo."""
    lang = get_user_language(message.from_user.id) or "uz"
    from bot.keyboards import kb_cancel
    await message.answer("❌ Iltimos, fayl emas, rasm yuboring.", reply_markup=kb_cancel(lang))


@router.message(lambda msg: msg.photo and get_state(msg.from_user.id) == STATE_WAIT_BG_REMOVE)
async def handle_bg_remove(message: Message, bot: Bot):
    """Handle photo for background removal."""
    user = message.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user_id) or "uz"

    if not await enforce_subscription(bot, user_id, lang):
        return

    if not REPLICATE_API_TOKEN:
        await message.answer("❌ AI xizmati hozir mavjud emas.")
        return

    photo = message.photo[-1]

    if photo.file_size and photo.file_size > MAX_FILE_SIZE:
        await message.answer(f"❌ Fayl hajmi juda katta (max {MAX_FILE_SIZE // (1024*1024)}MB).")
        return

    file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{photo.file_id}.jpg")
    file = await bot.get_file(photo.file_id)
    await bot.download_file(file.file_path, file_path)

    status = await message.answer(t("bg_remove_generating", lang))
    try:
        result_bytes = await _remove_background(file_path)
        doc = BufferedInputFile(result_bytes, filename="no_background.png")
        await bot.send_document(user_id, doc, caption=t("bg_remove_ready", lang), parse_mode="HTML")
        inc_uses_and_log(user_id, "bg_remove")
        logger.info(f"User {user_id}: bg_remove success")
    except Exception as e:
        logger.error(f"BG Remove error for user {user_id}: {e}")
        from bot.utils.helpers import friendly_error
        await message.answer(friendly_error(e))
    finally:
        safe_remove(file_path)
        try:
            await status.delete()
        except Exception:
            pass
    set_state(user_id, STATE_NONE)
    await show_main_menu(bot, message.chat.id)
