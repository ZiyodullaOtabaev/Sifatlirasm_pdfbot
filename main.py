import os
import asyncio
import replicate
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image

# BOT_TOKEN = os.getenv("8508492779:AAFmPa_x0qs-GLTlpZ0PYjSEfYXhqSk1UVE", "").strip()
# REPLICATE_API_TOKEN = os.getenv("r8_KH3F0UnShk2lzd2Q9Scz3OH9armqf363lKBku", "").strip()


BOT_TOKEN = os.getenv("8508492779:AAFmPa_x0qs-GLTlpZ0PYjSEfYXhqSk1UVE", "").strip()
CHANNEL_USER = os.getenv("CHANNEL_USER", "@xonziyy").strip()  # ixtiyoriy

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi. Alwaysdata Services -> Environment ga qo'ying.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Har user uchun oxirgi rasm fayli
LAST_PHOTO_BY_USER = {}

# =====================
#   YORDAMCHI FUNKSIYALAR
# =====================
async def check_sub(user_id: int) -> bool:
    """Kanalga a'zolikni tekshiradi (bot kanalda admin bo'lishi kerak)."""
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USER, user_id=user_id)
        return member.status != "left"
    except Exception:
        # bot admin bo'lmasa yoki xato bo'lsa, bloklamaymiz
        return True

def get_action_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📄 PDF-ga aylantirish", callback_data="make_pdf"),
        InlineKeyboardButton("✨ Sifatni oshirish", callback_data="upscale_free"),
    )
    return kb

def safe_remove(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

# =====================
#   HANDLERLAR
# =====================
@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    await message.reply(
        f"Salom! Botdan foydalanish uchun {CHANNEL_USER} kanaliga a'zo bo'ling va rasm yuboring."
    )

@dp.message_handler(content_types=["photo"])
async def handle_photo(message: types.Message):
    if not await check_sub(message.from_user.id):
        await message.answer(
            f"❌ Botdan foydalanish uchun kanalimizga a'zo bo'ling: {CHANNEL_USER}"
        )
        return

    photo = message.photo[-1]
    user_id = message.from_user.id

    file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{photo.file_id}.jpg")

    # Aiogram v2 uchun to'g'ri variantlar:
    # await photo.download(destination_file=file_path)  # ba'zi versiyalarda bor
    # Sizda working bo'lgan usul:
    await photo.download(destination=file_path)

    LAST_PHOTO_BY_USER[user_id] = file_path
    await message.reply("Rasm qabul qilindi! Nima qilamiz?", reply_markup=get_action_keyboard())

@dp.callback_query_handler(text="make_pdf")
async def process_pdf(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    last_file = LAST_PHOTO_BY_USER.get(user_id)

    if not last_file or not os.path.exists(last_file):
        await callback_query.answer("Rasm topilmadi!", show_alert=True)
        return

    pdf_path = last_file.rsplit(".", 1)[0] + ".pdf"

    try:
        img = Image.open(last_file)
        img.convert("RGB").save(pdf_path)

        with open(pdf_path, "rb") as pdf:
            await bot.send_document(user_id, pdf, caption="Tayyor! ✅ @xonziyy")

    except Exception as e:
        await bot.send_message(user_id, f"Xato yuz berdi: {e}")

    finally:
        safe_remove(last_file)
        safe_remove(pdf_path)
        LAST_PHOTO_BY_USER.pop(user_id, None)

    await callback_query.answer()

@dp.callback_query_handler(text="upscale_free")
async def process_upscale_free(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    last_file = LAST_PHOTO_BY_USER.get(user_id)

    if not last_file or not os.path.exists(last_file):
        await callback_query.answer("Rasm topilmadi!", show_alert=True)
        return

    status_msg = await bot.send_message(user_id, "Sifat oshirilmoqda... ⏳")

    output_path = last_file.rsplit(".", 1)[0] + "_upscaled.jpg"

    try:
        img = Image.open(last_file)

        # 2x upscale (eng yaxshi bepul filtr)
        new_size = (img.width * 2, img.height * 2)
        upscaled = img.resize(new_size, Image.LANCZOS)

        # Sifatni maksimalroq saqlab yozamiz
        upscaled.save(output_path, quality=95, optimize=True)

        with open(output_path, "rb") as f:
            await bot.send_photo(user_id, f, caption="✨ Sifati oshirilgan rasm ✅ @xonziyy")

        await bot.delete_message(user_id, status_msg.message_id)

    except Exception as e:
        await bot.send_message(user_id, f"Xato: {e}")

    finally:
        safe_remove(last_file)
        safe_remove(output_path)
        LAST_PHOTO_BY_USER.pop(user_id, None)

    await callback_query.answer()

if __name__ == "__main__":
    print("Bot muvaffaqiyatli ishga tushdi...")
    executor.start_polling(dp, skip_updates=True)