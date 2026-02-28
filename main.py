import os
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
from PyPDF2 import PdfMerger

# ======================
#   ENV / SETTINGS
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL_USER = os.getenv("CHANNEL_USER", "@xonziyy").strip()

# ✅ Endi 15 ta bepul urinish
FREE_USES_BEFORE_SUB = int((os.getenv("FREE_USES_BEFORE_SUB", "15").strip() or "15"))

REAL_ESRGAN_BIN = os.getenv("REAL_ESRGAN_BIN", "").strip()
REAL_ESRGAN_MODELS = os.getenv("REAL_ESRGAN_MODELS", "").strip()
ENABLE_REAL_AI = os.getenv("ENABLE_REAL_AI", "1").strip() != "0"

ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "").strip()  # "5853...,123..."
ADMIN_ID_SINGLE = int(os.getenv("ADMIN_ID", "0") or "0")

DB_PATH = os.getenv("DB_PATH", "bot.db").strip() or "bot.db"
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads").strip() or "downloads"

# ✅ 24 soatdan eski fayllar o‘chadi
CLEANUP_MAX_AGE_SECONDS = int(os.getenv("CLEANUP_MAX_AGE_SECONDS", str(24 * 3600)))
CLEANUP_INTERVAL_SECONDS = int(os.getenv("CLEANUP_INTERVAL_SECONDS", str(60 * 60)))  # har 1 soatda tekshiradi

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi. Alwaysdata Services -> Environment ga qo'ying.")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def parse_admin_ids(value: str) -> set:
    out = set()
    if value:
        for x in value.split(","):
            x = x.strip()
            if x.isdigit():
                out.add(int(x))
    if ADMIN_ID_SINGLE:
        out.add(int(ADMIN_ID_SINGLE))
    return out

ADMIN_IDS = parse_admin_ids(ADMIN_IDS_RAW)

# ======================
#   BOT INIT
# ======================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

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

# ======================
#   STATE (in-memory)
# ======================
STATE_NONE = "none"
STATE_WAIT_TEXT = "wait_text"
STATE_WAIT_IMG_PDF = "wait_img_pdf"
STATE_WAIT_UPSCALE = "wait_upscale"
STATE_WAIT_PDF_MERGE = "wait_pdf_merge"

USER_STATE: Dict[int, str] = {}
MEDIA_BUFFER: Dict[Tuple[int, str], List[str]] = {}  # (user_id, media_group_id) -> [paths]
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
        InlineKeyboardButton("📎 PDFlarni bitta qilish", callback_data="act_merge_pdf"),
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


def kb_admin() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🏆 TOP-30", callback_data="admin_top30"),
        InlineKeyboardButton("📈 7 kun grafik", callback_data="admin_chart7"),
    )
    kb.add(
        InlineKeyboardButton("🟢 Aktiv 24h", callback_data="admin_active24"),
        InlineKeyboardButton("🆕 Yangi 24h", callback_data="admin_new24"),
    )
    return kb

def get_admin_summary():
    with db_connect() as con:
        total_users = con.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        total_uses = con.execute("SELECT COALESCE(SUM(uses_count),0) s FROM users").fetchone()["s"]
        active_24h = con.execute("""
            SELECT COUNT(*) c
            FROM users
            WHERE updated_at >= datetime('now','-24 hours')
        """).fetchone()["c"]
        new_24h = con.execute("""
            SELECT COUNT(*) c
            FROM users
            WHERE created_at >= datetime('now','-24 hours')
        """).fetchone()["c"]
    return total_users, total_uses, active_24h, new_24h

def daily_usage_totals(days: int = 7) -> List[Tuple[str, int]]:
    with db_connect() as con:
        rows = con.execute(f"""
            SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS cnt
            FROM usage_logs
            WHERE created_at >= datetime('now', '-{days} day')
            GROUP BY day
            ORDER BY day ASC
        """).fetchall()
    return [(r["day"], int(r["cnt"])) for r in rows]

