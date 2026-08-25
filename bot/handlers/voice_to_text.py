"""
Voice to Text (Audio Transcriber) Handler — 100% Free & Fast AI Transcription.
- Accurately transcribes Telegram voice messages and audio files in Uzbek, Russian, and English.
- Uses OpenAI Whisper AI / Incredibly Fast Whisper.
- Provides 1-click action buttons: "📄 PDF qilish" and "📊 Slayd yasash".
"""
import os
import io
import asyncio
import logging
from typing import Dict

from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command

from bot.config import DOWNLOAD_DIR, MAX_FILE_SIZE, REPLICATE_API_TOKEN
from bot.database import (
    upsert_user,
    inc_uses_and_log,
    get_user_language
)
from bot.i18n import t
from bot.keyboards import kb_cancel, kb_voice_actions
from bot.states import get_state, set_state, STATE_WAIT_VOICE_TO_TEXT, STATE_NONE
from bot.utils.helpers import safe_remove
from bot.handlers.menu import enforce_subscription, show_main_menu

logger = logging.getLogger(__name__)
router = Router(name="voice_to_text")

# Temporary cache for transcribed text per user
USER_VOICE_TEXT: Dict[int, str] = {}


async def _safe_answer(call: CallbackQuery):
    try:
        await call.answer()
    except Exception:
        pass


async def _transcribe_audio(audio_path: str) -> str:
    """Transcribe audio file to text using Whisper AI."""
    import httpx

    with open(audio_path, "rb") as f:
        audio_data = f.read()

    # Upload file to Replicate
    async with httpx.AsyncClient(timeout=120) as client:
        upload_resp = await client.post(
            "https://api.replicate.com/v1/files",
            headers={"Authorization": f"Bearer {REPLICATE_API_TOKEN}"},
            files={"content": ("audio.ogg", audio_data, "audio/ogg")},
        )
        upload_resp.raise_for_status()
        audio_url = upload_resp.json()["urls"]["get"]

        headers = {
            "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
            "Content-Type": "application/json",
            "Prefer": "wait",
        }

        # Run incredibly-fast-whisper
        predict_resp = await client.post(
            "https://api.replicate.com/v1/predictions",
            headers=headers,
            json={
                "version": "3ab86df6c8f54c11309d4d1f930ac292bad43ace52d10c80d87eb258b3c9f79c",
                "input": {
                    "audio": audio_url,
                    "batch_size": 64
                },
            },
        )
        predict_resp.raise_for_status()
        prediction = predict_resp.json()

        if prediction.get("status") == "succeeded":
            output = prediction.get("output", {})
            if isinstance(output, dict) and "text" in output:
                return output["text"].strip()
            elif isinstance(output, str):
                return output.strip()

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
                out = poll_data.get("output", {})
                if isinstance(out, dict) and "text" in out:
                    return out["text"].strip()
                elif isinstance(out, str):
                    return out.strip()
            elif poll_data.get("status") == "failed":
                raise RuntimeError(poll_data.get("error", "Whisper transcription failed"))

    raise RuntimeError("Whisper transcription timed out")


@router.callback_query(F.data == "act_voice_to_text")
async def cb_voice_to_text_prompt(call: CallbackQuery, bot: Bot):
    """Handle Voice to Text menu button."""
    await _safe_answer(call)
    user = call.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user_id) or "uz"

    if not await enforce_subscription(bot, user_id, lang=lang):
        return

    set_state(user_id, STATE_WAIT_VOICE_TO_TEXT)
    await bot.send_message(
        user_id,
        t("voice_to_text_prompt", lang),
        parse_mode="HTML",
        reply_markup=kb_cancel(lang)
    )


@router.message(Command("voice"))
async def cmd_voice_to_text(message: Message, bot: Bot):
    """Handle /voice command."""
    user = message.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user_id) or "uz"

    if not await enforce_subscription(bot, user_id, lang=lang):
        return

    set_state(user_id, STATE_WAIT_VOICE_TO_TEXT)
    await message.answer(
        t("voice_to_text_prompt", lang),
        parse_mode="HTML",
        reply_markup=kb_cancel(lang)
    )


