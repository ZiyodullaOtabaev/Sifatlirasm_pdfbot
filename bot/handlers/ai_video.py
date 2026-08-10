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
from bot.database import (
    upsert_user, get_user_balance, deduct_user_balance, inc_uses_and_log,
    get_user_language, get_user_ai_video_count, inc_user_ai_video_count
)
from bot.i18n import t
from bot.keyboards import kb_cancel, kb_top_up, kb_top_up_video
from bot.states import get_state, set_state, STATE_WAIT_AI_VIDEO, STATE_NONE
from bot.handlers.menu import show_main_menu

logger = logging.getLogger(__name__)
router = Router(name="ai_video")


async def _generate_video(prompt: str) -> bytes:
    """Generate video using Replicate API (video generation model)."""
    import replicate

    client = replicate.Client(api_token=REPLICATE_API_TOKEN)
    loop = asyncio.get_event_loop()

    output = await loop.run_in_executor(
        None,
        lambda: client.run(
            "minimax/video-01",
            input={
                "prompt": prompt,
                "prompt_optimizer": True
            }
        )
    )

    if output:
        import httpx
        if isinstance(output, str):
            resp = httpx.get(output, timeout=120, follow_redirects=True)
            return resp.content
        elif hasattr(output, 'read'):
            return output.read()
        elif hasattr(output, 'url'):
            resp = httpx.get(output.url, timeout=120, follow_redirects=True)
            return resp.content

    raise RuntimeError("AI Video generation model did not return output.")


AI_VIDEO_FREE_LIMIT = 2
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

    used_videos = get_user_ai_video_count(user_id)
    is_free = used_videos < AI_VIDEO_FREE_LIMIT
    balance = get_user_balance(user_id)

    if not is_free and balance < VIDEO_COST:
        await bot.send_message(
            user_id,
            t("ai_video_insufficient_balance", lang, balance=balance),
            parse_mode="HTML",
            reply_markup=kb_top_up_video(lang)
        )
        return

    from bot.keyboards import kb_ai_video_terms
    trial_note = f"🎁 <b>Sizda {AI_VIDEO_FREE_LIMIT - used_videos} ta BEPUL sinov videosi bor!</b>" if is_free else f"📌 Video narxi: <b>{VIDEO_COST} kredit (1 500 so'm yoki ⭐️ 15 Stars)</b>"
    
    await bot.send_message(
        user_id,
        f"🎬 <b>AI Video Yaratish</b>\n\n"
        f"{trial_note}\n\n"
        f"• ⏱ Video davomiyligi: <b>5 soniya</b> (HD 720p MP4)\n"
        f"• ⏳ Generatsiya vaqti: <b>1-2 daqiqa</b>\n"
        f"• 🌐 Til: <b>O'zbek, Rus va Ingliz</b> (avto-tarjima)\n"
        f"• 💰 Balansingiz: <b>{balance} kredit</b>\n\n"
        f"Davom etish uchun quyidagi tugmani bosing 👇",
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

    used_videos = get_user_ai_video_count(user_id)
    is_free = used_videos < AI_VIDEO_FREE_LIMIT
    balance = get_user_balance(user_id)

    if not is_free and balance < VIDEO_COST:
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

    used_videos = get_user_ai_video_count(user_id)
    is_free = used_videos < AI_VIDEO_FREE_LIMIT
    balance = get_user_balance(user_id)

    if not is_free and balance < VIDEO_COST:
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
        
        inc_user_ai_video_count(user_id)
        if not is_free:
            deduct_user_balance(user_id, VIDEO_COST)
            remaining = get_user_balance(user_id)
            cost_text = f"💰 Yechildi: <b>{VIDEO_COST} kredit</b> | Qolgan balans: <b>{remaining} kredit</b>"
        else:
            cost_text = f"🎁 Bepul sinov videosi: <b>{used_videos + 1}/{AI_VIDEO_FREE_LIMIT}</b>"

        inc_uses_and_log(user_id, "ai_video")
        caption = f"🎬 <i>{prompt[:100]}</i>\n\n{cost_text}"
        
        video_file = BufferedInputFile(video_bytes, filename="ai_generated_video.mp4")
        await bot.send_video(user_id, video_file, caption=caption, parse_mode="HTML")
        logger.info(f"User {user_id}: ai_video '{prompt[:50]}' (remaining balance: {get_user_balance(user_id)})")
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
