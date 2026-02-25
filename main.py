import os
import re
import io
import time
import asyncio
import sqlite3
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ======================
#   ENV / SETTINGS
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL_USER = os.getenv("CHANNEL_USER", "@xonziyy").strip()
FREE_USES_BEFORE_SUB = int(os.getenv("FREE_USES_BEFORE_SUB", "10").strip() or "10")

REAL_ESRGAN_BIN = os.getenv("REAL_ESRGAN_BIN", "").strip()          # e.g. /home/ziyodulla/apps/realesrgan-ncnn-vulkan
REAL_ESRGAN_MODELS = os.getenv("REAL_ESRGAN_MODELS", "").strip()    # e.g. /home/ziyodulla/apps/models
ENABLE_REAL_AI = os.getenv("ENABLE_REAL_AI", "1").strip() != "0"

ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "").strip()  # "5853...,123..."
DB_PATH = os.getenv("DB_PATH", "bot.db").strip() or "bot.db"
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads").strip() or "downloads"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi. Alwaysdata Services -> Environment ga qo'ying.")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def parse_admin_ids(value: str) -> set:
    out = set()
    if not value:
        return out
    for x in value.split(","):
        x = x.strip()
        if x.isdigit():
            out.add(int(x))
    return out

ADMIN_IDS = parse_admin_ids(ADMIN_IDS_RAW)

# ======================
#   BOT INIT
# ======================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


import sqlite3
from datetime import datetime, timedelta

ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or "0")
DB_PATH = os.getenv("DB_PATH", "bot.db")

def is_admin(user_id: int) -> bool:
    return ADMIN_ID and user_id == ADMIN_ID

def db_one(sql: str, params=()):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(sql, params)
    row = cur.fetchone()
    con.close()
    return row

def db_all(sql: str, params=()):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    con.close()
    return rows

@dp.message_handler(commands=["admin"])
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    total_users = db_one("SELECT COUNT(*) FROM users")[0]
    total_uses = db_one("SELECT COALESCE(SUM(uses_count),0) FROM users")[0]

    # Bugun (server vaqti bo'yicha) ro'yxatdan o'tganlar
    today_new = db_one(
        "SELECT COUNT(*) FROM users WHERE date(created_at) = date('now')"
    )[0]

    # Oxirgi 24 soatda aktivlar (updated_at yangilangan bo'lsa)
    active_24h = db_one(
        "SELECT COUNT(*) FROM users WHERE updated_at >= datetime('now','-24 hours')"
    )[0]

    top10 = db_all(
        "SELECT user_id, COALESCE(username,''), COALESCE(first_name,''), COALESCE(last_name,''), uses_count "
        "FROM users ORDER BY uses_count DESC, updated_at DESC LIMIT 10"
    )

    lines = []
    for i, (uid, un, fn, ln, uses) in enumerate(top10, start=1):
        name = (fn + " " + ln).strip() or "-"
        uname = f"@{un}" if un else "-"
        lines.append(f"{i}) {uname} | {name} | uses={uses} | id={uid}")

    text = (
        "📊 Admin statistika\n\n"
        f"👥 Jami foydalanuvchi: {total_users}\n"
        f"⚡️ Jami foydalanish: {total_uses}\n"
        f"🆕 Bugun qo‘shilgan: {today_new}\n"
        f"🕒 Oxirgi 24 soat aktiv: {active_24h}\n\n"
        "🏆 TOP-10:\n" + ("\n".join(lines) if lines else "Hali yo‘q")
    )

    await message.answer(text)

