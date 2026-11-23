"""
Admin panel: stats, charts, user search, professional broadcast system.
Features:
- Inline buttons in broadcast [text|url] format
- HTML formatting support (bold, italic, links)
- Photo/Video/Document/Text broadcast
- Scheduled broadcast (time-delayed)
- Click tracking via inline buttons
"""
import re
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, BufferedInputFile, FSInputFile,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

from bot.config import ADMIN_IDS, BROADCAST_RATE, DB_PATH
from bot.database import (
    upsert_user, get_admin_summary, daily_usage_by_action,
    get_top_users, get_new_users_24h, get_new_users_24h_count,
    get_active_users_24h, get_active_users_24h_count,
    get_vip_users, get_vip_users_count,
    get_all_user_ids, get_segmented_user_ids, count_segmented_users,
    mark_user_blocked, save_broadcast_result,
    get_action_stats, get_growth_stats,
    get_broadcast_history, search_user,
)
from bot.i18n import t
from bot.keyboards import (
    kb_admin, kb_admin_back, kb_admin_pagination,
    kb_broadcast_confirm, kb_cancel, kb_user_balance_actions,
)
from bot.states import (
    set_state, get_state, STATE_NONE, STATE_WAIT_BROADCAST,
    STATE_WAIT_ADMIN_BALANCE_INPUT, STATE_WAIT_SEARCH,
    STATE_WAIT_ADMIN_CHANNEL_ID, STATE_WAIT_ADMIN_CHANNEL_TARGET
)
from bot.utils.chart import render_usage_chart_png, render_growth_chart_png, render_stats_image

logger = logging.getLogger(__name__)
router = Router(name="admin")

# Broadcast state storage
PENDING_BROADCAST: Dict[int, dict] = {}
BROADCAST_RUNNING: Dict[int, bool] = {}
BROADCAST_CANCEL: Dict[int, bool] = {}
SCHEDULED_TASKS: Dict[int, asyncio.Task] = {}

STATE_WAIT_SCHEDULE_TIME = "wait_schedule_time"
STATE_WAIT_BROADCAST_CAPTION = "wait_broadcast_caption"


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("addbalance"))
async def cmd_addbalance(message: Message, bot: Bot):
    """Admin command to add paid credits balance to a user: /addbalance <user_id_yoki_username> <amount>"""
    if not _is_admin(message.from_user.id):
        return

    args = message.text.split()
    if len(args) < 3 or not args[2].lstrip("-").isdigit():
        await message.answer(
            "⚠️ <b>Noto'g'ri buyruq formati!</b>\n\n"
            "Foydalanish: <code>/addbalance &lt;user_id yoki username&gt; &lt;miqdor&gt;</code>\n\n"
            "Misollar:\n"
            "• <code>/addbalance otabyvaa1 5</code>\n"
            "• <code>/addbalance 8247903602 10</code>",
            parse_mode="HTML"
        )
        return

    target_query = args[1]
    amount = int(args[2])

    from bot.database import resolve_user_id, add_user_balance, get_user_balance
    user_info = resolve_user_id(target_query)
    if not user_info:
        await message.answer(
            f"❌ Foydalanuvchi topilmadi: <b>{target_query}</b>\n"
            "<i>Foydalanuvchi botga kamida bir marta /start bosgan bo'lishi kerak.</i>",
            parse_mode="HTML"
        )
        return

    target_user_id = user_info["user_id"]
    username_str = f"@{user_info['username']}" if user_info.get("username") else f"ID: {target_user_id}"

    add_user_balance(target_user_id, amount)
    new_bal = get_user_balance(target_user_id)

    await message.answer(
        f"✅ Foydalanuvchi <b>{username_str}</b> (<code>{target_user_id}</code>) balansiga <b>+{amount}</b> kredit qo'shildi!\n"
        f"💰 Yangi balans: <b>{new_bal} kredit</b>",
        parse_mode="HTML"
    )

    # Foydalanuvchiga bildirishnoma yuborish
    try:
        from bot.i18n import t
        from bot.database import get_user_language
        u_lang = get_user_language(target_user_id) or "uz"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_ai_video", u_lang), callback_data="act_ai_video")]
        ])
        await bot.send_message(
            target_user_id,
            f"🎉 <b>Balansingiz to'ldirildi!</b>\n\n"
            f"➕ Qo'shildi: <b>+{amount} kredit</b>\n"
            f"📊 Umumiy balans: <b>{new_bal} kredit</b>\n\n"
            f"Video yaratish uchun pastdagi tugmani bosing 👇",
            parse_mode="HTML",
            reply_markup=kb
        )
    except Exception as e:
        logger.warning(f"Could not notify user {target_user_id} about balance add: {e}")


@router.message(Command("setbalance"))
async def cmd_setbalance(message: Message, bot: Bot):
    """Admin command to set exact credits balance for a user: /setbalance <user_id_yoki_username> <amount>"""
    if not _is_admin(message.from_user.id):
        return

    args = message.text.split()
    if len(args) < 3 or not args[2].isdigit():
        await message.answer(
            "⚠️ <b>Noto'g'ri buyruq formati!</b>\n\n"
            "Foydalanish: <code>/setbalance &lt;user_id yoki username&gt; &lt;miqdor&gt;</code>\n\n"
            "Misol: <code>/setbalance otabyvaa1 10</code>",
            parse_mode="HTML"
        )
        return

    target_query = args[1]
    amount = int(args[2])

    from bot.database import resolve_user_id, set_user_balance
    user_info = resolve_user_id(target_query)
    if not user_info:
        await message.answer(f"❌ Foydalanuvchi topilmadi: <b>{target_query}</b>", parse_mode="HTML")
        return

    target_user_id = user_info["user_id"]
    username_str = f"@{user_info['username']}" if user_info.get("username") else f"ID: {target_user_id}"

    set_user_balance(target_user_id, amount)

    await message.answer(
        f"✅ Foydalanuvchi <b>{username_str}</b> (<code>{target_user_id}</code>) balansi <b>{amount} kredit</b> ga o'rnatildi!",
        parse_mode="HTML"
    )

    try:
        from bot.i18n import t
        from bot.database import get_user_language
        u_lang = get_user_language(target_user_id) or "uz"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_ai_video", u_lang), callback_data="act_ai_video")]
        ])
        await bot.send_message(
            target_user_id,
            f"📊 <b>Balansingiz o'zgartirildi:</b>\n"
            f"💰 Joriy balans: <b>{amount} kredit</b>",
            parse_mode="HTML",
            reply_markup=kb
        )
    except Exception:
        pass


def _parse_inline_buttons(text: str) -> tuple[str, Optional[InlineKeyboardMarkup]]:
    """
    Parse [text|url] patterns from caption and create inline keyboard.
    Returns (cleaned_text, keyboard_or_None).
    
    Format:
      [Kanalga o'tish|https://t.me/channel]
      [Saytga kirish|https://example.com]
    
    Multiple buttons per line separated by space create columns.
    Each new line of buttons = new row.
    """
    pattern = r'\[([^\]|]+)\|([^\]]+)\]'
    matches = re.findall(pattern, text)
    
    if not matches:
        return text, None
    
    # Remove button patterns from text
    clean_text = re.sub(pattern, '', text).strip()
    # Remove empty lines left behind
    clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
    
    # Build keyboard rows
    # Each line with buttons = separate row
    lines_with_buttons = []
    for line in text.split('\n'):
        line_matches = re.findall(pattern, line)
        if line_matches:
            row = [
                InlineKeyboardButton(text=btn_text.strip(), url=btn_url.strip())
                for btn_text, btn_url in line_matches
            ]
            lines_with_buttons.append(row)
    
    if not lines_with_buttons:
        # Fallback: all buttons in one column
        lines_with_buttons = [
            [InlineKeyboardButton(text=btn_text.strip(), url=btn_url.strip())]
            for btn_text, btn_url in matches
        ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=lines_with_buttons)
    return clean_text, keyboard


# ========================
# COMMANDS
# ========================

@router.message(Command("admin"))
async def cmd_admin(message: Message, bot: Bot):
    """Admin panel — statistics as image."""
    if not _is_admin(message.from_user.id):
        return
    s = get_admin_summary()
    action_stats = get_action_stats()
    png = render_stats_image(s, action_stats)
    photo = BufferedInputFile(png, filename="stats.png")
    await bot.send_photo(
        message.from_user.id, photo,
        caption="🛠 <b>Admin Panel</b>\nQuyidan bo'lim tanlang:",
        parse_mode="HTML",
        reply_markup=kb_admin()
    )


