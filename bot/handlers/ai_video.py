"""
AI Video Generation Handler (Paid feature via Replicate API).
"""
import os
import asyncio
import logging
from typing import Optional

from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile

from bot.config import REPLICATE_API_TOKEN
from bot.database import upsert_user, get_user_balance, deduct_user_balance, inc_uses_and_log, get_user_language
from bot.i18n import t
from bot.keyboards import kb_cancel, kb_top_up, kb_top_up_video
from bot.states import get_state, set_state, STATE_WAIT_AI_VIDEO, STATE_NONE
from bot.handlers.menu import show_main_menu

logger = logging.getLogger(__name__)
router = Router(name="ai_video")


async def _generate_video(prompt: str) -> bytes:
    """Generate video using Replicate API (video generation model)."""
    import replicate
    import httpx

    os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

    loop = asyncio.get_event_loop()
    
    # Try video generation models in priority order
    models_to_try = [
        ("minimax/video-01", {"prompt": prompt}),
        ("cjwbw/damo-text-to-video", {"prompt": prompt}),
    ]

    output = None
    last_err = None

    for model_name, inputs in models_to_try:
        try:
            output = await loop.run_in_executor(
                None,
                lambda: replicate.run(model_name, input=inputs)
            )
            if output:
                break
        except Exception as e:
            logger.warning(f"Replicate video model {model_name} failed: {e}")
            last_err = e

    if not output and last_err:
        raise last_err

    # Extract video bytes from output
    if output:
        if isinstance(output, list):
            output = output[0]

        if hasattr(output, 'read'):
            return output.read()
        elif isinstance(output, str):
            resp = httpx.get(output, follow_redirects=True, timeout=60)
            return resp.content

    raise RuntimeError("AI Video generation model did not return output.")


VIDEO_COST = 4


@router.callback_query(F.data == "act_ai_video")
async def cb_ai_video(call: CallbackQuery, bot: Bot):
    """Show AI Video terms and conditions."""
    try:
        await call.answer()
    except Exception:
        pass
    user = call.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user_id) or "uz"

    balance = get_user_balance(user_id)
    if balance < VIDEO_COST:
        await bot.send_message(
            user_id,
            t("ai_video_insufficient_balance", lang, balance=balance),
            parse_mode="HTML",
            reply_markup=kb_top_up_video(lang)
        )
        return

    from bot.keyboards import kb_ai_video_terms
    await bot.send_message(
        user_id,
        t("ai_video_terms", lang, balance=balance),
        parse_mode="HTML",
        reply_markup=kb_ai_video_terms(lang)
    )


@router.callback_query(F.data == "act_start_ai_video")
async def cb_start_ai_video(call: CallbackQuery, bot: Bot):
    """Start video prompt input after confirming terms."""
    try:
        await call.answer()
    except Exception:
        pass
    user = call.from_user
    user_id = user.id
    lang = get_user_language(user_id) or "uz"

    balance = get_user_balance(user_id)
    if balance < VIDEO_COST:
        await bot.send_message(
            user_id,
            t("ai_video_insufficient_balance", lang, balance=balance),
            parse_mode="HTML",
            reply_markup=kb_top_up_video(lang)
        )
        return

    set_state(user_id, STATE_WAIT_AI_VIDEO)
    await bot.send_message(
        user_id,
        t("ai_video_prompt", lang),
        parse_mode="HTML",
        reply_markup=kb_cancel(lang)
    )


@router.message(lambda msg: msg.text and not msg.text.startswith("/") and get_state(msg.from_user.id) == STATE_WAIT_AI_VIDEO)
async def handle_ai_video(message: Message, bot: Bot):
    """Handle text prompt for AI video generation."""
    user = message.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user_id) or "uz"

    if not REPLICATE_API_TOKEN:
        await message.answer("❌ AI Video xizmati konfiguratsiya qilinmagan (REPLICATE_API_TOKEN yetishmaydi).")
        set_state(user_id, STATE_NONE)
        await show_main_menu(bot, message.chat.id)
        return

    balance = get_user_balance(user_id)
    if balance < VIDEO_COST:
        await message.answer(
            t("ai_video_insufficient_balance", lang, balance=balance),
            parse_mode="HTML",
            reply_markup=kb_top_up_video(lang)
        )
        set_state(user_id, STATE_NONE)
        return

    prompt = (message.text or "").strip()
    if not prompt:
        return

    if len(prompt) > 500:
        await message.answer("❌ Matn juda uzun (max 500 belgi).", reply_markup=kb_cancel(lang))
        return

    status = await message.answer(t("ai_video_generating", lang))
    try:
        from bot.utils.helpers import auto_translate_to_en
        en_prompt = await auto_translate_to_en(prompt)
        logger.info(f"User {user_id} video prompt translated: '{prompt}' -> '{en_prompt}'")

        video_bytes = await _generate_video(en_prompt)
        
        # Deduct balance & log use
        deduct_user_balance(user_id, VIDEO_COST)
        inc_uses_and_log(user_id, "ai_video")
        
        remaining = get_user_balance(user_id)
        caption = f"🎬 <i>{prompt[:100]}</i>\n\n💰 Balans: <b>{remaining} kredit</b>"
        
        video_file = BufferedInputFile(video_bytes, filename="ai_generated_video.mp4")
        await bot.send_video(user_id, video_file, caption=caption, parse_mode="HTML")
        logger.info(f"User {user_id}: ai_video '{prompt[:50]}' (remaining balance: {remaining})")
    except Exception as e:
        logger.error(f"AI Video error for user {user_id}: {e}")
        from bot.utils.helpers import friendly_error
        await message.answer(friendly_error(e))
    finally:
        try:
            await status.delete()
        except Exception:
            pass

    set_state(user_id, STATE_NONE)
    await show_main_menu(bot, message.chat.id)
