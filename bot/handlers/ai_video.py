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
    """Generate 5-second 720p HD video with synchronized AI audio using Replicate API."""
    import replicate
    import httpx

    client = replicate.Client(api_token=REPLICATE_API_TOKEN)
    loop = asyncio.get_event_loop()

    # Step 1: Generate 5-second 720p HD video (121 frames) via LTX-Video
    output = await loop.run_in_executor(
        None,
        lambda: client.run(
            "lightricks/ltx-video:8c47da666861d081eeb4d1261853087de23923a268a69b63febdf5dc1dee08e4",
            input={
                "prompt": prompt,
                "aspect_ratio": "16:9",
                "num_frames": 121,
                "negative_prompt": "low quality, worst quality, deformed, distorted, watermark"
            }
        )
    )

    if not output:
        raise RuntimeError("AI Video generation model did not return output.")

    video_url = output[0] if isinstance(output, (list, tuple)) and len(output) > 0 else output
    if hasattr(video_url, 'url'):
        video_url = video_url.url
    video_url = str(video_url)

    # Step 2: Add synchronized AI audio / sound effects via MMAudio
    audio_video_url = None
    try:
        audio_output = await loop.run_in_executor(
            None,
            lambda: client.run(
                "zsxkib/mmaudio:62871fb59889b2d7c13777f08deb3b36bdff88f7e1d53a50ad7694548a41b484",
                input={
                    "video": video_url,
                    "prompt": prompt,
                    "duration": 5
                }
            )
        )
        if audio_output:
            if isinstance(audio_output, (list, tuple)) and len(audio_output) > 0:
                audio_output = audio_output[0]
            if hasattr(audio_output, 'url'):
                audio_output = audio_output.url
            audio_video_url = str(audio_output)
    except Exception as e:
        logger.warning(f"MMAudio audio synthesis fallback: {e}")

    final_url = audio_video_url or video_url
    resp = httpx.get(final_url, timeout=120, follow_redirects=True)
    if resp.status_code == 200:
        return resp.content

    raise RuntimeError("Could not download generated AI Video file.")


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

    if is_free:
        if lang == "ru":
            trial_note = f"🎁 <b>У вас есть {AI_VIDEO_FREE_LIMIT - used_videos} БЕСПЛАТНЫХ пробных видео!</b>"
        elif lang == "en":
            trial_note = f"🎁 <b>You have {AI_VIDEO_FREE_LIMIT - used_videos} FREE trial videos!</b>"
        else:
            trial_note = f"🎁 <b>Sizda {AI_VIDEO_FREE_LIMIT - used_videos} ta BEPUL sinov videosi bor!</b>"
    else:
        if lang == "ru":
            trial_note = f"📌 Стоимость видео: <b>{VIDEO_COST} кредита (1 500 сум или ⭐️ 15 Stars)</b>"
        elif lang == "en":
            trial_note = f"📌 Video price: <b>{VIDEO_COST} credits (1,500 UZS or ⭐️ 15 Stars)</b>"
        else:
            trial_note = f"📌 Video narxi: <b>{VIDEO_COST} kredit (1 500 so'm yoki ⭐️ 15 Stars)</b>"

    if lang == "ru":
        terms_text = (
            f"🎬 <b>AI Генерация видео</b>\n\n"
            f"{trial_note}\n\n"
            f"• ⏱ Длительность: <b>5 секунд</b> (HD 720p + AI Звук MP4)\n"
            f"• 🔊 Аудио: <b>Синхронные звуковые эффекты (MMAudio)</b>\n"
            f"• ⏳ Время генерации: <b>15-30 секунд</b>\n"
            f"• 🌐 Язык: <b>Узбекский, Русский, Английский</b>\n"
            f"• 💰 Ваш баланс: <b>{balance} кредитов</b>\n\n"
            f"Для продолжения нажмите кнопку ниже 👇"
        )
    elif lang == "en":
        terms_text = (
            f"🎬 <b>AI Video Generator</b>\n\n"
            f"{trial_note}\n\n"
            f"• ⏱ Video duration: <b>5 seconds</b> (HD 720p + AI Audio MP4)\n"
            f"• 🔊 Audio: <b>Synchronized Sound FX (MMAudio)</b>\n"
            f"• ⏳ Generation time: <b>15-30 seconds</b>\n"
            f"• 🌐 Languages: <b>Uzbek, Russian, English</b>\n"
            f"• 💰 Your balance: <b>{balance} credits</b>\n\n"
            f"Click the button below to continue 👇"
        )
    else:
        terms_text = (
            f"🎬 <b>AI Video Yaratish</b>\n\n"
            f"{trial_note}\n\n"
            f"• ⏱ Video davomiyligi: <b>5 soniya</b> (HD 720p + AI Ovoz MP4)\n"
            f"• 🔊 Ovoz: <b>Sinxron sound effektlar va audio (MMAudio)</b>\n"
            f"• ⏳ Generatsiya vaqti: <b>15-30 soniya</b>\n"
            f"• 🌐 Til: <b>O'zbek, Rus va Ingliz</b> (avto-tarjima)\n"
            f"• 💰 Balansingiz: <b>{balance} kredit</b>\n\n"
            f"Davom etish uchun quyidagi tugmani bosing 👇"
        )

    await bot.send_message(
        user_id,
        terms_text,
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
            if lang == "ru":
                cost_text = f"💰 Списано: <b>{VIDEO_COST} кредита</b> | Остаток: <b>{remaining} кредитов</b>"
            elif lang == "en":
                cost_text = f"💰 Deducted: <b>{VIDEO_COST} credits</b> | Balance: <b>{remaining} credits</b>"
            else:
                cost_text = f"💰 Yechildi: <b>{VIDEO_COST} kredit</b> | Qolgan balans: <b>{remaining} kredit</b>"
        else:
            if lang == "ru":
                cost_text = f"🎁 Бесплатное видео: <b>{used_videos + 1}/{AI_VIDEO_FREE_LIMIT}</b>"
            elif lang == "en":
                cost_text = f"🎁 Free trial video: <b>{used_videos + 1}/{AI_VIDEO_FREE_LIMIT}</b>"
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
