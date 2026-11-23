"""
Inline keyboard markups for the bot with multi-language support.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

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


def kb_main_reply(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Main menu Reply keyboard (collapsible at the bottom of the screen)."""
    placeholder = "Kerakli bo'limni tanlang 👇" if lang == "uz" else "Выберите раздел 👇" if lang == "ru" else "Select an option 👇"
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t("btn_img_pdf", lang)),
                KeyboardButton(text=t("btn_text_pdf", lang)),
            ],
            [
                KeyboardButton(text=t("btn_pdf_to_word", lang)),
                KeyboardButton(text=t("btn_office_to_pdf", lang)),
            ],
            [
                KeyboardButton(text=t("btn_merge_pdf", lang)),
                KeyboardButton(text=t("btn_compress_pdf", lang)),
            ],
            [
                KeyboardButton(text=t("btn_pdf_to_img", lang)),
                KeyboardButton(text=t("btn_watermark_pdf", lang)),
            ],
            [
                KeyboardButton(text=t("btn_profile", lang)),
                KeyboardButton(text=t("btn_vip", lang)),
            ],
            [
                KeyboardButton(text=t("btn_ads", lang)),
                KeyboardButton(text=t("btn_donate", lang)),
            ],
            [
                KeyboardButton(text=t("btn_change_lang", lang)),
            ],
        ],
        resize_keyboard=True,
        is_persistent=False,
        input_field_placeholder=placeholder,
    )


def kb_main(lang: str = "uz") -> InlineKeyboardMarkup:
    """Main menu inline keyboard localized."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_img_pdf", lang), callback_data="act_img_pdf"),
            InlineKeyboardButton(text=t("btn_text_pdf", lang), callback_data="act_text_pdf"),
        ],
        [
            InlineKeyboardButton(text=t("btn_pdf_to_word", lang), callback_data="act_pdf_to_word"),
            InlineKeyboardButton(text=t("btn_office_to_pdf", lang), callback_data="act_office_to_pdf"),
        ],
        [
            InlineKeyboardButton(text=t("btn_merge_pdf", lang), callback_data="act_merge_pdf"),
            InlineKeyboardButton(text=t("btn_compress_pdf", lang), callback_data="act_compress_pdf"),
        ],
        [
            InlineKeyboardButton(text=t("btn_pdf_to_img", lang), callback_data="act_pdf_to_img"),
            InlineKeyboardButton(text=t("btn_watermark_pdf", lang), callback_data="act_watermark_pdf"),
        ],
        [
            InlineKeyboardButton(text=t("btn_profile", lang), callback_data="act_profile"),
            InlineKeyboardButton(text=t("btn_vip", lang), callback_data="act_vip"),
        ],
        [
            InlineKeyboardButton(text=t("btn_ads", lang), callback_data="act_ads"),
            InlineKeyboardButton(text=t("btn_donate", lang), callback_data="act_donate"),
        ],
        [
            InlineKeyboardButton(text=t("btn_change_lang", lang), callback_data="act_change_lang"),
        ],
    ])


def kb_ads(lang: str = "uz", admin_user: str = "ziyodullame") -> InlineKeyboardMarkup:
    """Keyboard for advertising info page."""
    admin_contact = admin_user.lstrip("@")
    btn_contact = {
        "uz": "💬 Reklama berish (@ziyodullame)",
        "ru": "💬 Заказать рекламу (@ziyodullame)",
        "en": "💬 Order Advertising (@ziyodullame)",
    }.get(lang, "💬 Reklama berish (@ziyodullame)")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_contact, url=f"https://t.me/{admin_contact}")],
        [InlineKeyboardButton(text=t("btn_home", lang), callback_data="act_cancel")],
    ])


def kb_donate(lang: str = "uz") -> InlineKeyboardMarkup:
    """Keyboard for donation page with Telegram Stars and Card options."""
    btn_card = {
        "uz": "💳 Karta orqali donat",
        "ru": "💳 Перевод на карту",
        "en": "💳 Donate via Card",
    }.get(lang, "💳 Karta orqali donat")
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐️ 10 Stars", callback_data="buy_donate_stars_10"),
            InlineKeyboardButton(text="⭐️ 25 Stars", callback_data="buy_donate_stars_25"),
        ],
        [
            InlineKeyboardButton(text="⭐️ 50 Stars", callback_data="buy_donate_stars_50"),
            InlineKeyboardButton(text="⭐️ 100 Stars", callback_data="buy_donate_stars_100"),
        ],
        [
            InlineKeyboardButton(text=btn_card, callback_data="act_donate_card"),
        ],
        [
            InlineKeyboardButton(text=t("btn_home", lang), callback_data="act_cancel"),
        ],
    ])


def kb_donate_card(lang: str = "uz", admin_user: str = "ziyodullame") -> InlineKeyboardMarkup:
    """Keyboard for card donation page."""
    admin_contact = admin_user.lstrip("@")
    btn_receipt = {
        "uz": "📩 Adminga chek yuborish (@ziyodullame)",
        "ru": "📩 Отправить чек админу (@ziyodullame)",
        "en": "📩 Send Receipt to Admin (@ziyodullame)",
    }.get(lang, "📩 Adminga chek yuborish (@ziyodullame)")
    btn_back_donate = {
        "uz": "⬅️ Boshqa usullar (Stars)",
        "ru": "⬅️ Другие способы (Stars)",
        "en": "⬅️ Other options (Stars)",
    }.get(lang, "⬅️ Boshqa usullar (Stars)")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_receipt, url=f"https://t.me/{admin_contact}")],
        [
            InlineKeyboardButton(text=btn_back_donate, callback_data="act_donate"),
            InlineKeyboardButton(text=t("btn_home", lang), callback_data="act_cancel"),
        ],
    ])



def kb_voice_actions(lang: str = "uz") -> InlineKeyboardMarkup:
    """Action buttons after voice transcription."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_voice_to_pdf", lang), callback_data="act_voice_to_pdf"),
        ],
        [
            InlineKeyboardButton(text=t("btn_home", lang), callback_data="act_cancel"),
        ],
    ])


