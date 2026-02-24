import os
import io
import time
import asyncio
import sqlite3
from typing import Dict, Tuple, List, Optional

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image

# =====================
#   CONFIG
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL_USER = os.getenv("CHANNEL_USER", "@xonziyy").strip()
FREE_USES = int(os.getenv("FREE_USES", "10").strip() or "10")  # default 10

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi. Alwaysdata Services -> Environment ga qo'ying.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

DB_PATH = os.path.join(BASE_DIR, "bot.db")

# =====================
#   DB
# =====================
def db_init():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            uses INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def db_get_uses(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT uses FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO users (user_id, uses) VALUES (?, 0)", (user_id,))
        conn.commit()
        uses = 0
    else:
        uses = int(row[0])
    conn.close()
    return uses

def db_inc_uses(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO users (user_id, uses) VALUES (?, 0) ON CONFLICT(user_id) DO NOTHING", (user_id,))
    cur.execute("UPDATE users SET uses = uses + 1 WHERE user_id=?", (user_id,))
    conn.commit()
    cur.execute("SELECT uses FROM users WHERE user_id=?", (user_id,))
    uses = int(cur.fetchone()[0])
    conn.close()
    return uses

# =====================
#   MENU / STATES
# =====================
MODE_NONE = "none"
MODE_WAIT_TEXT = "wait_text"
MODE_WAIT_PHOTO_PDF = "wait_photo_pdf"
MODE_WAIT_PHOTO_UPSCALE = "wait_photo_upscale"

USER_MODE: Dict[int, str] = {}
LAST_TEXT: Dict[int, str] = {}

# album/multi-photo buffer: (user_id, media_group_id) -> list of file paths
MEDIA_GROUP_PHOTOS: Dict[Tuple[int, str], List[str]] = {}
MEDIA_GROUP_TASKS: Dict[Tuple[int, str], asyncio.Task] = {}

def menu_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📝 Matnni PDF qilish", callback_data="menu_text_pdf"),
        InlineKeyboardButton("📄 Rasmni PDF qilish", callback_data="menu_photo_pdf"),
        InlineKeyboardButton("✨ Sifatni oshirish", callback_data="menu_upscale"),
    )
    return kb

def subscribe_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("✅ Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USER.lstrip('@')}"),
        InlineKeyboardButton("🔄 Tekshirish", callback_data="check_sub"),
    )
    return kb

async def send_menu(chat_id: int):
    USER_MODE[chat_id] = MODE_NONE
    await bot.send_message(
        chat_id,
        "Salom! 👋\n\n"
        "📌 Rasm yoki matnlaringizni PDF qiling va\n"
        "✨ rasmlaringiz sifatini oshiring.\n\n"
        "Quyidagi tugmalardan birini tanlang:",
        reply_markup=menu_keyboard()
    )

# =====================
#   SUBSCRIPTION / LIMIT
# =====================
async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USER, user_id=user_id)
        return member.status != "left"
    except Exception:
        # bot admin bo'lmasa tekshiruv ishlamasligi mumkin, shunda bloklamaymiz
        return True

async def can_use_service(user_id: int) -> bool:
    uses = db_get_uses(user_id)
    if uses < FREE_USES:
        return True
    # 10+ bo'lsa kanalga obuna bo'lish shart
    return await is_subscribed(user_id)

async def require_subscribe(chat_id: int):
    await bot.send_message(
        chat_id,
        f"⚠️ Siz xizmatimizdan {FREE_USES} marta foydalandingiz.\n"
        f"Yana foydalanish uchun kanalimizga obuna bo‘ling: {CHANNEL_USER}",
        reply_markup=subscribe_keyboard()
    )

