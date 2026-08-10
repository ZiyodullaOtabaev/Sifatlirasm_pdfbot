"""
Text to PDF handler.
"""
import io
import logging

from aiogram import Router, Bot
from aiogram.types import Message, BufferedInputFile

from bot.database import upsert_user, inc_uses_and_log, get_user_language
from bot.i18n import t
from bot.keyboards import kb_main
from bot.states import get_state, set_state, STATE_WAIT_TEXT, STATE_NONE
from bot.utils.pdf import make_text_pdf_bytes
from bot.utils.helpers import user_pdf_filename
from bot.handlers.menu import enforce_subscription, show_main_menu

logger = logging.getLogger(__name__)
router = Router(name="text_pdf")


@router.message(lambda msg: msg.text and not msg.text.startswith("/") and get_state(msg.from_user.id) == STATE_WAIT_TEXT)
async def handle_text_pdf(message: Message, bot: Bot):
    """Convert user text to PDF."""
    user = message.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user_id) or "uz"

    if not await enforce_subscription(bot, user_id, lang):
        return

    text = (message.text or "").strip()
    if not text:
        return

    status = await message.answer(t("text_pdf_generating", lang))
    try:
        pdf_bytes = make_text_pdf_bytes(text)
        filename = user_pdf_filename(user)
        doc = BufferedInputFile(pdf_bytes, filename=filename)
        await bot.send_document(user_id, doc, caption=t("text_pdf_ready", lang), parse_mode="HTML")
        inc_uses_and_log(user_id, "text_pdf")
        logger.info(f"User {user_id}: text_pdf ({len(text)} chars)")
    except Exception as e:
        logger.error(f"Text PDF error for user {user_id}: {e}")
        from bot.utils.helpers import friendly_error
        await message.answer(friendly_error(e))
    finally:
        try:
            await status.delete()
        except Exception:
            pass

    set_state(user_id, STATE_NONE)
    await show_main_menu(bot, message.chat.id)