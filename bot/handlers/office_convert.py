"""
Office <-> PDF Conversion Handlers (100% Free Server-Local, 3-language localized):
1. PDF -> Word (.docx)
2. Word / Excel / PowerPoint -> PDF
Integrated with dynamic Free daily limit & VIP unlimited pass, plus immediate disk cleanup.
"""
import os
import shutil
import asyncio
import logging
import tempfile
from pathlib import Path

from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, FSInputFile

from bot.config import DOWNLOAD_DIR, MAX_FILE_SIZE
from bot.database import upsert_user, inc_uses_and_log, get_user_language
from bot.i18n import t
from bot.keyboards import kb_cancel
from bot.states import (
    get_state, set_state, STATE_NONE,
    STATE_WAIT_PDF_TO_WORD, STATE_WAIT_OFFICE_TO_PDF,
)
from bot.utils.office_tools import pdf_to_word, office_to_pdf, SUPPORTED_OFFICE_EXTS
from bot.utils.helpers import safe_remove, friendly_error
from bot.handlers.menu import enforce_subscription, show_main_menu, _safe_answer

logger = logging.getLogger(__name__)
router = Router(name="office_convert")

# Limit heavy concurrent conversions to 2 at a time so bot remains fast under load
CONVERSION_SEMAPHORE = asyncio.Semaphore(2)


# ========================================================
# 1. CALLBACK ENTRY POINTS
# ========================================================

@router.callback_query(F.data == "act_pdf_to_word")
async def cb_pdf_to_word(call: CallbackQuery, bot: Bot):
    """Start PDF -> Word conversion flow."""
    await _safe_answer(call)
    user = call.from_user
    upsert_user(user.id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user.id) or "uz"
    if not await enforce_subscription(bot, user.id, lang):
        return
    set_state(user.id, STATE_WAIT_PDF_TO_WORD)
    await bot.send_message(
        user.id,
        t("pdf_to_word_prompt", lang),
        parse_mode="HTML",
        reply_markup=kb_cancel(lang),
    )


@router.callback_query(F.data == "act_office_to_pdf")
async def cb_office_to_pdf(call: CallbackQuery, bot: Bot):
    """Start Word / Excel / PowerPoint -> PDF conversion flow."""
    await _safe_answer(call)
    user = call.from_user
    upsert_user(user.id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user.id) or "uz"
    if not await enforce_subscription(bot, user.id, lang):
        return
    set_state(user.id, STATE_WAIT_OFFICE_TO_PDF)
    await bot.send_message(
        user.id,
        t("office_to_pdf_prompt", lang),
        parse_mode="HTML",
        reply_markup=kb_cancel(lang),
    )


# ========================================================
# 2. WRONG MEDIA TYPE GUARD (Photo sent instead of file)
# ========================================================

@router.message(lambda msg: msg.photo and get_state(msg.from_user.id) == STATE_WAIT_PDF_TO_WORD)
async def handle_pdf_to_word_photo_guard(message: Message):
    lang = get_user_language(message.from_user.id) or "uz"
    await message.answer(t("err_only_pdf", lang), parse_mode="HTML", reply_markup=kb_cancel(lang))


@router.message(lambda msg: msg.photo and get_state(msg.from_user.id) == STATE_WAIT_OFFICE_TO_PDF)
async def handle_office_to_pdf_photo_guard(message: Message):
    lang = get_user_language(message.from_user.id) or "uz"
    await message.answer(t("err_only_office_file", lang), parse_mode="HTML", reply_markup=kb_cancel(lang))


_MAIN_MENU_KEYS = (
    "btn_home", "btn_img_pdf", "btn_text_pdf", "btn_pdf_to_word", "btn_office_to_pdf",
    "btn_merge_pdf", "btn_compress_pdf", "btn_pdf_to_img", "btn_watermark_pdf",
    "btn_profile", "btn_vip", "btn_ads", "btn_donate", "btn_change_lang",
)


@router.message(
    lambda msg: msg.text and not msg.text.startswith("/")
    and get_state(msg.from_user.id) in (STATE_WAIT_PDF_TO_WORD, STATE_WAIT_OFFICE_TO_PDF)
)
async def handle_office_text_or_menu_switch(message: Message, bot: Bot):
    """Allow switching menu buttons cleanly or remind user to send the expected file."""
    user_id = message.from_user.id
    state = get_state(user_id)
    lang = get_user_language(user_id) or "uz"
    text = (message.text or "").strip()

    is_menu_btn = any(
        text == t(key, l) for key in _MAIN_MENU_KEYS for l in ("uz", "ru", "en")
    ) or text in ("🏠 Bosh menyu", "🏠 Главное меню", "🏠 Main Menu", "❌ Bekor qilish", "❌ Отмена", "❌ Cancel")

    if is_menu_btn:
        set_state(user_id, STATE_NONE)
        from bot.handlers.menu import handle_reply_menu_or_fallback
        await handle_reply_menu_or_fallback(message, bot)
        return

    err_key = "err_only_pdf" if state == STATE_WAIT_PDF_TO_WORD else "err_only_office_file"
    await message.answer(t(err_key, lang), parse_mode="HTML", reply_markup=kb_cancel(lang))


