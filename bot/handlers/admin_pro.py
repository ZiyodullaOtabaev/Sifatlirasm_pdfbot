"""
PRO Admin Control Center Router:
- Dynamic Zero-Code Settings & Maintenance Mode
- Ad Links (UTM) Analytics (?start=ad_<code>)
- Finance Dashboard (Stars & Card revenue)
- Promo Codes Management
- User CRM (1-click VIP grant/revoke, Ban/Unban, Direct Message)
"""
import html
import logging
import re
import time
from typing import Dict

from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.config import ADMIN_IDS, ADMIN_ID
from bot.database import (
    get_all_settings, set_setting, get_vip_until, has_active_img_pdf_pass,
    activate_img_pdf_pass, revoke_vip_pass, set_user_banned, get_user_full_info,
    get_user_daily_uses, get_daily_free_limit, get_user_language,
    create_ad_link, delete_ad_link, get_ad_links_stats,
    get_finance_summary, create_promo_code, get_all_promo_codes,
    toggle_promo_code, delete_promo_code, log_payment,
)
from bot.i18n import t
from bot.keyboards import kb_admin_back, kb_cancel, kb_user_crm_actions, kb_main_reply
from bot.states import (
    get_state, set_state, STATE_NONE,
    STATE_WAIT_ADMIN_SETTING_VALUE, STATE_WAIT_ADMIN_AD_TITLE,
    STATE_WAIT_ADMIN_PROMO_INPUT, STATE_WAIT_ADMIN_DM_TEXT,
)

logger = logging.getLogger(__name__)
router = Router(name="admin_pro")

# Temporary wizard state per admin
ADMIN_EDIT_SETTING_KEY: Dict[int, str] = {}
ADMIN_DM_TARGET: Dict[int, int] = {}


def _is_admin(user_id: int) -> bool:
    return (user_id in ADMIN_IDS) or (ADMIN_ID and user_id == ADMIN_ID)


