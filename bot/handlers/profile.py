"""
User profile and balance management handlers.
"""
import logging

from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from bot.database import get_user_language, get_uses, get_user_balance, get_referral_count
from bot.i18n import t
from bot.keyboards import kb_profile, kb_top_up
from bot.states import set_state, STATE_NONE

logger = logging.getLogger(__name__)
router = Router(name="profile")


async def _safe_answer(call: CallbackQuery):
    """Safely answer callback query."""
    try:
        await call.answer()
    except Exception:
        pass


@router.message(Command("profile"))
@router.callback_query(F.data == "act_profile")
async def show_user_profile(event: Message | CallbackQuery, bot: Bot):
    """Display user profile, balance, and referral link."""
    user_id = event.from_user.id
    if isinstance(event, CallbackQuery):
        await _safe_answer(event)

    set_state(user_id, STATE_NONE)
    lang = get_user_language(user_id) or "uz"
    uses_count = get_uses(user_id)
    balance = get_user_balance(user_id)
    ref_count = get_referral_count(user_id)

    me = await bot.get_me()
    bot_username = me.username or "unixziyodullabot"

    lang_names = {"uz": "O'zbekcha 🇺🇿", "ru": "Русский 🇷🇺", "en": "English 🇬🇧"}
    lang_name = lang_names.get(lang, "O'zbekcha 🇺🇿")

    text = t(
        "profile_text", lang,
        user_id=user_id,
        lang_name=lang_name,
        uses_count=uses_count,
        balance=balance,
        referral_count=ref_count,
        bot_username=bot_username
    )

    if isinstance(event, CallbackQuery):
        try:
            await bot.edit_message_text(
                text,
                chat_id=user_id,
                message_id=event.message.message_id,
                reply_markup=kb_profile(lang),
                parse_mode="HTML"
            )
            return
        except Exception:
            pass

    await bot.send_message(user_id, text, reply_markup=kb_profile(lang), parse_mode="HTML")


@router.callback_query(F.data == "act_show_top_up")
async def cb_show_top_up(call: CallbackQuery, bot: Bot):
    """Show top up balance info and pricing bundles."""
    await _safe_answer(call)
    user_id = call.from_user.id
    lang = get_user_language(user_id) or "uz"
    text = t("top_up_info", lang)

    try:
        await bot.edit_message_text(
            text,
            chat_id=user_id,
            message_id=call.message.message_id,
            reply_markup=kb_top_up(lang),
            parse_mode="HTML"
        )
    except Exception:
        await bot.send_message(user_id, text, reply_markup=kb_top_up(lang), parse_mode="HTML")


@router.callback_query(F.data == "act_share_ref")
async def cb_share_ref(call: CallbackQuery, bot: Bot):
    """Show dedicated referral sharing page with 1-click Telegram share button."""
    await _safe_answer(call)
    user_id = call.from_user.id
    lang = get_user_language(user_id) or "uz"
    ref_count = get_referral_count(user_id)

    me = await bot.get_me()
    bot_username = me.username or "unixziyodullabot"

    from urllib.parse import quote_plus
    from bot.keyboards import kb_referral

    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    share_msg = t("referral_share_msg", lang)
    share_url = f"https://t.me/share/url?url={quote_plus(ref_link)}&text={quote_plus(share_msg)}"

    text = t(
        "referral_page_text", lang,
        bot_username=bot_username,
        user_id=user_id,
        referral_count=ref_count
    )

    try:
        await bot.edit_message_text(
            text,
            chat_id=user_id,
            message_id=call.message.message_id,
            reply_markup=kb_referral(lang, share_url),
            parse_mode="HTML"
        )
    except Exception:
        await bot.send_message(user_id, text, reply_markup=kb_referral(lang, share_url), parse_mode="HTML")