# ========================================================
# 3. PDF -> WORD (.docx) DOCUMENT HANDLER
# ========================================================

@router.message(lambda msg: msg.document and get_state(msg.from_user.id) == STATE_WAIT_PDF_TO_WORD)
async def handle_pdf_to_word_document(message: Message, bot: Bot):
    """Convert uploaded PDF into editable Word (.docx)."""
    user = message.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user_id) or "uz"

    if not await enforce_subscription(bot, user_id, lang):
        return

    doc = message.document
    file_name = doc.file_name or "document.pdf"
    if doc.mime_type != "application/pdf" and not file_name.lower().endswith(".pdf"):
        await message.answer(t("err_only_pdf", lang), parse_mode="HTML", reply_markup=kb_cancel(lang))
        return

    if doc.file_size and doc.file_size > MAX_FILE_SIZE:
        await message.answer(
            t("err_file_too_large", lang, max_mb=MAX_FILE_SIZE // (1024 * 1024)),
            parse_mode="HTML",
            reply_markup=kb_cancel(lang),
        )
        return

    in_pdf = os.path.join(DOWNLOAD_DIR, f"{user_id}_{doc.file_unique_id}.pdf")
    out_docx = os.path.join(DOWNLOAD_DIR, f"{user_id}_{doc.file_unique_id}.docx")
    base_name = Path(file_name).stem or "document"

    status = await message.answer(t("pdf_to_word_generating", lang), parse_mode="HTML")
    try:
        tg_file = await bot.get_file(doc.file_id)
        await bot.download_file(tg_file.file_path, in_pdf)

        async with CONVERSION_SEMAPHORE:
            pages, is_scanned = await asyncio.to_thread(pdf_to_word, in_pdf, out_docx)

        caption = t("pdf_to_word_ready", lang, pages=pages)
        if is_scanned:
            caption += t("pdf_to_word_scanned_note", lang)

        result_file = FSInputFile(out_docx, filename=f"{base_name}.docx")
        await bot.send_document(user_id, result_file, caption=caption, parse_mode="HTML")
        inc_uses_and_log(user_id, "pdf_to_word")
        logger.info(f"User {user_id}: pdf_to_word ({pages} pages, scanned={is_scanned})")
    except Exception as e:
        logger.error(f"PDF->Word error for user {user_id}: {e}")
        await message.answer(friendly_error(e, lang), parse_mode="HTML")
    finally:
        safe_remove(in_pdf)
        safe_remove(out_docx)
        try:
            await status.delete()
        except Exception:
            pass

    set_state(user_id, STATE_NONE)
    await show_main_menu(bot, message.chat.id)


# ========================================================
# 4. WORD / EXCEL / POWERPOINT -> PDF DOCUMENT HANDLER
# ========================================================

@router.message(lambda msg: msg.document and get_state(msg.from_user.id) == STATE_WAIT_OFFICE_TO_PDF)
async def handle_office_to_pdf_document(message: Message, bot: Bot):
    """Convert uploaded Word/Excel/PowerPoint document into high-fidelity PDF."""
    user = message.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user_id) or "uz"

    if not await enforce_subscription(bot, user_id, lang):
        return

    doc = message.document
    file_name = doc.file_name or ""
    ext = Path(file_name).suffix.lower()
    if ext not in SUPPORTED_OFFICE_EXTS:
        await message.answer(t("err_only_office_file", lang), parse_mode="HTML", reply_markup=kb_cancel(lang))
        return

    if doc.file_size and doc.file_size > MAX_FILE_SIZE:
        await message.answer(
            t("err_file_too_large", lang, max_mb=MAX_FILE_SIZE // (1024 * 1024)),
            parse_mode="HTML",
            reply_markup=kb_cancel(lang),
        )
        return

    job_dir = tempfile.mkdtemp(prefix=f"office_{user_id}_", dir=DOWNLOAD_DIR)
    in_path = os.path.join(job_dir, f"input{ext}")
    base_name = Path(file_name).stem or "document"

    status = await message.answer(t("office_to_pdf_generating", lang), parse_mode="HTML")
    try:
        tg_file = await bot.get_file(doc.file_id)
        await bot.download_file(tg_file.file_path, in_path)

        async with CONVERSION_SEMAPHORE:
            out_pdf = await asyncio.to_thread(office_to_pdf, in_path, job_dir)

        result_file = FSInputFile(out_pdf, filename=f"{base_name}.pdf")
        await bot.send_document(
            user_id,
            result_file,
            caption=t("office_to_pdf_ready", lang),
            parse_mode="HTML",
        )
        inc_uses_and_log(user_id, "office_to_pdf")
        logger.info(f"User {user_id}: office_to_pdf ({ext})")
    except Exception as e:
        logger.error(f"Office->PDF error for user {user_id}: {e}")
        await message.answer(friendly_error(e, lang), parse_mode="HTML")
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)
        try:
            await status.delete()
        except Exception:
            pass

    set_state(user_id, STATE_NONE)
    await show_main_menu(bot, message.chat.id)
