"""
User profile and balance management handlers.
"""
import logging

from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from bot.config import ADMIN_IDS
from bot.database import (
    get_user_language, get_uses, get_referral_count, get_total_users_count,
    get_user_daily_uses, get_user_balance, get_vip_until,
    get_daily_free_limit, get_vip_prices, redeem_promo_code,
)
from bot.i18n import t
from bot.keyboards import kb_profile, kb_vip_plans, kb_cancel, kb_main_reply
from bot.states import get_state, set_state, STATE_NONE, STATE_WAIT_PROMO_INPUT

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
    daily_limit = get_daily_free_limit()
    daily_used = get_user_daily_uses(user_id)
    if daily_limit > 0:
        daily_used = min(daily_used, daily_limit)
    daily_limit_str = "∞" if daily_limit == 0 else daily_limit
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
        daily_limit=daily_limit_str,
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
    daily_limit = get_daily_free_limit()
    daily_used = get_user_daily_uses(user_id)
    if daily_limit > 0:
        daily_used = min(daily_used, daily_limit)
    daily_limit_str = "∞" if daily_limit == 0 else daily_limit
    bonus_balance = get_user_balance(user_id)
    vip_status = format_vip_status(user_id, lang)
    p = get_vip_prices()

    text = t(
        "vip_info_text", lang,
        vip_status=vip_status,
        daily_used=daily_used,
        daily_limit=daily_limit_str,
        bonus_balance=bonus_balance,
        uzs_30=f"{p['uzs_30']:,}".replace(",", " "),
        uzs_365=f"{p['uzs_365']:,}".replace(",", " "),
        stars_30=p["stars_30"],
        stars_365=p["stars_365"],
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


# ========================
# PROMO CODE REDEMPTION
# ========================

async def _process_promo_redemption(message: Message, bot: Bot, code: str):
    """Attempt to redeem a promo code and reply in user's language."""
    user_id = message.from_user.id
    lang = get_user_language(user_id) or "uz"
    ok, status, info = redeem_promo_code(user_id, code)
    set_state(user_id, STATE_NONE)

    if ok:
        if info["reward_type"] == "vip_days":
            reply_text = t("promo_success_vip", lang, value=info["reward_value"], vip_until=info.get("vip_until", ""))
        else:
            reply_text = t("promo_success_bonus", lang, value=info["reward_value"], new_balance=info.get("new_balance", 0))
        await message.answer(reply_text, parse_mode="HTML", reply_markup=kb_main_reply(lang))
    else:
        key_map = {
            "not_found": "promo_not_found",
            "inactive": "promo_inactive",
            "exhausted": "promo_exhausted",
            "already_used": "promo_already_used",
        }
        await message.answer(t(key_map.get(status, "promo_not_found"), lang), parse_mode="HTML", reply_markup=kb_main_reply(lang))


@router.message(Command("promo"))
async def cmd_promo(message: Message, bot: Bot):
    """Handle /promo or /promo <CODE>."""
    user_id = message.from_user.id
    lang = get_user_language(user_id) or "uz"
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) > 1 and parts[1].strip():
        await _process_promo_redemption(message, bot, parts[1].strip())
        return
    set_state(user_id, STATE_WAIT_PROMO_INPUT)
    await message.answer(t("promo_prompt", lang), parse_mode="HTML", reply_markup=kb_cancel(lang))


@router.callback_query(F.data == "act_promo")
async def cb_promo_prompt(call: CallbackQuery, bot: Bot):
    """Prompt user to enter promo code from Profile or VIP menu."""
    await _safe_answer(call)
    user_id = call.from_user.id
    lang = get_user_language(user_id) or "uz"
    set_state(user_id, STATE_WAIT_PROMO_INPUT)
    await bot.send_message(user_id, t("promo_prompt", lang), parse_mode="HTML", reply_markup=kb_cancel(lang))


@router.message(lambda msg: msg.text and not msg.text.startswith("/") and get_state(msg.from_user.id) == STATE_WAIT_PROMO_INPUT)
async def handle_promo_code_input(message: Message, bot: Bot):
    """Redeem promo code typed by user."""
    text = (message.text or "").strip()
    if any(text == t("btn_home", l) for l in ("uz", "ru", "en")) or text in ("🏠 Bosh menyu", "❌ Bekor qilish", "Cancel", "Отмена"):
        set_state(message.from_user.id, STATE_NONE)
        from bot.handlers.menu import show_main_menu
        await show_main_menu(bot, message.chat.id)
        return
    await _process_promo_redemption(message, bot, text)