def render_user_crm_card(user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    """Render full CRM profile card and 1-click management keyboard for a user."""
    u = get_user_full_info(user_id)
    if not u:
        return f"❌ Foydalanuvchi topilmadi (<code>{user_id}</code>).", kb_admin_back()

    uname = f"@{html.escape(u['username'])}" if u.get("username") else "yo'q"
    name = html.escape(f"{u.get('first_name') or ''} {u.get('last_name') or ''}".strip() or "-")
    vip_until = get_vip_until(user_id)
    is_vip = bool(vip_until)
    is_banned = bool(u.get("is_banned"))
    is_blocked = bool(u.get("is_blocked"))
    daily_limit = get_daily_free_limit()
    daily_used = get_user_daily_uses(user_id)
    ad_src = html.escape(u.get("ad_source") or "")
    created = str(u.get("created_at") or "")[:10]

    vip_str = f"💎 VIP (<b>{vip_until}</b> gacha)" if is_vip else "🆓 Oddiy"
    status_flags = []
    if is_banned:
        status_flags.append("🚫 BAN QILINGAN")
    if is_blocked:
        status_flags.append("📵 Botni bloklagan")
    if not status_flags:
        status_flags.append("🟢 Faol / Tirik")

    limit_str = "♾ Cheksiz" if (is_vip or daily_limit == 0) else f"{daily_used}/{daily_limit} ta"

    lines = [
        f"👤 <b>Foydalanuvchi CRM Kartasi</b>",
        "",
        f"• Ism: <b>{name}</b> ({uname})",
        f"• ID: <code>{user_id}</code> | Til: <b>{u.get('language', 'uz').upper()}</b>",
        f"• Holat: <b>{' | '.join(status_flags)}</b>",
        f"• Maqom: {vip_str}",
        f"• 📅 Bugungi limit: <b>{limit_str}</b>",
        f"• 🎁 Bonus zaxira: <b>{u.get('balance', 0)} ta</b>",
        f"• 📊 Jami foydalanish: <b>{u.get('uses_count', 0)} marta</b>",
        f"• 📆 Ro'yxatdan o'tgan: <b>{created}</b>",
    ]
    if ad_src:
        lines.append(f"• 🔗 Reklama manbasi: <code>ad_{ad_src}</code>")

    return "\n".join(lines), kb_user_crm_actions(user_id, is_vip=is_vip, is_banned=is_banned)


# =========================================================================
# 1. DYNAMIC SETTINGS & MAINTENANCE MODE
# =========================================================================

SETTING_META = {
    "daily_free_limit": ("📅 Kunlik bepul limit (0 = Cheksiz)", "int_zero"),
    "vip_30_uzs": ("💎 1 Oylik VIP narxi (so'm)", "int_pos"),
    "vip_365_uzs": ("👑 1 Yillik VIP narxi (so'm)", "int_pos"),
    "vip_30_stars": ("⭐️ 1 Oylik VIP narxi (Stars)", "int_pos"),
    "vip_365_stars": ("⭐️ 1 Yillik VIP narxi (Stars)", "int_pos"),
    "card_number": ("💳 To'lov karta raqami", "card"),
}


def _build_settings_view() -> tuple[str, InlineKeyboardMarkup]:
    s = get_all_settings()
    limit_val = s["daily_free_limit"]
    limit_disp = "♾ Cheksiz (0)" if limit_val == "0" else f"{limit_val} ta/kun"
    maint_on = s["maintenance_mode"] == "1"
    maint_disp = "🟢 YOQIQ (Foydalanuvchilar uchun yopiq)" if maint_on else "🔴 O'CHIQ (Bot ishlayapti)"
    uzs_30 = f"{int(s['vip_30_uzs']):,}".replace(",", " ")
    uzs_365 = f"{int(s['vip_365_uzs']):,}".replace(",", " ")

    text = (
        "⚙️ <b>Bot Dinamik Sozlamalari</b>\n"
        "<i>Kodga tegmasdan barcha narx va cheklovlarni 1 soniyada o'zgartiring:</i>\n\n"
        f"📅 <b>Kunlik bepul limit:</b> {limit_disp}\n"
        f"💎 <b>1 Oylik VIP:</b> {uzs_30} so'm | ⭐️ {s['vip_30_stars']} Stars\n"
        f"👑 <b>1 Yillik VIP:</b> {uzs_365} so'm | ⭐️ {s['vip_365_stars']} Stars\n"
        f"💳 <b>Karta raqami:</b> <code>{html.escape(s['card_number'])}</code>\n"
        f"🔧 <b>Texnik rejim:</b> {maint_disp}\n\n"
        "👇 O'zgartirmoqchi bo'lgan bo'limni tanlang:"
    )

    maint_btn_text = "🟢 Texnik rejimni O'CHIRISH" if maint_on else "🔧 Texnik rejimni YOQISH"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📅 Kunlik limit ({limit_val})", callback_data="set_edit_daily_free_limit")],
        [
            InlineKeyboardButton(text=f"💎 1 Oy ({uzs_30})", callback_data="set_edit_vip_30_uzs"),
            InlineKeyboardButton(text=f"⭐️ 1 Oy ({s['vip_30_stars']}⭐)", callback_data="set_edit_vip_30_stars"),
        ],
        [
            InlineKeyboardButton(text=f"👑 1 Yil ({uzs_365})", callback_data="set_edit_vip_365_uzs"),
            InlineKeyboardButton(text=f"⭐️ 1 Yil ({s['vip_365_stars']}⭐)", callback_data="set_edit_vip_365_stars"),
        ],
        [InlineKeyboardButton(text="💳 Karta raqamini o'zgartirish", callback_data="set_edit_card_number")],
        [InlineKeyboardButton(text=maint_btn_text, callback_data="set_toggle_maint")],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="admin_back")],
    ])
    return text, kb