def kb_profile(lang: str = "uz", total_users: int = 0) -> InlineKeyboardMarkup:
    """User profile keyboard with total users badge."""
    btn_users_text = {
        "uz": f"👥 Bot a'zolari: {total_users:,} ta",
        "ru": f"👥 Пользователи: {total_users:,}",
        "en": f"👥 Total Users: {total_users:,}",
    }.get(lang, f"👥 Bot a'zolari: {total_users:,} ta")

    rows = []
    if total_users > 0:
        rows.append([InlineKeyboardButton(text=btn_users_text, callback_data="act_noop")])
    rows.append([
        InlineKeyboardButton(text=t("btn_vip", lang), callback_data="act_vip"),
        InlineKeyboardButton(text=t("btn_promo", lang), callback_data="act_promo"),
    ])
    rows.append([InlineKeyboardButton(text=t("btn_share_ref", lang), callback_data="act_share_ref")])
    rows.append([
        InlineKeyboardButton(text=t("btn_change_lang", lang), callback_data="act_change_lang"),
        InlineKeyboardButton(text=t("btn_home", lang), callback_data="act_cancel"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_vip_plans(lang: str = "uz") -> InlineKeyboardMarkup:
    """Hybrid payment keyboard for VIP subscriptions (Dynamic prices from DB)."""
    from bot.database import get_vip_prices
    p = get_vip_prices()
    uzs_30 = f"{p['uzs_30']:,}".replace(",", " ")
    uzs_365 = f"{p['uzs_365']:,}".replace(",", " ")
    st_30 = p["stars_30"]
    st_365 = p["stars_365"]

    if lang == "ru":
        s_30, s_365 = f"⭐️ 1 Мес VIP ({st_30} ⭐)", f"⭐️ 1 Год VIP ({st_365} ⭐)"
        c_30, c_365 = f"💳 Карта: 1 Мес ({uzs_30} сум)", f"💳 Карта: 1 Год ({uzs_365} сум)"
    elif lang == "en":
        s_30, s_365 = f"⭐️ 1-Mo VIP ({st_30} ⭐)", f"⭐️ 1-Yr VIP ({st_365} ⭐)"
        c_30, c_365 = f"💳 Card: 1-Mo ({uzs_30} UZS)", f"💳 Card: 1-Yr ({uzs_365} UZS)"
    else:
        s_30, s_365 = f"⭐️ 1 Oylik VIP ({st_30} ⭐)", f"⭐️ 1 Yillik VIP ({st_365} ⭐)"
        c_30, c_365 = f"💳 Karta: 1 Oy ({uzs_30} so'm)", f"💳 Karta: 1 Yil ({uzs_365} so'm)"

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=s_30, callback_data="buy_vip_stars_30"),
            InlineKeyboardButton(text=s_365, callback_data="buy_vip_stars_365"),
        ],
        [
            InlineKeyboardButton(text=c_30, callback_data="act_vip_card_30"),
            InlineKeyboardButton(text=c_365, callback_data="act_vip_card_365"),
        ],
        [
            InlineKeyboardButton(text=t("btn_promo", lang), callback_data="act_promo"),
            InlineKeyboardButton(text=t("btn_share_ref", lang), callback_data="act_share_ref"),
        ],
        [
            InlineKeyboardButton(text=t("btn_home", lang), callback_data="act_cancel"),
        ],
    ])


