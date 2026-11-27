"""
/start command handler with language check.
"""
import logging

from aiogram import Router, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.database import (
    upsert_user, get_user_language, set_user_language,
    process_referral, record_ad_click, complete_telegram_link,
)
from bot.i18n import t
from bot.keyboards import kb_main, kb_main_reply, kb_language
from bot.states import set_state, STATE_NONE

logger = logging.getLogger(__name__)
router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    """Handle /start command with referral and UTM ad link tracking."""
    user = message.from_user
    is_new_user = upsert_user(user.id, user.username, user.first_name, user.last_name)
    set_state(user.id, STATE_NONE)

    # Check deep link parameter e.g. /start ref_123456 or /start ad_kanal1
    text_args = (message.text or "").split()
    if len(text_args) > 1:
        param = text_args[1].strip()
        if param.startswith("ref_"):
            try:
                referrer_id = int(param.replace("ref_", ""))
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
        elif param.startswith("ad_"):
            try:
                ad_code = param[3:]
                record_ad_click(ad_code, user.id, is_new_user)
                logger.info(f"User {user.id} came from ad link ad_{ad_code} (new={is_new_user})")
            except Exception as ad_err:
                logger.warning(f"Error processing ad link: {ad_err}")
        elif param.startswith("app_"):
            try:
                link_token = param[4:].strip()
                u_lang = get_user_language(user.id) or "uz"
                if complete_telegram_link(link_token, user.id):
                    link_msgs = {
                        "uz": (
                            "✅ <b>Mobil ilova hisobingiz Telegram profilingiz bilan muvaffaqiyatli ulandi!</b>\n\n"
                            "📱 Endi <b>Sifatli PDF</b> mobil ilovasiga qaytishingiz mumkin — VIP obuna va balanslaringiz sinxronlashdi!"
                        ),
                        "ru": (
                            "✅ <b>Мобильное приложение успешно привязано к вашему Telegram профилю!</b>\n\n"
                            "📱 Можете вернуться в приложение <b>Sifatli PDF</b> — ваш VIP-статус и баланс синхронизированы!"
                        ),
                        "en": (
                            "✅ <b>Mobile app successfully linked to your Telegram profile!</b>\n\n"
                            "📱 You can now return to the <b>Sifatli PDF</b> app — your VIP status and balance are synced!"
                        ),
                    }
                    await message.answer(link_msgs.get(u_lang, link_msgs["uz"]), parse_mode="HTML")
                    logger.info(f"User {user.id} linked mobile app via token")
            except Exception as app_err:
                logger.warning(f"Error processing mobile app link: {app_err}")

    lang = get_user_language(user.id) or "uz"
    set_user_language(user.id, lang)
    await message.answer(t("welcome_text", lang), reply_markup=kb_main_reply(lang), parse_mode="HTML")
    logger.info(f"User {user.id} ({user.username}) started bot [lang={lang}]")
