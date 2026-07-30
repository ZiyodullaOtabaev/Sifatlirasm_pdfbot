"""
Telegram Stars Payment and Admin Contact Handlers.
"""
import logging
from aiogram import Router, Bot, F
from aiogram.types import (
    Message, CallbackQuery, PreCheckoutQuery,
    LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
)

from bot.database import get_user_language, add_user_balance, get_user_balance
from bot.i18n import t
from bot.keyboards import kb_top_up
from bot.states import set_state, STATE_NONE

logger = logging.getLogger(__name__)
router = Router(name="payments")


async def _safe_answer(call: CallbackQuery):
    try:
        await call.answer()
    except Exception:
        pass


STARS_BUNDLES = {
    "stars_bundle_5": {"credits": 5, "stars": 15, "label": "5 Kredit (15 ⭐)", "desc": "5 ta AI Video yaratish uchun kreditlar"},
    "stars_bundle_15": {"credits": 15, "stars": 40, "label": "15 Kredit (40 ⭐)", "desc": "15 ta AI Video yaratish uchun kreditlar"},
    "stars_bundle_50": {"credits": 50, "stars": 120, "label": "50 Kredit (120 ⭐)", "desc": "50 ta AI Video yaratish uchun kreditlar"},
}


@router.callback_query(F.data.startswith("buy_stars_"))
async def cb_buy_stars(call: CallbackQuery, bot: Bot):
    """Send invoice for Telegram Stars payment."""
    await _safe_answer(call)
    user_id = call.from_user.id
    lang = get_user_language(user_id) or "uz"

    bundle_key = call.data.replace("buy_", "")
    bundle = STARS_BUNDLES.get(bundle_key)
    if not bundle:
        await call.answer("❌ Noma'lum to'plam", show_alert=True)
        return

    title = f"{bundle['credits']} ta AI Video Kredit"
    description = bundle["desc"]
    payload = bundle_key
    prices = [LabeledPrice(label=bundle["label"], amount=bundle["stars"])]

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
    credits_to_add = bundle["credits"] if bundle else 5

    add_user_balance(user_id, credits_to_add)
    new_bal = get_user_balance(user_id)
    lang = get_user_language(user_id) or "uz"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_ai_video", lang), callback_data="act_ai_video")],
        [InlineKeyboardButton(text=t("btn_home", lang), callback_data="act_cancel")]
    ])

    await message.answer(
        f"🎉 <b>Xarid muvaffaqiyatli amalga oshirildi!</b>\n\n"
        f"⭐️ To'lov: <b>{payment_info.total_amount} Stars</b>\n"
        f"➕ Qo'shilgan kredit: <b>+{credits_to_add} kredit</b>\n"
        f"💰 Jami balansingiz: <b>{new_bal} kredit</b>\n\n"
        f"Video yaratish uchun pastdagi tugmani bosing 👇",
        parse_mode="HTML",
        reply_markup=kb
    )
    logger.info(f"User {user_id} paid {payment_info.total_amount} Stars for {credits_to_add} credits. New balance: {new_bal}")
