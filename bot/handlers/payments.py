"""
Telegram Stars Payment and Admin Contact Handlers.
"""
import logging
from aiogram import Router, Bot, F
from aiogram.types import (
    Message, CallbackQuery, PreCheckoutQuery,
    LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
)

from bot.database import get_user_language, add_user_balance, get_user_balance, activate_img_pdf_pass
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
    "stars_video_1": {"credits": 4, "stars": 15, "label": "🎬 1 ta Video (15 ⭐)", "desc": "1 ta AI Video yaratish (4 kredit)"},
    "stars_slide_1": {"credits": 7, "stars": 20, "label": "📊 1 ta Slayd (20 ⭐)", "desc": "1 ta 12 betli AI Slayd (7 kredit)"},
    "stars_image_1": {"credits": 2, "stars": 10, "label": "🤖 1 ta AI Rasm (10 ⭐)", "desc": "1 ta AI Rasm yaratish (2 kredit)"},
    "stars_image_5": {"credits": 10, "stars": 45, "label": "🤖 5 ta AI Rasm (45 ⭐)", "desc": "5 ta AI Rasm yaratish (10 kredit)"},
    "stars_img_pdf_1yr": {"credits": 0, "stars": 50, "label": "🖼 1 Yillik Cheksiz Pass (50 ⭐)", "desc": "1 yil davomida Rasm->PDF cheksiz foydalanish", "is_pass": True},
    "stars_video_5": {"credits": 20, "stars": 65, "label": "🎬 5 ta Video (65 ⭐)", "desc": "5 ta AI Video uchun kreditlar (Chegirma bilan)"},
    "stars_slide_5": {"credits": 35, "stars": 85, "label": "📊 5 ta Slayd (85 ⭐)", "desc": "5 ta 12 betli AI Slayd uchun kreditlar (Chegirma bilan)"},
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

    title = bundle["label"]
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
    lang = get_user_language(user_id) or "uz"

    if bundle and bundle.get("is_pass"):
        activate_img_pdf_pass(user_id, days=365)
        if lang == "ru":
            pass_success_text = (
                f"🎉 <b>Поздравляем! 1-Годовой Безлимитный Pass активирован!</b>\n\n"
                f"⭐️ Оплачено: <b>{payment_info.total_amount} Stars</b>\n"
                f"🖼 Функция <b>Фото ➡️ PDF</b> доступна вам абсолютно БЕЗЛИМИТНО на 1 год (365 дней)! 🚀"
            )
        elif lang == "en":
            pass_success_text = (
                f"🎉 <b>Congratulations! 1-Year Unlimited Pass is activated!</b>\n\n"
                f"⭐️ Paid: <b>{payment_info.total_amount} Stars</b>\n"
                f"🖼 <b>Image ➡️ PDF</b> feature is now completely UNLIMITED for 1 Year (365 days)! 🚀"
            )
        else:
            pass_success_text = (
                f"🎉 <b>Tabriklaymiz! 1 Yillik Cheksiz Pass faollashtirildi!</b>\n\n"
                f"⭐️ To'lov: <b>{payment_info.total_amount} Stars</b>\n"
                f"🖼 <b>Rasm ➡️ PDF</b> funksiyasini 1 yil (365 kun) davomida butunlay cheksiz ishlatishingiz mumkin! 🚀"
            )

        await message.answer(pass_success_text, parse_mode="HTML")
        logger.info(f"User {user_id} activated 1-Year Image-to-PDF pass with {payment_info.total_amount} Stars")
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

