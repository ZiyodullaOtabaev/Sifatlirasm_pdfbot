"""
PDF compress handler — reduce file size without quality loss.
"""
import os
import logging

from aiogram import Router, Bot
from aiogram.types import Message, FSInputFile

from bot.config import DOWNLOAD_DIR, MAX_FILE_SIZE
from bot.database import upsert_user, inc_uses_and_log
from bot.keyboards import kb_cancel
from bot.states import get_state, STATE_WAIT_COMPRESS_PDF
from bot.utils.image import compress_pdf
from bot.utils.helpers import safe_remove, user_pdf_filename
from bot.handlers.menu import enforce_subscription, show_main_menu

logger = logging.getLogger(__name__)
router = Router(name="compress")


@router.message(lambda msg: msg.photo and get_state(msg.from_user.id) == STATE_WAIT_COMPRESS_PDF)
async def handle_compress_photo_error(message: Message, bot: Bot):
    """Reject photos in compress mode."""
    await message.answer("❌ Faqat PDF fayl yuboring, rasm emas.", reply_markup=kb_cancel())


@router.message(lambda msg: msg.document and get_state(msg.from_user.id) == STATE_WAIT_COMPRESS_PDF)
async def handle_compress_pdf(message: Message, bot: Bot):
    """Handle document for PDF compression."""
    user = message.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)

    if not await enforce_subscription(bot, user_id):
        return

    doc = message.document
    file_name = (doc.file_name or "").lower()

    # Faqat PDF qabul qilish
    if doc.mime_type != "application/pdf" and not file_name.endswith(".pdf"):
        await message.answer("❌ Faqat PDF fayl yuboring.", reply_markup=kb_cancel())
        return

    if doc.file_size and doc.file_size > MAX_FILE_SIZE:
        await message.answer(f"❌ Fayl hajmi juda katta (max {MAX_FILE_SIZE // (1024*1024)}MB).")
        return

    file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{doc.file_id}.pdf")
    file = await bot.get_file(doc.file_id)
    await bot.download_file(file.file_path, file_path)

    status = await message.answer("🗜 PDF siqilmoqda...")
    out_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{doc.file_id}_compressed.pdf")
    try:
        compress_pdf(file_path, out_path)

        # Hajm farqini ko'rsatish
        original_size = os.path.getsize(file_path)
        compressed_size = os.path.getsize(out_path)
        saved_pct = round((1 - compressed_size / original_size) * 100, 1) if original_size > 0 else 0

        if saved_pct <= 0:
            await message.answer("ℹ️ Bu PDF allaqachon optimallashtirilgan — siqib bo'lmadi.")
        else:
            result = FSInputFile(out_path, filename=f"compressed_{doc.file_name or 'file.pdf'}")
            caption = (
                f"✅ PDF siqildi!\n\n"
                f"📁 Oldingi: {original_size // 1024} KB\n"
                f"📦 Hozirgi: {compressed_size // 1024} KB\n"
                f"💾 Tejaldi: {saved_pct}%"
            )
            await bot.send_document(user_id, result, caption=caption)
            inc_uses_and_log(user_id, "compress_pdf")
            logger.info(f"User {user_id}: compress_pdf ({saved_pct}% saved)")
    except Exception as e:
        logger.error(f"Compress PDF error for user {user_id}: {e}")
        from bot.utils.helpers import friendly_error
        await message.answer(friendly_error(e))
    finally:
        safe_remove(file_path)
        safe_remove(out_path)
        try:
            await status.delete()
        except Exception:
            pass
    await show_main_menu(bot, message.chat.id)
