# import os
# from aiogram import Bot, Dispatcher, executor, types
# from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
# from PIL import Image, ImageFilter, ImageEnhance
#
# # =========================
# #   ENVIRONMENT VARIABLES
# # =========================
#
# BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
# CHANNEL_USER = os.getenv("CHANNEL_USER", "@xonziyy").strip()
#
# if not BOT_TOKEN:
#     raise RuntimeError("BOT_TOKEN topilmadi! Alwaysdata -> Services -> Environment ga qo'ying.")
#
# bot = Bot(token=BOT_TOKEN)
# dp = Dispatcher(bot)
#
# DOWNLOAD_DIR = "downloads"
# os.makedirs(DOWNLOAD_DIR, exist_ok=True)
#
# LAST_PHOTO_BY_USER = {}
#
# # =========================
# #   HELPER FUNCTIONS
# # =========================
#
# async def check_sub(user_id: int) -> bool:
#     try:
#         member = await bot.get_chat_member(chat_id=CHANNEL_USER, user_id=user_id)
#         return member.status != "left"
#     except Exception:
#         return True
#
#
# def get_action_keyboard():
#     kb = InlineKeyboardMarkup(row_width=2)
#     kb.add(
#         InlineKeyboardButton("📄 PDF qilish", callback_data="make_pdf"),
#         InlineKeyboardButton("✨ Sifatni oshirish", callback_data="upscale"),
#     )
#     return kb
#
#
# def safe_remove(path):
#     try:
#         if path and os.path.exists(path):
#             os.remove(path)
#     except:
#         pass
#
#
# # =========================
# #   FREE UPSCALE (NO AI)
# # =========================
#
# def upscale_image(input_path, output_path, scale=2):
#     img = Image.open(input_path).convert("RGB")
#
#     # 1️⃣ Resize (High quality)
#     up = img.resize((img.width * scale, img.height * scale), Image.LANCZOS)
#
#     # 2️⃣ Sharpen (AIga o‘xshash effekt)
#     up = up.filter(ImageFilter.UnsharpMask(radius=2, percent=180, threshold=3))
#
#     # 3️⃣ Contrast ozgina oshiramiz
#     up = ImageEnhance.Contrast(up).enhance(1.08)
#
#     # 4️⃣ Save with max quality
#     up.save(output_path, quality=95, optimize=True)
#
#
# # =========================
# #   HANDLERS
# # =========================
#
# @dp.message_handler(commands=["start"])
# async def start(message: types.Message):
#     await message.reply(
#         f"Salom! Botdan foydalanish uchun {CHANNEL_USER} kanaliga a'zo bo‘ling va rasm yuboring."
#     )
#
#
# @dp.message_handler(content_types=["photo"])
# async def handle_photo(message: types.Message):
#
#     if not await check_sub(message.from_user.id):
#         await message.answer(f"❌ Kanalga a'zo bo‘ling: {CHANNEL_USER}")
#         return
#
#     photo = message.photo[-1]
#     user_id = message.from_user.id
#
#     file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}.jpg")
#     await photo.download(destination=file_path)
#
#     LAST_PHOTO_BY_USER[user_id] = file_path
#
#     await message.reply("Rasm qabul qilindi!", reply_markup=get_action_keyboard())
#
#
# @dp.callback_query_handler(text="make_pdf")
# async def make_pdf(callback: types.CallbackQuery):
#     user_id = callback.from_user.id
#     file = LAST_PHOTO_BY_USER.get(user_id)
#
#     if not file or not os.path.exists(file):
#         await callback.answer("Rasm topilmadi!", show_alert=True)
#         return
#
#     pdf_path = file.replace(".jpg", ".pdf")
#
#     img = Image.open(file)
#     img.convert("RGB").save(pdf_path)
#
#     with open(pdf_path, "rb") as f:
#         await bot.send_document(user_id, f, caption="✅ PDF tayyor!")
#
#     safe_remove(file)
#     safe_remove(pdf_path)
#     LAST_PHOTO_BY_USER.pop(user_id, None)
#
#     await callback.answer()
#
#
# @dp.callback_query_handler(text="upscale")
# async def upscale(callback: types.CallbackQuery):
#
#     user_id = callback.from_user.id
#     file = LAST_PHOTO_BY_USER.get(user_id)
#
#     if not file or not os.path.exists(file):
#         await callback.answer("Rasm topilmadi!", show_alert=True)
#         return
#
#     status = await bot.send_message(user_id, "⏳ Sifat oshirilmoqda...")
#
#     output_path = file.replace(".jpg", "_upscaled.jpg")
#
#     upscale_image(file, output_path)
#
#     with open(output_path, "rb") as f:
#         await bot.send_photo(user_id, f, caption="✨ Sifat oshirildi!")
#
#     await bot.delete_message(user_id, status.message_id)
#
#     safe_remove(file)
#     safe_remove(output_path)
#     LAST_PHOTO_BY_USER.pop(user_id, None)
#
#     await callback.answer()
#
#
# # =========================
# #   RUN BOT
# # =========================
#
# if __name__ == "__main__":
#     print("Bot ishga tushdi...")
#     executor.start_polling(dp, skip_updates=True)


