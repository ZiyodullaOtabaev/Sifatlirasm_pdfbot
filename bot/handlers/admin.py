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
    Message, CallbackQuery, BufferedInputFile,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

from bot.config import ADMIN_IDS, BROADCAST_RATE
from bot.database import (
    upsert_user, get_admin_summary, daily_usage_by_action,
    get_top_users, get_new_users_24h,
    get_all_user_ids, save_broadcast_result,
    get_action_stats, get_growth_stats,
    get_broadcast_history, search_user,
)
from bot.keyboards import kb_admin, kb_admin_back, kb_broadcast_confirm, kb_cancel, kb_user_balance_actions
from bot.states import set_state, get_state, STATE_NONE, STATE_WAIT_BROADCAST, STATE_WAIT_ADMIN_BALANCE_INPUT, STATE_WAIT_SEARCH
from bot.utils.chart import render_usage_chart_png, render_growth_chart_png, render_stats_image

logger = logging.getLogger(__name__)
router = Router(name="admin")

# Broadcast state storage
PENDING_BROADCAST: Dict[int, dict] = {}
BROADCAST_RUNNING: Dict[int, bool] = {}
SCHEDULED_TASKS: Dict[int, asyncio.Task] = {}

STATE_WAIT_SCHEDULE_TIME = "wait_schedule_time"


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
    png = render_stats_image(s, action_stats)
    photo = BufferedInputFile(png, filename="actions.png")
    await bot.send_photo(call.from_user.id, photo,
                         caption="📋 Funksiyalar statistikasi",
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


@router.callback_query(F.data == "admin_new24")
async def cb_admin_new24(call: CallbackQuery, bot: Bot):
    """New users 24h."""
    await call.answer()
    if not _is_admin(call.from_user.id):
        return
    rows = get_new_users_24h(30)
    lines = []
    for i, r in enumerate(rows, start=1):
        uname = f"@{r['username']}" if r["username"] else "-"
        name = (f"{r['first_name'] or ''}").strip() or "-"
        t = r["created_at"][11:16] if r["created_at"] and len(r["created_at"]) > 16 else ""
        lines.append(f"{i}. {uname} | {name} | {t}")
    text = "<b>🆕 Yangi 24 soat:</b>\n\n" + ("\n".join(lines) if lines else "Hech kim yo'q")
    await bot.send_message(call.from_user.id, text, parse_mode="HTML",
                           reply_markup=kb_admin_back())


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
    set_state(call.from_user.id, STATE_WAIT_BROADCAST)
    await bot.send_message(
        call.from_user.id,
        "<b>📢 Broadcast</b>\n\n"
        "Rasm, video, fayl yoki matn yuboring.\n\n"
        "<b>💡 Tugma qo'shish:</b>\n"
        "<code>[Matn|https://link.com]</code>\n\n"
        "Caption'ga yozib yuboring — tugma avtomatik qo'shiladi.",
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
    """Execute user search and send results."""
    set_state(admin_id, STATE_NONE)
    rows = search_user(query)
    if not rows:
        await bot.send_message(
            admin_id, f"🔍 '<b>{query}</b>' bo'yicha topilmadi.",
            parse_mode="HTML", reply_markup=kb_admin_back()
        )
        return
    lines = []
    from bot.database import get_user_balance
    for r in rows:
        d = dict(r)
        uname = f"@{d['username']}" if d.get("username") else "-"
        first_name = d.get("first_name") or ""
        last_name = d.get("last_name") or ""
        name = f"{first_name} {last_name}".strip() or "-"
        bal = get_user_balance(d['user_id'])
        created = str(d.get('created_at', ''))[:10]
        uses = d.get('uses_count', 0)
        lines.append(
            f"👤 <b>{name}</b> ({uname})\n"
            f"   ID: <code>{d['user_id']}</code> | 💰 Balans: <b>{bal} kredit</b>\n"
            f"   Foydalanish: {uses} marta\n"
            f"   Ro'yxatdan: {created}"
        )
    text = f"🔍 Natijalar ({len(rows)}):\n\n" + "\n\n".join(lines)
    first_uid = dict(rows[0])['user_id']
    kb = kb_user_balance_actions(first_uid) if len(rows) == 1 else kb_admin_back()
    await bot.send_message(admin_id, text, parse_mode="HTML", reply_markup=kb)


# ========================
# BROADCAST CONTENT HANDLERS
# ========================

def _build_broadcast_data(message: Message) -> dict:
    """Build broadcast data from any message type."""
    caption = message.caption or message.text or ""
    clean_caption, keyboard = _parse_inline_buttons(caption)

    data = {
        "caption": clean_caption,
        "keyboard": keyboard,
        "media_type": "text",
        "file_id": None,
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


@router.message(lambda msg: (msg.photo or msg.video or msg.document or msg.animation) and get_state(msg.from_user.id) == STATE_WAIT_BROADCAST and msg.from_user.id in ADMIN_IDS)
async def broadcast_media(message: Message, bot: Bot):
    """Receive media (photo/video/document/gif) for broadcast."""
    user_id = message.from_user.id
    data = _build_broadcast_data(message)
    PENDING_BROADCAST[user_id] = data

    user_count = len(get_all_user_ids())
    kb = _preview_keyboard()

    preview_caption = (
        f"👁 <b>Preview</b>\n\n"
        f"{'📸 Rasm' if data['media_type'] == 'photo' else '🎥 Video' if data['media_type'] == 'video' else '📄 Fayl' if data['media_type'] == 'document' else '🎞 GIF'}\n"
        f"👥 <b>{user_count}</b> foydalanuvchiga yuboriladi\n"
    )
    if data["keyboard"]:
        btn_count = sum(len(row) for row in data["keyboard"].inline_keyboard)
        preview_caption += f"🔗 {btn_count} ta tugma\n"
    preview_caption += "\n<i>Quyidagi variantlardan tanlang:</i>"

    if data["media_type"] == "photo":
        await bot.send_photo(user_id, data["file_id"],
                             caption=preview_caption, parse_mode="HTML",
                             reply_markup=kb)
    elif data["media_type"] == "video":
        await bot.send_video(user_id, data["file_id"],
                             caption=preview_caption, parse_mode="HTML",
                             reply_markup=kb)
    elif data["media_type"] == "document":
        await bot.send_document(user_id, data["file_id"],
                                caption=preview_caption, parse_mode="HTML",
                                reply_markup=kb)
    else:
        await bot.send_animation(user_id, data["file_id"],
                                 caption=preview_caption, parse_mode="HTML",
                                 reply_markup=kb)


@router.message(lambda msg: msg.text and not msg.text.startswith("/") and get_state(msg.from_user.id) == STATE_WAIT_BROADCAST and msg.from_user.id in ADMIN_IDS)
async def broadcast_text(message: Message, bot: Bot):
    """Receive text for broadcast."""
    user_id = message.from_user.id
    data = _build_broadcast_data(message)
    PENDING_BROADCAST[user_id] = data

    user_count = len(get_all_user_ids())
    kb = _preview_keyboard()

    preview = (
        f"👁 <b>Preview</b>\n\n"
        f"📝 Matn broadcast\n"
        f"👥 <b>{user_count}</b> foydalanuvchiga yuboriladi\n"
    )
    if data["keyboard"]:
        btn_count = sum(len(row) for row in data["keyboard"].inline_keyboard)
        preview += f"🔗 {btn_count} ta tugma\n"
    preview += f"\n━━━━━━━━━━━━━━━\n{data['caption']}\n━━━━━━━━━━━━━━━\n\n<i>Quyidagi variantlardan tanlang:</i>"

    await message.answer(preview, parse_mode="HTML", reply_markup=kb)


def _preview_keyboard() -> InlineKeyboardMarkup:
    """Broadcast preview keyboard with send options."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📤 Hozir yuborish", callback_data="broadcast_now"),
        ],
        [
            InlineKeyboardButton(text="⏰ Rejalash", callback_data="broadcast_schedule"),
        ],
        [
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel"),
        ],
    ])


# ========================
# BROADCAST CALLBACKS
# ========================

@router.callback_query(F.data == "broadcast_now")
async def cb_broadcast_now(call: CallbackQuery, bot: Bot):
    """Send broadcast immediately."""
    await call.answer()
    admin_id = call.from_user.id
    if not _is_admin(admin_id):
        return
    data = PENDING_BROADCAST.pop(admin_id, None)
    if not data:
        await call.message.answer("⚠️ Broadcast topilmadi.")
        return
    BROADCAST_RUNNING[admin_id] = True
    set_state(admin_id, STATE_NONE)
    user_count = len(get_all_user_ids())
    status_msg = await bot.send_message(
        admin_id, f"📡 Broadcast boshlandi... ({user_count} foydalanuvchi)"
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

    # Format: +30 (minutes), +2h (hours)
    if time_str.startswith("+"):
        val = time_str[1:]
        if val.endswith("h"):
            hours = int(val[:-1])
            send_at = now + timedelta(hours=hours)
        elif val.isdigit():
            minutes = int(val)
            send_at = now + timedelta(minutes=minutes)

    # Format: HH:MM
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

    # Schedule the task
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
    user_count = len(get_all_user_ids())
    status_msg = await bot.send_message(
        admin_id, f"📡 Rejalashtirilgan broadcast boshlandi! ({user_count} foydalanuvchi)"
    )
    await _do_broadcast(bot, admin_id, data, status_msg.message_id)
    SCHEDULED_TASKS.pop(admin_id, None)


# ========================
# BROADCAST ENGINE
# ========================

async def _do_broadcast(bot: Bot, admin_id: int, broadcast_data: dict, status_msg_id: int):
    """Execute broadcast to all users with inline buttons support."""
    user_ids = get_all_user_ids()
    total = len(user_ids)
    success = 0
    failed = 0

    media_type = broadcast_data["media_type"]
    file_id = broadcast_data.get("file_id")
    caption = broadcast_data.get("caption", "")
    keyboard = broadcast_data.get("keyboard")  # InlineKeyboardMarkup or None

    semaphore = asyncio.Semaphore(BROADCAST_RATE)

    async def send_one(uid: int):
        nonlocal success, failed
        async with semaphore:
            try:
                if media_type == "photo":
                    await bot.send_photo(
                        uid, file_id, caption=caption or None,
                        parse_mode="HTML", reply_markup=keyboard
                    )
                elif media_type == "video":
                    await bot.send_video(
                        uid, file_id, caption=caption or None,
                        parse_mode="HTML", reply_markup=keyboard
                    )
                elif media_type == "document":
                    await bot.send_document(
                        uid, file_id, caption=caption or None,
                        parse_mode="HTML", reply_markup=keyboard
                    )
                elif media_type == "animation":
                    await bot.send_animation(
                        uid, file_id, caption=caption or None,
                        parse_mode="HTML", reply_markup=keyboard
                    )
                else:
                    await bot.send_message(
                        uid, caption,
                        parse_mode="HTML", reply_markup=keyboard
                    )
                success += 1
            except Exception:
                failed += 1
            await asyncio.sleep(1 / BROADCAST_RATE)

    batch_size = 50
    tasks = []
    for uid in user_ids:
        tasks.append(send_one(uid))
        if len(tasks) >= batch_size:
            await asyncio.gather(*tasks)
            tasks = []
            try:
                pct = round((success + failed) / total * 100)
                await bot.edit_message_text(
                    f"📡 Yuborilmoqda... {pct}%\n"
                    f"✅ {success} | ❌ {failed} | {success + failed}/{total}",
                    chat_id=admin_id, message_id=status_msg_id
                )
            except Exception:
                pass

    if tasks:
        await asyncio.gather(*tasks)

    save_broadcast_result(admin_id, media_type, file_id or "", caption, total, success, failed)

    try:
        await bot.edit_message_text(
            f"✅ <b>Broadcast tugadi!</b>\n\n"
            f"👥 Jami: {total}\n"
            f"✅ Yuborildi: {success}\n"
            f"🚫 Xato: {failed}\n"
            f"📊 Samaradorlik: {round(success/max(total,1)*100)}%\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            chat_id=admin_id, message_id=status_msg_id,
            parse_mode="HTML"
        )
    except Exception:
        await bot.send_message(admin_id, f"✅ Broadcast: {success}/{total}")

    BROADCAST_RUNNING.pop(admin_id, None)
    logger.info(f"Broadcast by {admin_id}: {success}/{total}, failed={failed}")
