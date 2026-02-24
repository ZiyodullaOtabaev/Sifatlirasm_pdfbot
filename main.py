import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image, ImageFilter, ImageEnhance

# =========================
#   ENVIRONMENT VARIABLES
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL_USER = os.getenv("CHANNEL_USER", "@xonziyy").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi! Alwaysdata -> Services -> Environment ga qo'ying.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

LAST_PHOTO_BY_USER = {}

# =========================
#   HELPER FUNCTIONS
# =========================

async def check_sub(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USER, user_id=user_id)
        return member.status != "left"
    except Exception:
        return True


def get_action_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📄 PDF qilish", callback_data="make_pdf"),
        InlineKeyboardButton("✨ Sifatni oshirish", callback_data="upscale"),
    )
    return kb


def safe_remove(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except:
        pass


# =========================
#   FREE UPSCALE (NO AI)
# =========================

def upscale_image(input_path, output_path, scale=2):
    img = Image.open(input_path).convert("RGB")

    # 1️⃣ Resize (High quality)
    up = img.resize((img.width * scale, img.height * scale), Image.LANCZOS)

    # 2️⃣ Sharpen (AIga o‘xshash effekt)
    up = up.filter(ImageFilter.UnsharpMask(radius=2, percent=180, threshold=3))

    # 3️⃣ Contrast ozgina oshiramiz
    up = ImageEnhance.Contrast(up).enhance(1.08)

    # 4️⃣ Save with max quality
    up.save(output_path, quality=95, optimize=True)


# =========================
#   HANDLERS
# =========================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.reply(
        f"Salom! Botdan foydalanish uchun {CHANNEL_USER} kanaliga a'zo bo‘ling va rasm yuboring."
    )


@dp.message_handler(content_types=["photo"])
async def handle_photo(message: types.Message):

    if not await check_sub(message.from_user.id):
        await message.answer(f"❌ Kanalga a'zo bo‘ling: {CHANNEL_USER}")
        return

    photo = message.photo[-1]
    user_id = message.from_user.id

    file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}.jpg")
    await photo.download(destination=file_path)

    LAST_PHOTO_BY_USER[user_id] = file_path

    await message.reply("Rasm qabul qilindi!", reply_markup=get_action_keyboard())


@dp.callback_query_handler(text="make_pdf")
async def make_pdf(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    file = LAST_PHOTO_BY_USER.get(user_id)

    if not file or not os.path.exists(file):
        await callback.answer("Rasm topilmadi!", show_alert=True)
        return

    pdf_path = file.replace(".jpg", ".pdf")

    img = Image.open(file)
    img.convert("RGB").save(pdf_path)

    with open(pdf_path, "rb") as f:
        await bot.send_document(user_id, f, caption="✅ PDF tayyor!")

    safe_remove(file)
    safe_remove(pdf_path)
    LAST_PHOTO_BY_USER.pop(user_id, None)

    await callback.answer()


@dp.callback_query_handler(text="upscale")
async def upscale(callback: types.CallbackQuery):

    user_id = callback.from_user.id
    file = LAST_PHOTO_BY_USER.get(user_id)

    if not file or not os.path.exists(file):
        await callback.answer("Rasm topilmadi!", show_alert=True)
        return

    status = await bot.send_message(user_id, "⏳ Sifat oshirilmoqda...")

    output_path = file.replace(".jpg", "_upscaled.jpg")

    upscale_image(file, output_path)

    with open(output_path, "rb") as f:
        await bot.send_photo(user_id, f, caption="✨ Sifat oshirildi!")

    await bot.delete_message(user_id, status.message_id)

    safe_remove(file)
    safe_remove(output_path)
    LAST_PHOTO_BY_USER.pop(user_id, None)

    await callback.answer()


# =========================
#   RUN BOT
# =========================

if __name__ == "__main__":
    print("Bot ishga tushdi...")
    executor.start_polling(dp, skip_updates=True)