def render_bar_chart_png(data: List[Tuple[str, int]], title: str = "So‘nggi 7 kun foydalanish") -> bytes:
    W, H = 1000, 420
    pad = 50
    img = Image.new("RGB", (W, H), "white")
    from PIL import ImageDraw, ImageFont
    d = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 18)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 14)
    except Exception:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()

    d.text((pad, 10), title, fill="black", font=font)

    if not data:
        d.text((pad, 60), "Ma'lumot yo‘q.", fill="black", font=font)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    max_v = max(v for _, v in data) or 1
    chart_top = 60
    chart_bottom = H - 80
    chart_left = pad
    chart_right = W - pad

    d.line((chart_left, chart_bottom, chart_right, chart_bottom), fill="black", width=2)
    d.line((chart_left, chart_top, chart_left, chart_bottom), fill="black", width=2)

    n = len(data)
    gap = 12
    bar_w = max(18, int((chart_right - chart_left - gap * (n + 1)) / n))
    x = chart_left + gap

    for day, val in data:
        bar_h = int((val / max_v) * (chart_bottom - chart_top))
        y1 = chart_bottom - bar_h
        d.rectangle((x, y1, x + bar_w, chart_bottom), outline="black", width=2)
        d.text((x, chart_bottom + 6), day[5:], fill="black", font=font_small)
        d.text((x, y1 - 18), str(val), fill="black", font=font_small)
        x += bar_w + gap

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# ======================
#   SUBSCRIPTION RULE
# ======================
async def check_sub(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USER, user_id=user_id)
        return member.status != "left"
    except Exception:
        # bot admin bo'lmasa ham bloklamaymiz
        return True

async def enforce_rule_or_block(user_id: int) -> bool:
    uses = get_uses(user_id)
    if uses < FREE_USES_BEFORE_SUB:
        return True

    ok = await check_sub(user_id)
    if ok:
        return True

    # foydalanuvchiga ko‘rsatamiz (bu xato emas)
    try:
        await bot.send_message(
            user_id,
            f"Siz xizmatimizdan {FREE_USES_BEFORE_SUB} marta foydalandingiz.\n"
            "Yana foydalanish uchun kanalimizga obuna bo‘ling 👇",
            reply_markup=kb_subscribe()
        )
    except Exception:
        pass
    return False

# ======================
#   PDF HELPERS
# ======================
def make_text_pdf_bytes(text: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    margin = 50
    y = height - margin
    line_height = 14

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
        raise RuntimeError("no images")

    first, rest = imgs[0], imgs[1:]
    first.save(out_pdf_path, save_all=True, append_images=rest)


def merge_pdfs(pdf_paths: List[str], out_pdf_path: str):
    merger = PdfMerger()
    try:
        for p in pdf_paths:
            merger.append(p)
        with open(out_pdf_path, "wb") as f:
            merger.write(f)
    finally:
        try:
            merger.close()
        except Exception:
            pass

# ======================
#   UPSCALE HELPERS
# ======================
def pillow_upscale_2x(in_path: str, out_path: str):
    img = Image.open(in_path)
    new_size = (img.width * 2, img.height * 2)
    up = img.resize(new_size, Image.LANCZOS)
    up.save(out_path, quality=95, optimize=True)

def try_realesrgan(in_path: str, out_path: str) -> bool:
    """
    True -> AI ishladi
    False -> ishlamadi (fallback ishlatiladi)
    """
    if not ENABLE_REAL_AI:
        return False

    if not REAL_ESRGAN_BIN or not os.path.exists(REAL_ESRGAN_BIN):
        return False

    model_dir = REAL_ESRGAN_MODELS if REAL_ESRGAN_MODELS else "models"
    if REAL_ESRGAN_MODELS and (not os.path.exists(REAL_ESRGAN_MODELS)):
        return False

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
        return p.returncode == 0 and os.path.exists(out_path)
    except Exception:
        return False

# ======================
#   CLEANUP TASK (24h+)
# ======================
def cleanup_download_dir_once():
    """
    downloads/ ichidagi 24 soatdan eski fayllarni o‘chiradi.
    (DB va kodga tegmaydi)
    """
    try:
        now = time.time()
        for name in os.listdir(DOWNLOAD_DIR):
            path = os.path.join(DOWNLOAD_DIR, name)
            if not os.path.isfile(path):
                continue
            try:
                mtime = os.path.getmtime(path)
                if now - mtime > CLEANUP_MAX_AGE_SECONDS:
                    safe_remove(path)
            except Exception:
                pass
    except Exception:
        pass

async def cleanup_worker():
    while True:
        cleanup_download_dir_once()
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)