@dp.message_handler(commands=["top"])
async def admin_top(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    rows = db_all(
        "SELECT COALESCE(username,''), COALESCE(first_name,''), COALESCE(last_name,''), uses_count "
        "FROM users ORDER BY uses_count DESC, updated_at DESC LIMIT 20"
    )
    out = []
    for i, (un, fn, ln, uses) in enumerate(rows, 1):
        uname = f"@{un}" if un else "-"
        name = (fn + " " + ln).strip() or "-"
        out.append(f"{i}) {uname} | {name} | {uses}")

    await message.answer("🏆 TOP-20:\n" + "\n".join(out))


# ======================
#   DB (SQLite)
# ======================
def db_connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def db_init():
    with db_connect() as con:
        cur = con.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            uses_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_usage_user ON usage_logs(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_usage_date ON usage_logs(created_at)")
        con.commit()

def upsert_user(u: types.User):
    with db_connect() as con:
        con.execute("""
        INSERT INTO users (user_id, username, first_name, last_name, uses_count, created_at, updated_at)
        VALUES (?, ?, ?, ?, 0, datetime('now'), datetime('now'))
        ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username,
            first_name=excluded.first_name,
            last_name=excluded.last_name,
            updated_at=datetime('now')
        """, (u.id, u.username, u.first_name, u.last_name))
        con.commit()

def get_uses(user_id: int) -> int:
    with db_connect() as con:
        row = con.execute("SELECT uses_count FROM users WHERE user_id=?", (user_id,)).fetchone()
        return int(row["uses_count"]) if row and row["uses_count"] is not None else 0

def inc_uses_and_log(user_id: int, action: str):
    now = datetime.now(timezone.utc).isoformat()
    with db_connect() as con:
        con.execute("UPDATE users SET uses_count = COALESCE(uses_count,0)+1, updated_at=datetime('now') WHERE user_id=?", (user_id,))
        con.execute("INSERT INTO usage_logs (user_id, action, created_at) VALUES (?, ?, ?)", (user_id, action, now))
        con.commit()

def stats_total_users() -> int:
    with db_connect() as con:
        row = con.execute("SELECT COUNT(*) c FROM users").fetchone()
        return int(row["c"]) if row else 0

def stats_total_uses() -> int:
    with db_connect() as con:
        row = con.execute("SELECT COALESCE(SUM(uses_count),0) s FROM users").fetchone()
        return int(row["s"]) if row else 0

def stats_top_users(limit: int = 10):
    with db_connect() as con:
        return con.execute("""
        SELECT user_id, username, first_name, uses_count
        FROM users
        ORDER BY uses_count DESC
        LIMIT ?
        """, (limit,)).fetchall()

def stats_daily_counts(days: int = 7):
    with db_connect() as con:
        return con.execute(f"""
        SELECT substr(created_at,1,10) AS day, action, COUNT(*) AS cnt
        FROM usage_logs
        WHERE created_at >= datetime('now', '-{days} day')
        GROUP BY day, action
        ORDER BY day DESC, cnt DESC
        """).fetchall()

# ======================
#   STATE (in-memory)
# ======================
STATE_NONE = "none"
STATE_WAIT_TEXT = "wait_text"
STATE_WAIT_IMG_PDF = "wait_img_pdf"
STATE_WAIT_UPSCALE = "wait_upscale"

USER_STATE: Dict[int, str] = {}
# photo buffering for media groups
MEDIA_BUFFER: Dict[Tuple[int, str], List[str]] = {}    # (user_id, media_group_id) -> [filepaths]
MEDIA_TASK: Dict[Tuple[int, str], asyncio.Task] = {}

def set_state(user_id: int, state: str):
    USER_STATE[user_id] = state

def get_state(user_id: int) -> str:
    return USER_STATE.get(user_id, STATE_NONE)

def safe_remove(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

# ======================
#   UI KEYBOARDS
# ======================
def kb_main() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📝 Matnni PDF qilish", callback_data="act_text_pdf"),
        InlineKeyboardButton("🖼 Rasmni PDF qilish", callback_data="act_img_pdf"),
        InlineKeyboardButton("✨ Rasm sifatini oshirish", callback_data="act_upscale"),
    )
    return kb

def kb_cancel() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("⬅️ Bekor qilish / Bosh menyu", callback_data="act_cancel"))
    return kb

def kb_subscribe() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("📢 Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USER.lstrip('@')}"))
    kb.add(InlineKeyboardButton("🔁 Tekshirish", callback_data="act_check_sub"))
    return kb

# ======================
#   SUBSCRIPTION RULE
# ======================
async def check_sub(user_id: int) -> bool:
    """Bot kanalga admin bo'lsa, a'zolikni tekshiradi."""
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USER, user_id=user_id)
        return member.status != "left"
    except Exception:
        # bot admin bo'lmasa yoki xato bo'lsa, bloklamaymiz
        return True