import os
import time
import sqlite3
import asyncio
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv()

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image, ImageFilter, ImageEnhance
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

# =========================
#   ENV
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL_USER = os.getenv("CHANNEL_USER", "@xonziyy").strip()
FREE_USES_BEFORE_SUB = int(os.getenv("FREE_USES_BEFORE_SUB", "10").strip())

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi! Alwaysdata -> Services -> Environment (yoki .env) ga qo'ying.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

DB_PATH = os.path.join(BASE_DIR, "bot.db")

# Har user uchun oxirgi bitta rasm / matn
LAST_PHOTO_BY_USER = {}
LAST_TEXT_BY_USER = {}

# Media group (album) uchun buffer
GROUP_FILES = defaultdict(list)          # key=(user_id, media_group_id) -> [filepaths]
GROUP_LAST_SEEN = {}                    # key -> timestamp
GROUP_FINALIZE_TASKS = {}               # key -> asyncio.Task

# =========================
#   DB HELPERS
# =========================
def db_init():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            uses INTEGER NOT NULL DEFAULT 0
        )
    """)
    con.commit()
    con.close()

def db_get_uses(user_id: int) -> int:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT uses FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if row is None:
        cur.execute("INSERT INTO users(user_id, uses) VALUES(?, 0)", (user_id,))
        con.commit()
        con.close()
        return 0
    con.close()
    return int(row[0])

def db_inc_uses(user_id: int, inc: int = 1):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("INSERT INTO users(user_id, uses) VALUES(?, 0) ON CONFLICT(user_id) DO NOTHING", (user_id,))
    cur.execute("UPDATE users SET uses = uses + ? WHERE user_id=?", (inc, user_id))
    con.commit()
    con.close()

# =========================
#   UTILS
# =========================
async def check_sub(user_id: int) -> bool:
    """Kanalga a'zolikni tekshiradi (bot kanalda admin bo‘lishi kerak)."""
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USER, user_id=user_id)
        return member.status != "left"
    except Exception:
        # bot admin bo'lmasa yoki xatolik bo'lsa - bloklamaymiz (xohlasangiz False qiling)
        return True

async def is_allowed(user_id: int) -> (bool, str):
    """10 marta ishlatgandan keyin obuna majburiy."""
    uses = db_get_uses(user_id)
    if uses < FREE_USES_BEFORE_SUB:
        left = FREE_USES_BEFORE_SUB - uses
        return True, f"✅ Sizda obunasiz {left} ta bepul urinish qoldi."
    # 10+ bo‘lsa obuna shart
    if not await check_sub(user_id):
        return False, f"❌ Botdan foydalanish uchun {CHANNEL_USER} kanaliga a’zo bo‘ling."
    return True, "✅ Rahmat! Siz obunachisiz."

def safe_remove(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except:
        pass

def kb_actions_for_photo():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📄 PDF qilish", callback_data="make_pdf"),
        InlineKeyboardButton("✨ Sifatni oshirish", callback_data="upscale"),
    )
    return kb

def kb_actions_for_text():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("📝 Matnni PDF qilish", callback_data="text_to_pdf"))
    return kb

