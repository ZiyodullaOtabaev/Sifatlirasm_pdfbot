"""
AI image generation handler — Flux Schnell via Replicate API.
"""
import os
import io
import asyncio
import logging

from aiogram import Router, Bot
from aiogram.types import Message, BufferedInputFile

from bot.config import REPLICATE_API_TOKEN
from bot.database import (
    upsert_user, inc_uses_and_log, get_user_balance, deduct_user_balance,
    get_user_language, get_user_ai_image_count, inc_user_ai_image_count
)
from bot.states import get_state, set_state, STATE_WAIT_AI_IMAGE, STATE_NONE
from bot.keyboards import kb_cancel, kb_top_up_ai_image
from bot.handlers.menu import enforce_subscription, show_main_menu

logger = logging.getLogger(__name__)
router = Router(name="ai_image")

AI_IMAGE_FREE_LIMIT = 7
AI_IMAGE_COST = 2


async def _generate_image(prompt: str) -> bytes:
    """Generate image using Flux Schnell via Replicate."""
    import replicate

    os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(
        None,
        lambda: replicate.run(
            "black-forest-labs/flux-schnell",
            input={
                "prompt": prompt,
                "num_outputs": 1,
                "aspect_ratio": "1:1",
                "output_format": "png",
                "output_quality": 90,
            }
        )
    )

    if output:
        import httpx
        if isinstance(output, list):
            for item in output:
                if hasattr(item, 'read'):
                    return item.read()
                elif isinstance(item, str):
                    resp = httpx.get(item, follow_redirects=True)
                    return resp.content
        elif hasattr(output, 'read'):
            return output.read()
        elif isinstance(output, str):
            resp = httpx.get(output, follow_redirects=True)
            return resp.content

    raise RuntimeError("AI rasm generatsiya natija qaytarmadi")


@router.message(lambda msg: msg.text and not msg.text.startswith("/") and get_state(msg.from_user.id) == STATE_WAIT_AI_IMAGE)
async def handle_ai_image(message: Message, bot: Bot):
    """Handle text prompt for AI image generation."""
    user = message.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user_id) or "uz"

    if not await enforce_subscription(bot, user_id):
        return

    if not REPLICATE_API_TOKEN:
        await message.answer("❌ AI xizmati hozir mavjud emas.")
        return

    used_images = get_user_ai_image_count(user_id)
    is_free = used_images < AI_IMAGE_FREE_LIMIT

    if not is_free:
        balance = get_user_balance(user_id)
        if balance < AI_IMAGE_COST:
            await message.answer(
                f"🤖 <b>AI Rasm Yaratish (Pullik xizmat)</b>\n\n"
                f"📌 Siz dastlabki <b>{AI_IMAGE_FREE_LIMIT} ta bepul</b> sinov rasmingizdan foydalanib bo'ldingiz.\n"
                f"1 ta AI rasm narxi: <b>{AI_IMAGE_COST} kredit (500 so'm yoki ⭐️ 10 Stars)</b>\n"
                f"💰 Sizning balansingiz: <b>{balance} kredit</b>\n\n"
                f"Davom etish uchun balansingizni to'ldiring 👇",
                parse_mode="HTML",
                reply_markup=kb_top_up_ai_image(lang)
            )
            set_state(user_id, STATE_NONE)
            return

    prompt = (message.text or "").strip()
    if not prompt:
        return

    if len(prompt) > 500:
        await message.answer("❌ Matn juda uzun (max 500 belgi).", reply_markup=kb_cancel(lang))
        return

    status = await message.answer(t("ai_image_generating", lang))
    try:
        from bot.utils.helpers import auto_translate_to_en
        en_prompt = await auto_translate_to_en(prompt)
        image_bytes = await _generate_image(en_prompt)
        photo = BufferedInputFile(image_bytes, filename="ai_generated.png")

        inc_user_ai_image_count(user_id)
        if not is_free:
            deduct_user_balance(user_id, AI_IMAGE_COST)
            remaining = get_user_balance(user_id)
            cost_text = f"💰 Yechildi: <b>{AI_IMAGE_COST} kredit</b> | Qolgan balans: <b>{remaining} kredit</b>"
        else:
            cost_text = f"🎁 Bepul sinov rasmi: <b>{used_images + 1}/{AI_IMAGE_FREE_LIMIT}</b>"

        caption = f"✦ <i>{prompt[:100]}</i>\n\n{cost_text}"
        await bot.send_photo(user_id, photo, caption=caption, parse_mode="HTML")
        inc_uses_and_log(user_id, "ai_image")
        logger.info(f"User {user_id}: ai_image '{prompt[:50]}'")
    except Exception as e:
        logger.error(f"AI Image error for user {user_id}: {e}")
        from bot.utils.helpers import friendly_error
        await message.answer(friendly_error(e))
    finally:
        try:
            await status.delete()
        except Exception:
            pass

    set_state(user_id, STATE_NONE)
    await show_main_menu(bot, message.chat.id)