@router.message(Command("top"))
async def cmd_top(message: Message):
    """Show top 30 users."""
    if not _is_admin(message.from_user.id):
        return
    rows = get_top_users(30)
    lines = []
    for i, r in enumerate(rows, start=1):
        uname = f"@{r['username']}" if r["username"] else "-"
        name = (f"{r['first_name'] or ''} {r['last_name'] or ''}").strip() or "-"
        lines.append(f"{i}) {uname} | {name} | {r['uses_count']}")
    await message.answer(
        "<b>🏆 TOP-30:</b>\n\n" + ("\n".join(lines) if lines else "---"),
        parse_mode="HTML"
    )


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    """Start broadcast mode."""
    if not _is_admin(message.from_user.id):
        return
    if BROADCAST_RUNNING.get(message.from_user.id):
        await message.answer("⚠️ Hozir broadcast davom etmoqda.")
        return
    PENDING_BROADCAST.pop(message.from_user.id, None)
    set_state(message.from_user.id, STATE_WAIT_BROADCAST)
    await message.answer(
        "<b>📢 Broadcast rejimi</b>\n\n"
        "Reklama xabarini yuboring:\n"
        "• 📸 Rasm (caption bilan)\n"
        "• 🎥 Video (caption bilan)\n"
        "• 📄 Fayl/PDF\n"
        "• 📝 Matn\n\n"
        "<b>💡 Qo'shimcha imkoniyatlar:</b>\n"
        "• HTML formatlash: &lt;b&gt;bold&lt;/b&gt;, &lt;i&gt;italic&lt;/i&gt;\n"
        "• Linklar: &lt;a href=\"url\"&gt;matn&lt;/a&gt;\n"
        "• Tugmalar: <code>[Matn|https://link.com]</code>\n\n"
        "<i>Misol caption:</i>\n"
        "<code>Yangi funksiya! 🎉\n"
        "[Kanalimiz|https://t.me/xonziyy]\n"
        "[Botni ishlatish|https://t.me/unixziyodullabot]</code>",
        parse_mode="HTML",
        reply_markup=kb_cancel()
    )


@router.message(Command("search"))
async def cmd_search(message: Message, bot: Bot):
    """Search user by username/name/id."""
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        await _do_search(message.from_user.id, parts[1].strip(), bot)
    else:
        set_state(message.from_user.id, STATE_WAIT_SEARCH)
        await message.answer(
            "🔍 Username, ism yoki user_id yuboring:",
            reply_markup=kb_admin_back()
        )


# ========================
# ADMIN CALLBACKS
# ========================

@router.callback_query(F.data == "admin_back")
async def cb_admin_back(call: CallbackQuery, bot: Bot):
    """Back to admin panel."""
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    set_state(call.from_user.id, STATE_NONE)
    s = get_admin_summary()
    action_stats = get_action_stats()
    png = render_stats_image(s, action_stats)
    photo = BufferedInputFile(png, filename="stats.png")
    await bot.send_photo(
        call.from_user.id, photo,
        caption="🛠 <b>Admin Panel</b>\nBo'lim tanlang:",
        parse_mode="HTML",
        reply_markup=kb_admin()
    )


@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(call: CallbackQuery, bot: Bot):
    """Full statistics as image."""
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    s = get_admin_summary()
    action_stats = get_action_stats()
    png = render_stats_image(s, action_stats)
    photo = BufferedInputFile(png, filename="stats.png")
    await bot.send_photo(
        call.from_user.id, photo,
        caption="📊 Batafsil statistika",
        reply_markup=kb_admin_back()
    )


@router.callback_query(F.data == "admin_chart7")
async def cb_admin_chart7(call: CallbackQuery, bot: Bot):
    """7-day usage chart."""
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    try:
        data = daily_usage_by_action(7)
        png = render_usage_chart_png(data, "So'nggi 7 kun foydalanish")
        photo = BufferedInputFile(png, filename="usage_7d.png")
        await bot.send_photo(call.from_user.id, photo,
                             caption="📈 7 kunlik foydalanish grafigi",
                             reply_markup=kb_admin_back())
    except Exception as e:
        logger.error(f"Chart7 error: {e}")
        await bot.send_message(call.from_user.id, "❌ Grafik xatolik.",
                               reply_markup=kb_admin_back())


@router.callback_query(F.data == "admin_chart30")
async def cb_admin_chart30(call: CallbackQuery, bot: Bot):
    """30-day growth chart."""
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    try:
        growth = get_growth_stats(30)
        png = render_growth_chart_png(growth, "30 kunlik yangi foydalanuvchilar")
        photo = BufferedInputFile(png, filename="growth_30d.png")
        await bot.send_photo(call.from_user.id, photo,
                             caption="📉 30 kunlik o'sish grafigi",
                             reply_markup=kb_admin_back())
    except Exception as e:
        logger.error(f"Chart30 error: {e}")
        await bot.send_message(call.from_user.id, "❌ Grafik xatolik.",
                               reply_markup=kb_admin_back())


@router.callback_query(F.data == "admin_actions")
async def cb_admin_actions(call: CallbackQuery, bot: Bot):
    """Per-action statistics."""
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    s = get_admin_summary()
    action_stats = get_action_stats()

    action_map = [
        ("img_pdf", "🖼 Rasm ➡️ PDF"),
        ("text_pdf", "📝 Matn ➡️ PDF"),
        ("pdf_to_img", "🖼 PDF ➡️ Rasm"),
        ("split_pdf", "✂️ PDF Bo'lish"),
        ("pdf_merge", "📑 PDF Birlashtirish"),
        ("compress_pdf", "🗜 PDF Siqish"),
        ("delete_pdf_pages", "🗑 Sahifani O'chirish"),
        ("watermark_pdf", "💧 Suv Belgisi Qo'yish"),
    ]

    lines = ["📋 <b>Faol Xizmatlar Statistikasi:</b>\n"]
    for key, name in action_map:
        cnt = action_stats.get(key, 0)
        lines.append(f"{name}: <b>{cnt:,} marta</b>")

    lines.append("\n" + "—" * 25)
    lines.append(f"📊 <b>Umumiy foydalanish:</b> <b>{s.get('total_uses', 0):,} marta</b>")
    lines.append(f"👥 <b>Jami foydalanuvchilar:</b> <b>{s.get('total_users', 0):,} ta</b>")

    text = "\n".join(lines)

    png = render_stats_image(s, action_stats)
    photo = BufferedInputFile(png, filename="actions.png")
    await bot.send_photo(call.from_user.id, photo,
                         caption=text,
                         parse_mode="HTML",
                         reply_markup=kb_admin_back())



@router.callback_query(F.data == "admin_top30")
async def cb_admin_top30(call: CallbackQuery, bot: Bot):
    """Top 30 users."""
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    rows = get_top_users(30)
    lines = []
    for i, r in enumerate(rows, start=1):
        uname = f"@{r['username']}" if r["username"] else "-"
        name = (f"{r['first_name'] or ''} {r['last_name'] or ''}").strip() or "-"
        lines.append(f"{i}. {uname} | {name} | <b>{r['uses_count']}</b>")
    text = "<b>🏆 TOP-30:</b>\n\n" + ("\n".join(lines) if lines else "---")
    await bot.send_message(call.from_user.id, text, parse_mode="HTML",
                           reply_markup=kb_admin_back())


ADMIN_PAGE_SIZE = 30


