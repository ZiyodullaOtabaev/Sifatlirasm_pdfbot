"""
Inline keyboard markups for the bot with multi-language support.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.config import CHANNEL_USER
from bot.i18n import t


def kb_language() -> InlineKeyboardMarkup:
    """Language selection keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="set_lang_uz"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru"),
        ],
        [
            InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en"),
        ],
    ])


def kb_main(lang: str = "uz") -> InlineKeyboardMarkup:
    """Main menu keyboard localized."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_text_pdf", lang), callback_data="act_text_pdf"),
            InlineKeyboardButton(text=t("btn_img_pdf", lang), callback_data="act_img_pdf"),
        ],
        [
            InlineKeyboardButton(text=t("btn_merge_pdf", lang), callback_data="act_merge_pdf"),
            InlineKeyboardButton(text=t("btn_compress_pdf", lang), callback_data="act_compress_pdf"),
        ],
        [
            InlineKeyboardButton(text=t("btn_upscale", lang), callback_data="act_upscale"),
            InlineKeyboardButton(text=t("btn_bg_remove", lang), callback_data="act_bg_remove"),
        ],
        [
            InlineKeyboardButton(text=t("btn_ai_image", lang), callback_data="act_ai_image"),
            InlineKeyboardButton(text=t("btn_ocr", lang), callback_data="act_ocr"),
        ],
        [
            InlineKeyboardButton(text=t("btn_ai_video", lang), callback_data="act_ai_video"),
            InlineKeyboardButton(text=t("btn_ai_slides", lang), callback_data="act_ai_slides"),
        ],
        [
            InlineKeyboardButton(text=t("btn_profile", lang), callback_data="act_profile"),
            InlineKeyboardButton(text=t("btn_change_lang", lang), callback_data="act_change_lang"),
        ],
    ])


def kb_profile(lang: str = "uz") -> InlineKeyboardMarkup:
    """User profile keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_share_ref", lang), callback_data="act_share_ref")],
        [InlineKeyboardButton(text=t("btn_top_up", lang), callback_data="act_show_top_up")],
        [
            InlineKeyboardButton(text=t("btn_change_lang", lang), callback_data="act_change_lang"),
            InlineKeyboardButton(text=t("btn_home", lang), callback_data="act_cancel"),
        ],
    ])


def kb_referral(lang: str = "uz", share_url: str = "") -> InlineKeyboardMarkup:
    """Referral sharing keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_share_url", lang), url=share_url)],
        [InlineKeyboardButton(text=t("btn_home", lang), callback_data="act_cancel")],
    ])


def kb_template_gallery(current_index: int, total_count: int, theme_key: str, lang: str = "uz") -> InlineKeyboardMarkup:
    """Visual template gallery navigation keyboard."""
    prev_idx = (current_index - 1) % total_count
    next_idx = (current_index + 1) % total_count
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️ Oldingisi", callback_data=f"gallery_nav_{prev_idx}"),
            InlineKeyboardButton(text=f"{current_index + 1}/{total_count}", callback_data="act_noop"),
            InlineKeyboardButton(text="Keyingisi ▶️", callback_data=f"gallery_nav_{next_idx}"),
        ],
        [
            InlineKeyboardButton(text="✅ Ushbu Shablonni Tanlash", callback_data=f"gallery_select_{theme_key}"),
        ],
        [
            InlineKeyboardButton(text=t("btn_home", lang), callback_data="act_cancel"),
        ]
    ])


def kb_author_skip(lang: str = "uz") -> InlineKeyboardMarkup:
    """Keyboard for author metadata prompt with skip button."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_skip", lang), callback_data="act_skip_author")],
        [InlineKeyboardButton(text=t("btn_home", lang), callback_data="act_cancel")],
    ])


