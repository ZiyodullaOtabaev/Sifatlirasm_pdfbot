"""
Telegram Stars Payment, In-Bot Card Receipt Verification, and Admin 1-Click VIP Approval Handlers.
"""
import html
import logging
from typing import Dict
from aiogram import Router, Bot, F
from aiogram.types import (
    Message, CallbackQuery, PreCheckoutQuery,
    LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
)

from bot.config import ADMIN_IDS, ADMIN_ID
from bot.database import (
    get_user_language, add_user_balance, get_user_balance,
    activate_img_pdf_pass, get_vip_until, upsert_user, resolve_user_id,
    get_vip_prices, get_payment_card, log_payment,
)
from bot.i18n import t
from bot.keyboards import kb_top_up, kb_cancel, kb_vip_plans, kb_admin_approve_vip, kb_main_reply
from bot.states import get_state, set_state, STATE_NONE, STATE_WAIT_PAYMENT_RECEIPT

logger = logging.getLogger(__name__)
router = Router(name="payments")

# Store selected card VIP plan per user: user_id -> days (30 or 365)
PENDING_VIP_PLAN: Dict[int, int] = {}


def _get_all_admin_ids() -> set[int]:
    """Return deduplicated set of all configured admin user IDs."""
    admins = set(ADMIN_IDS) if ADMIN_IDS else set()
    if ADMIN_ID:
        admins.add(ADMIN_ID)
    return admins