def _build_new_users_24h_page(page: int = 1) -> tuple[str, InlineKeyboardMarkup]:
    """Build dynamic paginated text and keyboard for new 24h users."""
    import html
    total = get_new_users_24h_count()
    total_pages = max(1, (total + ADMIN_PAGE_SIZE - 1) // ADMIN_PAGE_SIZE)
    page = max(1, min(page, total_pages))
    offset = (page - 1) * ADMIN_PAGE_SIZE

    rows = get_new_users_24h(limit=ADMIN_PAGE_SIZE, offset=offset)
    lines = []
    for idx, row in enumerate(rows, start=offset + 1):
        r = dict(row)
        uname = f"@{html.escape(r['username'])}" if r.get("username") else f"<code>{r['user_id']}</code>"
        raw_name = (f"{r.get('first_name') or ''} {r.get('last_name') or ''}").strip() or "-"
        if len(raw_name) > 26:
            raw_name = raw_name[:25] + "…"
        name = html.escape(raw_name)
        created_at = str(r.get("created_at") or "")
        t_str = created_at[11:16] if len(created_at) >= 16 else ""
        uses = r.get("uses_count", 0)
        lines.append(f"{idx}. {uname} | {name} | <b>{uses} ta</b> | {t_str}")

    header = f"<b>🆕 Yangi 24 soat (Jami: {total:,} ta)</b> | Sahifa: <b>{page}/{total_pages}</b>\n\n"
    text = header + ("\n".join(lines) if lines else "Hozircha hech kim yo'q")
    if len(text) > 4000:
        text = text[:3950] + "\n\n<i>...(qisqartirildi)</i>"
    return text, kb_admin_pagination("admin_new24", page, total_pages)


def _build_active_users_24h_page(page: int = 1) -> tuple[str, InlineKeyboardMarkup]:
    """Build dynamic paginated text and keyboard for active 24h users."""
    import html
    total = get_active_users_24h_count()
    total_pages = max(1, (total + ADMIN_PAGE_SIZE - 1) // ADMIN_PAGE_SIZE)
    page = max(1, min(page, total_pages))
    offset = (page - 1) * ADMIN_PAGE_SIZE

    rows = get_active_users_24h(limit=ADMIN_PAGE_SIZE, offset=offset)
    lines = []
    for idx, row in enumerate(rows, start=offset + 1):
        r = dict(row)
        uname = f"@{html.escape(r['username'])}" if r.get("username") else f"<code>{r['user_id']}</code>"
        raw_name = (f"{r.get('first_name') or ''} {r.get('last_name') or ''}").strip() or "-"
        if len(raw_name) > 26:
            raw_name = raw_name[:25] + "…"
        name = html.escape(raw_name)
        updated_at = str(r.get("updated_at") or "")
        t_str = updated_at[11:16] if len(updated_at) >= 16 else ""
        uses = r.get("uses_count", 0)
        lines.append(f"{idx}. {uname} | {name} | <b>{uses} ta</b> | {t_str}")

    header = f"<b>⚡️ Aktiv 24 soat (Jami: {total:,} ta)</b> | Sahifa: <b>{page}/{total_pages}</b>\n\n"
    text = header + ("\n".join(lines) if lines else "Hozircha hech kim yo'q")
    if len(text) > 4000:
        text = text[:3950] + "\n\n<i>...(qisqartirildi)</i>"
    return text, kb_admin_pagination("admin_active24", page, total_pages)


@router.callback_query(F.data == "admin_noop")
async def cb_admin_noop(call: CallbackQuery):
    """Ignore clicks on page indicator button."""
    await call.answer()


@router.callback_query(F.data == "admin_new24")
async def cb_admin_new24(call: CallbackQuery, bot: Bot):
    """New users 24h (page 1)."""
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    text, kb = _build_new_users_24h_page(1)
    await bot.send_message(call.from_user.id, text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("admin_new24_p_"))
async def cb_admin_new24_page(call: CallbackQuery, bot: Bot):
    """Dynamic pagination for new 24h users."""
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    try:
        page = int(call.data.replace("admin_new24_p_", ""))
    except ValueError:
        page = 1
    text, kb = _build_new_users_24h_page(page)
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await call.answer()
    except Exception:
        await call.answer("✅ Yangilandi")


@router.callback_query(F.data == "admin_active24")
async def cb_admin_active24(call: CallbackQuery, bot: Bot):
    """Active users in the last 24 hours (page 1)."""
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    text, kb = _build_active_users_24h_page(1)
    await bot.send_message(call.from_user.id, text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("admin_active24_p_"))
async def cb_admin_active24_page(call: CallbackQuery, bot: Bot):
    """Dynamic pagination for active 24h users."""
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    try:
        page = int(call.data.replace("admin_active24_p_", ""))
    except ValueError:
        page = 1
    text, kb = _build_active_users_24h_page(page)
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await call.answer()
    except Exception:
        await call.answer("✅ Yangilandi")


@router.message(Command("active24h"))
async def cmd_admin_active24(message: Message, bot: Bot):
    """Active users in the last 24 hours (command)."""
    if not _is_admin(message.from_user.id):
        return
    text, kb = _build_active_users_24h_page(1)
    await bot.send_message(message.from_user.id, text, parse_mode="HTML", reply_markup=kb)


def _build_vip_users_page(page: int = 1) -> tuple[str, InlineKeyboardMarkup]:
    """Build dynamic paginated list of active VIP subscribers."""
    import html
    total = get_vip_users_count()
    total_pages = max(1, (total + ADMIN_PAGE_SIZE - 1) // ADMIN_PAGE_SIZE)
    page = max(1, min(page, total_pages))
    offset = (page - 1) * ADMIN_PAGE_SIZE

    rows = get_vip_users(limit=ADMIN_PAGE_SIZE, offset=offset)
    lines = []
    for idx, row in enumerate(rows, start=offset + 1):
        r = dict(row)
        uname = f"@{html.escape(r['username'])}" if r.get("username") else f"<code>{r['user_id']}</code>"
        raw_name = (f"{r.get('first_name') or ''} {r.get('last_name') or ''}").strip() or "-"
        if len(raw_name) > 24:
            raw_name = raw_name[:23] + "…"
        name = html.escape(raw_name)
        vip_until = r.get("vip_until") or "-"
        days_left = max(0, int(r.get("days_left") or 0))
        uses = r.get("uses_count", 0)
        lines.append(
            f"{idx}. {uname} | {name}\n"
            f"   💎 <b>{vip_until}</b> gacha ({days_left} kun qoldi) | 📊 {uses} ta"
        )

    header = f"<b>💎 Faol VIP Obunachilar (Jami: {total:,} ta)</b> | Sahifa: <b>{page}/{total_pages}</b>\n\n"
    text = header + ("\n".join(lines) if lines else "Hozircha faol VIP obunachilar yo'q.")
    if len(text) > 4000:
        text = text[:3950] + "\n\n<i>...(qisqartirildi)</i>"
    return text, kb_admin_pagination("admin_vip_users", page, total_pages)


@router.callback_query(F.data == "admin_vip_users")
async def cb_admin_vip_users(call: CallbackQuery, bot: Bot):
    """Active VIP subscribers (page 1)."""
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    text, kb = _build_vip_users_page(1)
    await bot.send_message(call.from_user.id, text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("admin_vip_users_p_"))
async def cb_admin_vip_users_page(call: CallbackQuery, bot: Bot):
    """Dynamic pagination for active VIP subscribers."""
    if not _is_admin(call.from_user.id):
        await call.answer()
        return
    try:
        page = int(call.data.replace("admin_vip_users_p_", ""))
    except ValueError:
        page = 1
    text, kb = _build_vip_users_page(page)
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await call.answer()
    except Exception:
        await call.answer("✅ Yangilandi")


def export_users_to_excel() -> bytes:
    """Generate Excel (.xlsx) file with all users."""
    import io
    import xlsxwriter
    from bot.database import db_connect

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Foydalanuvchilar")

    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#2C3E50',
        'font_color': '#FFFFFF',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    row_format = workbook.add_format({
        'border': 1,
        'align': 'left',
        'valign': 'vcenter'
    })
    num_format = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })

    headers = ["№", "Telegram ID", "Username", "Ism", "Familiya", "Jami Ishlatgan", "Balans", "Qo'shilgan Sana", "Oxirgi Faollik"]
    for col_num, header in enumerate(headers):
        worksheet.write(0, col_num, header, header_format)

    with db_connect() as con:
        rows = con.execute("""
            SELECT user_id, COALESCE(username,'') as username,
                   COALESCE(first_name,'') as first_name,
                   COALESCE(last_name,'') as last_name,
                   COALESCE(uses_count, 0) as uses_count,
                   COALESCE(balance, 0) as balance,
                   COALESCE(created_at, '') as created_at,
                   COALESCE(updated_at, '') as updated_at
            FROM users
            ORDER BY uses_count DESC, created_at DESC
        """).fetchall()

        for row_idx, r in enumerate(rows, start=1):
            worksheet.write(row_idx, 0, row_idx, num_format)
            worksheet.write(row_idx, 1, r["user_id"], num_format)
            worksheet.write(row_idx, 2, f"@{r['username']}" if r["username"] else "-", row_format)
            worksheet.write(row_idx, 3, r["first_name"] or "-", row_format)
            worksheet.write(row_idx, 4, r["last_name"] or "-", row_format)
            worksheet.write(row_idx, 5, r["uses_count"], num_format)
            worksheet.write(row_idx, 6, r["balance"], num_format)
            worksheet.write(row_idx, 7, str(r["created_at"])[:16], num_format)
            worksheet.write(row_idx, 8, str(r["updated_at"])[:16], num_format)

    worksheet.set_column(0, 0, 6)
    worksheet.set_column(1, 1, 14)
    worksheet.set_column(2, 2, 18)
    worksheet.set_column(3, 4, 18)
    worksheet.set_column(5, 6, 14)
    worksheet.set_column(7, 8, 18)

    workbook.close()
    return output.getvalue()


@router.message(Command("backup"))
@router.callback_query(F.data == "admin_backup")
async def cb_admin_backup(event: Message | CallbackQuery, bot: Bot):
    """Send Excel (.xlsx) report and database backup to admin."""
    user_id = event.from_user.id
    if isinstance(event, CallbackQuery):
        await event.answer()
    if not _is_admin(user_id):
        return

    import os
    date_str = datetime.now().strftime('%Y%m%d_%H%M%S')

    # 1. Send Excel (.xlsx) user table
    try:
        excel_bytes = export_users_to_excel()
        excel_file = BufferedInputFile(excel_bytes, filename=f"foydalanuvchilar_{date_str}.xlsx")
        await bot.send_document(
            user_id, excel_file,
            caption="📊 <b>Foydalanuvchilar Ro'yxati (Excel .xlsx)</b>\n\nUshbu faylni telefon yoki kompyuterda Excel/WPS orqali ochib, barcha obunachilaringiz ma'lumotlarini qulay ko'rishingiz mumkin.",
            parse_mode="HTML"
        )
    except Exception as exc:
        logger.error(f"Error generating Excel user export: {exc}")

    # 2. Send Raw SQLite DB
    if os.path.exists(DB_PATH):
        doc = FSInputFile(DB_PATH, filename=f"bot_backup_{date_str}.db")
        await bot.send_document(
            user_id, doc,
            caption="💾 <b>Texnik Server Bazasi (bot.db)</b>\n\nServerni kelajakda qayta tiklash uchun texnik zaxira fayli.",
            parse_mode="HTML",
            reply_markup=kb_admin_back()
        )
    else:
        await bot.send_message(user_id, "❌ Baza fayli topilmadi.", reply_markup=kb_admin_back())


@router.callback_query(F.data == "admin_bc_history")
async def cb_admin_bc_history(call: CallbackQuery, bot: Bot):
    """Broadcast history."""
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    rows = get_broadcast_history(10)
    if not rows:
        await bot.send_message(call.from_user.id, "📜 Broadcast tarixida hech narsa yo'q.",
                               reply_markup=kb_admin_back())
        return
    lines = []
    for r in rows:
        media = {"photo": "📸", "video": "🎥", "text": "📝", "document": "📄"}.get(r["media_type"], "?")
        date = r["created_at"][:16] if r["created_at"] else "?"
        lines.append(
            f"{media} #{r['id']} | {date}\n"
            f"   ✅ {r['success']}/{r['total']} | ❌ {r['failed']}"
        )
    text = "<b>📜 Broadcast tarixi:</b>\n\n" + "\n\n".join(lines)
    await bot.send_message(call.from_user.id, text, parse_mode="HTML",
                           reply_markup=kb_admin_back())


@router.callback_query(F.data == "admin_search")
async def cb_admin_search(call: CallbackQuery, bot: Bot):
    """Start user search."""
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    set_state(call.from_user.id, STATE_WAIT_SEARCH)
    await bot.send_message(call.from_user.id,
                           "🔍 Username, ism yoki user_id yuboring:",
                           reply_markup=kb_admin_back())


@router.callback_query(F.data == "admin_add_balance")
async def cb_admin_add_balance(call: CallbackQuery, bot: Bot):
    """Start admin add balance flow."""
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    set_state(call.from_user.id, STATE_WAIT_ADMIN_BALANCE_INPUT)
    await bot.send_message(
        call.from_user.id,
        "<b>💳 Foydalanuvchiga Kredit Qo'shish</b>\n\n"
        "Foydalanuvchi <b>Username</b> (masalan <code>otabyvaa1</code>) yoki <b>User ID</b> va <b>kredit soni</b>ni yuboring:\n\n"
        "<i>Misollar:</i>\n"
        "• <code>otabyvaa1 5</code>\n"
        "• <code>8247903602 10</code>",
        parse_mode="HTML",
        reply_markup=kb_admin_back()
    )


@router.message(lambda msg: msg.text and not msg.text.startswith("/") and get_state(msg.from_user.id) == STATE_WAIT_ADMIN_BALANCE_INPUT and _is_admin(msg.from_user.id))
async def handle_admin_balance_input(message: Message, bot: Bot):
    """Process admin balance input."""
    set_state(message.from_user.id, STATE_NONE)
    args = message.text.strip().split()
    if len(args) < 2 or not args[-1].lstrip("-").isdigit():
        await message.answer(
            "⚠️ <b>Noto'g'ri shakl!</b>\n\n"
            "Username/ID va kredit sonini ajratib yozing.\n"
            "<i>Masalan: <code>otabyvaa1 5</code> yoki <code>8247903602 10</code></i>",
            parse_mode="HTML",
            reply_markup=kb_admin_back()
        )
        return

    target_query = " ".join(args[:-1])
    amount = int(args[-1])

    from bot.database import resolve_user_id, add_user_balance, get_user_balance
    user_info = resolve_user_id(target_query)
    if not user_info:
        await message.answer(
            f"❌ Foydalanuvchi topilmadi: <b>{target_query}</b>\n"
            "<i>Foydalanuvchi botga kamida bir marta /start bosgan bo'lishi kerak.</i>",
            parse_mode="HTML",
            reply_markup=kb_admin_back()
        )
        return

    target_user_id = user_info["user_id"]
    username_str = f"@{user_info['username']}" if user_info.get("username") else f"ID: {target_user_id}"

    add_user_balance(target_user_id, amount)
    new_bal = get_user_balance(target_user_id)

    await message.answer(
        f"✅ <b>Balans muvaffaqiyatli to'ldirildi!</b>\n\n"
        f"👤 Foydalanuvchi: <b>{username_str}</b> (<code>{target_user_id}</code>)\n"
        f"➕ Qo'shildi: <b>+{amount} kredit</b>\n"
        f"💰 Yangi balans: <b>{new_bal} kredit</b>",
        parse_mode="HTML",
        reply_markup=kb_user_balance_actions(target_user_id)
    )

    # Foydalanuvchiga bildirishnoma yuborish
    try:
        from bot.i18n import t
        from bot.database import get_user_language
        u_lang = get_user_language(target_user_id) or "uz"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_ai_video", u_lang), callback_data="act_ai_video")]
        ])
        await bot.send_message(
            target_user_id,
            f"🎉 <b>Balansingiz to'ldirildi!</b>\n\n"
            f"➕ Qo'shildi: <b>+{amount} kredit</b>\n"
            f"📊 Umumiy balans: <b>{new_bal} kredit</b>\n\n"
            f"Video yaratish uchun pastdagi tugmani bosing 👇",
            parse_mode="HTML",
            reply_markup=kb
        )
    except Exception as e:
        logger.warning(f"Could not notify user {target_user_id}: {e}")