def kb_slide_result(lang: str = "uz", pptx_file_id: str = "") -> InlineKeyboardMarkup:
    """Keyboard for generated PPTX presentation with PDF download button."""
    buttons = []
    if pptx_file_id:
        buttons.append([InlineKeyboardButton(text=t("btn_convert_pdf", lang), callback_data=f"convert_slide_pdf_{pptx_file_id}")])
    buttons.append([InlineKeyboardButton(text=t("btn_home", lang), callback_data="act_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kb_top_up(lang: str = "uz", admin_user: str = "") -> InlineKeyboardMarkup:
    """Top up balance keyboard with Telegram Stars and Admin contact options."""
    admin_contact = admin_user.lstrip("@") if admin_user else "ziyodullame"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐ 5 Kredit (15 Stars)", callback_data="buy_stars_bundle_5"),
            InlineKeyboardButton(text="⭐ 15 Kredit (40 Stars)", callback_data="buy_stars_bundle_15"),
        ],
        [
            InlineKeyboardButton(text="⭐ 50 Kredit (120 Stars)", callback_data="buy_stars_bundle_50"),
        ],
        [
            InlineKeyboardButton(text="👤 Admin orqali kartaga to'lash (@ziyodullame)", url=f"https://t.me/{admin_contact}"),
        ],
        [
            InlineKeyboardButton(text=t("btn_home", lang), callback_data="act_cancel"),
        ],
    ])


def kb_ai_video_terms(lang: str = "uz") -> InlineKeyboardMarkup:
    """Terms confirmation keyboard for AI Video."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_confirm_ai_video", lang), callback_data="act_start_ai_video")],
        [InlineKeyboardButton(text=t("btn_home", lang), callback_data="act_cancel")],
    ])


def kb_cancel(lang: str = "uz") -> InlineKeyboardMarkup:
    """Cancel / back to menu keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_home", lang), callback_data="act_cancel")],
    ])


def kb_subscribe(lang: str = "uz") -> InlineKeyboardMarkup:
    """Subscription prompt keyboard."""
    channel_link = CHANNEL_USER.lstrip("@")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("sub_btn", lang), url=f"https://t.me/{channel_link}")],
        [InlineKeyboardButton(text=t("sub_check_btn", lang), callback_data="act_check_sub")],
    ])


def kb_admin() -> InlineKeyboardMarkup:
    """Admin panel keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"),
            InlineKeyboardButton(text="📈 7 kun", callback_data="admin_chart7"),
        ],
        [
            InlineKeyboardButton(text="📉 30 kun", callback_data="admin_chart30"),
            InlineKeyboardButton(text="📋 Funksiyalar", callback_data="admin_actions"),
        ],
        [
            InlineKeyboardButton(text="🏆 TOP-30", callback_data="admin_top30"),
            InlineKeyboardButton(text="⚡️ Aktiv 24h", callback_data="admin_active24"),
        ],
        [
            InlineKeyboardButton(text="🆕 Yangi 24h", callback_data="admin_new24"),
            InlineKeyboardButton(text="🔍 Qidirish", callback_data="admin_search"),
        ],
        [
            InlineKeyboardButton(text="💳 Kredit Qo'shish", callback_data="admin_add_balance"),
            InlineKeyboardButton(text="💾 Baza Zaxira", callback_data="admin_backup"),
        ],
        [
            InlineKeyboardButton(text="📜 BC tarix", callback_data="admin_bc_history"),
            InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast"),
        ],
    ])


def kb_user_balance_actions(user_id: int) -> InlineKeyboardMarkup:
    """Quick balance add buttons for a specific user in admin panel."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ 1 Kredit", callback_data=f"adm_addbal_{user_id}_1"),
            InlineKeyboardButton(text="➕ 5 Kredit", callback_data=f"adm_addbal_{user_id}_5"),
            InlineKeyboardButton(text="➕ 10 Kredit", callback_data=f"adm_addbal_{user_id}_10"),
        ],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="admin_back")],
    ])


def kb_admin_back() -> InlineKeyboardMarkup:
    """Back to admin panel."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="admin_back")],
    ])


def kb_broadcast_confirm() -> InlineKeyboardMarkup:
    """Broadcast confirmation keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, yubor", callback_data="broadcast_confirm"),
            InlineKeyboardButton(text="❌ Bekor", callback_data="broadcast_cancel"),
        ],
    ])