# =====================
#   HELPERS
# =====================
def safe_remove(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

def unique_name(prefix: str, ext: str) -> str:
    return f"{prefix}_{int(time.time()*1000)}.{ext}"

async def download_photo(message: types.Message, file_id: str, out_path: str):
    file = await bot.get_file(file_id)
    await bot.download_file(file.file_path, out_path)

def make_pdf_from_images(image_paths: List[str], pdf_path: str):
    imgs = []
    for p in image_paths:
        im = Image.open(p)
        if im.mode != "RGB":
            im = im.convert("RGB")
        imgs.append(im)

    if not imgs:
        raise RuntimeError("Rasm topilmadi")

    first, rest = imgs[0], imgs[1:]
    first.save(pdf_path, save_all=True, append_images=rest)

def make_pdf_from_text(text: str, pdf_path: str):
    # Pillow bilan oddiy PDF (font default). Reportlab ham bo'ladi, lekin soddaroq variant:
    # Katta matnlar uchun bo'lib yozamiz.
    lines = text.splitlines() if text else [""]
    # oddiy kanvas
    img = Image.new("RGB", (1240, 1754), "white")  # A4 ga yaqin
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 36)
    except Exception:
        font = ImageFont.load_default()

    x, y = 60, 60
    max_w = 1120

    def wrap_line(s: str) -> List[str]:
        words = s.split(" ")
        out = []
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if draw.textlength(test, font=font) <= max_w:
                cur = test
            else:
                if cur:
                    out.append(cur)
                cur = w
        if cur:
            out.append(cur)
        return out

    wrapped = []
    for ln in lines:
        wrapped.extend(wrap_line(ln) or [""])

    for ln in wrapped:
        draw.text((x, y), ln, fill="black", font=font)
        y += 52
        if y > 1680:
            break

    img.save(pdf_path, "PDF", resolution=100.0)

def upscale_pil_2x(in_path: str, out_path: str):
    img = Image.open(in_path)
    new_size = (img.width * 2, img.height * 2)
    up = img.resize(new_size, Image.LANCZOS)
    up.save(out_path, quality=95, optimize=True)

# =====================
#   COMMANDS
# =====================
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    # /start bosilganda har doim bosh menyu
    await send_menu(message.chat.id)

# =====================
#   CALLBACKS (MENU)
# =====================
@dp.callback_query_handler(lambda c: c.data in ["menu_text_pdf", "menu_photo_pdf", "menu_upscale"])
async def menu_callbacks(call: types.CallbackQuery):
    user_id = call.from_user.id

    if not await can_use_service(user_id):
        await call.answer()
        await require_subscribe(user_id)
        return

    if call.data == "menu_text_pdf":
        USER_MODE[user_id] = MODE_WAIT_TEXT
        await bot.send_message(user_id, "📝 Matn yuboring (men uni PDF qilib beraman).")
        await call.answer()

    elif call.data == "menu_photo_pdf":
        USER_MODE[user_id] = MODE_WAIT_PHOTO_PDF
        await bot.send_message(user_id, "📄 Rasm yuboring (1 ta yoki 2+ ta rasm yuborsangiz ham bitta PDF qilaman).")
        await call.answer()

    elif call.data == "menu_upscale":
        USER_MODE[user_id] = MODE_WAIT_PHOTO_UPSCALE
        await bot.send_message(user_id, "✨ Sifatni oshirish uchun rasm yuboring.")
        await call.answer()

@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def cb_check_sub(call: types.CallbackQuery):
    user_id = call.from_user.id
    if await can_use_service(user_id):
        await call.answer("✅ Rahmat! Endi foydalanishingiz mumkin.", show_alert=True)
        await send_menu(user_id)
    else:
        await call.answer("❌ Hali obuna emassiz. Avval obuna bo‘ling.", show_alert=True)

# =====================
#   TEXT HANDLER
# =====================
@dp.message_handler(content_types=["text"])
async def on_text(message: types.Message):
    user_id = message.from_user.id
    mode = USER_MODE.get(user_id, MODE_NONE)

    if mode != MODE_WAIT_TEXT:
        # oddiy chat bo'lsa — faqat menuni ko'rsatib qo'yamiz
        await send_menu(user_id)
        return

    if not await can_use_service(user_id):
        await require_subscribe(user_id)
        return

    text = (message.text or "").strip()
    if not text:
        await message.reply("Matn bo‘sh. Qaytadan yuboring.")
        return

    pdf_name = unique_name(f"{user_id}_text", "pdf")
    pdf_path = os.path.join(DOWNLOAD_DIR, pdf_name)

    try:
        make_pdf_from_text(text, pdf_path)
        with open(pdf_path, "rb") as f:
            await bot.send_document(user_id, f, caption="✅ Matn PDF tayyor!")
        db_inc_uses(user_id)
    except Exception as e:
        await message.reply(f"Xato: {e}")
    finally:
        safe_remove(pdf_path)

    await send_menu(user_id)

