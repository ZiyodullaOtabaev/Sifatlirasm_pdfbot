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


async def _call_replicate_with_retry(model: str, input_data: dict, max_retries: int = 3) -> dict:
    """
    Create a Replicate prediction and poll until complete.
    Auto-retries on 429 (rate limit) and timeout errors with exponential back-off.
    Returns the final prediction dict.
    """
    import httpx

    headers = {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
        "Prefer": "wait",
    }
    payload = (
        {"version": model.split(":")[1], "input": input_data}
        if ":" in model
        else {"model": model, "input": input_data}
    )

    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=15.0)) as client:
                create_resp = await client.post(
                    "https://api.replicate.com/v1/predictions",
                    headers=headers,
                    json=payload,
                )

                if create_resp.status_code == 429:
                    wait = 6 * attempt
                    logger.warning(f"Replicate 429 rate-limit on attempt {attempt}. Waiting {wait}s")
                    await asyncio.sleep(wait)
                    continue

                create_resp.raise_for_status()
                prediction = create_resp.json()
                pred_id = prediction.get("id")

                if prediction.get("status") in ("succeeded", "failed", "canceled"):
                    return prediction

                # Poll until complete (max 180 seconds)
                for _ in range(90):
                    await asyncio.sleep(2)
                    poll = await client.get(
                        f"https://api.replicate.com/v1/predictions/{pred_id}",
                        headers={"Authorization": f"Bearer {REPLICATE_API_TOKEN}"},
                    )
                    poll.raise_for_status()
                    data = poll.json()
                    s = data.get("status")
                    if s == "succeeded":
                        return data
                    elif s in ("failed", "canceled"):
                        raise RuntimeError(f"Replicate prediction {s}: {data.get('error', '')}")

                raise RuntimeError("Prediction timed out after 180 seconds")

        except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.TimeoutException) as e:
            if attempt < max_retries:
                wait = 5 * attempt
                logger.warning(f"Timeout attempt {attempt}/{max_retries}. Retrying in {wait}s: {e}")
                await asyncio.sleep(wait)
            else:
                raise RuntimeError(
                    f"AI xizmati {max_retries} marta urinishdan keyin ham javob bermadi. "
                    f"Keyinroq qaytib urinib ko'ring."
                )

    raise RuntimeError("Replicate prediction failed after all retries")


async def _extract_url(output) -> str:
    """Extract URL string from various Replicate output formats."""
    if isinstance(output, (list, tuple)) and output:
        output = output[0]
    if hasattr(output, "url"):
        return str(output.url)
    return str(output)


async def _generate_video(prompt: str) -> bytes:
    """
    Generate 5-second 720p HD video with synchronized AI audio.
    Uses async polling with 180s timeout and 3x auto-retry on rate-limit/timeout.
    """
    import httpx
    import gc

    # Step 1: Generate video via LTX-Video
    video_prediction = await _call_replicate_with_retry(
        model="lightricks/ltx-video:8c47da666861d081eeb4d1261853087de23923a268a69b63febdf5dc1dee08e4",
        input_data={
            "prompt": prompt,
            "aspect_ratio": "16:9",
            "num_frames": 121,
            "negative_prompt": "low quality, worst quality, deformed, distorted, watermark",
        },
    )

    output = video_prediction.get("output")
    if not output:
        raise RuntimeError("AI Video generation model did not return output.")

    video_url = await _extract_url(output)

    # Step 2: Add synchronized AI audio (MMAudio) — optional, skip if fails
    audio_video_url: Optional[str] = None
    try:
        audio_prediction = await _call_replicate_with_retry(
            model="zsxkib/mmaudio:62871fb59889b2d7c13777f08deb3b36bdff88f7e1d53a50ad7694548a41b484",
            input_data={"video": video_url, "prompt": prompt, "duration": 5},
            max_retries=2,
        )
        audio_out = audio_prediction.get("output")
        if audio_out:
            audio_video_url = await _extract_url(audio_out)
    except Exception as e:
        logger.warning(f"MMAudio fallback (audio step skipped): {e}")

    final_url = audio_video_url or video_url

    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        resp = await client.get(final_url)
        if resp.status_code == 200:
            data = resp.content
            gc.collect()  # free memory after large file download
            return data

    raise RuntimeError("AI Video faylini yuklab bo'lmadi.")


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
        from bot.utils.helpers import enhance_video_prompt
        en_prompt = await enhance_video_prompt(prompt)
        logger.info(f"User {user_id} video prompt enhanced: '{prompt}' -> '{en_prompt}'")

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
