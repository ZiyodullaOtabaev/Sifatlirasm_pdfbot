import os
import replicate
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image

# --- SOZLAMALAR ---
BOT_TOKEN = '8508492779:AAFmPa_x0qs-GLTlpZ0PYjSEfYXhqSk1UVE'
REPLICATE_API_TOKEN = 'r8_KH3F0UnShk2lzd2Q9Scz3OH9armqf363lKBku'

# Obunachi yig'ish uchun kanal (Oldin botni kanalda admin qiling!)
CHANNEL_USER = "@xonziyy"  # Kanalingiz yuzernemini yozing

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Replicate clientni sozlash
client = replicate.Client(api_token=REPLICATE_API_TOKEN)

if not os.path.exists('downloads'):
    os.makedirs('downloads')


# --- FUNKSIYALAR ---

# Kanalga a'zolikni tekshirish
async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USER, user_id=user_id)
        return member.status != 'left'
    except:
        return True  # Xatolik bo'lsa o'tkazib yuboradi (masalan bot admin bo'lmasa)


def get_action_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    btn_pdf = InlineKeyboardButton("📄 PDF-ga aylantirish", callback_data="make_pdf")
    btn_upscale = InlineKeyboardButton("✨ Sifatni oshirish (AI)", callback_data="upscale")
    keyboard.add(btn_pdf, btn_upscale)
    return keyboard


# --- HANDLERLAR ---

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply(f"Salom! Botdan foydalanish uchun {CHANNEL_USER} kanaliga a'zo bo'ling va rasm yuboring.")


@dp.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    # A'zolikni tekshirish
    if not await check_sub(message.from_user.id):
        await message.answer(
            f"❌ Kechirasiz, botdan foydalanish uchun kanalimizga a'zo bo'lishingiz kerak: {CHANNEL_USER}")
        return

    photo = message.photo[-1]
    file_path = f"downloads/{photo.file_id}.jpg"

    # To'g'ri yuklab olish (destination ishlatiladi)
    await photo.download(destination=file_path)

    await message.reply("Rasm qabul qilindi! Nima qilamiz?", reply_markup=get_action_keyboard())


@dp.callback_query_handler(text="make_pdf")
async def process_pdf(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    files = [f for f in os.listdir('downloads') if f.endswith('.jpg')]

    if not files:
        await bot.send_message(user_id, "Xatolik: Rasm topilmadi.")
        return

    last_file = f"downloads/{files[-1]}"
    pdf_path = last_file.replace(".jpg", ".pdf")

    try:
        img = Image.open(last_file)
        img.convert('RGB').save(pdf_path)

        with open(pdf_path, 'rb') as pdf:
            await bot.send_document(user_id, pdf, caption="Tayyor! ✅ @xonziyy")

        os.remove(last_file)
        os.remove(pdf_path)
    except Exception as e:
        await bot.send_message(user_id, f"Xato yuz berdi: {e}")
    await callback_query.answer()


@dp.callback_query_handler(text="upscale")
async def process_upscale(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    files = [f for f in os.listdir('downloads') if f.endswith('.jpg')]

    if not files:
        await callback_query.answer("Rasm topilmadi!")
        return

    last_file = f"downloads/{files[-1]}"
    status_msg = await bot.send_message(user_id, "AI rasm sifatini oshirmoqda... ⏳ (15-30 soniya)")

    try:
        # UPDATED: Using the latest stable Real-ESRGAN version
        model = "nightmare-ai/real-esrgan:f121d640fb3770173f11f1429307456d69d31f0067118745a0797a4abc22c366"

        output = client.run(
            model,
            input={
                "image": open(last_file, "rb"),
                "upscale": 2,
                "face_enhance": True  # Optional: Good for the selfie in your screenshot
            }
        )

        await bot.send_photo(user_id, output, caption="✨ Sifati oshirilgan rasm! @sizning_kanalingiz")
        await bot.delete_message(user_id, status_msg.message_id)

    except Exception as e:
        await bot.send_message(user_id, f"AI xatosi: {str(e)}")
    finally:
        if os.path.exists(last_file):
            os.remove(last_file)

    await callback_query.answer()

if __name__ == '__main__':
    print("Bot muvaffaqiyatli ishga tushdi...")
    executor.start_polling(dp, skip_updates=True)