@router.callback_query(F.data.startswith("adm_addbal_"))
async def cb_admin_quick_add_balance(call: CallbackQuery, bot: Bot):
    """Handle quick balance add buttons from admin interface."""
    await call.answer()
    if not _is_admin(call.from_user.id):
        return

    parts = call.data.split("_")
    if len(parts) < 4:
        return

    target_user_id = int(parts[2])
    amount = int(parts[3])

    from bot.database import add_user_balance, get_user_balance, resolve_user_id
    add_user_balance(target_user_id, amount)
    new_bal = get_user_balance(target_user_id)

    user_info = resolve_user_id(str(target_user_id))
    username_str = f"@{user_info['username']}" if user_info and user_info.get("username") else f"ID: {target_user_id}"

    await bot.send_message(
        call.from_user.id,
        f"✅ <b>{username_str}</b> (<code>{target_user_id}</code>) balansiga <b>+{amount} kredit</b> qo'shildi!\n"
        f"💰 Yangi balans: <b>{new_bal} kredit</b>",
        parse_mode="HTML",
        reply_markup=kb_user_balance_actions(target_user_id)
    )

    try:
        from bot.i18n import t
        from bot.database import get_user_language
        u_lang = get_user_language(target_user_id) or "uz"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_ai_video", u_lang), callback_data="act_ai_video")]
        ])
        await bot.send_message(
            target_user_id,
            f"🎉 <b>Balansingiz to'ldirildi!</b>\n\n"
            f"➕ Qo'shildi: <b>+{amount} kredit</b>\n"
            f"📊 Umumiy balans: <b>{new_bal} kredit</b>\n\n"
            f"Video yaratish uchun pastdagi tugmani bosing 👇",
            parse_mode="HTML",
            reply_markup=kb
        )
    except Exception as e:
        logger.warning(f"Could not notify user {target_user_id}: {e}")


@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(call: CallbackQuery, bot: Bot):
    """Start broadcast from admin panel."""
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    if BROADCAST_RUNNING.get(call.from_user.id):
        await bot.send_message(call.from_user.id, "⚠️ Hozir broadcast davom etmoqda.")
        return
    PENDING_BROADCAST.pop(call.from_user.id, None)
    set_state(call.from_user.id, STATE_WAIT_BROADCAST)
    await bot.send_message(
        call.from_user.id,
        "<b>📢 Broadcast rejimi</b>\n\n"
        "Rasm (tagiga matn bilan yoki matnsiz), video, fayl yoki oddiy matn yuboring.\n\n"
        "<b>💡 Qulayliklar:</b>\n"
        "• Rasm + matnni bitta xabarda yuborishingiz <b>YOKI</b> avval rasm yuborib, keyin tagiga matn qo'shishingiz mumkin.\n"
        "• Inline tugma qo'shish: <code>[Matn|https://link.com]</code>",
        parse_mode="HTML",
        reply_markup=kb_cancel()
    )