@router.callback_query(F.data == "admin_settings")
async def cb_admin_settings(call: CallbackQuery, bot: Bot):
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    set_state(call.from_user.id, STATE_NONE)
    text, kb = _build_settings_view()
    await bot.send_message(call.from_user.id, text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "set_toggle_maint")
async def cb_toggle_maintenance(call: CallbackQuery, bot: Bot):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    s = get_all_settings()
    new_val = "0" if s["maintenance_mode"] == "1" else "1"
    set_setting("maintenance_mode", new_val)
    text, kb = _build_settings_view()
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await bot.send_message(call.from_user.id, text, parse_mode="HTML", reply_markup=kb)
    await call.answer("🔧 Texnik rejim YOQILDI!" if new_val == "1" else "✅ Bot oddiy rejimga qaytdi!", show_alert=True)


@router.callback_query(F.data.startswith("set_edit_"))
async def cb_edit_setting_prompt(call: CallbackQuery, bot: Bot):
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    key = call.data.replace("set_edit_", "")
    if key not in SETTING_META:
        return
    label, _ = SETTING_META[key]
    ADMIN_EDIT_SETTING_KEY[call.from_user.id] = key
    set_state(call.from_user.id, STATE_WAIT_ADMIN_SETTING_VALUE)
    await bot.send_message(
        call.from_user.id,
        f"✏️ <b>{label}</b>\n\nYangi qiymatni yozib yuboring:",
        parse_mode="HTML",
        reply_markup=kb_cancel(),
    )


@router.message(lambda msg: msg.text and not msg.text.startswith("/") and get_state(msg.from_user.id) == STATE_WAIT_ADMIN_SETTING_VALUE and _is_admin(msg.from_user.id))
async def handle_admin_setting_input(message: Message, bot: Bot):
    admin_id = message.from_user.id
    key = ADMIN_EDIT_SETTING_KEY.get(admin_id)
    if not key or key not in SETTING_META:
        set_state(admin_id, STATE_NONE)
        return

    raw = message.text.strip().replace(" ", "").replace(",", "")
    label, kind = SETTING_META[key]

    if kind == "int_zero":
        if not raw.isdigit():
            await message.answer("❌ Iltimos, faqat 0 yoki musbat son kiriting (masalan: <code>5</code> yoki <code>0</code>):", parse_mode="HTML")
            return
        set_setting(key, str(int(raw)))
    elif kind == "int_pos":
        if not raw.isdigit() or int(raw) <= 0:
            await message.answer("❌ Iltimos, 0 dan katta son kiriting (masalan: <code>9000</code>):", parse_mode="HTML")
            return
        set_setting(key, str(int(raw)))
    elif kind == "card":
        digits = "".join(c for c in message.text if c.isdigit())
        if len(digits) < 12:
            await message.answer("❌ Karta raqami noto'g'ri ko'rinadi. Kamida 16 xonali karta raqamini kiriting:", parse_mode="HTML")
            return
        set_setting(key, digits)

    ADMIN_EDIT_SETTING_KEY.pop(admin_id, None)
    set_state(admin_id, STATE_NONE)
    text, kb = _build_settings_view()
    await message.answer(f"✅ <b>{label}</b> muvaffaqiyatli yangilandi!\n\n" + text, parse_mode="HTML", reply_markup=kb)


# =========================================================================
# 2. AD LINKS (UTM ANALYTICS)
# =========================================================================

