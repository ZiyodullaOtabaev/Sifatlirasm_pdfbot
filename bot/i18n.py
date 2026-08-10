"""
Internationalization / Multi-language support (Uzbek, Russian, English).
"""
from typing import Optional

DEFAULT_LANG = "uz"

TEXTS = {
    "uz": {
        "lang_select_prompt": "🌐 <b>Iltimos, tilni tanlang / Пожалуйста, выберите язык / Please select a language:</b>",
        "lang_selected": "✅ Til muvaffaqiyatli tanlandi: <b>O'zbekcha</b> 🇺🇿",
        "welcome_text": (
            "👋 <b>Assalomu alaykum!</b>\n\n"
            "🛠 Men sizga quyidagilarda yordam beraman:\n"
            "• PDF yaratish va boshqarish\n"
            "• AI orqali rasmlarni yaxshilash\n"
            "• Rasmdan matn ajratish va AI rasmlar\n"
            "• 🎬 <b>AI Video yaratish (Pullik)</b>\n\n"
            "⬇️ Kerakli bo'limni tanlang:"
        ),
        "btn_profile": "👤 Mening profilim",
        "btn_text_pdf": "📝 Matn → PDF",
        "btn_img_pdf": "🖼 Rasm → PDF",
        "btn_merge_pdf": "📎 PDF birlashtirish",
        "btn_compress_pdf": "🗜 PDF siqish",
        "btn_upscale": "✨ Sifat oshirish (AI)",
        "btn_bg_remove": "🎨 Fon olib tashlash",
        "btn_ai_image": "✦ AI rasm yaratish",
        "btn_ai_video": "🎬 AI Video yaratish (Pullik)",
        "btn_ai_slides": "📊 AI Slayd Yaratish (Pullik)",
        "btn_ocr": "📖 Matn ajratish (OCR)",
        "btn_change_lang": "🌐 Tilni o'zgartirish",
        "btn_home": "🏠 Bosh menyu",
        "btn_top_up": "💳 Balansni to'ldirish",
        "btn_share_ref": "🎁 Do'stlarni taklif qilish (+1 Kredit)",
        "btn_share_url": "📲 Telegram'da ulashish",
        "btn_confirm_ai_video": "✅ Tushundim, video yaratish",
        "profile_text": (
            "👤 <b>Foydalanuvchi Profili</b>\n\n"
            "🆔 ID: <code>{user_id}</code>\n"
            "🌐 Til: <b>{lang_name}</b>\n"
            "📊 Ishlatishlar soni: <b>{uses_count} marta</b>\n"
            "💰 AI Video Balansi: <b>{balance} kredit</b>\n"
            "👥 Taklif qilgan do'stlaringiz: <b>{referral_count} ta</b>"
        ),
        "referral_page_text": (
            "🎁 <b>Do'stlarni Taklif Qiling va Kredit Yuting!</b>\n\n"
            "Har bir sizning havolangiz orqali botga qo'shilgan do'stingiz uchun sizga <b>+1 kredit bonus</b> beriladi!\n\n"
            "🔗 <b>Sizning shaxsiy havolangiz:</b>\n"
            "<code>https://t.me/{bot_username}?start=ref_{user_id}</code>\n\n"
            "👥 Jami taklif qilgan do'stlaringiz: <b>{referral_count} ta</b>\n\n"
            "👇 Do'stlaringizga ulashish uchun pastdagi tugmani bosing:"
        ),
        "referral_share_msg": "🤖 Zo'r AI Video va PDF botini topdim! Siz ham sinab ko'ring:",
        "referral_bonus_notify": "🎉 <b>Yangi do'stingiz botga qo'shildi!</b>\n🎁 Sizga <b>+1 kredit bonus</b> berildi!",
        "ai_video_refund_notify": "⚠️ <b>Video yaratishda xatolik yuz berdi.</b>\n💰 1 kredit balansingizga qaytarildi!",
        "top_up_info": (
            "💳 <b>Rasmiy Xizmat Tariflari va To'lovlar:</b>\n\n"
            "🎬 <b>1 ta AI Video yaratish:</b> 1 500 so'm <i>(yoki ⭐️ 15 Stars)</i>\n"
            "📊 <b>1 ta AI Slayd (12 bet) yaratish:</b> 2 000 so'm <i>(yoki ⭐️ 20 Stars)</i>\n\n"
            "⭐️ <b>Telegram Stars</b> orqali pastdagi tugmalar bilan 1 soniyada to'lashingiz mumkin!\n"
            "💳 <b>Karta orqali to'lash</b> uchun admin @ziyodullame ga murojaat qiling 👇"
        ),
        "sub_required": "⚠️ Botdan foydalanish uchun rasmiy kanalimizga obuna bo'ling:",
        "sub_btn": "📢 Kanalga obuna bo'lish",
        "sub_check_btn": "✅ Tekshirish",
        "sub_not_yet": "❌ Siz hali kanalga obuna bo'lmadingiz. Iltimos, obuna bo'lib qayta urinib ko'ring.",
        "text_pdf_prompt": "📝 PDF ga aylantirmoqchi bo'lgan matningizni yuboring:",
        "img_pdf_prompt": "🖼 PDF ga aylantirish uchun rasmlarni birma-bir yoki albom qilib yuboring. Tugagach 'Tugatish' tugmasini bosing.",
        "upscale_prompt": "✨ Sifatini oshirmoqchi bo'lgan rasmingizni yuboring:",
        "bg_remove_prompt": "🎨 Fonini olib tashlamoqchi bo'lgan rasmingizni yuboring:",
        "ai_image_prompt": "🤖 AI rasm yaratish uchun tavsif (prompt) yuboring (O'zbek, Rus yoki Ingliz tilida):\n<i>Masalan: Koinotda uchayotgan mushuk, 8k photo</i>",
        "ai_slides_prompt": (
            "📊 <b>AI Professional Taqdimot Generator</b>\n\n"
            "🤖 Ushbu slayd <b>Google Gemini & FLUX AI Engine</b> orqali 12 betli standart formatda avtomatik yaratiladi!\n\n"
            "{trial_text}\n"
            "💰 Sizning balansingiz: <b>{balance} kredit</b>\n\n"
            "Taqdimot mavzusini yuboring:\n"
            "<i>Masalan: \"Sun'iy intellektning rivojlanishi va jamiyatga ta'siri\"</i>"
        ),
        "ai_slides_author_prompt": (
            "👤 <b>Taqdimotchi va Muassasa Ma'lumotlari:</b>\n\n"
            "Slayd muqovasida ko'rinishi uchun ism-familiyangiz va o'quv/ish joyingizni kiriting:\n"
            "<i>Masalan: \"Abdulla Abdullayev | TATU 3-bosqich talabasi\"</i>\n\n"
            "<i>(Agar kerak bo'lmasa, pastdagi tugmani bosing)</i>"
        ),
        "btn_skip": "⏩ O'tkazib yuborish",
        "ai_slides_select_template": (
            "🎨 <b>Slayd Dizayn Shablonini Tanlang:</b>\n\n"
            "Mavzu: <b>{topic}</b>\n"
            "Taqdimotchi: <b>{author}</b>\n\n"
            "O'zingizga ma'qul 10 ta professional shablondan birini tanlang:"
        ),
        "ai_slides_insufficient_balance": (
            "📊 <b>AI Slayd Yaratish (Pullik xizmat)</b>\n\n"
            "📌 1 ta to'liq professional slayd (12 bet) narxi: <b>2 000 so'm (yoki ⭐️ 20 Stars / 1 kredit)</b>\n"
            "💰 Sizning balansingiz: <b>{balance} kredit</b>\n\n"
            "Davom etish uchun balansingizni to'ldiring 👇"
        ),
        "ai_slides_generating": "📊 Professional PowerPoint (.pptx) slayd taqdimoti yaratilmoqda, biroz kuting...",
        "btn_convert_pdf": "📄 PDF shaklida yuklab olish",
        "pdf_converting_msg": "📄 PowerPoint slayd PDF shakliga o'tkazilmoqda, biroz kuting...",
        "ai_video_terms": (
            "🎬 <b>AI Video yaratish shartlari va tariflar:</b>\n\n"
            "• 📌 1 ta AI video yaratish: <b>1 kredit</b>\n"
            "• ⏱ Video davomiyligi: <b>5 soniya</b> (HD 720p MP4)\n"
            "• 🎞 Video sifati: <b>HD (720p MP4)</b>\n"
            "• ⏳ Generatsiya vaqti: <b>1-2 daqiqa</b>\n"
            "• 🌐 Prompt tili: <b>O'zbek, Rus va Ingliz tili</b> (avto-tarjima qilinadi)\n"
            "• 💰 Sizning balansingiz: <b>{balance} kredit</b>\n\n"
            "💡 Balansni to'ldirish uchun kerakli kredit sonini ko'rsatib, admin @ziyodullame ga murojaat qiling."
        ),
        "ai_video_prompt": (
            "🎬 <b>AI Video yaratish</b>\n\n"
            "Qanday video hosil qilishni istaysiz? Tavsif (prompt) yuboring:\n"
            "<i>O'zbek, Rus yoki Ingliz tilida yozishingiz mumkin!</i>\n\n"
            "<i>Masalan: \"Koinotda uchayotgan mushuk, kinematik 4k video\"</i>"
        ),
        "ai_video_insufficient_balance": (
            "🎬 <b>AI Video yaratish (Pullik xizmat)</b>\n\n"
            "📌 1 ta AI video narxi: <b>1 500 so'm (yoki ⭐️ 15 Stars / 1 kredit)</b>\n"
            "💰 Sizning balansingiz: <b>{balance} kredit</b>\n\n"
            "❌ Balansingizda kredit yetarli emas.\n"
            "Telegram Stars yoki admin @ziyodullame orqali to'ldirishingiz mumkin 👇"
        ),
        "ai_video_generating": "🎬 AI Video yaratilmoqda... Bu jarayon 1-2 daqiqa vaqt olishi mumkin, kuting...",
        "ocr_prompt": "📖 Matnini ajratib olmoqchi bo'lgan me'yoriy/tiniq rasmingizni yuboring:",
        "merge_pdf_prompt": "📎 Birlashtirish uchun 2 yoki undan ortiq PDF fayllarni yuboring:",
        "compress_pdf_prompt": "🗜 Hajmini siqmoqchi bo'lgan PDF faylingizni yuboring:",
        "processing": "⏳ Qayta ishlanmoqda, kuting...",
        "error_occurred": "❌ Xatolik yuz berdi. Qayta urinib ko'ring.",
        "fallback_text_prompt": "💡 Iltimos, pastdagi menyudan kerakli bo'limni tanlang 👇",
        "bot_description": "🤖 Rasmlar va PDF hujjatchalar bilan ishlash, AI Slayd, AI sifat oshirish, fon olib tashlash, OCR va AI Video bot.",
        "bot_short_description": "⚡️ PDF & AI Video Bot",
    },
    "ru": {
        "lang_select_prompt": "🌐 <b>Пожалуйста, выберите язык / Please select a language:</b>",
        "lang_selected": "✅ Язык успешно выбран: <b>Русский</b> 🇷🇺",
        "welcome_text": (
            "👋 <b>Здравствуйте!</b>\n\n"
            "🛠 Я помогу вам в следующем:\n"
            "• Создание и обработка PDF\n"
            "• Улучшение качества фото с помощью ИИ\n"
            "• Распознавание текста и генерация изображений\n"
            "• 🎬 <b>AI Генерация видео (Платная)</b>\n\n"
            "⬇️ Выберите нужный раздел:"
        ),
        "btn_text_pdf": "📝 Текст → PDF",
        "btn_img_pdf": "🖼 Фото → PDF",
        "btn_merge_pdf": "📎 Объединить PDF",
        "btn_compress_pdf": "🗜 Сжать PDF",
        "btn_upscale": "✨ Улучшить качество (AI)",
        "btn_bg_remove": "🎨 Удалить фон",
        "btn_ai_image": "✦ AI Генерация фото",
        "btn_ai_video": "🎬 AI Генерация видео (Платная)",
        "btn_ocr": "📖 Извлечь текст (OCR)",
        "btn_change_lang": "🌐 Сменить язык",
        "btn_home": "🏠 Главное меню",
        "btn_top_up": "💳 Пополнить баланс",
        "btn_confirm_ai_video": "✅ Понятно, создать видео",
        "sub_required": "⚠️ Для использования бота подпишитесь на наш официальный канал:",
        "sub_btn": "📢 Подписаться на канал",
        "sub_check_btn": "✅ Проверить",
        "sub_not_yet": "❌ Вы еще не подписались на канал. Пожалуйста, подпишитесь и попробуйте снова.",
        "text_pdf_prompt": "📝 Отправьте текст, который вы хотите конвертировать в PDF:",
        "img_pdf_prompt": "🖼 Отправьте изображения для создания PDF. По окончании нажмите кнопку 'Завершить'.",
        "upscale_prompt": "✨ Отправьте изображение для улучшения качества:",
        "bg_remove_prompt": "🎨 Отправьте изображение, чтобы удалить фон:",
        "ai_image_prompt": "🤖 Отправьте описание (промпт) для генерации ИИ изображения (на Узбекском, Русском или Английском):\n<i>Например: Кот летящий в космосе, 8k photo</i>",
        "ai_video_terms": (
            "🎬 <b>Условия создания AI видео:</b>\n\n"
            "• 📌 Стоимость 1 ИИ видео: <b>1 кредит (500 сум)</b>\n"
            "• ⏱ Длительность видео: <b>5 секунд</b>\n"
            "• 🎞 Качество видео: <b>HD (720p MP4)</b>\n"
            "• ⏳ Время генерации: <b>1-2 минуты</b>\n"
            "• 🌐 Язык промпта: <b>Узбекский, Русский и Английский</b> (авто-перевод)\n"
            "• 💰 Ваш баланс: <b>{balance} кредитов</b>\n\n"
            "💡 Для пополнения баланса свяжитесь с админом @ziyodullame с указанием количества нужных кредитов."
        ),
        "ai_video_prompt": (
            "🎬 <b>AI Генерация видео</b>\n\n"
            "Отправьте текстовое описание (промпт) для видео:\n"
            "<i>Вы можете писать на Узбекском, Русском или Английском языке!</i>\n\n"
            "<i>Например: \"Кот летящий в космосе, кинематографическое 4k видео\"</i>"
        ),
        "ai_video_insufficient_balance": (
            "🎬 <b>AI Генерация видео (Платная услуга)</b>\n\n"
            "📌 Стоимость 1 ИИ видео: <b>1 500 сум (или ⭐️ 15 Stars / 1 кредит)</b>\n"
            "💰 Ваш баланс: <b>{balance} кредитов</b>\n\n"
            "❌ На вашем балансе недостаточно кредитов.\n"
            "Вы можете пополнить баланс через Telegram Stars или написав админу @ziyodullame 👇"
        ),
        "ai_video_generating": "🎬 Создание ИИ видео... Это может занять 1-2 минуты, пожалуйста подождите...",
        "ocr_prompt": "📖 Отправьте четкое изображение для распознавания текста:",
        "merge_pdf_prompt": "📎 Отправьте 2 или более PDF-файла для объединения:",
        "compress_pdf_prompt": "🗜 Отправьте PDF-файл, который вы хотите сжать:",
        "processing": "⏳ Обработка, пожалуйста подождите...",
        "error_occurred": "❌ Произошла ошибка. Попробуйте снова.",
        "fallback_text_prompt": "💡 Пожалуйста, выберите нужный раздел в меню ниже 👇",
        "bot_description": "🤖 Бот для работы с фото и PDF, улучшение качества с помощью ИИ, удаление фона, OCR и AI видео.\n\n👥 Ежемесячные пользователи: {monthly_count}",
        "bot_short_description": "⚡️ PDF & AI Video Bot — Ежемесячные пользователи: {monthly_count}",
    },
    "en": {
        "lang_select_prompt": "🌐 <b>Please select a language:</b>",
        "lang_selected": "✅ Language successfully set to: <b>English</b> 🇬🇧",
        "welcome_text": (
            "👋 <b>Welcome!</b>\n\n"
            "🛠 I can help you with:\n"
            "• PDF creation and editing\n"
            "• AI Image Quality Enhancement\n"
            "• Text Extraction (OCR) & AI Image Generation\n"
            "• 🎬 <b>AI Video Generator (Paid)</b>\n\n"
            "⬇️ Select an option below:"
        ),
        "btn_text_pdf": "📝 Text → PDF",
        "btn_img_pdf": "🖼 Image → PDF",
        "btn_merge_pdf": "📎 Merge PDF",
        "btn_compress_pdf": "🗜 Compress PDF",
        "btn_upscale": "✨ Upscale Quality (AI)",
        "btn_bg_remove": "🎨 Remove BG",
        "btn_ai_image": "✦ AI Image Generator",
        "btn_ai_video": "🎬 AI Video Generator (Paid)",
        "btn_ocr": "📖 Extract Text (OCR)",
        "btn_change_lang": "🌐 Change Language",
        "btn_home": "🏠 Main Menu",
        "btn_top_up": "💳 Top-up Balance",
        "btn_confirm_ai_video": "✅ I understand, create video",
        "sub_required": "⚠️ To use the bot, please subscribe to our official channel:",
        "sub_btn": "📢 Subscribe to channel",
        "sub_check_btn": "✅ Verify",
        "sub_not_yet": "❌ You haven't subscribed to the channel yet. Please subscribe and try again.",
        "text_pdf_prompt": "📝 Send the text you want to convert into a PDF:",
        "img_pdf_prompt": "🖼 Send images to convert into a PDF. Click 'Finish' when done.",
        "upscale_prompt": "✨ Send an image to enhance its quality:",
        "bg_remove_prompt": "🎨 Send an image to remove its background:",
        "ai_image_prompt": "🤖 Send a prompt description for AI image generation (in Uzbek, Russian or English):\n<i>Example: A cat flying in space, 8k photo</i>",
        "ai_video_terms": (
            "🎬 <b>AI Video Generator Terms:</b>\n\n"
            "• 📌 Price per 1 AI video: <b>1 credit (500 UZS)</b>\n"
            "• ⏱ Video duration: <b>5 seconds</b>\n"
            "• 🎞 Video quality: <b>HD (720p MP4)</b>\n"
            "• ⏳ Generation time: <b>1-2 minutes</b>\n"
            "• 🌐 Prompt language: <b>Uzbek, Russian & English</b> (auto-translated)\n"
            "• 💰 Your balance: <b>{balance} credits</b>\n\n"
            "💡 To top up balance, contact admin @ziyodullame with the number of credits needed."
        ),
        "ai_video_prompt": (
            "🎬 <b>AI Video Generator</b>\n\n"
            "Send a prompt description for your video:\n"
            "<i>You can type in Uzbek, Russian, or English!</i>\n\n"
            "<i>Example: \"A cat flying in space, cinematic 4k video\"</i>"
        ),
        "ai_video_insufficient_balance": (
            "🎬 <b>AI Video Generator (Paid Service)</b>\n\n"
            "📌 Price per 1 AI Video: <b>1,500 UZS (or ⭐️ 15 Stars / 1 credit)</b>\n"
            "💰 Your balance: <b>{balance} credits</b>\n\n"
            "❌ Insufficient credits on your balance.\n"
            "You can top up via Telegram Stars or by contacting admin @ziyodullame 👇"
        ),
        "ai_video_generating": "🎬 Generating AI Video... This may take 1-2 minutes, please wait...",
        "ocr_prompt": "📖 Send a clear image to extract text from:",
        "merge_pdf_prompt": "📎 Send 2 or more PDF files to merge together:",
        "compress_pdf_prompt": "🗜 Send the PDF file you want to compress:",
        "processing": "⏳ Processing, please wait...",
        "error_occurred": "❌ An error occurred. Please try again.",
        "fallback_text_prompt": "💡 Please select a section from the menu below 👇",
        "bot_description": "🤖 Image & PDF tools, AI Upscaling, Background Removal, OCR & AI Video bot.\n\n👥 Monthly Active Users: {monthly_count}",
        "bot_short_description": "⚡️ PDF & AI Video Bot — Monthly Users: {monthly_count}",
    },
}


def t(key: str, lang: Optional[str] = None, **kwargs) -> str:
    """Get localized text by key and language code."""
    language = (lang or DEFAULT_LANG).lower()
    if language not in TEXTS:
        language = DEFAULT_LANG

    text = TEXTS[language].get(key) or TEXTS[DEFAULT_LANG].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
