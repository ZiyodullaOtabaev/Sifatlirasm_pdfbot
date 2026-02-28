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

# ======================
#   ENV / SETTINGS
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL_USER = os.getenv("CHANNEL_USER", "@xonziyy").strip()
FREE_USES_BEFORE_SUB = int((os.getenv("FREE_USES_BEFORE_SUB", "15").strip() or "15"))  # 10 -> 15

REAL_ESRGAN_BIN = os.getenv("REAL_ESRGAN_BIN", "").strip()
REAL_ESRGAN_MODELS = os.getenv("REAL_ESRGAN_MODELS", "").strip()
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

def stats_top_users(limit: int = 15):
    with db_connect() as con:
        return con.execute("""
        SELECT user_id, username, first_name, last_name, uses_count, created_at
        FROM users
        ORDER BY uses_count DESC, updated_at DESC
        LIMIT ?
        """, (limit,)).fetchall()

def stats_last_users(limit: int = 10):
    with db_connect() as con:
        return con.execute("""
        SELECT user_id, username, first_name, last_name, uses_count, created_at
        FROM users
        ORDER BY datetime(created_at) DESC
        LIMIT ?
        """, (limit,)).fetchall()

# ======================
#   STATE (in-memory)
# ======================
STATE_NONE = "none"
STATE_WAIT_TEXT = "wait_text"
STATE_WAIT_IMG_PDF = "wait_img_pdf"
STATE_WAIT_UPSCALE = "wait_upscale"
STATE_WAIT_PDF_MERGE = "wait_pdf_merge"

USER_STATE: Dict[int, str] = {}

# photo buffering (media group)
MEDIA_BUFFER: Dict[Tuple[int, str], List[str]] = {}
MEDIA_TASK: Dict[Tuple[int, str], asyncio.Task] = {}

# pdf merge buffering (no media_group for documents reliably)
PDF_BUFFER: Dict[int, List[str]] = {}
PDF_TASK: Dict[int, asyncio.Task] = {}

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
        InlineKeyboardButton("🧩 PDFlarni bitta qilish", callback_data="act_pdf_merge"),
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
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USER, user_id=user_id)
        return member.status != "left"
    except Exception:
        return True

async def enforce_rule_or_block(user_id: int) -> bool:
    uses = get_uses(user_id)
    if uses < FREE_USES_BEFORE_SUB:
        return True

    ok = await check_sub(user_id)
    if ok:
        return True

    await bot.send_message(
        user_id,
        f"Siz xizmatimizdan {FREE_USES_BEFORE_SUB} marta foydalandingiz.\n"
        "Yana foydalanish uchun kanalimizga obuna bo‘ling 👇",
        reply_markup=kb_subscribe()
    )
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
        raise RuntimeError("Rasm topilmadi")

    first, rest = imgs[0], imgs[1:]
    first.save(out_pdf_path, save_all=True, append_images=rest)

def merge_pdfs(pdf_paths: List[str], out_pdf_path: str):
    # pypdf preferred; fallback PyPDF2 if installed
    try:
        from pypdf import PdfMerger
    except Exception:
        from PyPDF2 import PdfMerger  # type: ignore

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

