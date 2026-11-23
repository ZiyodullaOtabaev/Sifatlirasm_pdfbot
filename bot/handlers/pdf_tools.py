"""
PDF Tools Handlers:
1. PDF to Images (PDF -> JPG)
2. Watermark PDF
All 100% free, run locally on server without any paid APIs.
"""
import os
import logging
from typing import Dict, Any

from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, FSInputFile

from bot.config import DOWNLOAD_DIR, MAX_FILE_SIZE
from bot.database import upsert_user, inc_uses_and_log, get_user_language
from bot.i18n import t
from bot.keyboards import kb_cancel
from bot.states import (
    get_state, set_state, STATE_NONE,
    STATE_WAIT_PDF_TO_IMG,
    STATE_WAIT_WATERMARK_PDF, STATE_WAIT_WATERMARK_TEXT,
)
from bot.utils.pdf_tools import (
    pdf_to_images, watermark_pdf,
)
from bot.utils.helpers import safe_remove, friendly_error
from bot.handlers.menu import enforce_subscription, show_main_menu, _safe_answer

logger = logging.getLogger(__name__)
router = Router(name="pdf_tools")

# Session storage for multi-step tools: user_id -> {"path": str, "name": str, "total": int}
PENDING_PDF_SESSIONS: Dict[int, Dict[str, Any]] = {}


def cleanup_session(user_id: int):
    """Safely remove any session-stored pending PDF."""
    session = PENDING_PDF_SESSIONS.pop(user_id, None)
    if session and "path" in session:
        safe_remove(session["path"])


# ========================================================
# 1. CALLBACK QUERY ENTRY POINTS
# ========================================================

@router.callback_query(F.data == "act_pdf_to_img")
async def cb_pdf_to_img(call: CallbackQuery, bot: Bot):
    """Start PDF to image conversion flow."""
    await _safe_answer(call)
    user = call.from_user
    upsert_user(user.id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user.id) or "uz"
    if not await enforce_subscription(bot, user.id, lang):
        return
    cleanup_session(user.id)
    set_state(user.id, STATE_WAIT_PDF_TO_IMG)
    await bot.send_message(user.id, t("pdf_to_img_prompt", lang), parse_mode="HTML", reply_markup=kb_cancel(lang))


@router.callback_query(F.data == "act_watermark_pdf")
async def cb_watermark_pdf(call: CallbackQuery, bot: Bot):
    """Start Watermark PDF flow."""
    await _safe_answer(call)
    user = call.from_user
    upsert_user(user.id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user.id) or "uz"
    if not await enforce_subscription(bot, user.id, lang):
        return
    cleanup_session(user.id)
    set_state(user.id, STATE_WAIT_WATERMARK_PDF)
    await bot.send_message(user.id, t("watermark_prompt", lang), parse_mode="HTML", reply_markup=kb_cancel(lang))


# ========================================================
# 2. DOCUMENT HANDLERS FOR INITIAL PDF UPLOAD
# ========================================================

@router.message(lambda msg: msg.photo and get_state(msg.from_user.id) in (
    STATE_WAIT_PDF_TO_IMG,
    STATE_WAIT_WATERMARK_PDF,
))
async def handle_pdf_tool_photo_guard(message: Message):
    """Reject photos when waiting for a PDF file."""
    lang = get_user_language(message.from_user.id) or "uz"
    await message.answer(t("err_only_pdf", lang), parse_mode="HTML", reply_markup=kb_cancel(lang))