def upscale_image(input_path, output_path, scale=2):
    img = Image.open(input_path).convert("RGB")
    up = img.resize((img.width * scale, img.height * scale), Image.LANCZOS)
    up = up.filter(ImageFilter.UnsharpMask(radius=2, percent=180, threshold=3))
    up = ImageEnhance.Contrast(up).enhance(1.08)
    up.save(output_path, quality=95, optimize=True)

def images_to_one_pdf(image_paths, pdf_path):
    imgs = []
    for p in image_paths:
        im = Image.open(p).convert("RGB")
        imgs.append(im)
    if not imgs:
        raise RuntimeError("Rasm topilmadi.")
    first, rest = imgs[0], imgs[1:]
    first.save(pdf_path, save_all=True, append_images=rest)

def text_to_pdf_file(text: str, pdf_path: str, title: str = "Document"):
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    margin = 15 * mm
    y = height - margin

    c.setTitle(title)
    c.setFont("Helvetica", 12)

    # Simple word wrap
    max_width = width - 2 * margin
    words = (text or "").split()
    line = ""
    lines = []

    for w in words:
        test = (line + " " + w).strip()
        if c.stringWidth(test, "Helvetica", 12) <= max_width:
            line = test
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)

    for ln in lines:
        if y < margin:
            c.showPage()
            c.setFont("Helvetica", 12)
            y = height - margin
        c.drawString(margin, y, ln)
        y -= 6 * mm

    c.save()

# =========================
#   MEDIA GROUP HANDLING
# =========================
async def finalize_media_group(key):
    """1-2 soniya ichida group kelishi tugasa, bitta PDF qilib yuboradi."""
    await asyncio.sleep(1.2)  # group messages kelishi tugashini kutamiz
    # agar oxirgi seen yaqinda yangilangan bo‘lsa, yana kutamiz
    last_seen = GROUP_LAST_SEEN.get(key, 0)
    if time.time() - last_seen < 1.0:
        # yana biroz kutib qayta finalize qilamiz
        await asyncio.sleep(1.2)

    user_id, group_id = key
    files = GROUP_FILES.get(key, [])
    if not files:
        return

    allowed, msg = await is_allowed(user_id)
    if not allowed:
        await bot.send_message(user_id, msg)
        # cleanup
        for f in files:
            safe_remove(f)
        GROUP_FILES.pop(key, None)
        return

    pdf_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{group_id}.pdf")
    try:
        images_to_one_pdf(files, pdf_path)
        with open(pdf_path, "rb") as f:
            await bot.send_document(user_id, f, caption="✅ Barcha rasmlar bitta PDF ichida!")
        db_inc_uses(user_id, 1)
    except Exception as e:
        await bot.send_message(user_id, f"Xato (PDF): {e}")
    finally:
        for f in files:
            safe_remove(f)
        safe_remove(pdf_path)
        GROUP_FILES.pop(key, None)
        GROUP_LAST_SEEN.pop(key, None)
        GROUP_FINALIZE_TASKS.pop(key, None)

# =========================
#   HANDLERS
# =========================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.reply(
        f"Salom! Rasm yuboring yoki matn yuboring.\n"
        f"⚙️ Qoidalar: {FREE_USES_BEFORE_SUB} marta bepul, keyin {CHANNEL_USER} kanaliga obuna shart."
    )

@dp.message_handler(content_types=["text"])
async def handle_text(message: types.Message):
    if message.text.startswith("/"):
        return

    user_id = message.from_user.id
    allowed, info = await is_allowed(user_id)
    if not allowed:
        await message.answer(info)
        return

    LAST_TEXT_BY_USER[user_id] = message.text
    await message.reply("Matn qabul qilindi. PDF qilamizmi?", reply_markup=kb_actions_for_text())

