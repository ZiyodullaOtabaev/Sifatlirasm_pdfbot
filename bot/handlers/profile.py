"""
User profile and balance management handlers.
"""
import logging

from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from bot.config import DAILY_FREE_LIMIT, ADMIN_IDS
from bot.database import (
    get_user_language, get_uses, get_referral_count, get_total_users_count,
    get_user_daily_uses, get_user_balance, get_vip_until,
)
from bot.i18n import t
from bot.keyboards import kb_profile, kb_vip_plans
from bot.states import set_state, STATE_NONE

logger = logging.getLogger(__name__)
router = Router(name="profile")


async def _safe_answer(call: CallbackQuery):
    """Safely answer callback query."""
    try:
        await call.answer()
    except Exception:
        pass


def format_vip_status(user_id: int, lang: str = "uz") -> str:
    """Return localized VIP status string for user."""
    if user_id in ADMIN_IDS:
        return "👑 Admin (VIP ∞)"
    vip_until = get_vip_until(user_id)
    if vip_until:
        if lang == "ru":
            return f"💎 VIP (до {vip_until})"
        elif lang == "en":
            return f"💎 VIP (until {vip_until})"
        return f"💎 VIP ({vip_until} gacha)"
    if lang == "ru":
        return "🆓 Обычный (Бесплатный)"
    elif lang == "en":
        return "🆓 Free Plan"
    return "🆓 Oddiy (Bepul)"


@router.message(Command("profile"))
@router.callback_query(F.data == "act_profile")
async def show_user_profile(event: Message | CallbackQuery, bot: Bot):
    """Display user profile and referral link."""
    user_id = event.from_user.id
    if isinstance(event, CallbackQuery):
        await _safe_answer(event)

    set_state(user_id, STATE_NONE)
    lang = get_user_language(user_id) or "uz"
    uses_count = get_uses(user_id)
    ref_count = get_referral_count(user_id)
    total_users = get_total_users_count()
    daily_used = min(get_user_daily_uses(user_id), DAILY_FREE_LIMIT)
    bonus_balance = get_user_balance(user_id)
    vip_status = format_vip_status(user_id, lang)

    me = await bot.get_me()
    bot_username = me.username or "sifatlirasm_pdfbot"

    lang_names = {"uz": "O'zbekcha 🇺🇿", "ru": "Русский 🇷🇺", "en": "English 🇬🇧"}
    lang_name = lang_names.get(lang, "O'zbekcha 🇺🇿")

    text = t(
        "profile_text", lang,
        user_id=user_id,
        lang_name=lang_name,
        vip_status=vip_status,
        daily_used=daily_used,
        daily_limit=DAILY_FREE_LIMIT,
        bonus_balance=bonus_balance,
        uses_count=uses_count,
        referral_count=ref_count,
        bot_username=bot_username,
        total_users=total_users
    )

    if isinstance(event, CallbackQuery):
        try:
            await bot.edit_message_text(
                text,
                chat_id=user_id,
                message_id=event.message.message_id,
                reply_markup=kb_profile(lang, total_users),
                parse_mode="HTML"
            )
            return
        except Exception:
            pass

    await bot.send_message(user_id, text, reply_markup=kb_profile(lang, total_users), parse_mode="HTML")


@router.message(Command("vip"))
@router.callback_query(F.data == "act_vip")
async def show_vip_info(event: Message | CallbackQuery, bot: Bot):
    """Display VIP subscription options and current limits."""
    user_id = event.from_user.id
    if isinstance(event, CallbackQuery):
        await _safe_answer(event)

    set_state(user_id, STATE_NONE)
    lang = get_user_language(user_id) or "uz"
    daily_used = min(get_user_daily_uses(user_id), DAILY_FREE_LIMIT)
    bonus_balance = get_user_balance(user_id)
    vip_status = format_vip_status(user_id, lang)

    text = t(
        "vip_info_text", lang,
        vip_status=vip_status,
        daily_used=daily_used,
        daily_limit=DAILY_FREE_LIMIT,
        bonus_balance=bonus_balance,
    )

    if isinstance(event, CallbackQuery):
        try:
            await bot.edit_message_text(
                text,
                chat_id=user_id,
                message_id=event.message.message_id,
                reply_markup=kb_vip_plans(lang),
                parse_mode="HTML"
            )
            return
        except Exception:
            pass

    await bot.send_message(user_id, text, reply_markup=kb_vip_plans(lang), parse_mode="HTML")


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