@router.message(lambda msg: msg.document and get_state(msg.from_user.id) in (
    STATE_WAIT_PDF_TO_IMG,
    STATE_WAIT_WATERMARK_PDF,
))
async def handle_pdf_tool_document(message: Message, bot: Bot):
    """Handle incoming PDF document for PDF to Image or Watermark."""
    user = message.from_user
    user_id = user.id
    lang = get_user_language(user_id) or "uz"
    state = get_state(user_id)

    if not await enforce_subscription(bot, user_id, lang):
        return

    doc = message.document
    file_name = (doc.file_name or "").lower()

    if doc.mime_type != "application/pdf" and not file_name.endswith(".pdf"):
        await message.answer(t("err_only_pdf", lang), parse_mode="HTML", reply_markup=kb_cancel(lang))
        return

    if doc.file_size and doc.file_size > MAX_FILE_SIZE:
        await message.answer(
            t("err_file_too_large", lang, max_mb=MAX_FILE_SIZE // (1024 * 1024)),
            parse_mode="HTML",
        )
        return

    file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{doc.file_id}.pdf")
    file = await bot.get_file(doc.file_id)
    await bot.download_file(file.file_path, file_path)

    # 1. PDF ➡️ Rasm
    if state == STATE_WAIT_PDF_TO_IMG:
        status = await message.answer(t("pdf_to_img_generating", lang), parse_mode="HTML")
        try:
            images, zip_path = pdf_to_images(file_path, DOWNLOAD_DIR)
            if not images:
                await message.answer(t("err_pdf_no_pages", lang), parse_mode="HTML")
                return

            await status.delete()

            # Agar sahifalar 5 tadan kam bo'lsa, rasmlarni alohida jo'natamiz
            if len(images) <= 5:
                for img_p in images:
                    await bot.send_document(user_id, FSInputFile(img_p))
            else:
                # Bir nechta dastlabki sahifalarni ko'rsatib, to'liq to'plamni ZIP qilib beramiz
                for img_p in images[:3]:
                    await bot.send_document(user_id, FSInputFile(img_p))
                if zip_path and os.path.exists(zip_path):
                    await bot.send_document(
                        user_id,
                        FSInputFile(zip_path, filename=f"{os.path.splitext(doc.file_name or 'pages')[0]}_images.zip"),
                        caption=t("pdf_to_img_zip_caption", lang, count=len(images)),
                        parse_mode="HTML"
                    )

            await message.answer(t("pdf_to_img_ready", lang), parse_mode="HTML")
            inc_uses_and_log(user_id, "pdf_to_img")
        except Exception as e:
            logger.error(f"Error in pdf_to_images for {user_id}: {e}")
            await message.answer(friendly_error(e, lang), parse_mode="HTML")
        finally:
            safe_remove(file_path)
            for img_p in images if 'images' in locals() else []:
                safe_remove(img_p)
            if 'zip_path' in locals() and zip_path:
                safe_remove(zip_path)
        set_state(user_id, STATE_NONE)
        await show_main_menu(bot, message.chat.id)
        return

    # 2. Watermark PDF
    from pypdf import PdfReader
    try:
        reader = PdfReader(file_path)
        total_pages = len(reader.pages)
    except Exception as e:
        safe_remove(file_path)
        await message.answer(t("err_pdf_unreadable", lang), parse_mode="HTML")
        set_state(user_id, STATE_NONE)
        return

    cleanup_session(user_id)
    PENDING_PDF_SESSIONS[user_id] = {
        "path": file_path,
        "name": doc.file_name or "document.pdf",
        "total": total_pages,
    }

    if state == STATE_WAIT_WATERMARK_PDF:
        set_state(user_id, STATE_WAIT_WATERMARK_TEXT)
        await message.answer(
            t("watermark_text_prompt", lang),
            parse_mode="HTML",
            reply_markup=kb_cancel(lang)
        )


# ========================================================
# 3. TEXT HANDLERS FOR WATERMARK OPERATION
# ========================================================

@router.message(lambda msg: msg.text and not msg.text.startswith("/") and get_state(msg.from_user.id) == STATE_WAIT_WATERMARK_TEXT)
async def handle_pdf_tool_text_input(message: Message, bot: Bot):
    """Handle the second step (text input) for Watermark."""
    user = message.from_user
    user_id = user.id
    lang = get_user_language(user_id) or "uz"
    text = (message.text or "").strip()

    # Cancel check
    if any(text == t("btn_home", l) for l in ("uz", "ru", "en")) or text in ("🏠 Bosh menyu", "❌ Bekor qilish", "Cancel", "Отмена"):
        cleanup_session(user_id)
        set_state(user_id, STATE_NONE)
        await show_main_menu(bot, message.chat.id)
        return

    session = PENDING_PDF_SESSIONS.get(user_id)
    if not session or not os.path.exists(session.get("path", "")):
        cleanup_session(user_id)
        set_state(user_id, STATE_NONE)
        await message.answer(t("err_pdf_not_found_restart", lang), parse_mode="HTML")
        await show_main_menu(bot, message.chat.id)
        return

    in_pdf = session["path"]
    doc_name = session["name"]
    base_name = os.path.splitext(doc_name)[0]

    out_pdf = os.path.join(DOWNLOAD_DIR, f"{user_id}_watermark.pdf")
    status = await message.answer(t("watermark_generating", lang), parse_mode="HTML")
    try:
        total = watermark_pdf(in_pdf, out_pdf, text)
        result_doc = FSInputFile(out_pdf, filename=f"watermarked_{base_name}.pdf")
        await bot.send_document(
            user_id,
            result_doc,
            caption=t("watermark_ready", lang).format(count=total),
            parse_mode="HTML"
        )
        inc_uses_and_log(user_id, "watermark_pdf")
        logger.info(f"User {user_id}: watermark_pdf ({total} pages)")
    except Exception as e:
        logger.error(f"Error in watermark_pdf for {user_id}: {e}")
        await message.answer(friendly_error(e, lang), parse_mode="HTML", reply_markup=kb_cancel(lang))
        try:
            await status.delete()
        except Exception:
            pass
        return
    finally:
        cleanup_session(user_id)
        safe_remove(out_pdf)
        try:
            await status.delete()
        except Exception:
            pass

    set_state(user_id, STATE_NONE)
    await show_main_menu(bot, message.chat.id)