async def _notify_admins(bot: Bot, text: str):
    """Send an HTML notification message to all admins safely."""
    for adm in _get_all_admin_ids():
        try:
            await bot.send_message(adm, text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Could not send admin notification to {adm}: {e}")


async def _safe_answer(call: CallbackQuery):
    try:
        await call.answer()
    except Exception:
        pass


DONATE_STARS_BUNDLES = {
    "donate_stars_10": {"stars": 10, "label": "⭐️ 10 Stars", "desc": "Sifatli PDF Bot loyihasini qo'llab-quvvatlash uchun donat ❤️"},
    "donate_stars_25": {"stars": 25, "label": "⭐️ 25 Stars", "desc": "Sifatli PDF Bot serverini qo'llab-quvvatlash uchun donat ❤️"},
    "donate_stars_50": {"stars": 50, "label": "⭐️ 50 Stars", "desc": "Sifatli PDF Bot yangi bepul funksiyalari uchun donat ❤️"},
    "donate_stars_100": {"stars": 100, "label": "⭐️ 100 Stars", "desc": "Sifatli PDF Bot loyihasiga homiylik donati ❤️"},
}

STARS_BUNDLES = {
    **DONATE_STARS_BUNDLES,
    "vip_stars_30": {
        "credits": 0,
        "stars": 50,
        "days": 30,
        "label": "💎 1 Oylik VIP Obuna (50 ⭐)",
        "desc": "30 kun davomida barcha PDF xizmatlardan cheksiz va majburiy obunalarsiz foydalanish",
        "is_pass": True,
    },
    "vip_stars_365": {
        "credits": 0,
        "stars": 150,
        "days": 365,
        "label": "👑 1 Yillik VIP Obuna (150 ⭐)",
        "desc": "365 kun davomida barcha PDF xizmatlardan cheksiz va majburiy obunalarsiz foydalanish",
        "is_pass": True,
    },
    "stars_video_1": {"credits": 4, "stars": 15, "label": "🎬 1 ta Video (15 ⭐)", "desc": "1 ta AI Video yaratish (4 kredit)"},
    "stars_slide_1": {"credits": 7, "stars": 20, "label": "📊 1 ta Slayd (20 ⭐)", "desc": "1 ta 12 betli AI Slayd (7 kredit)"},
    "stars_image_1": {"credits": 2, "stars": 10, "label": "🤖 1 ta AI Rasm (10 ⭐)", "desc": "1 ta AI Rasm yaratish (2 kredit)"},
    "stars_image_5": {"credits": 10, "stars": 45, "label": "🤖 5 ta AI Rasm (45 ⭐)", "desc": "5 ta AI Rasm yaratish (10 kredit)"},
    "stars_img_pdf_1yr": {"credits": 0, "stars": 50, "days": 365, "label": "🖼 1 Yillik Cheksiz Pass (50 ⭐)", "desc": "1 yil davomida Rasm->PDF cheksiz foydalanish", "is_pass": True},
    "stars_video_5": {"credits": 20, "stars": 65, "label": "🎬 5 ta Video (65 ⭐)", "desc": "5 ta AI Video uchun kreditlar (Chegirma bilan)"},
    "stars_slide_5": {"credits": 35, "stars": 85, "label": "📊 5 ta Slayd (85 ⭐)", "desc": "5 ta 12 betli AI Slayd uchun kreditlar (Chegirma bilan)"},
}


@router.callback_query(F.data.startswith("buy_"))
async def cb_buy_stars(call: CallbackQuery, bot: Bot):
    """Send invoice for Telegram Stars payment or donation."""
    await _safe_answer(call)
    user_id = call.from_user.id
    lang = get_user_language(user_id) or "uz"

    bundle_key = call.data.replace("buy_", "")
    bundle = STARS_BUNDLES.get(bundle_key)
    if not bundle:
        await call.answer("❌ Noma'lum to'plam", show_alert=True)
        return

    # Use live dynamic Stars prices from DB for VIP plans
    stars_amount = bundle["stars"]
    title = bundle["label"]
    if bundle_key == "vip_stars_30":
        stars_amount = get_vip_prices()["stars_30"]
        title = f"💎 1 Oylik VIP Obuna ({stars_amount} ⭐)"
    elif bundle_key == "vip_stars_365":
        stars_amount = get_vip_prices()["stars_365"]
        title = f"👑 1 Yillik VIP Obuna ({stars_amount} ⭐)"

    description = bundle["desc"]
    payload = bundle_key
    prices = [LabeledPrice(label=title, amount=stars_amount)]

    try:
        await bot.send_invoice(
            chat_id=user_id,
            title=title,
            description=description,
            payload=payload,
            provider_token="",  # Empty string for Telegram Stars!
            currency="XTR",     # Telegram Stars currency code
            prices=prices
        )
        logger.info(f"Sent Stars invoice to user {user_id} for bundle {bundle_key}")
    except Exception as e:
        logger.error(f"Error sending Stars invoice: {e}")
        await bot.send_message(
            user_id,
            "⚠️ <b>To'lov xabarnomasini yuborishda xatolik!</b>\n\n"
            "Iltimos, Telegram ilovangizni yangilang yoki Admin @ziyodullame ga murojaat qiling.",
            parse_mode="HTML",
            reply_markup=kb_top_up(lang)
        )


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    """Approve pre-checkout query for Telegram Stars."""
    try:
        await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
        logger.info(f"Pre-checkout approved for user {pre_checkout_query.from_user.id}")
    except Exception as e:
        logger.error(f"Pre-checkout error: {e}")


@router.message(F.successful_payment)
async def process_successful_payment(message: Message, bot: Bot):
    """Handle successful Telegram Stars payment."""
    user = message.from_user
    user_id = user.id
    payment_info = message.successful_payment
    payload = payment_info.invoice_payload

    bundle = STARS_BUNDLES.get(payload)
    lang = get_user_language(user_id) or "uz"

    if payload.startswith("donate_stars_"):
        amount_stars = payment_info.total_amount
        log_payment(user_id, "donate_stars", plan_days=0, amount_uzs=0, amount_stars=amount_stars, note="Donat")
        await message.answer(
            t("donate_stars_success", lang, amount=amount_stars),
            parse_mode="HTML"
        )
        logger.info(f"User {user_id} donated {amount_stars} Stars!")

        safe_name = html.escape(user.full_name or "-")
        uname = f"@{html.escape(user.username)}" if user.username else "username yo'q"
        admin_text = (
            f"⭐️ <b>Yangi Donat Qabul Qilindi!</b> ❤️\n\n"
            f"👤 Foydalanuvchi: <b>{safe_name}</b> ({uname} | <code>{user_id}</code>)\n"
            f"💰 Miqdor: <b>{amount_stars} Stars</b>\n"
            f"📦 To'plam: <code>{payload}</code>"
        )
        await _notify_admins(bot, admin_text)
        return

    if bundle and bundle.get("is_pass"):
        days = int(bundle.get("days", 30))
        activate_img_pdf_pass(user_id, days=days)
        vip_until = get_vip_until(user_id) or ""
        plan_label = "1 Yillik VIP" if days >= 365 else "1 Oylik VIP"
        log_payment(
            user_id, "vip_stars", plan_days=days, amount_uzs=0,
            amount_stars=payment_info.total_amount, note=plan_label,
        )
        await message.answer(
            t("vip_activated_notify", lang, days=days, vip_until=vip_until),
            parse_mode="HTML",
            reply_markup=kb_main_reply(lang)
        )
        logger.info(f"User {user_id} activated {days}-day VIP pass with {payment_info.total_amount} Stars")

        safe_name = html.escape(user.full_name or "-")
        uname = f"@{html.escape(user.username)}" if user.username else "username yo'q"
        plan_label = "1 Yillik VIP" if days >= 365 else "1 Oylik VIP"
        admin_text = (
            f"💎 <b>Yangi VIP Obuna sotib olindi!</b>\n\n"
            f"👤 Foydalanuvchi: <b>{safe_name}</b> ({uname})\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"💳 To'lov usuli: <b>⭐️ Telegram Stars ({payment_info.total_amount} ⭐)</b>\n"
            f"📦 Tarif: <b>{plan_label} (+{days} kun)</b>\n"
            f"📅 Amal qilish muddati: <b>{vip_until}</b> gacha"
        )
        await _notify_admins(bot, admin_text)
        return

    credits_to_add = bundle["credits"] if bundle else 5
    add_user_balance(user_id, credits_to_add)
    new_bal = get_user_balance(user_id)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_home", lang), callback_data="act_cancel")]
    ])

    if lang == "ru":
        credit_success_text = (
            f"🎉 <b>Покупка успешно завершена!</b>\n\n"
            f"⭐️ Оплачено: <b>{payment_info.total_amount} Stars</b>\n"
            f"➕ Начислено: <b>+{credits_to_add} кредитов</b>\n"
            f"💰 Ваш баланс: <b>{new_bal} кредитов</b>\n\n"
            f"Вы можете пользоваться услугами бота 👇"
        )
    elif lang == "en":
        credit_success_text = (
            f"🎉 <b>Purchase completed successfully!</b>\n\n"
            f"⭐️ Paid: <b>{payment_info.total_amount} Stars</b>\n"
            f"➕ Credited: <b>+{credits_to_add} credits</b>\n"
            f"💰 Your balance: <b>{new_bal} credits</b>\n\n"
            f"You can now use all bot services 👇"
        )
    else:
        credit_success_text = (
            f"🎉 <b>Xarid muvaffaqiyatli amalga oshirildi!</b>\n\n"
            f"⭐️ To'lov: <b>{payment_info.total_amount} Stars</b>\n"
            f"➕ Qo'shilgan kredit: <b>+{credits_to_add} kredit</b>\n"
            f"💰 Jami balansingiz: <b>{new_bal} kredit</b>\n\n"
            f"Xizmatlardan foydalanishingiz mumkin 👇"
        )

    await message.answer(
        credit_success_text,
        parse_mode="HTML",
        reply_markup=kb
    )
    logger.info(f"User {user_id} paid {payment_info.total_amount} Stars for {credits_to_add} credits. New balance: {new_bal}")