# ======================
#   MAIN MENU
# ======================
async def show_main_menu(user_id: int):
    set_state(user_id, STATE_NONE)
    try:
        await bot.send_message(
            user_id,
            "Assalamu Alaykum! 📌 Rasm yoki matnlaringizni PDF qiling va rasmlaringizni sifatini oshiring.\n"
            "Quyidan kerakli bo‘limni tanlang:",
            reply_markup=kb_main()
        )
    except Exception:
        pass

# ======================
#   COMMANDS
# ======================
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    upsert_user(message.from_user)
    await show_main_menu(message.from_user.id)

@dp.message_handler(commands=["admin"])
async def cmd_admin(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    total_users, total_uses, active_24h, new_24h = get_admin_summary()

    text = (
        "🛠 Admin panel\n\n"
        f"👥 Jami foydalanuvchi: {total_users}\n"
        f"⚡️ Jami foydalanish: {total_uses}\n"
        f"🟢 Oxirgi 24 soat aktiv: {active_24h}\n"
        f"🆕 Oxirgi 24 soatda qo‘shilgan: {new_24h}\n\n"
        "Quyidan bo‘lim tanlang:"
    )

    try:
        data = daily_usage_totals(7)
        png = render_bar_chart_png(data, "📈 So‘nggi 7 kun foydalanish")
        await bot.send_photo(
            message.from_user.id,
            types.InputFile(io.BytesIO(png), filename="usage_7d.png"),
            caption=text,
            reply_markup=kb_admin()
        )
    except Exception:
        await message.answer(text, reply_markup=kb_admin())


@dp.message_handler(commands=["top"])
async def cmd_top(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    with db_connect() as con:
        rows = con.execute("""
            SELECT user_id, COALESCE(username,''), COALESCE(first_name,''), COALESCE(last_name,''), uses_count
            FROM users
            ORDER BY uses_count DESC, updated_at DESC
            LIMIT 30
        """).fetchall()

    def fmt(r):
        uname = f"@{r[1]}" if r[1] else "-"
        name = (f"{r[2] or ''} {r[3] or ''}").strip() or "-"
        return f"{uname} | {name} | id={r[0]} | uses={r[4]}"

    lines = [f"{i}) {fmt(r)}" for i, r in enumerate(rows, start=1)]
    text = "🏆 TOP-30 foydalanuvchilar:\n" + ("\n".join(lines) if lines else "—")
    await message.answer(text)

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
        try:
            await bot.send_message(call.from_user.id, "✅ Rahmat! Endi foydalanishingiz mumkin.")
        except Exception:
            pass
        await show_main_menu(call.from_user.id)
    else:
        try:
            await bot.send_message(call.from_user.id, "❌ Hali obuna emassiz. Iltimos, kanalga obuna bo‘ling.", reply_markup=kb_subscribe())
        except Exception:
            pass


@dp.callback_query_handler(text="admin_top30")
async def cb_admin_top30(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer()
        return
    await call.answer()

    with db_connect() as con:
        rows = con.execute("""
            SELECT user_id, COALESCE(username,''), COALESCE(first_name,''), COALESCE(last_name,''), uses_count
            FROM users
            ORDER BY uses_count DESC, updated_at DESC
            LIMIT 30
        """).fetchall()

    def fmt(r):
        uname = f"@{r[1]}" if r[1] else "-"
        name = (f"{r[2] or ''} {r[3] or ''}").strip() or "-"
        return f"{uname} | {name} | id={r[0]} | uses={r[4]}"

    lines = [f"{i}) {fmt(r)}" for i, r in enumerate(rows, start=1)]
    text = "🏆 TOP-30 foydalanuvchilar:\n" + ("\n".join(lines) if lines else "—")
    try:
        await bot.send_message(call.from_user.id, text)
    except Exception:
        pass

@dp.callback_query_handler(text="admin_active24")
async def cb_admin_active24(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer()
        return
    await call.answer()

    with db_connect() as con:
        rows = con.execute("""
            SELECT user_id, COALESCE(username,''), COALESCE(first_name,''), COALESCE(last_name,''), updated_at
            FROM users
            WHERE updated_at >= datetime('now','-24 hours')
            ORDER BY updated_at DESC
            LIMIT 30
        """).fetchall()

    def fmt(r):
        uname = f"@{r[1]}" if r[1] else "-"
        name = (f"{r[2] or ''} {r[3] or ''}").strip() or "-"
        return f"{uname} | {name} | id={r[0]} | updated={r[4]}"

    lines = [f"{i}) {fmt(r)}" for i, r in enumerate(rows, start=1)]
    text = "🟢 Oxirgi 24 soat aktivlar (max 30):\n" + ("\n".join(lines) if lines else "—")
    try:
        await bot.send_message(call.from_user.id, text)
    except Exception:
        pass

@dp.callback_query_handler(text="admin_new24")
async def cb_admin_new24(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer()
        return
    await call.answer()

    with db_connect() as con:
        rows = con.execute("""
            SELECT user_id, COALESCE(username,''), COALESCE(first_name,''), COALESCE(last_name,''), created_at
            FROM users
            WHERE created_at >= datetime('now','-24 hours')
            ORDER BY created_at DESC
            LIMIT 30
        """).fetchall()

    def fmt(r):
        uname = f"@{r[1]}" if r[1] else "-"
        name = (f"{r[2] or ''} {r[3] or ''}").strip() or "-"
        return f"{uname} | {name} | id={r[0]} | created={r[4]}"

    lines = [f"{i}) {fmt(r)}" for i, r in enumerate(rows, start=1)]
    text = "🆕 Oxirgi 24 soatda qo‘shilganlar (max 30):\n" + ("\n".join(lines) if lines else "—")
    try:
        await bot.send_message(call.from_user.id, text)
    except Exception:
        pass

@dp.callback_query_handler(text="admin_chart7")
async def cb_admin_chart7(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer()
        return
    await call.answer()

    try:
        data = daily_usage_totals(7)
        png = render_bar_chart_png(data, "📈 So‘nggi 7 kun foydalanish")
        await bot.send_photo(
            call.from_user.id,
            types.InputFile(io.BytesIO(png), filename="usage_7d.png"),
            caption="📈 7 kunlik foydalanish grafigi"
        )
    except Exception:
        pass

@dp.callback_query_handler(text="act_text_pdf")
async def cb_text_pdf(call: types.CallbackQuery):
    await call.answer()
    upsert_user(call.from_user)
    if not await enforce_rule_or_block(call.from_user.id):
        return

    set_state(call.from_user.id, STATE_WAIT_TEXT)
    try:
        await bot.send_message(call.from_user.id, "📝 Matn yuboring (PDF qilib qaytaraman).", reply_markup=kb_cancel())
    except Exception:
        pass

@dp.callback_query_handler(text="act_img_pdf")
async def cb_img_pdf(call: types.CallbackQuery):
    await call.answer()
    upsert_user(call.from_user)
    if not await enforce_rule_or_block(call.from_user.id):
        return

    set_state(call.from_user.id, STATE_WAIT_IMG_PDF)
    try:
        await bot.send_message(call.from_user.id, "🖼 Rasm yuboring.", reply_markup=kb_cancel())
    except Exception:
        pass

@dp.callback_query_handler(text="act_upscale")
async def cb_upscale(call: types.CallbackQuery):
    await call.answer()
    upsert_user(call.from_user)
    if not await enforce_rule_or_block(call.from_user.id):
        return

    set_state(call.from_user.id, STATE_WAIT_UPSCALE)
    try:
        await bot.send_message(call.from_user.id, "✨ Sifatini oshirish uchun rasm yuboring.", reply_markup=kb_cancel())
    except Exception:
        pass


@dp.callback_query_handler(text="act_merge_pdf")
async def cb_merge_pdf(call: types.CallbackQuery):
    await call.answer()
    upsert_user(call.from_user)
    if not await enforce_rule_or_block(call.from_user.id):
        return

    set_state(call.from_user.id, STATE_WAIT_PDF_MERGE)
    try:
        await bot.send_message(
            call.from_user.id,
            "📎 2 ta yoki undan ko‘p PDF yuboring (bitta faylga birlashtirib qaytaraman).",
            reply_markup=kb_cancel()
        )
    except Exception:
        pass

# ======================
#   MESSAGE HANDLERS
# ======================
@dp.message_handler(content_types=["text"])
async def on_text(message: types.Message):
    upsert_user(message.from_user)

    st = get_state(message.from_user.id)
    if st != STATE_WAIT_TEXT:
        return

    if not await enforce_rule_or_block(message.from_user.id):
        return

    text = (message.text or "").strip()
    if not text:
        return  # foydalanuvchiga xabar bermaymiz

    try:
        status = await message.answer("⏳ PDF tayyorlanmoqda...")
    except Exception:
        status = None

    try:
        pdf_bytes = make_text_pdf_bytes(text)
        file_name = f"text_{message.from_user.id}_{int(time.time())}.pdf"
        await bot.send_document(
            message.from_user.id,
            types.InputFile(io.BytesIO(pdf_bytes), filename=file_name),
            caption="✅ Tayyor!"
        )
        inc_uses_and_log(message.from_user.id, "text_pdf")
    except Exception:
        # foydalanuvchiga xato ko‘rsatmaymiz
        pass
    finally:
        if status:
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

    try:
        photo = message.photo[-1]
        file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{photo.file_id}.jpg")
        await photo.download(destination=file_path)  # aiogram v2.25.1
    except Exception:
        return

    # ===== UPSCALE MODE =====
    if st == STATE_WAIT_UPSCALE:
        try:
            status = await message.answer("⏳ Sifat oshirilmoqda...")
        except Exception:
            status = None

        out_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{photo.file_id}_up.jpg")
        try:
            ok = try_realesrgan(file_path, out_path)
            if not ok:
                pillow_upscale_2x(file_path, out_path)

            with open(out_path, "rb") as f:
                await bot.send_photo(user_id, f, caption="✅ Tayyor!")
            inc_uses_and_log(user_id, "upscale")
        except Exception:
            pass
        finally:
            safe_remove(file_path)
            safe_remove(out_path)
            if status:
                try:
                    await bot.delete_message(user_id, status.message_id)
                except Exception:
                    pass

        await show_main_menu(user_id)
        return

    # ===== IMG PDF MODE =====
    if message.media_group_id:
        key = (user_id, message.media_group_id)
        MEDIA_BUFFER.setdefault(key, []).append(file_path)

        old_task = MEDIA_TASK.get(key)
        if old_task and not old_task.done():
            old_task.cancel()

        async def finalize_group():
            await asyncio.sleep(1.2)
            paths = MEDIA_BUFFER.pop(key, [])
            MEDIA_TASK.pop(key, None)
            if not paths:
                return

            try:
                status = await bot.send_message(user_id, "⏳ PDF tayyorlanmoqda...")
            except Exception:
                status = None

            pdf_path = os.path.join(DOWNLOAD_DIR, f"images_{user_id}_{int(time.time())}.pdf")
            try:
                images_to_pdf(paths, pdf_path)
                with open(pdf_path, "rb") as f:
                    await bot.send_document(user_id, f, caption="✅ Tayyor!")
                inc_uses_and_log(user_id, "img_pdf")
            except Exception:
                pass
            finally:
                for p in paths:
                    safe_remove(p)
                safe_remove(pdf_path)
                if status:
                    try:
                        await bot.delete_message(user_id, status.message_id)
                    except Exception:
                        pass

            await show_main_menu(user_id)

        MEDIA_TASK[key] = asyncio.create_task(finalize_group())
        return

    try:
        status = await message.answer("⏳ PDF tayyorlanmoqda...")
    except Exception:
        status = None

    pdf_path = os.path.join(DOWNLOAD_DIR, f"image_{user_id}_{int(time.time())}.pdf")
    try:
        images_to_pdf([file_path], pdf_path)
        with open(pdf_path, "rb") as f:
            await bot.send_document(user_id, f, caption="✅ Tayyor!")
        inc_uses_and_log(user_id, "img_pdf")
    except Exception:
        pass
    finally:
        safe_remove(file_path)
        safe_remove(pdf_path)
        if status:
            try:
                await bot.delete_message(user_id, status.message_id)
            except Exception:
                pass

    await show_main_menu(user_id)


@dp.message_handler(content_types=["document"])
async def on_document(message: types.Message):
    upsert_user(message.from_user)
    user_id = message.from_user.id
    st = get_state(user_id)

    if st != STATE_WAIT_PDF_MERGE:
        return

    if not await enforce_rule_or_block(user_id):
        return

    doc = message.document
    if not doc:
        return

    if doc.mime_type != "application/pdf" and not (doc.file_name or "").lower().endswith(".pdf"):
        try:
            await message.answer("Faqat PDF yuboring.", reply_markup=kb_cancel())
        except Exception:
            pass
        return

    try:
        file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{doc.file_id}.pdf")
        await doc.download(destination_file=file_path)
    except Exception:
        return

    group_id = message.media_group_id or "pdfmerge"
    key = (user_id, str(group_id))
    MEDIA_BUFFER.setdefault(key, []).append(file_path)

    old_task = MEDIA_TASK.get(key)
    if old_task and not old_task.done():
        old_task.cancel()

    async def finalize_pdf_group():
        await asyncio.sleep(1.2)
        paths = MEDIA_BUFFER.pop(key, [])
        MEDIA_TASK.pop(key, None)
        if not paths:
            return

        if len(paths) < 2:
            for p in paths:
                safe_remove(p)
            try:
                await bot.send_message(user_id, "Iltimos, kamida 2 ta PDF yuboring.", reply_markup=kb_cancel())
            except Exception:
                pass
            return

        try:
            status = await bot.send_message(user_id, "⏳ PDFlar birlashtirilmoqda...")
        except Exception:
            status = None

        out_pdf = os.path.join(DOWNLOAD_DIR, f"merged_{user_id}_{int(time.time())}.pdf")
        try:
            merge_pdfs(paths, out_pdf)
            with open(out_pdf, "rb") as f:
                await bot.send_document(user_id, f, caption="✅ Tayyor!")
            inc_uses_and_log(user_id, "pdf_merge")
        except Exception:
            pass
        finally:
            for p in paths:
                safe_remove(p)
            safe_remove(out_pdf)
            if status:
                try:
                    await bot.delete_message(user_id, status.message_id)
                except Exception:
                    pass

        await show_main_menu(user_id)

    MEDIA_TASK[key] = asyncio.create_task(finalize_pdf_group())


# ======================
#   STARTUP
# ======================
async def on_startup(_dp: Dispatcher):
    db_init()
    # cleanup worker
    asyncio.create_task(cleanup_worker())

if __name__ == "__main__":
    print("Bot ishga tushdi...")
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)