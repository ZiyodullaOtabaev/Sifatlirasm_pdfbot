"""
Voice to Text (Audio Transcriber) Handler — 100% Free & Fast AI Transcription.
- Accurately transcribes Telegram voice messages and audio files in Uzbek, Russian, and English.
- Output formatting rules:
  * Uzbek audio: High-quality Latin script (o', g', sh, ch, q, h)
  * English audio: High-quality Latin script
  * Russian audio: High-quality Cyrillic script
- Provides 1-click action button: "📄 Matndan PDF qilish".
"""
import os
import io
import re
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


def _fallback_cyrillic_to_latin_uz(text: str) -> str:
    """Fallback rule-based Cyrillic to Latin Uzbek transliterator."""
    table = {
        'А': 'A', 'а': 'a', 'Б': 'B', 'б': 'b', 'В': 'V', 'в': 'v',
        'Г': 'G', 'г': 'g', 'Д': 'D', 'д': 'd', 'Е': 'E', 'е': 'e',
        'Ё': 'Yo', 'ё': 'yo', 'Ж': 'J', 'ж': 'j', 'З': 'Z', 'з': 'z',
        'И': 'I', 'и': 'i', 'Й': 'Y', 'й': 'y', 'К': 'K', 'к': 'k',
        'Л': 'L', 'л': 'l', 'М': 'M', 'м': 'm', 'Н': 'N', 'н': 'n',
        'О': 'O', 'о': 'o', 'П': 'P', 'п': 'p', 'Р': 'R', 'р': 'r',
        'С': 'S', 'с': 's', 'Т': 'T', 'т': 't', 'У': 'U', 'у': 'u',
        'Ф': 'F', 'ф': 'f', 'Х': 'X', 'х': 'x', 'Ц': 'Ts', 'ц': 'ts',
        'Ч': 'Ch', 'ч': 'ch', 'Ш': 'Sh', 'ш': 'sh', 'Щ': 'Sh', 'щ': 'sh',
        'Ъ': "'", 'ъ': "'", 'Ь': '', 'ь': '', 'Э': 'E', 'э': 'e',
        'Ю': 'Yu', 'ю': 'yu', 'Я': 'Ya', 'я': 'ya',
        'Ў': "O'", 'ў': "o'", 'Ғ': "G'", 'ғ': "g'", 'Қ': 'Q', 'қ': 'q', 'Ҳ': 'H', 'ҳ': 'h'
    }
    return "".join(table.get(ch, ch) for ch in text)


async def _format_and_clean_transcription(raw_text: str) -> str:
    """
    Format speech transcription:
    - Uzbek: Output in clean, correct Latin script.
    - English: Output in clean Latin script.
    - Russian: Output in clean Russian Cyrillic script.
    """
    if not raw_text or len(raw_text.strip()) == 0:
        return raw_text

    clean_raw = raw_text.strip()

    if REPLICATE_API_TOKEN:
        try:
            import replicate
            client = replicate.Client(api_token=REPLICATE_API_TOKEN)
            loop = asyncio.get_event_loop()

            system_prompt = (
                "You are an expert multilingual speech transcriber and text formatter. "
                "Format the given raw audio transcription according to these exact rules:\n"
                "1. If the input is in Uzbek (spoken Uzbek or Uzbek Cyrillic): Output in clean, grammatically correct Uzbek LATIN script (using o', g', sh, ch, q, h).\n"
                "2. If the input is in English: Output in clean, grammatically correct English LATIN script.\n"
                "3. If the input is in Russian: Output in clean, grammatically correct Russian CYRILLIC script.\n"
                "4. Fix punctuation, capitalization, and speech filler. Do NOT add conversational commentary, quotes, or markdown. Output ONLY the finalized text."
            )

            output = await loop.run_in_executor(
                None,
                lambda: client.run(
                    "meta/meta-llama-3-70b-instruct",
                    input={
                        "prompt": f"{system_prompt}\n\nRaw transcription: {clean_raw}\n\nFinalized Text:",
                        "max_tokens": 600,
                        "temperature": 0.2
                    }
                )
            )

            enhanced = "".join(output).strip()
            if len(enhanced) > 2:
                # Remove any accidental leading/trailing quotes
                if (enhanced.startswith('"') and enhanced.endswith('"')) or (enhanced.startswith("'") and enhanced.endswith("'")):
                    enhanced = enhanced[1:-1].strip()
                return enhanced
        except Exception as e:
            logger.warning(f"LLM transcription formatting fallback: {e}")

    # Fallback: if Uzbek specific Cyrillic letters exist, convert to Latin
    uz_specific = ["ў", "Ў", "ғ", "Ғ", "қ", "Қ", "ҳ", "Ҳ"]
    if any(c in clean_raw for c in uz_specific):
        return _fallback_cyrillic_to_latin_uz(clean_raw)

    return clean_raw


async def _transcribe_audio(audio_path: str) -> str:
    """Transcribe audio file to text using Whisper AI and format script."""
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

        raw_output_text = ""
        if prediction.get("status") == "succeeded":
            output = prediction.get("output", {})
            if isinstance(output, dict) and "text" in output:
                raw_output_text = output["text"].strip()
            elif isinstance(output, str):
                raw_output_text = output.strip()

        # Poll if not completed immediately
        if not raw_output_text and prediction.get("status") != "failed":
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
                        raw_output_text = out["text"].strip()
                    elif isinstance(out, str):
                        raw_output_text = out.strip()
                    break
                elif poll_data.get("status") == "failed":
                    raise RuntimeError(poll_data.get("error", "Whisper transcription failed"))

        if not raw_output_text:
            raise RuntimeError("Whisper returned empty output")

        # Post-process into proper Latin/Cyrillic depending on language
        final_text = await _format_and_clean_transcription(raw_output_text)
        return final_text


async def trigger_voice_to_text_flow(event: CallbackQuery | Message, bot: Bot):
    """Handle Voice to Text menu initiation."""
    if isinstance(event, CallbackQuery):
        await _safe_answer(event)
    user = event.from_user
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


@router.callback_query(F.data == "act_voice_to_text")
async def cb_voice_to_text_prompt(call: CallbackQuery, bot: Bot):
    """Handle Voice to Text menu button."""
    await trigger_voice_to_text_flow(call, bot)


@router.message(Command("voice"))
async def cmd_voice_to_text(message: Message, bot: Bot):
    """Handle /voice command."""
    await trigger_voice_to_text_flow(message, bot)


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