# ========================
# SEARCH HANDLER
# ========================

@router.message(lambda msg: msg.text and not msg.text.startswith("/") and get_state(msg.from_user.id) == STATE_WAIT_SEARCH and msg.from_user.id in ADMIN_IDS)
async def handle_search(message: Message, bot: Bot):
    """Process user search query."""
    query = message.text.strip().lstrip("@")
    await _do_search(message.from_user.id, query, bot)


async def _do_search(admin_id: int, query: str, bot: Bot):
    """Execute user search and show full CRM card for single result or quick-open buttons for multiple."""
    import html as _html
    from bot.handlers.admin_pro import render_user_crm_card

    set_state(admin_id, STATE_NONE)
    rows = search_user(query)
    if not rows:
        await bot.send_message(
            admin_id, f"🔍 '<b>{_html.escape(query)}</b>' bo'yicha topilmadi.",
            parse_mode="HTML", reply_markup=kb_admin_back()
        )
        return

    if len(rows) == 1:
        uid = dict(rows[0])["user_id"]
        text, kb = render_user_crm_card(uid)
        await bot.send_message(admin_id, text, parse_mode="HTML", reply_markup=kb)
        return

    lines = []
    buttons = []
    for r in rows[:10]:
        d = dict(r)
        uid = d["user_id"]
        uname = f"@{_html.escape(d['username'])}" if d.get("username") else "-"
        name = _html.escape(f"{d.get('first_name') or ''} {d.get('last_name') or ''}".strip() or "-")
        uses = d.get("uses_count", 0)
        lines.append(f"👤 <b>{name}</b> ({uname}) | <code>{uid}</code> | {uses} ta")
        if len(buttons) < 6:
            lbl = f"👤 Ochish: {d.get('username') or name[:18]} ({uid})"
            buttons.append([InlineKeyboardButton(text=lbl, callback_data=f"crm_open_{uid}")])

    buttons.append([InlineKeyboardButton(text="⬅️ Admin panel", callback_data="admin_back")])
    text = f"🔍 <b>Qidiruv natijalari ({len(rows)} ta):</b>\n\n" + "\n".join(lines)
    await bot.send_message(admin_id, text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("crm_open_"))
async def cb_crm_open_user(call: CallbackQuery, bot: Bot):
    """Open full CRM card for a user from search results."""
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    from bot.handlers.admin_pro import render_user_crm_card
    uid = int(call.data.replace("crm_open_", ""))
    text, kb = render_user_crm_card(uid)
    await bot.send_message(call.from_user.id, text, parse_mode="HTML", reply_markup=kb)


# ========================
# BROADCAST CONTENT HANDLERS
# ========================

def _extract_raw_or_html_text(message: Message) -> str:
    """
    Preserve Telegram rich-text formatting (bold, italic, links) if message has entities,
    otherwise keep raw text so manual HTML tags like <b>...</b> also work.
    """
    is_media = bool(message.photo or message.video or message.document or message.animation)
    entities = message.caption_entities if is_media else message.entities
    raw_text = (message.caption if is_media else message.text) or ""
    if entities:
        try:
            return message.html_text or raw_text
        except Exception:
            return raw_text
    return raw_text


SEGMENT_LABELS = {
    "live": "👥 Barcha tiriklar",
    "free": "🆓 Faqat Oddiy (VIP emas)",
    "vip": "💎 Faqat VIP",
    "lang_uz": "🇺🇿 O'zbek tili",
    "lang_ru": "🇷🇺 Rus tili",
    "active_7d": "🔥 Aktiv 7 kun",
}


def _build_broadcast_data(message: Message) -> dict:
    """Build broadcast data from any message type, capturing source IDs for optional Forward mode."""
    raw_caption = _extract_raw_or_html_text(message)
    clean_caption, keyboard = _parse_inline_buttons(raw_caption)

    is_forwarded = bool(getattr(message, "forward_origin", None) or getattr(message, "forward_date", None))
    data = {
        "caption": clean_caption,
        "keyboard": keyboard,
        "media_type": "text",
        "file_id": None,
        "parse_mode": "HTML",
        "segment": "live",
        "forward_mode": False,
        "src_chat_id": message.chat.id,
        "src_msg_id": message.message_id,
        "is_forwarded": is_forwarded,
    }

    if message.photo:
        data["media_type"] = "photo"
        data["file_id"] = message.photo[-1].file_id
    elif message.video:
        data["media_type"] = "video"
        data["file_id"] = message.video.file_id
    elif message.document:
        data["media_type"] = "document"
        data["file_id"] = message.document.file_id
    elif message.animation:
        data["media_type"] = "animation"
        data["file_id"] = message.animation.file_id

    return data


async def _send_broadcast_item(bot: Bot, chat_id: int, data: dict):
    """Send a single broadcast item (Copy/Normal or Forward) with automatic plain-text fallback."""
    if data.get("forward_mode") and data.get("src_chat_id") and data.get("src_msg_id"):
        await bot.forward_message(chat_id=chat_id, from_chat_id=data["src_chat_id"], message_id=data["src_msg_id"])
        return

    media_type = data["media_type"]
    file_id = data.get("file_id")
    caption = data.get("caption") or ""
    keyboard = data.get("keyboard")
    parse_mode = data.get("parse_mode", "HTML")

    async def _attempt(pm):
        if media_type == "photo":
            await bot.send_photo(chat_id, file_id, caption=caption or None, parse_mode=pm, reply_markup=keyboard)
        elif media_type == "video":
            await bot.send_video(chat_id, file_id, caption=caption or None, parse_mode=pm, reply_markup=keyboard)
        elif media_type == "document":
            await bot.send_document(chat_id, file_id, caption=caption or None, parse_mode=pm, reply_markup=keyboard)
        elif media_type == "animation":
            await bot.send_animation(chat_id, file_id, caption=caption or None, parse_mode=pm, reply_markup=keyboard)
        else:
            await bot.send_message(chat_id, caption, parse_mode=pm, reply_markup=keyboard)

    try:
        await _attempt(parse_mode)
    except Exception as e:
        err_str = str(e).lower()
        if parse_mode and ("can't parse entities" in err_str or "parse" in err_str):
            data["parse_mode"] = None
            await _attempt(None)
        else:
            raise


def _build_broadcast_control_text(data: dict) -> str:
    """Build control summary text showing selected segment, live recipient count, and mode."""
    is_media = data["media_type"] != "text"
    caption = data.get("caption") or ""
    segment = data.get("segment", "live")
    user_count = count_segmented_users(segment)
    seg_label = SEGMENT_LABELS.get(segment, "👥 Barcha tiriklar")
    mode_str = "↪️ Forward (asl post ko'rinishida)" if data.get("forward_mode") else "📋 Oddiy yuborish"

    media_labels = {
        "photo": "📸 Rasm + matn" if caption else "📸 Rasm (matnsiz)",
        "video": "🎥 Video + matn" if caption else "🎥 Video (matnsiz)",
        "document": "📄 Fayl + matn" if caption else "📄 Fayl (matnsiz)",
        "animation": "🎞 GIF + matn" if caption else "🎞 GIF (matnsiz)",
        "text": "📝 Matn xabari",
    }
    info_text = (
        f"👁 <b>Yuqoridagi xabar — haqiqiy ko'rinish (Preview)!</b>\n\n"
        f"📦 Turi: <b>{media_labels.get(data['media_type'], '📝 Matn')}</b>\n"
        f"📨 Rejim: <b>{mode_str}</b>\n"
        f"🎯 Segment: <b>{seg_label}</b>\n"
        f"👥 Yuboriladi: <b>{user_count:,}</b> tirik foydalanuvchiga\n"
    )
    if data.get("keyboard") and not data.get("forward_mode"):
        btn_count = sum(len(row) for row in data["keyboard"].inline_keyboard)
        info_text += f"🔗 Tugmalar: <b>{btn_count} ta</b>\n"
    if is_media and not caption and not data.get("forward_mode"):
        info_text += "\n💡 <i>Rasm tagiga matn qo'shmoqchi bo'lsangiz, matnni hoziroq yozib yuboring yoki pastdagi tugmani bosing!</i>\n"
    info_text += "\n👇 <b>Segmentni tanlang yoki yuborishni bosing:</b>"
    return info_text