async def _build_ad_links_view(bot: Bot) -> tuple[str, InlineKeyboardMarkup]:
    me = await bot.get_me()
    bot_uname = me.username or "sifatlirasm_pdfbot"
    links = get_ad_links_stats()

    lines = [
        "🔗 <b>Reklama Havolalari (UTM Analitika)</b>",
        "<i>Har bir reklama bergan kanalingiz uchun alohida havola yarating va aniq natijani ko'ring:</i>",
        "",
    ]
    buttons = []
    if not links:
        lines.append("Hozircha reklama havolalari yaratilmagan.")
    else:
        for item in links[:15]:
            code = item["code"]
            title = html.escape(item["title"])
            url = f"https://t.me/{bot_uname}?start=ad_{code}"
            lines.append(
                f"📌 <b>{title}</b> ({item['created_date']})\n"
                f"🔗 <code>{url}</code>\n"
                f"   👆 Bosish: <b>{item['clicks']}</b> | 🆕 Yangi: <b>{item['new_users']}</b> | "
                f"⚙️ Ishlatgan: <b>{item['active_users']}</b> | 💎 VIP: <b>{item['vip_users']}</b>\n"
            )
            buttons.append([
                InlineKeyboardButton(text=f"🗑 O'chirish: {item['title'][:22]}", callback_data=f"admin_ad_del_{item['id']}")
            ])

    buttons.insert(0, [InlineKeyboardButton(text="➕ Yangi reklama havolasi", callback_data="admin_ad_new")])
    buttons.append([InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_ad_links_refresh")])
    buttons.append([InlineKeyboardButton(text="⬅️ Admin panel", callback_data="admin_back")])
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "admin_ad_links")
async def cb_admin_ad_links(call: CallbackQuery, bot: Bot):
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    text, kb = await _build_ad_links_view(bot)
    await bot.send_message(call.from_user.id, text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)


@router.callback_query(F.data == "admin_ad_links_refresh")
async def cb_admin_ad_links_refresh(call: CallbackQuery, bot: Bot):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    text, kb = await _build_ad_links_view(bot)
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
        await call.answer()
    except Exception:
        await call.answer("✅ Yangilandi")


@router.callback_query(F.data == "admin_ad_new")
async def cb_admin_ad_new(call: CallbackQuery, bot: Bot):
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    set_state(call.from_user.id, STATE_WAIT_ADMIN_AD_TITLE)
    await bot.send_message(
        call.from_user.id,
        "➕ <b>Yangi Reklama Havolasi Yaratish</b>\n\n"
        "Reklama berayotgan kanal yoki bloger nomini yozing:\n"
        "<i>Masalan: <code>Talabalar kanali 1K</code></i>",
        parse_mode="HTML",
        reply_markup=kb_cancel(),
    )


@router.message(lambda msg: msg.text and not msg.text.startswith("/") and get_state(msg.from_user.id) == STATE_WAIT_ADMIN_AD_TITLE and _is_admin(msg.from_user.id))
async def handle_admin_ad_title(message: Message, bot: Bot):
    admin_id = message.from_user.id
    title = message.text.strip()[:80]
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:16]
    code = f"{slug}_{int(time.time()) % 10000}" if slug else f"ch_{int(time.time()) % 100000}"
    create_ad_link(code, title)
    set_state(admin_id, STATE_NONE)

    me = await bot.get_me()
    bot_uname = me.username or "sifatlirasm_pdfbot"
    full_url = f"https://t.me/{bot_uname}?start=ad_{code}"

    await message.answer(
        f"✅ <b>Reklama havolasi tayyor!</b>\n\n"
        f"📌 Nomi: <b>{html.escape(title)}</b>\n"
        f"🔗 Havola (nusxalab reklama postiga qo'ying):\n"
        f"<code>{full_url}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Barcha havolalar", callback_data="admin_ad_links")],
            [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="admin_back")],
        ]),
    )


@router.callback_query(F.data.startswith("admin_ad_del_"))
async def cb_admin_ad_delete(call: CallbackQuery, bot: Bot):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    try:
        link_id = int(call.data.replace("admin_ad_del_", ""))
        delete_ad_link(link_id)
    except ValueError:
        pass
    await call.answer("🗑 Havola o'chirildi!")
    text, kb = await _build_ad_links_view(bot)
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
    except Exception:
        await bot.send_message(call.from_user.id, text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)


# =========================================================================
# 3. FINANCE DASHBOARD
# =========================================================================

