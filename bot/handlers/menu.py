"""
Menu navigation and subscription check handlers with multi-language support.
"""
import logging

from aiogram import Router, Bot, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from bot.config import CHANNEL_USER, FREE_USES_BEFORE_SUB
from bot.database import upsert_user, get_uses, get_user_language, set_user_language
from bot.i18n import t
from bot.keyboards import kb_main, kb_subscribe, kb_cancel, kb_language
from bot.states import (
    set_state, STATE_NONE, STATE_WAIT_TEXT,
    STATE_WAIT_IMG_PDF, STATE_WAIT_UPSCALE, STATE_WAIT_PDF_MERGE,
    STATE_WAIT_BG_REMOVE, STATE_WAIT_AI_IMAGE, STATE_WAIT_OCR,
    STATE_WAIT_COMPRESS_PDF,
)

logger = logging.getLogger(__name__)
router = Router(name="menu")


async def _safe_answer(call: CallbackQuery):
    """Safely answer callback query without raising timeout errors."""
    try:
        await call.answer()
    except Exception:
        pass


async def check_user_subscriptions(bot: Bot, user_id: int) -> tuple[bool, list[dict]]:
    """
    Check if user is subscribed to all active required channels.
    Returns: (is_all_subscribed, list_of_unjoined_channels)
    """
    from bot.database import get_active_channels, record_channel_join
    from bot.config import ADMIN_IDS, ADMIN_ID

    channels = get_active_channels()
    if not channels:
        # Fallback to CHANNEL_USER if configured
        if CHANNEL_USER:
            try:
                member = await bot.get_chat_member(chat_id=CHANNEL_USER, user_id=user_id)
                if member.status in ("left", "kicked"):
                    return False, [{"channel_id": CHANNEL_USER, "channel_title": CHANNEL_USER, "invite_link": f"https://t.me/{CHANNEL_USER.lstrip('@')}"}]
            except Exception:
                pass
        return True, []

    unjoined = []
    joined_channels = []

    for ch in channels:
        ch_id = ch["channel_id"]
        try:
            member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            if member.status in ("left", "kicked"):
                unjoined.append(ch)
            else:
                joined_channels.append(ch)
        except Exception as e:
            logger.warning(f"Could not verify membership in {ch_id} for user {user_id}: {e}")
            # If bot cannot check (e.g. not admin), do not block user
            joined_channels.append(ch)

    if unjoined:
        return False, unjoined

    # If all joined, record join counts and check auto-detach targets
    admin_list = list(ADMIN_IDS) if ADMIN_IDS else ([ADMIN_ID] if ADMIN_ID else [])
    for ch in joined_channels:
        ch_id = ch["channel_id"]
        is_new, target_reached, cur_subs, target = record_channel_join(ch_id, user_id)
        if target_reached:
            title = ch.get("channel_title") or ch_id
            alert_text = (
                f"🎯 <b>Kanal Obunachi Maqsadi Bajarildi!</b>\n\n"
                f"📢 Kanal: <b>{title}</b> ({ch_id})\n"
                f"👥 Yig'ilgan obunachilar: <b>{cur_subs}/{target} ta</b>\n\n"
                f"✅ Ushbu kanal majburiy obuna ro'yxatidan <b>avtomatik tarzda uzildi!</b>"
            )
            for adm in set(admin_list):
                try:
                    await bot.send_message(adm, alert_text, parse_mode="HTML")
                except Exception:
                    pass

    return True, []


async def check_subscription(bot: Bot, user_id: int) -> bool:
    """Backward-compatible helper."""
    ok, _ = await check_user_subscriptions(bot, user_id)
    return ok


async def enforce_subscription(bot: Bot, user_id: int, lang: str = "uz") -> bool:
    """Check if user can use the service."""
    uses = get_uses(user_id)
    if uses < FREE_USES_BEFORE_SUB:
        return True

    from bot.keyboards import kb_required_channels

    ok, unjoined = await check_user_subscriptions(bot, user_id)
    if ok:
        return True

    await bot.send_message(
        user_id,
        t("sub_required", lang),
        parse_mode="HTML",
        reply_markup=kb_required_channels(unjoined, lang)
    )
    return False


async def show_main_menu(bot: Bot, chat_id: int, message_id: int = None):
    """Show or edit the main menu in user's chosen language."""
    set_state(chat_id, STATE_NONE)
    lang = get_user_language(chat_id) or "uz"
    text = t("welcome_text", lang)

    if message_id:
        try:
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=message_id,
                reply_markup=kb_main(lang), parse_mode="HTML"
            )
            return
        except Exception:
            pass
    await bot.send_message(chat_id, text, reply_markup=kb_main(lang), parse_mode="HTML")


# ========================
# LANGUAGE SELECTION HANDLERS
# ========================

