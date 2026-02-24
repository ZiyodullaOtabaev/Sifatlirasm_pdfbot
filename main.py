import os
import io
import time
import sqlite3
import asyncio
import subprocess
from typing import List, Dict, Optional

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

# Local dev uchun (.env bo'lsa o'qiydi). Alwaysdata-da shart emas.
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# =====================
#   ENV / SETTINGS
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL_USER = os.getenv("CHANNEL_USER", "@xonziyy").strip()  # @username
FREE_USES = int(os.getenv("FREE_USES", "10"))
DB_PATH = os.getenv("DB_PATH", "data/bot.db").strip()

# Real-ESRGAN (optional)
REALESRGAN_BIN = os.getenv("REALESRGAN_BIN", "/home/ziyodulla/apps/realesrgan-ncnn-vulkan").strip()
REALESRGAN_MODELS_DIR = os.getenv("REALESRGAN_MODELS_DIR", "/home/ziyodulla/apps/models").strip()
REALESRGAN_MODEL_NAME = os.getenv("REALESRGAN_MODEL_NAME", "realesrgan-x4plus").strip()  # or realesrgan-x4plus-anime
REALESRGAN_SCALE = int(os.getenv("REALESRGAN_SCALE", "2"))

DOWNLOAD_DIR = "downloads"
DATA_DIR = "data"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi. Alwaysdata Services -> Environment ga BOT_TOKEN=... qo'ying.")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# =====================
#   DB (usage counter)
# =====================
def db_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    with db_conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS usage (
                user_id INTEGER PRIMARY KEY,
                used_count INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL DEFAULT 0
            )
        """)
        con.commit()

def get_used(user_id: int) -> int:
    with db_conn() as con:
        cur = con.execute("SELECT used_count FROM usage WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return int(row[0]) if row else 0

def inc_used(user_id: int, step: int = 1) -> int:
    now = int(time.time())
    with db_conn() as con:
        con.execute("""
            INSERT INTO usage(user_id, used_count, updated_at)
            VALUES(?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                used_count = used_count + ?,
                updated_at = ?
        """, (user_id, step, now, step, now))
        con.commit()
    return get_used(user_id)

init_db()

# =====================
#   IN-MEM STATE (last text / last photos)
# =====================
LAST_TEXT_BY_USER: Dict[int, str] = {}
LAST_PHOTOS_BY_USER: Dict[int, List[str]] = {}  # list of local file paths

# Media-group (album) yig'ish
ALBUM_CACHE: Dict[str, List[types.Message]] = {}
ALBUM_TASKS: Dict[str, asyncio.Task] = {}

# =====================
#   UI: KEYBOARDS
# =====================
def main_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📝 Matnni PDF qilish", callback_data="make_text_pdf"),
        InlineKeyboardButton("📄 Rasmni PDF qilish", callback_data="make_img_pdf"),
        InlineKeyboardButton("✨ Sifatni oshirish", callback_data="upscale"),
    )
    return kb

def subscribe_kb() -> InlineKeyboardMarkup:
    # Faqat 1 tugma: kanalga olib boradi
    url = f"https://t.me/{CHANNEL_USER.lstrip('@')}"
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("📢 Kanalga obuna bo‘lish", url=url))
    return kb

# =====================
#   HELPERS
# =====================
async def is_subscribed(user_id: int) -> bool:
    """
    Kanalga a'zolikni tekshiradi.
    Bot kanalda admin bo'lsa, status aniq keladi.
    """
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USER, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        # agar bot admin bo'lmasa yoki xatolik bo'lsa: bloklamaymiz
        return True

async def can_use(user_id: int) -> bool:
    """
    Qoidasi:
    - Agar kanalga obuna bo'lgan bo'lsa: cheksiz
    - Aks holda: 10 marta (FREE_USES) ishlatadi, keyin blok
    """
    if await is_subscribed(user_id):
        return True
    used = get_used(user_id)
    return used < FREE_USES

async def require_subscribe_message(user_id: int):
    await bot.send_message(
        user_id,
        f"❌ Siz xizmatimizdan {FREE_USES} marta foydalandingiz.\n"
        f"Yana foydalanish uchun kanalimizga obuna bo‘ling: {CHANNEL_USER}",
        reply_markup=subscribe_kb()
    )

def safe_remove(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

def images_to_pdf(image_paths: List[str], pdf_path: str):
    imgs = []
    for p in image_paths:
        img = Image.open(p).convert("RGB")
        imgs.append(img)
    if not imgs:
        raise RuntimeError("Rasm topilmadi.")
    first, rest = imgs[0], imgs[1:]
    first.save(pdf_path, save_all=True, append_images=rest)

def text_to_pdf(text: str, pdf_path: str):
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    left = 15 * mm
    top = height - 20 * mm
    line_h = 6 * mm
    max_width = width - 30 * mm

    # Oddiy wrap (reportlab uchun sodda)
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        if c.stringWidth(test, "Helvetica", 12) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)

    y = top
    c.setFont("Helvetica", 12)
    for line in lines:
        if y < 20 * mm:
            c.showPage()
            c.setFont("Helvetica", 12)
            y = top
        c.drawString(left, y, line)
        y -= line_h

    c.save()

def pil_upscale(input_path: str, output_path: str, scale: int = 2):
    img = Image.open(input_path)
    new_size = (img.width * scale, img.height * scale)
    up = img.resize(new_size, Image.LANCZOS)
    up.save(output_path, quality=95, optimize=True)

def try_realesrgan(input_path: str, output_path: str) -> Optional[str]:
    """
    Real-ESRGAN urinamiz.
    Agar serverda Vulkan/GPU bo'lmasa, xato qaytadi.
    """
    if not (os.path.exists(REALESRGAN_BIN) and os.access(REALESRGAN_BIN, os.X_OK)):
        return "realesrgan binary topilmadi"

    if not os.path.isdir(REALESRGAN_MODELS_DIR):
        return "realesrgan models papkasi topilmadi"

    cmd = [
        REALESRGAN_BIN,
        "-i", input_path,
        "-o", output_path,
        "-s", str(REALESRGAN_SCALE),
        "-n", REALESRGAN_MODEL_NAME,
        "-m", REALESRGAN_MODELS_DIR,
    ]
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120)
        if p.returncode != 0:
            # stderr ichida vkCreateInstance failed chiqadi
            return (p.stderr.strip() or "realesrgan error")
        return None
    except Exception as e:
        return str(e)

# =====================
#   HANDLERS
# =====================
@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    text = (
        "Salom! 👋\n\n"
        "📌 Rasm yoki matnlaringizni PDF qiling va rasmlaringiz sifatini oshiring.\n\n"
        "Quyidagi tugmalardan birini tanlang:"
    )
    await message.answer(text, reply_markup=main_menu_kb())

@dp.message_handler(content_types=["text"])
async def text_handler(message: types.Message):
    # faqat matnni saqlaymiz, hali limitni yemaymiz
    LAST_TEXT_BY_USER[message.from_user.id] = message.text.strip()
    await message.reply("Matn qabul qilindi. Endi menyudan tanlang:", reply_markup=main_menu_kb())

@dp.message_handler(content_types=["photo"])
async def photo_handler(message: types.Message):
    """
    1 ta rasm bo'lsa ham, album bo'lsa ham ishlaydi.
    Album bo'lsa message.media_group_id bo'ladi.
    """
    user_id = message.from_user.id

    # Album bo'lsa yig'amiz
    if message.media_group_id:
        gid = str(message.media_group_id)
        ALBUM_CACHE.setdefault(gid, []).append(message)

        # avvalgi task bo'lsa bekor qilamiz
        if gid in ALBUM_TASKS and not ALBUM_TASKS[gid].done():
            ALBUM_TASKS[gid].cancel()

        async def _flush():
            await asyncio.sleep(1.0)  # albumdagi qolgan rasmlar ham kelib ulguradi
            msgs = ALBUM_CACHE.pop(gid, [])
            if not msgs:
                return

            paths: List[str] = []
            for m in msgs:
                photo = m.photo[-1]
                fp = os.path.join(DOWNLOAD_DIR, f"{user_id}_{photo.file_id}.jpg")
                await photo.download(destination=fp)
                paths.append(fp)

            LAST_PHOTOS_BY_USER[user_id] = paths
            await bot.send_message(
                user_id,
                "Rasmlar qabul qilindi! Menyudan tanlang:",
                reply_markup=main_menu_kb()
            )

        ALBUM_TASKS[gid] = asyncio.create_task(_flush())
        return

    # Oddiy 1 ta rasm
    photo = message.photo[-1]
    fp = os.path.join(DOWNLOAD_DIR, f"{user_id}_{photo.file_id}.jpg")
    await photo.download(destination=fp)
    LAST_PHOTOS_BY_USER[user_id] = [fp]
    await message.reply("Rasm qabul qilindi! Menyudan tanlang:", reply_markup=main_menu_kb())

# =====================
#   CALLBACKS (ACTIONS)
# =====================
@dp.callback_query_handler(text="make_text_pdf")
async def cb_text_pdf(call: types.CallbackQuery):
    user_id = call.from_user.id

    if not await can_use(user_id):
        await require_subscribe_message(user_id)
        await call.answer()
        return

    text = LAST_TEXT_BY_USER.get(user_id, "").strip()
    if not text:
        await call.answer("Avval matn yuboring!", show_alert=True)
        return

    # limitni shu yerda yeymiz
    inc_used(user_id, 1)

    pdf_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_text.pdf")
    try:
        text_to_pdf(text, pdf_path)
        with open(pdf_path, "rb") as f:
            await bot.send_document(user_id, f, caption="✅ Matn PDF tayyor!")
    except Exception as e:
        await bot.send_message(user_id, f"Xato: {e}")
    finally:
        safe_remove(pdf_path)
        LAST_TEXT_BY_USER.pop(user_id, None)

    await call.answer()

@dp.callback_query_handler(text="make_img_pdf")
async def cb_img_pdf(call: types.CallbackQuery):
    user_id = call.from_user.id

    if not await can_use(user_id):
        await require_subscribe_message(user_id)
        await call.answer()
        return

    paths = LAST_PHOTOS_BY_USER.get(user_id, [])
    paths = [p for p in paths if os.path.exists(p)]
    if not paths:
        await call.answer("Avval rasm yuboring!", show_alert=True)
        return

    inc_used(user_id, 1)

    pdf_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_images.pdf")
    try:
        images_to_pdf(paths, pdf_path)
        with open(pdf_path, "rb") as f:
            await bot.send_document(user_id, f, caption="✅ PDF tayyor!")
    except Exception as e:
        await bot.send_message(user_id, f"Xato: {e}")
    finally:
        for p in paths:
            safe_remove(p)
        safe_remove(pdf_path)
        LAST_PHOTOS_BY_USER.pop(user_id, None)

    await call.answer()

@dp.callback_query_handler(text="upscale")
async def cb_upscale(call: types.CallbackQuery):
    user_id = call.from_user.id

    if not await can_use(user_id):
        await require_subscribe_message(user_id)
        await call.answer()
        return

    paths = LAST_PHOTOS_BY_USER.get(user_id, [])
    paths = [p for p in paths if os.path.exists(p)]
    if not paths:
        await call.answer("Avval rasm yuboring!", show_alert=True)
        return

    # Faqat oxirgi rasmni upscale qilamiz (xohlasang keyin hammasini qilamiz)
    input_path = paths[-1]
    out_path = input_path.rsplit(".", 1)[0] + "_up.jpg"

    inc_used(user_id, 1)

    status = await bot.send_message(user_id, "✨ Sifat oshirilmoqda... (AI bo‘lsa AI, bo‘lmasa oddiy usul)")

    try:
        err = try_realesrgan(input_path, out_path)
        if err is not None:
            # fallback
            pil_upscale(input_path, out_path, scale=2)
            await bot.send_message(user_id, f"⚠️ AI ishlamadi, oddiy usul ishlatildi.\nSabab: {err}")

        with open(out_path, "rb") as f:
            await bot.send_photo(user_id, f, caption="✅ Tayyor!")
    except Exception as e:
        await bot.send_message(user_id, f"Xato: {e}")
    finally:
        await bot.delete_message(user_id, status.message_id)
        # fayllarni tozalaymiz
        for p in paths:
            safe_remove(p)
        safe_remove(out_path)
        LAST_PHOTOS_BY_USER.pop(user_id, None)

    await call.answer()

if __name__ == "__main__":
    print("Bot ishga tushdi...")
    executor.start_polling(dp, skip_updates=True)