# ========================================================
# CARD VIP PAYMENT & 1-CLICK ADMIN RECEIPT VERIFICATION
# ========================================================

@router.callback_query(F.data.in_({"act_vip_card_30", "act_vip_card_365"}))
async def cb_vip_card_payment(call: CallbackQuery, bot: Bot):
    """Show card payment instructions and wait for user's payment receipt photo."""
    await _safe_answer(call)
    user = call.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user_id) or "uz"

    is_yearly = call.data == "act_vip_card_365"
    days = 365 if is_yearly else 30
    p = get_vip_prices()
    price_uzs = f"{p['uzs_365']:,}".replace(",", " ") if is_yearly else f"{p['uzs_30']:,}".replace(",", " ")
    if lang == "ru":
        plan_name = "👑 VIP на 1 год (365 дней)" if is_yearly else "💎 VIP на 1 месяц (30 дней)"
    elif lang == "en":
        plan_name = "👑 1-Year VIP (365 days)" if is_yearly else "💎 1-Month VIP (30 days)"
    else:
        plan_name = "👑 1 Yillik VIP (365 kun)" if is_yearly else "💎 1 Oylik VIP (30 kun)"

    PENDING_VIP_PLAN[user_id] = days
    set_state(user_id, STATE_WAIT_PAYMENT_RECEIPT)

    text = t(
        "vip_card_payment_text",
        lang,
        plan_name=plan_name,
        price_uzs=price_uzs,
        card_number=get_payment_card(),
    )
    try:
        await bot.edit_message_text(
            text,
            chat_id=user_id,
            message_id=call.message.message_id,
            reply_markup=kb_cancel(lang),
            parse_mode="HTML",
        )
    except Exception:
        await bot.send_message(user_id, text, reply_markup=kb_cancel(lang), parse_mode="HTML")