@dp.message_handler(content_types=["photo"])
async def handle_photo(message: types.Message):
    user_id = message.from_user.id

    # Media group bo‘lsa: hammasini yig‘amiz va bitta PDF qilamiz
    if message.media_group_id:
        group_id = message.media_group_id
        key = (user_id, group_id)

        photo = message.photo[-1]
        file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{group_id}_{photo.file_id}.jpg")
        await photo.download(destination=file_path)

        GROUP_FILES[key].append(file_path)
        GROUP_LAST_SEEN[key] = time.time()

        # finalize taskni bir marta ishga tushiramiz
        if key not in GROUP_FINALIZE_TASKS:
            GROUP_FINALIZE_TASKS[key] = asyncio.create_task(finalize_media_group(key))

        return

    # Oddiy bitta rasm: tugmalar chiqadi
    allowed, info = await is_allowed(user_id)
    if not allowed:
        await message.answer(info)
        return

    photo = message.photo[-1]
    file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{photo.file_id}.jpg")
    await photo.download(destination=file_path)

    LAST_PHOTO_BY_USER[user_id] = file_path
    await message.reply(info + "\nRasm qabul qilindi! Nima qilamiz?", reply_markup=kb_actions_for_photo())

@dp.callback_query_handler(text="text_to_pdf")
async def cb_text_to_pdf(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    allowed, info = await is_allowed(user_id)
    if not allowed:
        await callback.message.answer(info)
        await callback.answer()
        return

    text = LAST_TEXT_BY_USER.get(user_id)
    if not text:
        await callback.answer("Matn topilmadi!", show_alert=True)
        return

    pdf_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_text.pdf")
    try:
        text_to_pdf_file(text, pdf_path, title="Text to PDF")
        with open(pdf_path, "rb") as f:
            await bot.send_document(user_id, f, caption="✅ Matn PDF tayyor!")
        db_inc_uses(user_id, 1)
    except Exception as e:
        await bot.send_message(user_id, f"Xato (text->pdf): {e}")
    finally:
        safe_remove(pdf_path)
        LAST_TEXT_BY_USER.pop(user_id, None)

    await callback.answer()

@dp.callback_query_handler(text="make_pdf")
async def cb_make_pdf(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    allowed, info = await is_allowed(user_id)
    if not allowed:
        await callback.message.answer(info)
        await callback.answer()
        return

    last_file = LAST_PHOTO_BY_USER.get(user_id)
    if not last_file or not os.path.exists(last_file):
        await callback.answer("Rasm topilmadi!", show_alert=True)
        return

    pdf_path = last_file.rsplit(".", 1)[0] + ".pdf"
    try:
        img = Image.open(last_file).convert("RGB")
        img.save(pdf_path)
        with open(pdf_path, "rb") as f:
            await bot.send_document(user_id, f, caption="✅ PDF tayyor!")
        db_inc_uses(user_id, 1)
    except Exception as e:
        await bot.send_message(user_id, f"Xato (pdf): {e}")
    finally:
        safe_remove(last_file)
        safe_remove(pdf_path)
        LAST_PHOTO_BY_USER.pop(user_id, None)

    await callback.answer()

@dp.callback_query_handler(text="upscale")
async def cb_upscale(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    allowed, info = await is_allowed(user_id)
    if not allowed:
        await callback.message.answer(info)
        await callback.answer()
        return

    last_file = LAST_PHOTO_BY_USER.get(user_id)
    if not last_file or not os.path.exists(last_file):
        await callback.answer("Rasm topilmadi!", show_alert=True)
        return

    status = await bot.send_message(user_id, "⏳ Sifat oshirilmoqda...")
    out_path = last_file.rsplit(".", 1)[0] + "_upscaled.jpg"

    try:
        upscale_image(last_file, out_path, scale=2)
        with open(out_path, "rb") as f:
            await bot.send_photo(user_id, f, caption="✨ Sifat oshirildi!")
        db_inc_uses(user_id, 1)
        await bot.delete_message(user_id, status.message_id)
    except Exception as e:
        await bot.send_message(user_id, f"Xato (upscale): {e}")
    finally:
        safe_remove(last_file)
        safe_remove(out_path)
        LAST_PHOTO_BY_USER.pop(user_id, None)

    await callback.answer()

# =========================
#   RUN
# =========================
if __name__ == "__main__":
    db_init()
    print("Bot ishga tushdi...")
    executor.start_polling(dp, skip_updates=True)