@router.callback_query(F.data == "admin_finance")
async def cb_admin_finance(call: CallbackQuery, bot: Bot):
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    fin = get_finance_summary()

    def _fmt(p: dict) -> str:
        uzs = f"{p['uzs']:,}".replace(",", " ")
        return f"<b>{uzs} so'm</b> + <b>⭐️ {p['stars']:,} Stars</b> ({p['cnt']} ta)"

    lines = [
        "💰 <b>Moliya va Daromad Hisoboti</b>",
        "",
        f"📅 <b>Bugun:</b> {_fmt(fin['today'])}",
        f"📆 <b>Oxirgi 7 kun:</b> {_fmt(fin['week'])}",
        f"🗓 <b>Oxirgi 30 kun:</b> {_fmt(fin['month'])}",
        f"🏦 <b>Jami (barcha vaqt):</b> {_fmt(fin['total'])}",
        "",
        "🧾 <b>So'nggi 10 ta to'lov:</b>",
    ]
    recent = fin["recent"]
    if not recent:
        lines.append("<i>Hozircha yangi to'lovlar qayd etilmagan (yangi to'lovlar shu yerga avtomatik yoziladi).</i>")
    else:
        for r in recent:
            uname = f"@{html.escape(r['username'])}" if r.get("username") else f"<code>{r['user_id']}</code>"
            amt = f"⭐️ {r['amount_stars']} Stars" if r["amount_stars"] else f"{r['amount_uzs']:,} so'm".replace(",", " ")
            m_icon = "⭐️" if "stars" in r["method"] else "💳"
            lines.append(f"• {r['dt']} | {uname} | {m_icon} <b>{amt}</b> ({html.escape(r.get('note') or r['method'])})")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 VIP obunachilar", callback_data="admin_vip_users")],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="admin_back")],
    ])
    await bot.send_message(call.from_user.id, "\n".join(lines), parse_mode="HTML", reply_markup=kb)


# =========================================================================
# 4. PROMO CODES MANAGEMENT
# =========================================================================

def _build_promos_view() -> tuple[str, InlineKeyboardMarkup]:
    promos = get_all_promo_codes()
    lines = [
        "🎟 <b>Promokodlar Boshqaruvi</b>",
        "<i>Blogerlar, aksiyalar va sovg'alar uchun cheklangan yoki cheksiz promokodlar yarating:</i>",
        "",
    ]
    buttons = [[InlineKeyboardButton(text="➕ Yangi promokod yaratish", callback_data="admin_promo_new")]]
    if not promos:
        lines.append("Hozircha promokodlar yo'q.")
    else:
        for p in promos[:15]:
            st = "🟢" if p["is_active"] == 1 else "🔴"
            reward = f"💎 +{p['reward_value']} kun VIP" if p["reward_type"] == "vip_days" else f"🎁 +{p['reward_value']} bonus"
            limit_str = f"{p['used_count']}/{p['max_uses']}" if p["max_uses"] > 0 else f"{p['used_count']}/∞"
            lines.append(f"{st} <code>{html.escape(p['code'])}</code> — {reward} | Ishlatildi: <b>{limit_str}</b>")
            buttons.append([
                InlineKeyboardButton(text=f"🔄 {p['code']}", callback_data=f"admin_promo_toggle_{p['id']}"),
                InlineKeyboardButton(text=f"🗑 O'chirish", callback_data=f"admin_promo_del_{p['id']}"),
            ])
    buttons.append([InlineKeyboardButton(text="⬅️ Admin panel", callback_data="admin_back")])
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "admin_promos")
async def cb_admin_promos(call: CallbackQuery, bot: Bot):
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    text, kb = _build_promos_view()
    await bot.send_message(call.from_user.id, text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "admin_promo_new")
