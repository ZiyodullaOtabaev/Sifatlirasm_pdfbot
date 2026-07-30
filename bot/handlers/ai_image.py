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
from bot.database import upsert_user, inc_uses_and_log
from bot.states import get_state, set_state, STATE_WAIT_AI_IMAGE, STATE_NONE
from bot.keyboards import kb_cancel
from bot.handlers.menu import enforce_subscription, show_main_menu

logger = logging.getLogger(__name__)
router = Router(name="ai_image")


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

    # Natijani olish — odatda list qaytadi
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

    if not await enforce_subscription(bot, user_id):
        return

    if not REPLICATE_API_TOKEN:
        await message.answer("❌ AI xizmati hozir mavjud emas.")
        return

    prompt = (message.text or "").strip()
    if not prompt:
        return

    if len(prompt) > 500:
        await message.answer("❌ Matn juda uzun (max 500 belgi).", reply_markup=kb_cancel())
        return

    status = await message.answer("✦ AI rasm yaratmoqda...")
    try:
        from bot.utils.helpers import auto_translate_to_en
        en_prompt = await auto_translate_to_en(prompt)
        image_bytes = await _generate_image(en_prompt)
        photo = BufferedInputFile(image_bytes, filename="ai_generated.png")
        await bot.send_photo(user_id, photo, caption=f"✦ <i>{prompt[:100]}</i>",
                            parse_mode="HTML")
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