@router.message(lambda msg: (msg.photo or msg.document) and get_state(msg.from_user.id) == STATE_WAIT_PAYMENT_RECEIPT)
async def handle_payment_receipt(message: Message, bot: Bot):
    """Receive user's payment screenshot/receipt and forward to admins with 1-click approve buttons."""
    user = message.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user_id) or "uz"

    days = PENDING_VIP_PLAN.pop(user_id, 30)
    p = get_vip_prices()
    uzs_val = p["uzs_365"] if days >= 365 else p["uzs_30"]
    uzs_fmt = f"{uzs_val:,}".replace(",", " ")
    plan_str = f"👑 1 Yillik VIP ({uzs_fmt} so'm)" if days >= 365 else f"💎 1 Oylik VIP ({uzs_fmt} so'm)"
    set_state(user_id, STATE_NONE)

    await message.answer(
        t("vip_receipt_received", lang),
        parse_mode="HTML",
        reply_markup=kb_main_reply(lang),
    )

    safe_name = html.escape(user.full_name or "-")
    uname = f"@{html.escape(user.username)}" if user.username else "username yo'q"
    admin_caption = (
        f"🧾 <b>Yangi VIP Obuna To'lov Cheki! (💳 Karta)</b>\n\n"
        f"👤 Foydalanuvchi: <b>{safe_name}</b> ({uname})\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"📦 Tanlagan tarifi: <b>{plan_str}</b>\n\n"
        f"👇 Tekshirib, quyidagi tugmalardan birini bosing:"
    )

    for adm in _get_all_admin_ids():
        try:
            if message.photo:
                await bot.send_photo(
                    adm,
                    photo=message.photo[-1].file_id,
                    caption=admin_caption,
                    parse_mode="HTML",
                    reply_markup=kb_admin_approve_vip(user_id),
                )
            elif message.document:
                await bot.send_document(
                    adm,
                    document=message.document.file_id,
                    caption=admin_caption,
                    parse_mode="HTML",
                    reply_markup=kb_admin_approve_vip(user_id),
                )
        except Exception as e:
            logger.error(f"Could not forward VIP receipt to admin {adm}: {e}")


@router.message(lambda msg: msg.text and not msg.text.startswith("/") and get_state(msg.from_user.id) == STATE_WAIT_PAYMENT_RECEIPT)
async def handle_payment_receipt_text_warning(message: Message, bot: Bot):
    """Remind user to send a screenshot image if they send plain text while waiting for receipt."""
    user_id = message.from_user.id
    lang = get_user_language(user_id) or "uz"
    text = (message.text or "").strip()

    if any(text == t("btn_home", l) for l in ("uz", "ru", "en")) or text in ("🏠 Bosh menyu", "❌ Bekor qilish", "Cancel", "Отмена"):
        PENDING_VIP_PLAN.pop(user_id, None)
        set_state(user_id, STATE_NONE)
        from bot.handlers.menu import show_main_menu
        await show_main_menu(bot, message.chat.id)
        return

    msg_warn = {
        "uz": "📸 Iltimos, to'lov chekining <b>rasmini (skrinshot)</b> yuboring yoki bekor qilish uchun 🏠 Bosh menyu tugmasini bosing.",
        "ru": "📸 Пожалуйста, отправьте <b>фото (скриншот)</b> чека об оплате или нажмите 🏠 Главное меню для отмены.",
        "en": "📸 Please send a <b>photo (screenshot)</b> of your payment receipt or tap 🏠 Main Menu to cancel.",
    }.get(lang, "📸 Iltimos, to'lov chekining rasmini (skrinshot) yuboring.")
    await message.answer(msg_warn, parse_mode="HTML", reply_markup=kb_cancel(lang))


