"""
/start command handler with language check.
"""
import logging

from aiogram import Router, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.database import upsert_user, get_user_language, process_referral
from bot.i18n import t
from bot.keyboards import kb_main, kb_language
from bot.states import set_state, STATE_NONE

logger = logging.getLogger(__name__)
router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    """Handle /start command with referral support."""
    user = message.from_user
    upsert_user(user.id, user.username, user.first_name, user.last_name)
    set_state(user.id, STATE_NONE)

    # Check deep link parameter e.g. /start ref_123456
    text_args = message.text.split()
    if len(text_args) > 1 and text_args[1].startswith("ref_"):
        try:
            referrer_id = int(text_args[1].replace("ref_", ""))
            if process_referral(user.id, referrer_id):
                ref_lang = get_user_language(referrer_id) or "uz"
                await bot.send_message(
                    referrer_id,
                    t("referral_bonus_notify", ref_lang),
                    parse_mode="HTML"
                )
                logger.info(f"User {user.id} was referred by {referrer_id}, bonus awarded.")
        except Exception as ref_err:
            logger.warning(f"Error processing referral link: {ref_err}")

    lang = get_user_language(user.id) or "uz"
    set_user_language(user.id, lang)
    await message.answer(t("welcome_text", lang), reply_markup=kb_main(lang), parse_mode="HTML")
    logger.info(f"User {user.id} ({user.username}) started bot [lang={lang}]")