async def enforce_rule_or_block(user_id: int) -> bool:
    """
    True -> davom etsin
    False -> bloklandi (kanal tugmasi chiqarildi)
    """
    uses = get_uses(user_id)
    if uses < FREE_USES_BEFORE_SUB:
        return True

    ok = await check_sub(user_id)
    if ok:
        return True

    await bot.send_message(
        user_id,
        "Siz xizmatimizdan 10 marta foydalandingiz.\n"
        "Yana foydalanish uchun kanalimizga obuna bo‘ling 👇",
        reply_markup=kb_subscribe()
    )
    return False

# ======================
#   PDF HELPERS
# ======================
def make_text_pdf_bytes(text: str) -> bytes:
    # Simple text-to-PDF (A4), wrap lines
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    margin = 50
    y = height - margin
    line_height = 14

    # basic wrapping
    def wrap_line(s: str, max_chars: int = 95):
        s = s.strip("\n")
        if not s:
            return [""]
        out = []
        while len(s) > max_chars:
            cut = s.rfind(" ", 0, max_chars)
            if cut <= 0:
                cut = max_chars
            out.append(s[:cut].rstrip())
            s = s[cut:].lstrip()
        out.append(s)
        return out

    lines: List[str] = []
    for raw in text.splitlines():
        lines.extend(wrap_line(raw))

    c.setFont("Helvetica", 12)
    for line in lines:
        if y < margin:
            c.showPage()
            c.setFont("Helvetica", 12)
            y = height - margin
        c.drawString(margin, y, line)
        y -= line_height

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()

def images_to_pdf(path_list: List[str], out_pdf_path: str):
    imgs = []
    for p in path_list:
        im = Image.open(p).convert("RGB")
        imgs.append(im)

    if not imgs:
        raise RuntimeError("Rasm topilmadi")

    first, rest = imgs[0], imgs[1:]
    first.save(out_pdf_path, save_all=True, append_images=rest)

# ======================
#   UPSCALE HELPERS
# ======================
def pillow_upscale_2x(in_path: str, out_path: str):
    img = Image.open(in_path)
    new_size = (img.width * 2, img.height * 2)
    up = img.resize(new_size, Image.LANCZOS)
    up.save(out_path, quality=95, optimize=True)

def try_realesrgan(in_path: str, out_path: str) -> Tuple[bool, str]:
    """
    returns: (success, error_msg)
    """
    if not ENABLE_REAL_AI:
        return (False, "ENABLE_REAL_AI=0 (o‘chirilgan)")

    if not REAL_ESRGAN_BIN or not os.path.exists(REAL_ESRGAN_BIN):
        return (False, "REAL_ESRGAN_BIN topilmadi")

    model_dir = REAL_ESRGAN_MODELS if REAL_ESRGAN_MODELS else "models"
    if REAL_ESRGAN_MODELS and (not os.path.exists(REAL_ESRGAN_MODELS)):
        return (False, "REAL_ESRGAN_MODELS yo‘li topilmadi")

    cmd = [
        REAL_ESRGAN_BIN,
        "-i", in_path,
        "-o", out_path,
        "-s", "2",
        "-n", "realesrgan-x4plus",
        "-m", model_dir
    ]

    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=180)
        if p.returncode == 0 and os.path.exists(out_path):
            return (True, "")
        return (False, (p.stderr or p.stdout or "Unknown error")[:800])
    except Exception as e:
        return (False, str(e))

# ======================
#   MAIN MENU
# ======================
async def show_main_menu(user_id: int):
    set_state(user_id, STATE_NONE)
    await bot.send_message(
        user_id,
        "Assalamu Alaykum! 📌 Rasm yoki matnlaringizni PDF qiling va rasmlaringizni sifatini oshiring.\n"
        "Quyidan kerakli bo‘limni tanlang:",
        reply_markup=kb_main()
    )

# ======================
#   COMMANDS
# ======================
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    upsert_user(message.from_user)
    await show_main_menu(message.from_user.id)