@router.callback_query(F.data.startswith("adm_vip_ok_"))
async def cb_admin_approve_vip(call: CallbackQuery, bot: Bot):
    """Admin 1-click approval for user's VIP subscription."""
    if call.from_user.id not in ADMIN_IDS and call.from_user.id != ADMIN_ID:
        await call.answer("⛔️ Faqat admin uchun!", show_alert=True)
        return

    await _safe_answer(call)
    parts = call.data.replace("adm_vip_ok_", "").split("_")
    if len(parts) < 2:
        return

    target_user_id = int(parts[0])
    days = int(parts[1])

    activate_img_pdf_pass(target_user_id, days=days)
    vip_until = get_vip_until(target_user_id) or ""
    p = get_vip_prices()
    uzs_val = p["uzs_365"] if days >= 365 else p["uzs_30"]
    uzs_fmt = f"{uzs_val:,}".replace(",", " ")
    plan_label = f"1 Yillik VIP ({uzs_fmt} so'm)" if days >= 365 else f"1 Oylik VIP ({uzs_fmt} so'm)"
    log_payment(
        target_user_id, "vip_card", plan_days=days,
        amount_uzs=uzs_val, amount_stars=0, note=plan_label,
    )

    # Update admin message
    status_line = f"\n\n✅ <b>TASDIQLANDI:</b> +{days} kun VIP (<b>{vip_until}</b> gacha)"
    try:
        old_caption = call.message.caption or call.message.text or ""
        await call.message.edit_caption(caption=old_caption + status_line, parse_mode="HTML", reply_markup=None)
    except Exception:
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

    # Confirm clearly to admins
    u_info = resolve_user_id(str(target_user_id)) or {}
    safe_name = html.escape((u_info.get("first_name") or "").strip() or "-")
    uname = f"@{html.escape(u_info['username'])}" if u_info.get("username") else "username yo'q"
    await _notify_admins(
        bot,
        f"💎 <b>Yangi VIP Obuna faollashtirildi! (💳 Karta)</b>\n\n"
        f"👤 Foydalanuvchi: <b>{safe_name}</b> ({uname})\n"
        f"🆔 ID: <code>{target_user_id}</code>\n"
        f"📦 Tarif: <b>{plan_label}</b>\n"
        f"📅 Amal qilish muddati: <b>{vip_until}</b> gacha",
    )

    # Notify user
    u_lang = get_user_language(target_user_id) or "uz"
    try:
        await bot.send_message(
            target_user_id,
            t("vip_activated_notify", u_lang, days=days, vip_until=vip_until),
            parse_mode="HTML",
            reply_markup=kb_main_reply(u_lang),
        )
    except Exception as e:
        logger.warning(f"Failed to notify user {target_user_id} of VIP activation: {e}")


@router.callback_query(F.data.startswith("adm_vip_no_"))
async def cb_admin_reject_vip(call: CallbackQuery, bot: Bot):
    """Admin 1-click rejection for invalid receipt."""
    if call.from_user.id not in ADMIN_IDS and call.from_user.id != ADMIN_ID:
        await call.answer("⛔️ Faqat admin uchun!", show_alert=True)
        return

    await _safe_answer(call)
    target_user_id = int(call.data.replace("adm_vip_no_", ""))

    status_line = "\n\n❌ <b>RAD ETILDI</b>"
    try:
        old_caption = call.message.caption or call.message.text or ""
        await call.message.edit_caption(caption=old_caption + status_line, parse_mode="HTML", reply_markup=None)
    except Exception:
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

    u_lang = get_user_language(target_user_id) or "uz"
    try:
        await bot.send_message(
            target_user_id,
            t("vip_rejected_notify", u_lang),
            parse_mode="HTML",
            reply_markup=kb_vip_plans(u_lang),
        )
    except Exception as e:
        logger.warning(f"Failed to notify user {target_user_id} of VIP rejection: {e}")