@router.callback_query(F.data.startswith("set_lang_"))
async def cb_set_language(call: CallbackQuery, bot: Bot):
    """Handle language selection."""
    await _safe_answer(call)
    user_id = call.from_user.id
    lang_code = call.data.replace("set_lang_", "") # 'uz', 'ru', 'en'
    if lang_code not in ("uz", "ru", "en"):
        lang_code = "uz"

    set_user_language(user_id, lang_code)
    await bot.send_message(
        user_id,
        t("lang_selected", lang_code),
        parse_mode="HTML"
    )
    await show_main_menu(bot, call.message.chat.id)


@router.callback_query(F.data == "act_change_lang")
async def cb_change_language(call: CallbackQuery, bot: Bot):
    """Prompt user to select language."""
    await _safe_answer(call)
    lang = get_user_language(call.from_user.id) or "uz"
    await bot.send_message(
        call.from_user.id,
        t("lang_select_prompt", lang),
        reply_markup=kb_language(),
        parse_mode="HTML"
    )


# ========================
# NAVIGATION CALLBACKS
# ========================

@router.callback_query(F.data == "act_cancel")
async def cb_cancel(call: CallbackQuery, bot: Bot):
    """Handle cancel/back to menu."""
    await _safe_answer(call)
    set_state(call.from_user.id, STATE_NONE)
    await show_main_menu(bot, call.message.chat.id, call.message.message_id)


@router.callback_query(F.data == "act_check_sub")
async def cb_check_sub(call: CallbackQuery, bot: Bot):
    """Handle subscription check button."""
    await _safe_answer(call)
    lang = get_user_language(call.from_user.id) or "uz"
    from bot.keyboards import kb_required_channels

    ok, unjoined = await check_user_subscriptions(bot, call.from_user.id)
    if ok:
        await bot.send_message(call.from_user.id, "✅ <b>Obuna tasdiqlandi! Xush kelibsiz!</b>", parse_mode="HTML")
        await show_main_menu(bot, call.message.chat.id, call.message.message_id)
    else:
        await bot.send_message(
            call.from_user.id,
            t("sub_not_yet", lang),
            parse_mode="HTML",
            reply_markup=kb_required_channels(unjoined, lang)
        )


@router.callback_query(F.data == "act_text_pdf")
async def cb_text_pdf(call: CallbackQuery, bot: Bot):
    """Start text-to-PDF flow."""
    await _safe_answer(call)
    user = call.from_user
    upsert_user(user.id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user.id) or "uz"
    if not await enforce_subscription(bot, user.id, lang):
        return
    set_state(user.id, STATE_WAIT_TEXT)
    await bot.send_message(user.id, t("text_pdf_prompt", lang),
                           reply_markup=kb_cancel(lang))


@router.callback_query(F.data == "act_img_pdf")
async def cb_img_pdf(call: CallbackQuery, bot: Bot):
    """Start image-to-PDF flow."""
    await _safe_answer(call)
    user = call.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user_id) or "uz"
    if not await enforce_subscription(bot, user_id, lang):
        return

    from bot.database import get_user_img_pdf_count, has_active_img_pdf_pass
    from bot.keyboards import kb_top_up_img_pdf

    has_pass = has_active_img_pdf_pass(user_id)
    cnt = get_user_img_pdf_count(user_id)

    if not has_pass and cnt >= 50:
        if lang == "ru":
            limit_msg = (
                "🖼 <b>Фото ➡️ PDF (Безлимит на 1 год)</b>\n\n"
                "📌 Вы использовали все <b>50 бесплатных</b> конвертаций.\n\n"
                "Чтобы использовать эту функцию <b>БЕЗЛИМИТНО в течение 1 ГОДА (365 дней)</b>, оплатите <b>5 000 сум (или ⭐️ 50 Stars)</b> 👇"
            )
        elif lang == "en":
            limit_msg = (
                "🖼 <b>Image ➡️ PDF (1-Year Unlimited Pass)</b>\n\n"
                "📌 You have used all <b>50 free</b> conversions.\n\n"
                "To use this feature <b>UNLIMITED for 1 YEAR (365 days)</b>, purchase the pass for <b>5,000 UZS (or ⭐️ 50 Stars)</b> 👇"
            )
        else:
            limit_msg = (
                "🖼 <b>Rasm ➡️ PDF (1 Yillik Cheksiz Pass)</b>\n\n"
                "📌 Siz dastlabki <b>50 ta bepul</b> rasmni PDF qilish limitidan to'liq foydalandingiz.\n\n"
                "Buyog'iga ushbu xizmatni <b>1 YIL (365 kun) davomida BUTUNLAY CHEKSIZ</b> ishlatish uchun <b>5 000 so'm (yoki ⭐️ 50 Stars)</b> to'lov qiling 👇"
            )
        await bot.send_message(
            user_id,
            limit_msg,
            parse_mode="HTML",
            reply_markup=kb_top_up_img_pdf(lang)
        )
        return

    status_note = ""
    if has_pass:
        status_note = "\n\n💎 <i>(1-Годовой VIP Pass активен!)</i>" if lang == "ru" else "\n\n💎 <i>(1-Year VIP Pass active!)</i>" if lang == "en" else "\n\n💎 <i>(Sizda 1 Yillik Cheksiz VIP Pass faol!)</i>"
    else:
        status_note = f"\n\n🎁 <i>(Бесплатный лимит: {cnt}/50)</i>" if lang == "ru" else f"\n\n🎁 <i>(Free trial: {cnt}/50)</i>" if lang == "en" else f"\n\n🎁 <i>(Bepul limit: {cnt}/50)</i>"

    set_state(user_id, STATE_WAIT_IMG_PDF)
    await bot.send_message(user_id, t("img_pdf_prompt", lang) + status_note,
                           parse_mode="HTML",
                           reply_markup=kb_cancel(lang))