# =====================
#   PHOTO HANDLER (PDF + UPSCALE)
# =====================
@dp.message_handler(content_types=["photo"])
async def on_photo(message: types.Message):
    user_id = message.from_user.id
    mode = USER_MODE.get(user_id, MODE_NONE)

    if mode not in [MODE_WAIT_PHOTO_PDF, MODE_WAIT_PHOTO_UPSCALE]:
        await send_menu(user_id)
        return

    if not await can_use_service(user_id):
        await require_subscribe(user_id)
        return

    # Eng katta rasm variantini olamiz
    photo = message.photo[-1]
    file_id = photo.file_id

    # ======= PHOTO -> PDF (multi-photo support) =======
    if mode == MODE_WAIT_PHOTO_PDF:
        # albom bo'lsa
        if message.media_group_id:
            key = (user_id, str(message.media_group_id))
            img_path = os.path.join(DOWNLOAD_DIR, unique_name(f"{user_id}_img", "jpg"))
            await download_photo(message, file_id, img_path)

            MEDIA_GROUP_PHOTOS.setdefault(key, []).append(img_path)

            # 1 ta task bilan 1s kutib, albom tugagach pdf qilamiz
            if key not in MEDIA_GROUP_TASKS:
                async def finalize_album():
                    await asyncio.sleep(1.2)  # albomdagi hamma xabarlar kelib ulguradi
                    paths = MEDIA_GROUP_PHOTOS.pop(key, [])
                    MEDIA_GROUP_TASKS.pop(key, None)

                    if not paths:
                        await bot.send_message(user_id, "Rasm topilmadi.")
                        await send_menu(user_id)
                        return

                    pdf_path = os.path.join(DOWNLOAD_DIR, unique_name(f"{user_id}_photos", "pdf"))
                    try:
                        make_pdf_from_images(paths, pdf_path)
                        with open(pdf_path, "rb") as f:
                            await bot.send_document(user_id, f, caption="✅ PDF tayyor!")
                        db_inc_uses(user_id)
                    except Exception as e:
                        await bot.send_message(user_id, f"Xato: {e}")
                    finally:
                        for p in paths:
                            safe_remove(p)
                        safe_remove(pdf_path)

                    await send_menu(user_id)

                MEDIA_GROUP_TASKS[key] = asyncio.create_task(finalize_album())

            return

        # albom emas (1 dona rasm)
        img_path = os.path.join(DOWNLOAD_DIR, unique_name(f"{user_id}_img", "jpg"))
        pdf_path = os.path.join(DOWNLOAD_DIR, unique_name(f"{user_id}_photo", "pdf"))

        try:
            await download_photo(message, file_id, img_path)
            make_pdf_from_images([img_path], pdf_path)
            with open(pdf_path, "rb") as f:
                await bot.send_document(user_id, f, caption="✅ PDF tayyor!")
            db_inc_uses(user_id)
        except Exception as e:
            await bot.send_message(user_id, f"Xato: {e}")
        finally:
            safe_remove(img_path)
            safe_remove(pdf_path)

        await send_menu(user_id)
        return

    # ======= PHOTO -> UPSCALE =======
    if mode == MODE_WAIT_PHOTO_UPSCALE:
        in_path = os.path.join(DOWNLOAD_DIR, unique_name(f"{user_id}_in", "jpg"))
        out_path = os.path.join(DOWNLOAD_DIR, unique_name(f"{user_id}_up", "jpg"))

        status = await bot.send_message(user_id, "✨ Sifat oshirilmoqda... ⏳")

        try:
            await download_photo(message, file_id, in_path)
            upscale_pil_2x(in_path, out_path)

            with open(out_path, "rb") as f:
                await bot.send_photo(user_id, f, caption="✅ Tayyor! (2x upscale)")
            db_inc_uses(user_id)

        except Exception as e:
            await bot.send_message(user_id, f"Xato: {e}")
        finally:
            safe_remove(in_path)
            safe_remove(out_path)
            try:
                await bot.delete_message(user_id, status.message_id)
            except Exception:
                pass

        await send_menu(user_id)
        return

# =====================
#   FALLBACK (other content)
# =====================
@dp.message_handler(content_types=types.ContentType.ANY)
async def fallback(message: types.Message):
    await send_menu(message.chat.id)

if __name__ == "__main__":
    db_init()
    print("Bot ishga tushdi...")
    executor.start_polling(dp, skip_updates=True)