async def _show_broadcast_preview(bot: Bot, user_id: int, data: dict):
    """Send exact real preview of the broadcast (media + caption + buttons) followed by segmented controls."""
    is_media = data["media_type"] != "text"
    caption = data.get("caption") or ""

    if is_media and len(caption) > 1024 and not data.get("forward_mode"):
        await bot.send_message(
            user_id,
            f"⚠️ <b>Rasm/video tagidagi matn juda uzun ({len(caption)} belgi)!</b>\n\n"
            f"Telegram media tagiga maksimal <b>1024 belgi</b> ruxsat beradi.\n"
            f"Iltimos, matnni qisqartirib qayta yuboring.",
            parse_mode="HTML",
            reply_markup=_preview_keyboard(data),
        )
        return

    try:
        await _send_broadcast_item(bot, user_id, data)
    except Exception as e:
        logger.error(f"Broadcast preview error for {user_id}: {e}")
        await bot.send_message(
            user_id,
            f"❌ Preview ko'rsatishda xatolik: <code>{e}</code>\nQayta urinib ko'ring.",
            parse_mode="HTML",
            reply_markup=kb_cancel(),
        )
        return

    await bot.send_message(
        user_id,
        _build_broadcast_control_text(data),
        parse_mode="HTML",
        reply_markup=_preview_keyboard(data),
    )