async def cb_admin_promo_new(call: CallbackQuery, bot: Bot):
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    set_state(call.from_user.id, STATE_WAIT_ADMIN_PROMO_INPUT)
    await bot.send_message(
        call.from_user.id,
        "➕ <b>Yangi Promokod Yaratish</b>\n\n"
        "Quyidagi formatda bitta qator yuboring:\n"
        "<code>KOD TURI MIQDOR LIMIT</code>\n\n"
        "<b>Misollar:</b>\n"
        "• <code>VIP3KUN vip 3 50</code> — 50 kishiga +3 kunlik VIP\n"
        "• <code>AKSIYA7 vip 7 0</code> — Cheksiz kishiga +7 kunlik VIP\n"
        "• <code>BONUS10 bonus 10 100</code> — 100 kishiga +10 ta bonus limit",
        parse_mode="HTML",
        reply_markup=kb_cancel(),
    )


@router.message(lambda msg: msg.text and not msg.text.startswith("/") and get_state(msg.from_user.id) == STATE_WAIT_ADMIN_PROMO_INPUT and _is_admin(msg.from_user.id))
async def handle_admin_promo_create(message: Message, bot: Bot):
    parts = message.text.strip().split()
    if len(parts) < 3:
        await message.answer(
            "❌ Noto'g'ri format! Misol: <code>VIP3KUN vip 3 50</code>",
            parse_mode="HTML",
            reply_markup=kb_cancel(),
        )
        return

    code = parts[0].upper()
    kind_raw = parts[1].lower()
    reward_type = "vip_days" if kind_raw in ("vip", "vip_days", "kun") else "bonus_uses" if kind_raw in ("bonus", "bonus_uses", "kredit") else ""
    if not reward_type or not parts[2].isdigit() or int(parts[2]) <= 0:
        await message.answer(
            "❌ Turi <code>vip</code> yoki <code>bonus</code> bo'lishi, miqdor esa musbat son bo'lishi kerak.\n"
            "Misol: <code>VIP3KUN vip 3 50</code>",
            parse_mode="HTML",
        )
        return

    reward_val = int(parts[2])
    max_uses = int(parts[3]) if (len(parts) >= 4 and parts[3].isdigit()) else 0

    ok = create_promo_code(code, reward_type, reward_val, max_uses)
    set_state(message.from_user.id, STATE_NONE)
    if not ok:
        await message.answer(f"⚠️ <code>{html.escape(code)}</code> promokodi allaqachon mavjud!", parse_mode="HTML", reply_markup=kb_admin_back())
        return

    text, kb = _build_promos_view()
    await message.answer(f"✅ Promokod <code>{html.escape(code)}</code> yaratildi!\n\n" + text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("admin_promo_toggle_"))
async def cb_admin_promo_toggle(call: CallbackQuery, bot: Bot):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    try:
        pid = int(call.data.replace("admin_promo_toggle_", ""))
        toggle_promo_code(pid)
    except ValueError:
        pass
    await call.answer("🔄 Holat o'zgartirildi!")
    text, kb = _build_promos_view()
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await bot.send_message(call.from_user.id, text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("admin_promo_del_"))
async def cb_admin_promo_delete(call: CallbackQuery, bot: Bot):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    try:
        pid = int(call.data.replace("admin_promo_del_", ""))
        delete_promo_code(pid)
    except ValueError:
        pass
    await call.answer("🗑 Promokod o'chirildi!")
    text, kb = _build_promos_view()
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await bot.send_message(call.from_user.id, text, parse_mode="HTML", reply_markup=kb)


# =========================================================================
# 5. USER CRM 1-CLICK ACTIONS (VIP, UNVIP, BAN, UNBAN, DIRECT MESSAGE)
# =========================================================================

@router.callback_query(F.data.startswith("crm_vip_"))
async def cb_crm_grant_vip(call: CallbackQuery, bot: Bot):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    parts = call.data.replace("crm_vip_", "").split("_")
    if len(parts) < 2:
        await call.answer()
        return
    uid, days = int(parts[0]), int(parts[1])
    activate_img_pdf_pass(uid, days=days)
    vip_until = get_vip_until(uid) or ""
    log_payment(uid, "admin_grant", plan_days=days, amount_uzs=0, amount_stars=0, note=f"Admin +{days} kun VIP")

    u_lang = get_user_language(uid) or "uz"
    try:
        await bot.send_message(
            uid,
            t("vip_activated_notify", u_lang, days=days, vip_until=vip_until),
            parse_mode="HTML",
            reply_markup=kb_main_reply(u_lang),
        )
    except Exception:
        pass

    text, kb = render_user_crm_card(uid)
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await bot.send_message(call.from_user.id, text, parse_mode="HTML", reply_markup=kb)
    await call.answer(f"💎 +{days} kun VIP berildi!", show_alert=True)