@router.message(F.voice | F.audio)
async def handle_audio_message(message: Message, bot: Bot):
    """Handle voice or audio file input."""
    user = message.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user_id) or "uz"

    # Process if in state OR if user directly forwarded a voice/audio message
    cur_state = get_state(user_id)
    if cur_state != STATE_WAIT_VOICE_TO_TEXT and not (message.voice or message.audio):
        return

    if not await enforce_subscription(bot, user_id, lang=lang):
        return

    status = await message.answer(t("voice_to_text_generating", lang))

    # Determine file_id and ext
    if message.voice:
        file_id = message.voice.file_id
        file_size = message.voice.file_size or 0
        ext = "ogg"
    else:
        file_id = message.audio.file_id
        file_size = message.audio.file_size or 0
        ext = "mp3"

    if file_size > MAX_FILE_SIZE:
        await status.edit_text("❌ Audio fayl hajmi juda katta (max 20 MB).")
        return

    file_info = await bot.get_file(file_id)
    audio_path = os.path.join(DOWNLOAD_DIR, f"voice_{user_id}_{file_id[:8]}.{ext}")

    try:
        await bot.download_file(file_info.file_path, audio_path)

        text = await _transcribe_audio(audio_path)
        if not text or len(text.strip()) == 0:
            await status.edit_text(t("voice_to_text_empty", lang))
            return

        # Store in session cache
        USER_VOICE_TEXT[user_id] = text

        inc_uses_and_log(user_id, "voice_to_text")

        import html
        escaped_text = html.escape(text)

        msg_body = (
            f"🎙 <b>Ovozli xabar matnga o'girildi:</b>\n\n"
            f"<code>{escaped_text}</code>\n\n"
            f"⬇️ <b>Ushbu matn bilan nima qilamiz?</b>"
        )
        if lang == "ru":
            msg_body = (
                f"🎙 <b>Распознанный текст:</b>\n\n"
                f"<code>{escaped_text}</code>\n\n"
                f"⬇️ <b>Что сделать с этим текстом?</b>"
            )
        elif lang == "en":
            msg_body = (
                f"🎙 <b>Transcribed Text:</b>\n\n"
                f"<code>{escaped_text}</code>\n\n"
                f"⬇️ <b>What would you like to do with this text?</b>"
            )

        try:
            await status.delete()
        except Exception:
            pass

        await message.answer(
            msg_body,
            parse_mode="HTML",
            reply_markup=kb_voice_actions(lang)
        )

    except Exception as e:
        logger.error(f"Voice transcription error: {e}", exc_info=True)
        await status.edit_text(t("voice_to_text_empty", lang))
    finally:
        safe_remove(audio_path)
        set_state(user_id, STATE_NONE)


@router.callback_query(F.data == "act_voice_to_pdf")
async def cb_voice_to_pdf(call: CallbackQuery, bot: Bot):
    """Convert transcribed voice text to PDF document."""
    await _safe_answer(call)
    user_id = call.from_user.id
    lang = get_user_language(user_id) or "uz"

    text = USER_VOICE_TEXT.get(user_id, "").strip()
    if not text:
        await bot.send_message(user_id, "❌ Matn topilmadi. Qaytadan ovoz yuboring.")
        return

    status = await bot.send_message(user_id, t("processing", lang))
    try:
        from bot.utils.pdf import create_pdf_from_text
        pdf_bytes = await create_pdf_from_text(text)
        pdf_file = BufferedInputFile(pdf_bytes, filename="Ovozli_xabar_konspekt.pdf")

        await bot.send_document(
            user_id,
            pdf_file,
            caption="📄 <b>Ovozli xabaringizdan tayyorlangan PDF hujjat!</b>",
            parse_mode="HTML"
        )
        inc_uses_and_log(user_id, "text_pdf")
        try:
            await status.delete()
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Voice to PDF error: {e}", exc_info=True)
        await status.edit_text(t("error_occurred", lang))


@router.callback_query(F.data == "act_voice_to_slides")
async def cb_voice_to_slides(call: CallbackQuery, bot: Bot):
    """Convert transcribed voice text into AI presentation slides."""
    await _safe_answer(call)
    user_id = call.from_user.id
    lang = get_user_language(user_id) or "uz"

    text = USER_VOICE_TEXT.get(user_id, "").strip()
    if not text:
        await bot.send_message(user_id, "❌ Matn topilmadi. Qaytadan ovoz yuboring.")
        return

    from bot.handlers.ai_slides import USER_SLIDE_DATA, _send_gallery_view
    topic = text[:200]
    USER_SLIDE_DATA[user_id] = {"topic": topic, "author": ""}

    await bot.send_message(
        user_id,
        f"📊 <b>Ovozli konspektingiz taqdimot mavzusi sifatida tanlandi:</b>\n\n"
        f"<i>\"{topic}\"</i>\n\n"
        f"🎨 <b>Endi slayd dizayn shablonini tanlang:</b>",
        parse_mode="HTML"
    )
    await _send_gallery_view(bot, user_id, 0, topic, "", lang)