@router.callback_query(F.data == "act_upscale")
async def cb_upscale(call: CallbackQuery, bot: Bot):
    """Start upscale flow."""
    await _safe_answer(call)
    user = call.from_user
    upsert_user(user.id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user.id) or "uz"
    if not await enforce_subscription(bot, user.id, lang):
        return
    set_state(user.id, STATE_WAIT_UPSCALE)
    await bot.send_message(user.id, t("upscale_prompt", lang),
                           parse_mode="HTML", reply_markup=kb_cancel(lang))


@router.callback_query(F.data == "act_merge_pdf")
async def cb_merge_pdf(call: CallbackQuery, bot: Bot):
    """Start PDF merge flow."""
    await _safe_answer(call)
    user = call.from_user
    upsert_user(user.id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user.id) or "uz"
    if not await enforce_subscription(bot, user.id, lang):
        return
    set_state(user.id, STATE_WAIT_PDF_MERGE)
    await bot.send_message(user.id, t("merge_pdf_prompt", lang),
                           reply_markup=kb_cancel(lang))


@router.callback_query(F.data == "act_compress_pdf")
async def cb_compress_pdf(call: CallbackQuery, bot: Bot):
    """Start PDF compress flow."""
    await _safe_answer(call)
    user = call.from_user
    upsert_user(user.id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user.id) or "uz"
    if not await enforce_subscription(bot, user.id, lang):
        return
    set_state(user.id, STATE_WAIT_COMPRESS_PDF)
    await bot.send_message(user.id, t("compress_pdf_prompt", lang),
                           reply_markup=kb_cancel(lang))


@router.callback_query(F.data == "act_bg_remove")
async def cb_bg_remove(call: CallbackQuery, bot: Bot):
    """Start background remove flow."""
    await _safe_answer(call)
    user = call.from_user
    upsert_user(user.id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user.id) or "uz"
    if not await enforce_subscription(bot, user.id, lang):
        return
    set_state(user.id, STATE_WAIT_BG_REMOVE)
    await bot.send_message(user.id, t("bg_remove_prompt", lang),
                           parse_mode="HTML", reply_markup=kb_cancel(lang))


@router.callback_query(F.data == "act_ai_image")
async def cb_ai_image(call: CallbackQuery, bot: Bot):
    """Start AI image generation flow."""
    await _safe_answer(call)
    user = call.from_user
    upsert_user(user.id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user.id) or "uz"
    if not await enforce_subscription(bot, user.id, lang):
        return
    set_state(user.id, STATE_WAIT_AI_IMAGE)
    await bot.send_message(
        user.id,
        t("ai_image_prompt", lang),
        parse_mode="HTML", reply_markup=kb_cancel(lang)
    )


@router.callback_query(F.data == "act_ocr")
async def cb_ocr(call: CallbackQuery, bot: Bot):
    """Start OCR flow."""
    await _safe_answer(call)
    user = call.from_user
    upsert_user(user.id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user.id) or "uz"
    if not await enforce_subscription(bot, user.id, lang):
        return
    set_state(user.id, STATE_WAIT_OCR)
    await bot.send_message(user.id, t("ocr_prompt", lang),
                           parse_mode="HTML", reply_markup=kb_cancel(lang))


@router.message(lambda msg: msg.text and not msg.text.startswith("/") and get_state(msg.from_user.id) == STATE_NONE)
async def handle_fallback_text(message: Message, bot: Bot):
    """Handle text messages sent when user is in STATE_NONE."""
    user = message.from_user
    lang = get_user_language(user.id) or "uz"
    await message.answer(
        t("fallback_text_prompt", lang),
        reply_markup=kb_main(lang),
        parse_mode="HTML"
    )