def _preview_keyboard(data: dict = None) -> InlineKeyboardMarkup:
    """Broadcast preview keyboard with audience segment selector, forward toggle, and send options."""
    data = data or {}
    is_media = data.get("media_type", "text") != "text"
    seg = data.get("segment", "live")
    fwd = bool(data.get("forward_mode", False))

    def _sbtn(key: str, short_label: str) -> InlineKeyboardButton:
        prefix = "✅ " if seg == key else ""
        return InlineKeyboardButton(text=f"{prefix}{short_label}", callback_data=f"bc_seg_{key}")

    fwd_label = "↪️ Forward rejimi: 🟢 YOQIQ" if fwd else "↪️ Forward rejimi: ⚪️ O'CHIQ"
    rows = [
        [_sbtn("live", "👥 Tiriklar"), _sbtn("free", "🆓 Oddiylar"), _sbtn("vip", "💎 VIP")],
        [_sbtn("lang_uz", "🇺🇿 UZ"), _sbtn("lang_ru", "🇷🇺 RU"), _sbtn("active_7d", "🔥 7 kun")],
        [InlineKeyboardButton(text=fwd_label, callback_data="bc_toggle_fwd")],
        [InlineKeyboardButton(text="📤 Hozir yuborish", callback_data="broadcast_now")],
    ]
    if is_media and not fwd:
        rows.append([InlineKeyboardButton(text="✏️ Matn (caption) qo'shish / tahrirlash", callback_data="broadcast_edit_caption")])
    rows.append([
        InlineKeyboardButton(text="⏰ Rejalash", callback_data="broadcast_schedule"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(lambda msg: (msg.photo or msg.video or msg.document or msg.animation) and get_state(msg.from_user.id) in (STATE_WAIT_BROADCAST, STATE_WAIT_BROADCAST_CAPTION) and msg.from_user.id in ADMIN_IDS)
async def broadcast_media(message: Message, bot: Bot):
    """Receive media (photo/video/document/gif) for broadcast, preserving existing text caption if sent without one."""
    user_id = message.from_user.id
    data = _build_broadcast_data(message)

    # If admin sent text first and then sent a photo without caption, combine them!
    existing = PENDING_BROADCAST.get(user_id)
    if existing and existing.get("media_type") == "text" and not data["caption"] and existing.get("caption"):
        data["caption"] = existing["caption"]
        data["keyboard"] = existing.get("keyboard")
        data["parse_mode"] = existing.get("parse_mode", "HTML")

    PENDING_BROADCAST[user_id] = data
    set_state(user_id, STATE_WAIT_BROADCAST)
    await _show_broadcast_preview(bot, user_id, data)


@router.message(lambda msg: msg.text and not msg.text.startswith("/") and get_state(msg.from_user.id) == STATE_WAIT_BROADCAST_CAPTION and msg.from_user.id in ADMIN_IDS)
async def broadcast_set_caption(message: Message, bot: Bot):
    """Attach or update caption text on an existing media broadcast."""
    user_id = message.from_user.id
    data = PENDING_BROADCAST.get(user_id)
    if not data:
        data = _build_broadcast_data(message)
    else:
        raw_text = _extract_raw_or_html_text(message)
        clean_caption, keyboard = _parse_inline_buttons(raw_text)
        data["caption"] = clean_caption
        data["keyboard"] = keyboard
        data["parse_mode"] = "HTML"

    PENDING_BROADCAST[user_id] = data
    set_state(user_id, STATE_WAIT_BROADCAST)
    await _show_broadcast_preview(bot, user_id, data)


@router.message(lambda msg: msg.text and not msg.text.startswith("/") and get_state(msg.from_user.id) == STATE_WAIT_BROADCAST and msg.from_user.id in ADMIN_IDS)
async def broadcast_text(message: Message, bot: Bot):
    """Receive text for broadcast (or auto-attach as caption if media was just uploaded without caption)."""
    user_id = message.from_user.id
    existing = PENDING_BROADCAST.get(user_id)

    # If admin just uploaded a photo/video without caption and now sends text, attach it under the media!
    if existing and existing.get("media_type") != "text" and not existing.get("caption"):
        raw_text = _extract_raw_or_html_text(message)
        clean_caption, keyboard = _parse_inline_buttons(raw_text)
        existing["caption"] = clean_caption
        existing["keyboard"] = keyboard
        existing["parse_mode"] = "HTML"
        PENDING_BROADCAST[user_id] = existing
        await _show_broadcast_preview(bot, user_id, existing)
        return

    data = _build_broadcast_data(message)
    PENDING_BROADCAST[user_id] = data
    await _show_broadcast_preview(bot, user_id, data)


# ========================
# BROADCAST CALLBACKS
# ========================

@router.callback_query(F.data.startswith("bc_seg_"))
async def cb_broadcast_select_segment(call: CallbackQuery, bot: Bot):
    """Switch target audience segment on broadcast preview."""
    admin_id = call.from_user.id
    if not _is_admin(admin_id):
        await call.answer()
        return
    data = PENDING_BROADCAST.get(admin_id)
    if not data:
        await call.answer("⚠️ Broadcast topilmadi.", show_alert=True)
        return
    seg = call.data.replace("bc_seg_", "")
    if seg not in SEGMENT_LABELS:
        seg = "live"
    data["segment"] = seg
    PENDING_BROADCAST[admin_id] = data
    try:
        await call.message.edit_text(
            _build_broadcast_control_text(data),
            parse_mode="HTML",
            reply_markup=_preview_keyboard(data),
        )
    except Exception:
        pass
    await call.answer(f"🎯 {SEGMENT_LABELS[seg]}")


@router.callback_query(F.data == "bc_toggle_fwd")
async def cb_broadcast_toggle_forward(call: CallbackQuery, bot: Bot):
    """Toggle Forward mode (forwards original message with channel attribution)."""
    admin_id = call.from_user.id
    if not _is_admin(admin_id):
        await call.answer()
        return
    data = PENDING_BROADCAST.get(admin_id)
    if not data:
        await call.answer("⚠️ Broadcast topilmadi.", show_alert=True)
        return
    data["forward_mode"] = not bool(data.get("forward_mode"))
    PENDING_BROADCAST[admin_id] = data
    try:
        await call.message.edit_text(
            _build_broadcast_control_text(data),
            parse_mode="HTML",
            reply_markup=_preview_keyboard(data),
        )
    except Exception:
        pass
    await call.answer("↪️ Forward rejimi YOQILDI" if data["forward_mode"] else "📋 Oddiy rejim tanlandi")


@router.callback_query(F.data == "broadcast_stop")
async def cb_broadcast_stop(call: CallbackQuery):
    """Stop an active running broadcast safely after current batch."""
    admin_id = call.from_user.id
    if not _is_admin(admin_id):
        await call.answer()
        return
    BROADCAST_CANCEL[admin_id] = True
    await call.answer("⏹ Broadcast to'xtatilmoqda...", show_alert=True)


@router.callback_query(F.data == "broadcast_edit_caption")
async def cb_broadcast_edit_caption(call: CallbackQuery, bot: Bot):
    """Prompt admin to send caption text for the uploaded media broadcast."""
    await call.answer()
    admin_id = call.from_user.id
    if not _is_admin(admin_id):
        return
    if admin_id not in PENDING_BROADCAST:
        await call.message.answer("⚠️ Avval rasm yoki matn yuboring.")
        return
    set_state(admin_id, STATE_WAIT_BROADCAST_CAPTION)
    await bot.send_message(
        admin_id,
        "✍️ <b>Rasm/video tagiga qo'yiladigan matnni yuboring:</b>\n\n"
        "<i>(Maksimal 1024 belgi. Tugma qo'shish uchun: <code>[Matn|https://link.com]</code>)</i>",
        parse_mode="HTML",
        reply_markup=kb_cancel(),
    )


def _broadcast_stop_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏹ To'xtatish (STOP)", callback_data="broadcast_stop")]
    ])


@router.callback_query(F.data == "broadcast_now")
async def cb_broadcast_now(call: CallbackQuery, bot: Bot):
    """Send broadcast immediately to the chosen audience segment."""
    await call.answer()
    admin_id = call.from_user.id
    if not _is_admin(admin_id):
        return
    data = PENDING_BROADCAST.pop(admin_id, None)
    if not data:
        await call.message.answer("⚠️ Broadcast topilmadi.")
        return
    BROADCAST_RUNNING[admin_id] = True
    BROADCAST_CANCEL[admin_id] = False
    set_state(admin_id, STATE_NONE)
    seg = data.get("segment", "live")
    user_count = count_segmented_users(seg)
    status_msg = await bot.send_message(
        admin_id,
        f"📡 Broadcast boshlandi...\n🎯 {SEGMENT_LABELS.get(seg, 'Tiriklar')} ({user_count:,} foydalanuvchi)",
        reply_markup=_broadcast_stop_kb(),
    )
    asyncio.create_task(_do_broadcast(bot, admin_id, data, status_msg.message_id))
    try:
        await call.message.delete()
    except Exception:
        pass


@router.callback_query(F.data == "broadcast_schedule")
async def cb_broadcast_schedule(call: CallbackQuery, bot: Bot):
    """Schedule broadcast — ask for time."""
    await call.answer()
    admin_id = call.from_user.id
    if not _is_admin(admin_id):
        return
    set_state(admin_id, STATE_WAIT_SCHEDULE_TIME)
    await bot.send_message(
        admin_id,
        "<b>⏰ Qachon yuborish?</b>\n\n"
        "Vaqtni yozing (24-soat formati):\n"
        "• <code>20:00</code> — bugun 20:00 da\n"
        "• <code>+30</code> — 30 daqiqadan keyin\n"
        "• <code>+2h</code> — 2 soatdan keyin",
        parse_mode="HTML",
        reply_markup=kb_cancel()
    )


@router.callback_query(F.data == "broadcast_cancel")
async def cb_broadcast_cancel(call: CallbackQuery, bot: Bot):
    """Cancel broadcast."""
    await call.answer()
    PENDING_BROADCAST.pop(call.from_user.id, None)
    set_state(call.from_user.id, STATE_NONE)
    try:
        await call.message.delete()
    except Exception:
        pass
    await bot.send_message(call.from_user.id, "❌ Bekor qilindi.", reply_markup=kb_admin_back())


# Keep old callback for compatibility
@router.callback_query(F.data == "broadcast_confirm")
async def cb_broadcast_confirm(call: CallbackQuery, bot: Bot):
    """Legacy confirm — redirect to broadcast_now."""
    await cb_broadcast_now(call, bot)


# ========================
# SCHEDULED BROADCAST
# ========================

@router.message(lambda msg: msg.text and not msg.text.startswith("/") and get_state(msg.from_user.id) == STATE_WAIT_SCHEDULE_TIME and msg.from_user.id in ADMIN_IDS)
async def handle_schedule_time(message: Message, bot: Bot):
    """Parse schedule time and set up delayed broadcast."""
    admin_id = message.from_user.id
    time_str = message.text.strip()
    data = PENDING_BROADCAST.get(admin_id)
    if not data:
        await message.answer("⚠️ Broadcast topilmadi. /broadcast yuboring.")
        set_state(admin_id, STATE_NONE)
        return

    now = datetime.now()
    send_at = None

    if time_str.startswith("+"):
        val = time_str[1:]
        if val.endswith("h"):
            hours = int(val[:-1])
            send_at = now + timedelta(hours=hours)
        elif val.isdigit():
            minutes = int(val)
            send_at = now + timedelta(minutes=minutes)

    elif re.match(r'^\d{1,2}:\d{2}$', time_str):
        h, m = map(int, time_str.split(':'))
        send_at = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if send_at <= now:
            send_at += timedelta(days=1)

    if not send_at:
        await message.answer(
            "❌ Noto'g'ri format.\n"
            "Misol: <code>20:00</code>, <code>+30</code>, <code>+2h</code>",
            parse_mode="HTML"
        )
        return

    delay_seconds = (send_at - now).total_seconds()
    set_state(admin_id, STATE_NONE)
    PENDING_BROADCAST.pop(admin_id, None)

    task = asyncio.create_task(_scheduled_broadcast(bot, admin_id, data, delay_seconds))
    SCHEDULED_TASKS[admin_id] = task

    formatted_time = send_at.strftime("%H:%M")
    await message.answer(
        f"✅ <b>Broadcast rejalashtirildi!</b>\n\n"
        f"⏰ Yuborish vaqti: <b>{formatted_time}</b>\n"
        f"⏳ Qolgan vaqt: {int(delay_seconds // 60)} daqiqa",
        parse_mode="HTML",
        reply_markup=kb_admin_back()
    )


async def _scheduled_broadcast(bot: Bot, admin_id: int, data: dict, delay: float):
    """Wait and then execute broadcast."""
    await asyncio.sleep(delay)
    BROADCAST_RUNNING[admin_id] = True
    BROADCAST_CANCEL[admin_id] = False
    seg = data.get("segment", "live")
    user_count = count_segmented_users(seg)
    status_msg = await bot.send_message(
        admin_id,
        f"📡 Rejalashtirilgan broadcast boshlandi! ({user_count:,} foydalanuvchi)",
        reply_markup=_broadcast_stop_kb(),
    )
    await _do_broadcast(bot, admin_id, data, status_msg.message_id)
    SCHEDULED_TASKS.pop(admin_id, None)


# ========================
# BROADCAST ENGINE
# ========================

async def _do_broadcast(bot: Bot, admin_id: int, broadcast_data: dict, status_msg_id: int):
    """Execute segmented broadcast with STOP control, Forward support, and auto-marking blocked users."""
    from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError

    segment = broadcast_data.get("segment", "live")
    user_ids = get_segmented_user_ids(segment)
    total = len(user_ids)
    success = 0
    failed = 0
    newly_blocked = 0
    stopped = False

    media_type = "forward" if broadcast_data.get("forward_mode") else broadcast_data["media_type"]
    file_id = broadcast_data.get("file_id")
    caption = broadcast_data.get("caption", "")

    semaphore = asyncio.Semaphore(BROADCAST_RATE)

    async def send_one(uid: int):
        nonlocal success, failed, newly_blocked
        async with semaphore:
            if BROADCAST_CANCEL.get(admin_id):
                return
            try:
                await _send_broadcast_item(bot, uid, broadcast_data)
                success += 1
            except TelegramForbiddenError:
                failed += 1
                newly_blocked += 1
                mark_user_blocked(uid, 1)
            except TelegramRetryAfter as retry_err:
                await asyncio.sleep(retry_err.retry_after + 0.5)
                try:
                    await _send_broadcast_item(bot, uid, broadcast_data)
                    success += 1
                except TelegramForbiddenError:
                    failed += 1
                    newly_blocked += 1
                    mark_user_blocked(uid, 1)
                except Exception:
                    failed += 1
            except Exception as e:
                err_l = str(e).lower()
                if "blocked" in err_l or "deactivated" in err_l or "chat not found" in err_l:
                    newly_blocked += 1
                    mark_user_blocked(uid, 1)
                failed += 1
            await asyncio.sleep(1 / BROADCAST_RATE)

    batch_size = 50
    tasks = []
    for uid in user_ids:
        if BROADCAST_CANCEL.get(admin_id):
            stopped = True
            break
        tasks.append(send_one(uid))
        if len(tasks) >= batch_size:
            await asyncio.gather(*tasks)
            tasks = []
            if BROADCAST_CANCEL.get(admin_id):
                stopped = True
                break
            try:
                pct = round((success + failed) / max(total, 1) * 100)
                await bot.edit_message_text(
                    f"📡 Yuborilmoqda... {pct}%\n"
                    f"🎯 {SEGMENT_LABELS.get(segment, 'Tiriklar')}\n"
                    f"✅ {success} | ❌ {failed} (📵 blok: {newly_blocked}) | {success + failed}/{total}",
                    chat_id=admin_id,
                    message_id=status_msg_id,
                    reply_markup=_broadcast_stop_kb(),
                )
            except Exception:
                pass

    if tasks and not stopped:
        await asyncio.gather(*tasks)

    save_broadcast_result(admin_id, media_type, file_id or "", caption, total, success, failed)

    title_line = "⏹ <b>Broadcast to'xtatildi!</b>" if stopped else "✅ <b>Broadcast tugadi!</b>"
    try:
        await bot.edit_message_text(
            f"{title_line}\n\n"
            f"🎯 Segment: <b>{SEGMENT_LABELS.get(segment, 'Tiriklar')}</b>\n"
            f"👥 Jami maqsad: <b>{total:,}</b>\n"
            f"✅ Yuborildi: <b>{success:,}</b>\n"
            f"🚫 Xato: <b>{failed:,}</b> (📵 Yangi bloklagan: <b>{newly_blocked:,}</b>)\n"
            f"📊 Samaradorlik: <b>{round(success/max(success+failed,1)*100)}%</b>\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            chat_id=admin_id,
            message_id=status_msg_id,
            parse_mode="HTML",
            reply_markup=kb_admin_back(),
        )
    except Exception:
        await bot.send_message(admin_id, f"✅ Broadcast: {success}/{total}", reply_markup=kb_admin_back())

    BROADCAST_RUNNING.pop(admin_id, None)
    BROADCAST_CANCEL.pop(admin_id, None)
    logger.info(f"Broadcast by {admin_id} [seg={segment}, stopped={stopped}]: {success}/{total}, failed={failed}, blocked={newly_blocked}")


# =========================================================================
# Dynamic Channels Management Handlers
# =========================================================================

ADMIN_CHANNEL_TEMP: Dict[int, Dict[str, any]] = {}


@router.callback_query(F.data == "admin_channels")
async def cb_admin_channels(call: CallbackQuery, bot: Bot):
    """Show list of required channels and management options."""
    if not _is_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q", show_alert=True)
        return
    await call.answer()

    from bot.database import get_all_channels
    from bot.keyboards import kb_admin_channels

    channels = get_all_channels()
    text = (
        "📢 <b>Majburiy Obuna Kanallari Boshqaruvi</b>\n\n"
        "Bu bo'limda siz botga yangi majburiy kanallar qo'shishingiz, obunachi limitini belgilashingiz "
        "yoki istalgan payt kanalni o'chirishingiz mumkin.\n\n"
        f"📋 <b>Jami kanallar:</b> {len(channels)} ta\n"
        "<i>(🟢 - Faol, 🔴 - To'xtatilgan yoki limiti to'lgan)</i>"
    )
    await bot.send_message(call.from_user.id, text, parse_mode="HTML", reply_markup=kb_admin_channels(channels))


@router.callback_query(F.data == "admin_add_channel")
async def cb_admin_add_channel(call: CallbackQuery, bot: Bot):
    """Start wizard to add a new channel."""
    if not _is_admin(call.from_user.id):
        return
    await call.answer()

    set_state(call.from_user.id, STATE_WAIT_ADMIN_CHANNEL_ID)
    ADMIN_CHANNEL_TEMP[call.from_user.id] = {}

    await bot.send_message(
        call.from_user.id,
        "➕ <b>Yangi Majburiy Kanal Qo'shish:</b>\n\n"
        "1️⃣ Kanal username yoki havolasini yuboring:\n"
        "<i>Masalan: <code>@mening_kanalim</code> yoki <code>https://t.me/mening_kanalim</code></i>\n\n"
        "⚠️ <b>Eslatma:</b> Bot ushbu kanalda <b>Administrator</b> bo'lishi shart (foydalanuvchilar a'zoligini tekshirishi uchun)!",
        parse_mode="HTML",
        reply_markup=kb_cancel()
    )


@router.message(lambda msg: msg.text and not msg.text.startswith("/") and get_state(msg.from_user.id) == STATE_WAIT_ADMIN_CHANNEL_ID)
async def handle_admin_channel_id_input(message: Message, bot: Bot):
    """Handle channel username or link input from admin."""
    admin_id = message.from_user.id
    if not _is_admin(admin_id):
        return

    text = message.text.strip()
    channel_id = text
    invite_link = ""

    if "t.me/" in text:
        parts = text.split("t.me/")[-1].replace("/", "").strip()
        invite_link = text
        if not parts.startswith("+"):
            channel_id = f"@{parts}"
        else:
            channel_id = text
    elif text.startswith("@"):
        channel_id = text
        invite_link = f"https://t.me/{text.lstrip('@')}"
    elif text.startswith("-100"):
        channel_id = text
        invite_link = ""
    else:
        channel_id = f"@{text}"
        invite_link = f"https://t.me/{text}"

    channel_title = channel_id
    try:
        chat = await bot.get_chat(channel_id)
        if chat.title:
            channel_title = chat.title
        if chat.username:
            channel_id = f"@{chat.username}"
            invite_link = f"https://t.me/{chat.username}"
    except Exception as e:
        logger.warning(f"Could not fetch chat info for {channel_id}: {e}")

    ADMIN_CHANNEL_TEMP[admin_id] = {
        "channel_id": channel_id,
        "channel_title": channel_title,
        "invite_link": invite_link or f"https://t.me/{channel_id.lstrip('@')}"
    }

    set_state(admin_id, STATE_WAIT_ADMIN_CHANNEL_TARGET)
    await message.answer(
        f"✅ Kanal qabul qilindi: <b>{channel_title}</b> ({channel_id})\n\n"
        f"2️⃣ <b>Obunachi Maqsadi (Limit):</b>\n\n"
        f"🎯 Ushbu kanal orqali nechta obunachi yig'ilishi kerak?\n\n"
        f"• <b>Cheksiz bo'lishi uchun:</b> <code>0</code> deb yozing\n"
        f"• <b>Avtomatik ajratish uchun:</b> Kerakli sonni yozing (masalan <code>100</code> yoki <code>500</code>):",
        parse_mode="HTML",
        reply_markup=kb_cancel()
    )


@router.message(lambda msg: msg.text and not msg.text.startswith("/") and get_state(msg.from_user.id) == STATE_WAIT_ADMIN_CHANNEL_TARGET)
async def handle_admin_channel_target_input(message: Message, bot: Bot):
    """Handle channel subscriber target limit input."""
    admin_id = message.from_user.id
    if not _is_admin(admin_id):
        return

    text = message.text.strip()
    try:
        target = int(text)
        if target < 0:
            target = 0
    except ValueError:
        await message.answer("❌ Iltimos, faqat raqam kiriting (masalan <code>0</code> yoki <code>100</code>):", parse_mode="HTML")
        return

    temp = ADMIN_CHANNEL_TEMP.pop(admin_id, {})
    channel_id = temp.get("channel_id")
    channel_title = temp.get("channel_title") or channel_id
    invite_link = temp.get("invite_link") or f"https://t.me/{channel_id.lstrip('@')}"

    if not channel_id:
        await message.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.")
        set_state(admin_id, STATE_NONE)
        return

    from bot.database import add_required_channel, get_all_channels
    from bot.keyboards import kb_admin_channels

    add_required_channel(channel_id, channel_title, invite_link, target)
    set_state(admin_id, STATE_NONE)

    target_desc = "Cheksiz (qo'lda o'chirilguncha)" if target == 0 else f"{target} ta obunachidan keyin avto-uziladi"
    await message.answer(
        f"🎉 <b>Kanal muvaffaqiyatli qo'shildi!</b>\n\n"
        f"📢 Kanal: <b>{channel_title}</b> ({channel_id})\n"
        f"🎯 Maqsad: <b>{target_desc}</b>\n\n"
        f"Endi yangi foydalanuvchilar ushbu kanalga a'zo bo'lishi talab etiladi.",
        parse_mode="HTML"
    )

    channels = get_all_channels()
    await message.answer("📋 <b>Yangilangan Kanallar Ro'yxati:</b>", parse_mode="HTML", reply_markup=kb_admin_channels(channels))


@router.callback_query(F.data.startswith("adm_ch_toggle_"))
async def cb_admin_channel_toggle(call: CallbackQuery, bot: Bot):
    """Toggle channel active status."""
    if not _is_admin(call.from_user.id):
        return
    await call.answer()

    ch_id = call.data.replace("adm_ch_toggle_", "")
    from bot.database import get_all_channels, toggle_channel_status
    from bot.keyboards import kb_admin_channels

    channels = get_all_channels()
    target_ch = next((c for c in channels if str(c["id"]) == ch_id), None)
    if target_ch:
        new_status = 0 if target_ch.get("is_active", 1) else 1
        toggle_channel_status(ch_id, new_status)

    updated_channels = get_all_channels()
    try:
        await call.message.edit_reply_markup(reply_markup=kb_admin_channels(updated_channels))
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm_ch_del_"))
async def cb_admin_channel_del(call: CallbackQuery, bot: Bot):
    """Delete a required channel."""
    if not _is_admin(call.from_user.id):
        return
    await call.answer("🗑 Kanal o'chirildi", show_alert=True)

    ch_id = call.data.replace("adm_ch_del_", "")
    from bot.database import delete_required_channel, get_all_channels
    from bot.keyboards import kb_admin_channels

    delete_required_channel(ch_id)
    channels = get_all_channels()
    try:
        await call.message.edit_reply_markup(reply_markup=kb_admin_channels(channels))
    except Exception:
        pass


@router.callback_query(F.data == "admin_back_to_menu")
async def cb_admin_back_to_menu(call: CallbackQuery, bot: Bot):
    """Return to main admin menu."""
    if not _is_admin(call.from_user.id):
        return
    await call.answer()
    from bot.keyboards import kb_admin
    await bot.send_message(call.from_user.id, "⚙️ <b>Admin Panel</b>", parse_mode="HTML", reply_markup=kb_admin())