@dp.message_handler(commands=["myid"])
async def cmd_myid(message: types.Message):
    await message.answer(f"Your user_id: {message.from_user.id}")

@dp.message_handler(commands=["stats"])
async def cmd_stats(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    upsert_user(message.from_user)

    tu = stats_total_users()
    ts = stats_total_uses()
    top = stats_top_users(10)
    daily = stats_daily_counts(7)

    top_lines = []
    for i, r in enumerate(top, 1):
        name = ("@" + r["username"]) if r["username"] else (r["first_name"] or "no_name")
        top_lines.append(f"{i}) {name} — {r['uses_count']}")

    daily_lines = []
    for r in daily[:50]:
        daily_lines.append(f"{r['day']} | {r['action']} = {r['cnt']}")

    text = (
        "📊 *Bot Statistikasi*\n\n"
        f"👥 Users: *{tu}*\n"
        f"⚙️ Total uses: *{ts}*\n\n"
        "🏆 *Top 10 users:*\n" + ("\n".join(top_lines) if top_lines else "—") + "\n\n"
        "📅 *Last 7 days (UTC):*\n" + ("\n".join(daily_lines) if daily_lines else "—")
    )
    await message.answer(text, parse_mode="Markdown")

# ======================
#   CALLBACKS
# ======================
@dp.callback_query_handler(text="act_cancel")
async def cb_cancel(call: types.CallbackQuery):
    await call.answer()
    await show_main_menu(call.from_user.id)

@dp.callback_query_handler(text="act_check_sub")
async def cb_check_sub(call: types.CallbackQuery):
    await call.answer()
    ok = await check_sub(call.from_user.id)
    if ok:
        await bot.send_message(call.from_user.id, "✅ Rahmat! Endi foydalanishingiz mumkin.")
        await show_main_menu(call.from_user.id)
    else:
        await bot.send_message(call.from_user.id, "❌ Hali obuna emassiz. Iltimos, kanalga obuna bo‘ling.", reply_markup=kb_subscribe())

@dp.callback_query_handler(text="act_text_pdf")
async def cb_text_pdf(call: types.CallbackQuery):
    await call.answer()

    upsert_user(call.from_user)
    if not await enforce_rule_or_block(call.from_user.id):
        return

    set_state(call.from_user.id, STATE_WAIT_TEXT)
    await bot.send_message(call.from_user.id, "📝 Matn yuboring (PDF qilib qaytaraman).", reply_markup=kb_cancel())

@dp.callback_query_handler(text="act_img_pdf")
async def cb_img_pdf(call: types.CallbackQuery):
    await call.answer()

    upsert_user(call.from_user)
    if not await enforce_rule_or_block(call.from_user.id):
        return

    set_state(call.from_user.id, STATE_WAIT_IMG_PDF)
    await bot.send_message(
        call.from_user.id,
        "🖼 Rasm yuboring.\n",
        reply_markup=kb_cancel()
    )

@dp.callback_query_handler(text="act_upscale")
async def cb_upscale(call: types.CallbackQuery):
    await call.answer()

    upsert_user(call.from_user)
    if not await enforce_rule_or_block(call.from_user.id):
        return

    set_state(call.from_user.id, STATE_WAIT_UPSCALE)
    await bot.send_message(call.from_user.id, "✨ Sifatini oshirish uchun rasm yuboring.", reply_markup=kb_cancel())

# ======================
#   MESSAGE HANDLERS
# ======================
@dp.message_handler(content_types=["text"])
async def on_text(message: types.Message):
    upsert_user(message.from_user)

    # menu bo'lmagan matnlar
    st = get_state(message.from_user.id)
    if st != STATE_WAIT_TEXT:
        return

    if not await enforce_rule_or_block(message.from_user.id):
        return

    text = message.text.strip()
    if not text:
        await message.answer("Matn bo‘sh. Qaytadan yuboring.", reply_markup=kb_cancel())
        return

    status = await message.answer("⏳ PDF tayyorlanmoqda...")

    try:
        pdf_bytes = make_text_pdf_bytes(text)
        file_name = f"text_{message.from_user.id}_{int(time.time())}.pdf"
        await bot.send_document(
            message.from_user.id,
            types.InputFile(io.BytesIO(pdf_bytes), filename=file_name),
            caption="✅ Tayyor!"
        )
        inc_uses_and_log(message.from_user.id, "text_pdf")
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")
    finally:
        try:
            await bot.delete_message(message.from_user.id, status.message_id)
        except Exception:
            pass

    await show_main_menu(message.from_user.id)

@dp.message_handler(content_types=["photo"])
async def on_photo(message: types.Message):
    upsert_user(message.from_user)
    user_id = message.from_user.id
    st = get_state(user_id)

    if st not in (STATE_WAIT_IMG_PDF, STATE_WAIT_UPSCALE):
        return

    if not await enforce_rule_or_block(user_id):
        return

    # Save photo
    photo = message.photo[-1]
    file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{photo.file_id}.jpg")
    await photo.download(destination=file_path)  # aiogram v2.25.1

    # ===== UPSCALE MODE =====
    if st == STATE_WAIT_UPSCALE:
        status = await message.answer("⏳ Sifat oshirilmoqda...")
        out_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{photo.file_id}_up.jpg")
        try:
            ok, err = try_realesrgan(file_path, out_path)
            if not ok:
                # fallback
                pillow_upscale_2x(file_path, out_path)
                await message.answer(f"⚠️ AI ishlamadi, fallback ishlatildi.\nSabab: {err}")

            with open(out_path, "rb") as f:
                await bot.send_photo(user_id, f, caption="✅ Tayyor!")
            inc_uses_and_log(user_id, "upscale")
        except Exception as e:
            await message.answer(f"❌ Xato: {e}")
        finally:
            safe_remove(file_path)
            safe_remove(out_path)
            try:
                await bot.delete_message(user_id, status.message_id)
            except Exception:
                pass

        await show_main_menu(user_id)
        return

    # ===== IMG PDF MODE =====
    # Media group (album) bo'lsa: buffer qilamiz
    if message.media_group_id:
        key = (user_id, message.media_group_id)
        MEDIA_BUFFER.setdefault(key, []).append(file_path)

        # debounce: oxirgi rasm kelgach 1.2s kutib PDF qilamiz
        old_task = MEDIA_TASK.get(key)
        if old_task and not old_task.done():
            old_task.cancel()

        async def finalize_group():
            await asyncio.sleep(1.2)
            paths = MEDIA_BUFFER.pop(key, [])
            MEDIA_TASK.pop(key, None)
            if not paths:
                return

            status = await bot.send_message(user_id, "⏳ PDF tayyorlanmoqda...")
            pdf_path = os.path.join(DOWNLOAD_DIR, f"images_{user_id}_{int(time.time())}.pdf")
            try:
                images_to_pdf(paths, pdf_path)
                with open(pdf_path, "rb") as f:
                    await bot.send_document(user_id, f, caption="✅ Tayyor!")
                inc_uses_and_log(user_id, "img_pdf")
            except Exception as e:
                await bot.send_message(user_id, f"❌ Xato: {e}")
            finally:
                for p in paths:
                    safe_remove(p)
                safe_remove(pdf_path)
                try:
                    await bot.delete_message(user_id, status.message_id)
                except Exception:
                    pass

            await show_main_menu(user_id)

        MEDIA_TASK[key] = asyncio.create_task(finalize_group())
        return

    # Bitta rasm bo'lsa: darhol PDF
    status = await message.answer("⏳ PDF tayyorlanmoqda...")
    pdf_path = os.path.join(DOWNLOAD_DIR, f"image_{user_id}_{int(time.time())}.pdf")
    try:
        images_to_pdf([file_path], pdf_path)
        with open(pdf_path, "rb") as f:
            await bot.send_document(user_id, f, caption="✅ Tayyor!")
        inc_uses_and_log(user_id, "img_pdf")
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")
    finally:
        safe_remove(file_path)
        safe_remove(pdf_path)
        try:
            await bot.delete_message(user_id, status.message_id)
        except Exception:
            pass

    await show_main_menu(user_id)

# ======================
#   BOOT
# ======================
if __name__ == "__main__":
    db_init()
    print("Bot ishga tushdi...")
    executor.start_polling(dp, skip_updates=True)