def kb_admin_approve_vip(user_id: int) -> InlineKeyboardMarkup:
    """1-click admin buttons to approve or reject a user's VIP payment receipt."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ 1 Oylik VIP (30 kun)", callback_data=f"adm_vip_ok_{user_id}_30"),
            InlineKeyboardButton(text="👑 1 Yillik VIP (365 kun)", callback_data=f"adm_vip_ok_{user_id}_365"),
        ],
        [
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"adm_vip_no_{user_id}"),
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


def kb_top_up_video(lang: str = "uz", admin_user: str = "") -> InlineKeyboardMarkup:
    """Top up balance keyboard specifically for AI Video."""
    admin_contact = admin_user.lstrip("@") if admin_user else "ziyodullame"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 1 Video (15 ⭐)", callback_data="buy_stars_video_1"),
        ],
        [
            InlineKeyboardButton(text="🎬 5 Video (65 ⭐)", callback_data="buy_stars_video_5"),
        ],
        [
            InlineKeyboardButton(text=t("btn_admin_pay", lang), url=f"https://t.me/{admin_contact}"),
        ],
        [
            InlineKeyboardButton(text=t("btn_home", lang), callback_data="act_cancel"),
        ],
    ])


def kb_top_up_slides(lang: str = "uz", admin_user: str = "") -> InlineKeyboardMarkup:
    """Top up balance keyboard specifically for AI Slides."""
    admin_contact = admin_user.lstrip("@") if admin_user else "ziyodullame"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 1 Slayd (20 ⭐)", callback_data="buy_stars_slide_1"),
        ],
        [
            InlineKeyboardButton(text="📊 5 Slayd (85 ⭐)", callback_data="buy_stars_slide_5"),
        ],
        [
            InlineKeyboardButton(text=t("btn_admin_pay", lang), url=f"https://t.me/{admin_contact}"),
        ],
        [
            InlineKeyboardButton(text=t("btn_home", lang), callback_data="act_cancel"),
        ],
    ])


def kb_top_up_ai_image(lang: str = "uz", admin_user: str = "") -> InlineKeyboardMarkup:
    """Top up balance keyboard specifically for AI Image."""
    admin_contact = admin_user.lstrip("@") if admin_user else "ziyodullame"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🤖 1 AI Rasm (10 ⭐)", callback_data="buy_stars_image_1"),
        ],
        [
            InlineKeyboardButton(text="🤖 5 AI Rasm (45 ⭐)", callback_data="buy_stars_image_5"),
        ],
        [
            InlineKeyboardButton(text=t("btn_admin_pay", lang), url=f"https://t.me/{admin_contact}"),
        ],
        [
            InlineKeyboardButton(text=t("btn_home", lang), callback_data="act_cancel"),
        ],
    ])


def kb_top_up_img_pdf(lang: str = "uz", admin_user: str = "") -> InlineKeyboardMarkup:
    """Top up keyboard specifically for Image-to-PDF 1-Year Pass."""
    admin_contact = admin_user.lstrip("@") if admin_user else "ziyodullame"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💎 1-Year Pass (50 ⭐)", callback_data="buy_stars_img_pdf_1yr"),
        ],
        [
            InlineKeyboardButton(text=t("btn_admin_pay", lang), url=f"https://t.me/{admin_contact}"),
        ],
        [
            InlineKeyboardButton(text=t("btn_home", lang), callback_data="act_cancel"),
        ],
    ])


def kb_top_up(lang: str = "uz", admin_user: str = "") -> InlineKeyboardMarkup:
    """General top up balance keyboard with Telegram Stars and Admin contact options."""
    admin_contact = admin_user.lstrip("@") if admin_user else "ziyodullame"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💎 1-Year VIP Pass (50 ⭐)", callback_data="buy_stars_img_pdf_1yr"),
        ],
        [
            InlineKeyboardButton(text=t("btn_admin_pay", lang), url=f"https://t.me/{admin_contact}"),
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
    """PRO Admin Control Center keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏆 TOP-30", callback_data="admin_top30"),
            InlineKeyboardButton(text="⚡️ Aktiv 24h", callback_data="admin_active24"),
        ],
        [
            InlineKeyboardButton(text="🆕 Yangi 24h", callback_data="admin_new24"),
            InlineKeyboardButton(text="🔍 Qidirish (CRM)", callback_data="admin_search"),
        ],
        [
            InlineKeyboardButton(text="💎 VIP obunachilar", callback_data="admin_vip_users"),
            InlineKeyboardButton(text="💰 Moliya", callback_data="admin_finance"),
        ],
        [
            InlineKeyboardButton(text="🔗 Reklama havolalar", callback_data="admin_ad_links"),
            InlineKeyboardButton(text="🎟 Promokodlar", callback_data="admin_promos"),
        ],
        [
            InlineKeyboardButton(text="📢 Kanallar (OP)", callback_data="admin_channels"),
            InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="admin_settings"),
            InlineKeyboardButton(text="💾 Baza Zaxira", callback_data="admin_backup"),
        ],
        [
            InlineKeyboardButton(text="💳 Kredit Qo'shish", callback_data="admin_add_balance"),
            InlineKeyboardButton(text="📜 BC tarix", callback_data="admin_bc_history"),
        ],
    ])