@router.callback_query(F.data.startswith("crm_unvip_"))
async def cb_crm_revoke_vip(call: CallbackQuery, bot: Bot):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    uid = int(call.data.replace("crm_unvip_", ""))
    revoke_vip_pass(uid)
    text, kb = render_user_crm_card(uid)
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await bot.send_message(call.from_user.id, text, parse_mode="HTML", reply_markup=kb)
    await call.answer("❌ VIP obuna bekor qilindi!", show_alert=True)


@router.callback_query(F.data.startswith("crm_ban_"))
async def cb_crm_ban_user(call: CallbackQuery, bot: Bot):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    uid = int(call.data.replace("crm_ban_", ""))
    if _is_admin(uid):
        await call.answer("⛔️ Adminni ban qilib bo'lmaydi!", show_alert=True)
        return
    set_user_banned(uid, 1)
    text, kb = render_user_crm_card(uid)
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await bot.send_message(call.from_user.id, text, parse_mode="HTML", reply_markup=kb)
    await call.answer("🚫 Foydalanuvchi bloklandi!", show_alert=True)


@router.callback_query(F.data.startswith("crm_unban_"))
async def cb_crm_unban_user(call: CallbackQuery, bot: Bot):
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    uid = int(call.data.replace("crm_unban_", ""))
    set_user_banned(uid, 0)
    text, kb = render_user_crm_card(uid)
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await bot.send_message(call.from_user.id, text, parse_mode="HTML", reply_markup=kb)
    await call.answer("✅ Foydalanuvchi bandan chiqarildi!", show_alert=True)


@router.callback_query(F.data.startswith("crm_dm_"))
async def cb_crm_dm_prompt(call: CallbackQuery, bot: Bot):
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    uid = int(call.data.replace("crm_dm_", ""))
    ADMIN_DM_TARGET[call.from_user.id] = uid
    set_state(call.from_user.id, STATE_WAIT_ADMIN_DM_TEXT)
    await bot.send_message(
        call.from_user.id,
        f"📩 <b>Foydalanuvchiga (<code>{uid}</code>) shaxsiy xabar yozish:</b>\n\n"
        f"Yubormoqchi bo'lgan matningizni yozing:",
        parse_mode="HTML",
        reply_markup=kb_cancel(),
    )


@router.message(lambda msg: msg.text and not msg.text.startswith("/") and get_state(msg.from_user.id) == STATE_WAIT_ADMIN_DM_TEXT and _is_admin(msg.from_user.id))
async def handle_crm_dm_send(message: Message, bot: Bot):
    admin_id = message.from_user.id
    target_uid = ADMIN_DM_TARGET.pop(admin_id, None)
    set_state(admin_id, STATE_NONE)
    if not target_uid:
        return
    try:
        await bot.send_message(
            target_uid,
            f"📩 <b>Admin xabari:</b>\n\n{html.escape(message.text)}",
            parse_mode="HTML",
        )
        await message.answer(
            f"✅ Xabar <code>{target_uid}</code> ga muvaffaqiyatli yuborildi!",
            parse_mode="HTML",
            reply_markup=kb_admin_back(),
        )
    except Exception as e:
        await message.answer(
            f"❌ Yuborib bo'lmadi (foydalanuvchi botni bloklagan bo'lishi mumkin): <code>{html.escape(str(e))}</code>",
            parse_mode="HTML",
            reply_markup=kb_admin_back(),
        )