@dp.message_handler(commands=["admin"])
async def cmd_admin(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    upsert_user(message.from_user)

    tu = stats_total_users()
    ts = stats_total_uses()

    top15 = stats_top_users(15)
    last10 = stats_last_users(10)

    top_lines = []
    for i, r in enumerate(top15, 1):
        uname = f"@{r['username']}" if r["username"] else "-"
        name = (f"{r['first_name'] or ''} {r['last_name'] or ''}").strip() or "-"
        top_lines.append(f"{i}) {uname} | {name} | uses={r['uses_count']} | id={r['user_id']}")

    last_lines = []
    for i, r in enumerate(last10, 1):
        uname = f"@{r['username']}" if r["username"] else "-"
        created = r["created_at"] or "-"
        last_lines.append(f"{i}) {uname} | {created} | id={r['user_id']}")

    text = (
        "📊 Admin statistika\n\n"
        f"👥 Jami foydalanuvchi: {tu}\n"
        f"⚡️ Jami foydalanish: {ts}\n\n"
        "🏆 TOP-15:\n" + ("\n".join(top_lines) if top_lines else "—") + "\n\n"
        "🆕 Oxirgi qo‘shilgan 10 ta:\n" + ("\n".join(last_lines) if last_lines else "—")
    )
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
    await bot.send_message(call.from_user.id, "🖼 Rasm yuboring.", reply_markup=kb_cancel())

@dp.callback_query_handler(text="act_upscale")
async def cb_upscale(call: types.CallbackQuery):
    await call.answer()
    upsert_user(call.from_user)
    if not await enforce_rule_or_block(call.from_user.id):
        return
    set_state(call.from_user.id, STATE_WAIT_UPSCALE)
    await bot.send_message(call.from_user.id, "✨ Sifatini oshirish uchun rasm yuboring.", reply_markup=kb_cancel())

@dp.callback_query_handler(text="act_pdf_merge")
async def cb_pdf_merge(call: types.CallbackQuery):
    await call.answer()
    upsert_user(call.from_user)
    if not await enforce_rule_or_block(call.from_user.id):
        return
    set_state(call.from_user.id, STATE_WAIT_PDF_MERGE)
    PDF_BUFFER.pop(call.from_user.id, None)
    t = PDF_TASK.get(call.from_user.id)
    if t and not t.done():
        t.cancel()
    await bot.send_message(call.from_user.id, "🧩 2 ta yoki undan ko‘p PDF yuboring (bittaga birlashtiraman).", reply_markup=kb_cancel())

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

    photo = message.photo[-1]
    file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{photo.file_id}.jpg")
    await photo.download(destination=file_path)

    # ===== UPSCALE MODE =====
    if st == STATE_WAIT_UPSCALE:
        status = await message.answer("⏳ Sifat oshirilmoqda...")
        out_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{photo.file_id}_up.jpg")
        try:
            ok = try_realesrgan(file_path, out_path)
            if not ok:
                pillow_upscale_2x(file_path, out_path)

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

            status2 = await bot.send_message(user_id, "⏳ PDF tayyorlanmoqda...")
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
                    await bot.delete_message(user_id, status2.message_id)
                except Exception:
                    pass

            await show_main_menu(user_id)

        MEDIA_TASK[key] = asyncio.create_task(finalize_group())
        return

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
    if not doc or (doc.mime_type != "application/pdf"):
        await message.answer("Iltimos, faqat PDF fayl yuboring.", reply_markup=kb_cancel())
        return

    file_path = os.path.join(DOWNLOAD_DIR, f"pdf_{user_id}_{doc.file_id}.pdf")
    await doc.download(destination=file_path)

    PDF_BUFFER.setdefault(user_id, []).append(file_path)

    old_task = PDF_TASK.get(user_id)
    if old_task and not old_task.done():
        old_task.cancel()

    async def finalize_pdf_merge():
        await asyncio.sleep(1.5)
        paths = PDF_BUFFER.get(user_id, [])
        if len(paths) < 2:
            # kamida 2 ta kutamiz (state o‘zgarmaydi)
            await bot.send_message(user_id, "Yana PDF yuboring (kamida 2 ta kerak).", reply_markup=kb_cancel())
            return

        status = await bot.send_message(user_id, "⏳ PDFlar birlashtirilmoqda...")
        out_pdf = os.path.join(DOWNLOAD_DIR, f"merged_{user_id}_{int(time.time())}.pdf")
        try:
            merge_pdfs(paths, out_pdf)
            with open(out_pdf, "rb") as f:
                await bot.send_document(user_id, f, caption="✅ Tayyor!")
            inc_uses_and_log(user_id, "pdf_merge")
        except Exception as e:
            await bot.send_message(user_id, f"❌ Xato: {e}")
        finally:
            for p in paths:
                safe_remove(p)
            safe_remove(out_pdf)
            PDF_BUFFER.pop(user_id, None)
            try:
                await bot.delete_message(user_id, status.message_id)
            except Exception:
                pass

        await show_main_menu(user_id)

    PDF_TASK[user_id] = asyncio.create_task(finalize_pdf_merge())

# ======================
#   BOOT
# ======================
if __name__ == "__main__":
    db_init()
    print("Bot ishga tushdi...")
    executor.start_polling(dp, skip_updates=True)