def kb_admin_channels(channels: list[dict]) -> InlineKeyboardMarkup:
    """Keyboard for managing required channels in admin panel."""
    buttons = []
    for ch in channels:
        ch_id = ch["channel_id"]
        title = ch.get("channel_title") or ch_id
        target = ch.get("target_subs", 0)
        current = ch.get("current_subs", 0)
        is_active = ch.get("is_active", 1)

        status_emoji = "🟢" if is_active else "🔴"
        target_str = f"({current}/{target} ta)" if target > 0 else f"({current} ta / Cheksiz)"
        
        buttons.append([
            InlineKeyboardButton(text=f"{status_emoji} {title} {target_str}", callback_data=f"adm_ch_info_{ch['id']}")
        ])
        buttons.append([
            InlineKeyboardButton(text="🔄 Yoqish/O'chirish", callback_data=f"adm_ch_toggle_{ch['id']}"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"adm_ch_del_{ch['id']}"),
        ])

    buttons.append([
        InlineKeyboardButton(text="➕ Yangi Kanal Qo'shish", callback_data="admin_add_channel")
    ])
    buttons.append([
        InlineKeyboardButton(text="⬅️ Admin menyu", callback_data="admin_back_to_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kb_required_channels(channels: list[dict], lang: str = "uz") -> InlineKeyboardMarkup:
    """Dynamic keyboard displaying all required channels for user subscription."""
    ch_word = {"uz": "Kanal", "ru": "Канал", "en": "Channel"}.get(lang, "Kanal")
    buttons = []
    for idx, ch in enumerate(channels, 1):
        title = ch.get("channel_title") or f"{ch_word} #{idx}"
        link = ch.get("invite_link")
        if not link:
            ch_uname = ch.get("channel_id", "").lstrip("@")
            link = f"https://t.me/{ch_uname}"
        
        buttons.append([
            InlineKeyboardButton(text=f"📢 {title}", url=link)
        ])

    buttons.append([
        InlineKeyboardButton(text=t("sub_check_btn", lang), callback_data="act_check_sub")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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


def kb_user_crm_actions(user_id: int, is_vip: bool = False, is_banned: bool = False) -> InlineKeyboardMarkup:
    """Full 1-click User CRM controls (VIP grant/revoke, Bonus, DM, Ban/Unban)."""
    vip_row = [
        InlineKeyboardButton(text="💎 +30 kun VIP", callback_data=f"crm_vip_{user_id}_30"),
        InlineKeyboardButton(text="👑 +365 kun VIP", callback_data=f"crm_vip_{user_id}_365"),
    ]
    rows = [vip_row]
    if is_vip:
        rows.append([InlineKeyboardButton(text="❌ VIP ni olib tashlash", callback_data=f"crm_unvip_{user_id}")])
    rows.append([
        InlineKeyboardButton(text="➕ 5 Bonus", callback_data=f"adm_addbal_{user_id}_5"),
        InlineKeyboardButton(text="➕ 10 Bonus", callback_data=f"adm_addbal_{user_id}_10"),
    ])
    ban_btn = (
        InlineKeyboardButton(text="✅ Bandan chiqarish", callback_data=f"crm_unban_{user_id}")
        if is_banned
        else InlineKeyboardButton(text="🚫 Bloklash (Ban)", callback_data=f"crm_ban_{user_id}")
    )
    rows.append([
        InlineKeyboardButton(text="📩 Xabar yozish", callback_data=f"crm_dm_{user_id}"),
        ban_btn,
    ])
    rows.append([InlineKeyboardButton(text="⬅️ Admin panel", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_admin_back() -> InlineKeyboardMarkup:
    """Back to admin panel."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="admin_back")],
    ])


def kb_admin_pagination(prefix: str, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Dynamic pagination keyboard for admin lists (e.g. active24, new24)."""
    rows = []
    if total_pages > 1:
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"{prefix}_p_{page - 1}"))
        nav_row.append(InlineKeyboardButton(text=f"📄 {page} / {total_pages}", callback_data="admin_noop"))
        if page < total_pages:
            nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"{prefix}_p_{page + 1}"))
        rows.append(nav_row)

    rows.append([
        InlineKeyboardButton(text="🔄 Yangilash", callback_data=f"{prefix}_p_{page}"),
        InlineKeyboardButton(text="⬅️ Admin panel", callback_data="admin_back"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_broadcast_confirm() -> InlineKeyboardMarkup:
    """Broadcast confirmation keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, yubor", callback_data="broadcast_confirm"),
            InlineKeyboardButton(text="❌ Bekor", callback_data="broadcast_cancel"),
        ],
    ])
