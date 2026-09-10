"""
Internationalization / Multi-language support (Uzbek, Russian, English).
100% symmetric key dictionary for flawless multi-language UX.
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
            "• 📊 12 betlik professional taqdimot (Slayd)\n"
            "• 👔 3x4 Pasport & Hujjat rasmlari tayyorlash\n"
            "• ✨ Rasm sifatini oshirish\n"
            "• 📝 PDF yaratish, birlashtirish va siqish\n\n"
            "⬇️ Kerakli bo'limni tanlang:"
        ),
        "btn_profile": "👤 Mening profilim",
        "btn_text_pdf": "📝 Matn → PDF",
        "btn_img_pdf": "🖼 Rasm → PDF",
        "btn_merge_pdf": "📎 PDF birlashtirish",
        "btn_compress_pdf": "🗜 PDF siqish",
        "btn_upscale": "✨ Sifat oshirish",
        "btn_ai_slides": "📊 AI Slayd Yaratish",
        "btn_donate": "💖 Donat",
        "btn_change_lang": "🌐 Tilni o'zgartirish",
        "btn_home": "🏠 Bosh menyu",
        "btn_share_ref": "🎁 Do'stlarni taklif qilish",
        "btn_share_url": "📲 Telegram'da ulashish",
        "btn_skip": "⏩ O'tkazib yuborish",
        "btn_convert_pdf": "📄 PDF shaklida yuklab olish",
        "donate_text": (
            "💖 <b>Bot Rivojiga O'z Hissangizni Qo'shing!</b>\n\n"
            "Ushbu bot sizga har doim tezkor, qulay va sifatli xizmat ko'rsatishi (slaydlar, 3x4 hujjat rasmi, PDF vositalari) hamda bepul imkoniyatlarni saqlab qolish uchun kuchli serverlar talab etiladi.\n\n"
            "Siz taqdim etgan har qanday ixtiyoriy <b>donat (ehson)</b>:\n"
            "🚀 <i>Botning ishlash va qayta ishlash tezligini oshirishga;</i>\n"
            "⚡️ <i>Yangi foydali funksiyalarni joriy etishga;</i>\n"
            "🛠 <i>Serverlarning 24/7 uzluksiz, barqaror va sifatli ishlashini ta'minlashga xizmat qiladi.</i>\n\n"
            "💳 <b>Plastik karta (Uzcard):</b>\n"
            "<code>5614682914822756</code>\n\n"
            "<i>(Karta raqami ustiga bir marta bossangiz, avtomatik nusxalanadi)</i>\n\n"
            "E'tiboringiz, ishonchingiz va samimiy qo'llab-quvvatlovingiz uchun chin dildan minnatdormiz! 🙏✨"
        ),
        "profile_text": (
            "👤 <b>Foydalanuvchi Profili</b>\n\n"
            "🆔 ID: <code>{user_id}</code>\n"
            "🌐 Til: <b>{lang_name}</b>\n"
            "📊 Ishlatishlar soni: <b>{uses_count} marta</b>\n"
            "👥 Taklif qilgan do'stlaringiz: <b>{referral_count} ta</b>"
        ),
        "referral_page_text": (
            "🎁 <b>Do'stlaringizni Taklif Qiling!</b>\n\n"
            "Har bir sizning havolangiz orqali botga qo'shilgan do'stingiz botdan foydalanib, sizga minnatdorchilik bildiradi! 😊\n\n"
            "🔗 <b>Sizning shaxsiy havolangiz:</b>\n"
            "<code>https://t.me/{bot_username}?start=ref_{user_id}</code>\n\n"
            "👥 Jami taklif qilgan do'stlaringiz: <b>{referral_count} ta</b>\n\n"
            "👇 Do'stlaringizga ulashish uchun pastdagi tugmani bosing:"
        ),
        "referral_share_msg": "🤖 Zo'r Slayd va PDF botini topdim! Siz ham sinab ko'ring:",
        "referral_bonus_notify": "🎉 <b>Yangi do'stingiz botga qo'shildi!</b>\n🙌 Rahmat sizga!",
        "sub_required": "⚠️ Botdan foydalanish uchun quyidagi rasmiy kanalimizga a'zo bo'ling:",
        "sub_btn": "📢 Kanalga obuna bo'lish",
        "sub_check_btn": "✅ Tekshirish",
        "sub_not_yet": "❌ Siz hali kanalga obuna bo'lmadingiz. Iltimos, obuna bo'lib qayta urinib ko'ring.",
        "text_pdf_prompt": "📝 PDF ga aylantirmoqchi bo'lgan matningizni yuboring:",
        "text_pdf_generating": "⏳ PDF hujjat tayyorlanmoqda, kuting...",
        "text_pdf_ready": "✅ <b>PDF hujjat tayyor!</b>",
        "img_pdf_prompt": "🖼 PDF ga aylantirish uchun rasmlarni yuboring (birma-bir yoki albom shaklida).",
        "img_pdf_generating": "⏳ Rasmlar PDF ga aylantirilmoqda, kuting...",
        "img_pdf_ready": "✅ <b>PDF Tayyor!</b>",
        "upscale_prompt": "✨ Sifatini oshirmoqchi bo'lgan rasmingizni yuboring:",
        "upscale_generating": "✦ Rasm sifatini oshirmoqda, kuting...",
        "upscale_ready": "✨ <b>Rasm sifati oshirildi!</b>",
        "ai_slides_prompt": (
            "📊 <b>Professional Taqdimot Generator</b>\n\n"
            "🤖 Ushbu slayd 12 betli standart akademik formatda avtomatik yaratiladi — <b>mutlaqo BEPUL!</b>\n\n"
            "Taqdimot mavzusini yuboring:\n"
            "<i>Masalan: \"Sun'iy intellektning rivojlanishi va jamiyatga ta'siri\"</i>"
        ),
        "ai_slides_author_prompt": (
            "👤 <b>Taqdimotchi va Muassasa Ma'lumotlari:</b>\n\n"
            "Slayd muqovasida ko'rinishi uchun ism-familiyangiz va o'quv/ish joyingizni kiriting:\n"
            "<i>Masalan: \"Abdulla Abdullayev | TATU 3-bosqich talabasi\"</i>\n\n"
            "<i>(Agar kerak bo'lmasa, pastdagi tugmani bosing)</i>"
        ),
        "ai_slides_select_template": (
            "🎨 <b>Slayd Dizayn Shablonini Tanlang:</b>\n\n"
            "Mavzu: <b>{topic}</b>\n"
            "Taqdimotchi: <b>{author}</b>\n\n"
            "O'zingizga ma'qul professional shablondan birini tanlang:"
        ),
        "ai_slides_generating": "📊 Professional PowerPoint (.pptx) slayd taqdimoti yaratilmoqda, biroz kuting...",
        "pdf_converting_msg": "📄 PowerPoint slayd PDF shakliga o'tkazilmoqda, biroz kuting...",
        "merge_pdf_prompt": "📎 Birlashtirish uchun 2 yoki undan ortiq PDF fayllarni yuboring:",
        "merge_pdf_generating": "⏳ PDF fayllar birlashtirilmoqda, kuting...",
        "merge_pdf_ready": "✅ <b>PDF fayllar muvaffaqiyatli birlashtirildi!</b>",
        "compress_pdf_prompt": "🗜 Hajmini siqmoqchi bo'lgan PDF faylingizni yuboring:",
        "compress_pdf_generating": "⏳ PDF fayl siqilmoqda, kuting...",
        "compress_pdf_ready": "✅ <b>PDF fayl muvaffaqiyatli siqildi!</b>",
        "processing": "⏳ Qayta ishlanmoqda, kuting...",
        "btn_passport_photo": "👔 3x4 Hujjat rasmi",
        "passport_photo_prompt": (
            "👔 <b>3x4 Pasport va Hujjat Rasmi Yaratish</b>\n\n"
            "🎁 <b>Ushbu xizmat mutlaqo BEPUL va cheksiz!</b>\n\n"
            "Iltimos, to'g'riga qaragan sifatli selfi yoki portret rasm yuboring.\n\n"
            "<i>Bot rasmni 3x4 sm o'lchamga moslab, oq fonli va chop etishga tayyor 6 talik varaq (PDF va JPG) hamda 1 dona 3x4 HD rasm beradi.</i>"
        ),
        "passport_photo_generating": "⏳ 3x4 hujjat rasmi tayyorlanmoqda, iltimos kuting...",
        "passport_photo_ready": "✅ <b>3x4 Hujjat rasmingiz tayyor!</b>",
        "passport_photo_error": "❌ Rasmda inson yuzi aniqlanmadi yoki qayta ishlashda xatolik yuz berdi. Boshqa rasm bilan urinib ko'ring.",
        "error_occurred": "❌ Xatolik yuz berdi. Qayta urinib ko'ring.",
        "fallback_text_prompt": "💡 Iltimos, pastdagi menyudan kerakli bo'limni tanlang 👇",
        "bot_description": "🤖 Rasmlar va PDF hujjatlar bilan ishlash: AI Slayd, sifat oshirish, 3x4 hujjat rasmi.",
        "bot_short_description": "⚡️ Slayd & PDF Bot",
    },
    "ru": {
        "lang_select_prompt": "🌐 <b>Пожалуйста, выберите язык / Please select a language:</b>",
        "lang_selected": "✅ Язык успешно выбран: <b>Русский</b> 🇷🇺",
        "welcome_text": (
            "👋 <b>Здравствуйте!</b>\n\n"
            "🛠 Я помогу вам в следующем:\n"
            "• 📊 Презентации из 12 слайдов\n"
            "• 👔 Создание фото 3x4 на документы\n"
            "• ✨ Улучшение качества изображений\n"
            "• 📝 Создание, объединение и сжатие PDF\n\n"
            "⬇️ Выберите нужный раздел:"
        ),
        "btn_profile": "👤 Мой профиль",
        "btn_text_pdf": "📝 Текст → PDF",
        "btn_img_pdf": "🖼 Фото → PDF",
        "btn_merge_pdf": "📎 Объединить PDF",
        "btn_compress_pdf": "🗜 Сжать PDF",
        "btn_upscale": "✨ Улучшить качество",
        "btn_ai_slides": "📊 AI Создание слайдов",
        "btn_donate": "💖 Донат",
        "btn_change_lang": "🌐 Сменить язык",
        "btn_home": "🏠 Главное меню",
        "btn_share_ref": "🎁 Пригласить друзей",
        "btn_share_url": "📲 Поделиться в Telegram",
        "btn_skip": "⏩ Пропустить",
        "btn_convert_pdf": "📄 Скачать в формате PDF",
        "donate_text": (
            "💖 <b>Поддержите Развитие Проекта!</b>\n\n"
            "Чтобы бот продолжал работать быстро, стабильно и качественно (слайды, фото 3x4, PDF инструменты), требуются мощные серверы.\n\n"
            "Каждый ваш добровольный <b>донат</b> напрямую помогает:\n"
            "🚀 <i>Увеличить скорость обработки запросов в боте;</i>\n"
            "⚡️ <i>Внедрять новые полезные функции;</i>\n"
            "🛠 <i>Обеспечивать бесперебойную и надежную работу 24/7.</i>\n\n"
            "💳 <b>Карта (Uzcard):</b>\n"
            "<code>5614682914822756</code>\n\n"
            "<i>(Нажмите на номер карты, чтобы скопировать)</i>\n\n"
            "Искренне благодарим вас за поддержку и доверие! 🙏✨"
        ),
        "profile_text": (
            "👤 <b>Профиль пользователя</b>\n\n"
            "🆔 ID: <code>{user_id}</code>\n"
            "🌐 Язык: <b>{lang_name}</b>\n"
            "📊 Использований: <b>{uses_count} раз</b>\n"
            "👥 Приглашено друзей: <b>{referral_count} чел.</b>"
        ),
        "referral_page_text": (
            "🎁 <b>Пригласите друзей!</b>\n\n"
            "Каждый друг, присоединившийся по вашей ссылке, будет пользоваться ботом и скажет вам спасибо! 😊\n\n"
            "🔗 <b>Ваша реферальная ссылка:</b>\n"
            "<code>https://t.me/{bot_username}?start=ref_{user_id}</code>\n\n"
            "👥 Всего приглашено: <b>{referral_count} чел.</b>\n\n"
            "👇 Нажмите кнопку ниже, чтобы поделиться ссылкой:"
        ),
        "referral_share_msg": "🤖 Нашел отличного бота для создания презентаций и PDF! Попробуй:",
        "referral_bonus_notify": "🎉 <b>Новый друг присоединился по вашей ссылке!</b>\n🙌 Спасибо вам!",
        "sub_required": "⚠️ Для использования бота подпишитесь на наш официальный канал:",
        "sub_btn": "📢 Подписаться на канал",
        "sub_check_btn": "✅ Проверить",
        "sub_not_yet": "❌ Вы еще не подписались на канал. Пожалуйста, подпишитесь и попробуйте снова.",
        "text_pdf_prompt": "📝 Отправьте текст, который вы хотите конвертировать в PDF:",
        "text_pdf_generating": "⏳ Создается PDF документ, пожалуйста подождите...",
        "text_pdf_ready": "✅ <b>PDF документ готов!</b>",
        "img_pdf_prompt": "🖼 Отправьте изображения для создания PDF (по одному или альбомом).",
        "img_pdf_generating": "⏳ Конвертация изображений в PDF, пожалуйста подождите...",
        "img_pdf_ready": "✅ <b>PDF документ готов!</b>",
        "upscale_prompt": "✨ Отправьте изображение для улучшения качества:",
        "upscale_generating": "✦ Улучшаем качество изображения, подождите...",
        "upscale_ready": "✨ <b>Качество изображения успешно улучшено!</b>",
        "ai_slides_prompt": (
            "📊 <b>Генератор профессиональных презентаций</b>\n\n"
            "🤖 Презентация на 12 слайдов в стандартном академическом формате создается автоматически — <b>совершенно БЕСПЛАТНО!</b>\n\n"
            "Отправьте тему презентации:\n"
            "<i>Например: \"Развитие искусственного интеллекта и его влияние на общество\"</i>"
        ),
        "ai_slides_author_prompt": (
            "👤 <b>Информация об авторе презентации:</b>\n\n"
            "Введите ваше имя, фамилию и место учебы/работы для титульного слайда:\n"
            "<i>Например: \"Иван Иванов | Студент МГУ 3 курса\"</i>\n\n"
            "<i>(Если не требуется, нажмите кнопку ниже)</i>"
        ),
        "ai_slides_select_template": (
            "🎨 <b>Выберите шаблон дизайна слайдов:</b>\n\n"
            "Тема: <b>{topic}</b>\n"
            "Автор: <b>{author}</b>\n\n"
            "Выберите понравившийся профессиональный шаблон:"
        ),
        "ai_slides_generating": "📊 Создается профессиональная презентация PowerPoint (.pptx), пожалуйста подождите...",
        "pdf_converting_msg": "📄 Презентация конвертируется в формат PDF, пожалуйста подождите...",
        "merge_pdf_prompt": "📎 Отправьте 2 или более PDF-файла для объединения:",
        "merge_pdf_generating": "⏳ Объединение PDF файлов, пожалуйста подождите...",
        "merge_pdf_ready": "✅ <b>PDF файлы успешно объединены!</b>",
        "compress_pdf_prompt": "🗜 Отправьте PDF-файл, который вы хотите сжать:",
        "compress_pdf_generating": "⏳ Сжатие PDF файла, пожалуйста подождите...",
        "compress_pdf_ready": "✅ <b>PDF файл успешно сжат!</b>",
        "processing": "⏳ Обработка, пожалуйста подождите...",
        "btn_passport_photo": "👔 Фото 3x4 на документы",
        "passport_photo_prompt": (
            "👔 <b>Создание Фото 3x4 на Документы</b>\n\n"
            "🎁 <b>Эта услуга абсолютно БЕСПЛАТНА и безлимитна!</b>\n\n"
            "Пожалуйста, отправьте четкое селфи или портретное фото.\n\n"
            "<i>Бот подгонит фото под формат 3x4 и создаст готовый лист на 6 фото для печати (PDF и JPG) и 1 одиночное фото 3x4 HD.</i>"
        ),
        "passport_photo_generating": "⏳ Создается фото 3x4, пожалуйста подождите...",
        "passport_photo_ready": "✅ <b>Ваши фото 3x4 готовы!</b>",
        "passport_photo_error": "❌ Лицо на фото не обнаружено или произошла ошибка. Попробуйте другое фото.",
        "error_occurred": "❌ Произошла ошибка. Попробуйте снова.",
        "fallback_text_prompt": "💡 Пожалуйста, выберите нужный раздел в меню ниже 👇",
        "bot_description": "🤖 Работа с фото и PDF: AI слайды, улучшение качества, фото 3x4 на документы.",
        "bot_short_description": "⚡️ Слайды & PDF Бот",
    },
    "en": {
        "lang_select_prompt": "🌐 <b>Please select a language:</b>",
        "lang_selected": "✅ Language successfully set to: <b>English</b> 🇬🇧",
        "welcome_text": (
            "👋 <b>Welcome!</b>\n\n"
            "🛠 I can help you with:\n"
            "• 📊 12-Slide Professional Presentations\n"
            "• 👔 3x4 Passport & ID Photo Maker\n"
            "• ✨ Image Quality Upscaling\n"
            "• 📝 PDF creation, merging & compression\n\n"
            "⬇️ Select an option below:"
        ),
        "btn_profile": "👤 My Profile",
        "btn_text_pdf": "📝 Text → PDF",
        "btn_img_pdf": "🖼 Image → PDF",
        "btn_merge_pdf": "📎 Merge PDF",
        "btn_compress_pdf": "🗜 Compress PDF",
        "btn_upscale": "✨ Upscale Quality",
        "btn_ai_slides": "📊 AI Slides Generator",
        "btn_donate": "💖 Donate",
        "btn_change_lang": "🌐 Change Language",
        "btn_home": "🏠 Main Menu",
        "btn_share_ref": "🎁 Invite Friends",
        "btn_share_url": "📲 Share via Telegram",
        "btn_skip": "⏩ Skip",
        "btn_convert_pdf": "📄 Download as PDF",
        "donate_text": (
            "💖 <b>Support the Bot Development!</b>\n\n"
            "To ensure the bot keeps delivering fast, high-quality, and seamless services (slides, 3x4 passport photos, PDF tools), high-performance servers are utilized 24/7.\n\n"
            "Any voluntary <b>donation</b> directly contributes to:\n"
            "🚀 <i>Boosting the bot's speed and response time;</i>\n"
            "⚡️ <i>Implementing brand new useful features;</i>\n"
            "🛠 <i>Maintaining robust 24/7 server uptime and stability.</i>\n\n"
            "💳 <b>Card (Uzcard):</b>\n"
            "<code>5614682914822756</code>\n\n"
            "<i>(Tap the card number to copy instantly)</i>\n\n"
            "We deeply appreciate your kindness and generous support! 🙏✨"
        ),
        "profile_text": (
            "👤 <b>User Profile</b>\n\n"
            "🆔 ID: <code>{user_id}</code>\n"
            "🌐 Language: <b>{lang_name}</b>\n"
            "📊 Usage Count: <b>{uses_count} times</b>\n"
            "👥 Invited Friends: <b>{referral_count} users</b>"
        ),
        "referral_page_text": (
            "🎁 <b>Invite Your Friends!</b>\n\n"
            "Every friend who joins the bot using your link will enjoy all the free tools and thank you! 😊\n\n"
            "🔗 <b>Your referral link:</b>\n"
            "<code>https://t.me/{bot_username}?start=ref_{user_id}</code>\n\n"
            "👥 Total invited friends: <b>{referral_count} users</b>\n\n"
            "👇 Click the button below to share with friends:"
        ),
        "referral_share_msg": "🤖 Found an amazing Slides & PDF bot! Try it out:",
        "referral_bonus_notify": "🎉 <b>A new friend joined using your link!</b>\n🙌 Thank you!",
        "sub_required": "⚠️ To use the bot, please subscribe to our official channel:",
        "sub_btn": "📢 Subscribe to channel",
        "sub_check_btn": "✅ Verify",
        "sub_not_yet": "❌ You haven't subscribed to the channel yet. Please subscribe and try again.",
        "text_pdf_prompt": "📝 Send the text you want to convert into a PDF:",
        "text_pdf_generating": "⏳ Creating PDF document, please wait...",
        "text_pdf_ready": "✅ <b>PDF document is ready!</b>",
        "img_pdf_prompt": "🖼 Send images to convert into a PDF (single or as an album).",
        "img_pdf_generating": "⏳ Converting images to PDF, please wait...",
        "img_pdf_ready": "✅ <b>PDF document is ready!</b>",
        "upscale_prompt": "✨ Send an image to enhance its quality:",
        "upscale_generating": "✦ Enhancing image quality, please wait...",
        "upscale_ready": "✨ <b>Image quality successfully enhanced!</b>",
        "ai_slides_prompt": (
            "📊 <b>Professional Presentation Generator</b>\n\n"
            "🤖 A standard 12-slide academic presentation is generated automatically — <b>100% FREE!</b>\n\n"
            "Send your presentation topic:\n"
            "<i>Example: \"Artificial Intelligence Development and its Impact on Society\"</i>"
        ),
        "ai_slides_author_prompt": (
            "👤 <b>Presenter & Institution Info:</b>\n\n"
            "Enter your full name and university/workplace to appear on the title slide:\n"
            "<i>Example: \"John Doe | MIT Computer Science Student\"</i>\n\n"
            "<i>(If not needed, click the button below)</i>"
        ),
        "ai_slides_select_template": (
            "🎨 <b>Select a Presentation Design Template:</b>\n\n"
            "Topic: <b>{topic}</b>\n"
            "Presenter: <b>{author}</b>\n\n"
            "Choose one of our professional templates:"
        ),
        "ai_slides_generating": "📊 Generating professional PowerPoint (.pptx) presentation, please wait...",
        "pdf_converting_msg": "📄 Converting PowerPoint presentation to PDF, please wait...",
        "merge_pdf_prompt": "📎 Send 2 or more PDF files to merge together:",
        "merge_pdf_generating": "⏳ Merging PDF files, please wait...",
        "merge_pdf_ready": "✅ <b>PDF files successfully merged!</b>",
        "compress_pdf_prompt": "🗜 Send the PDF file you want to compress:",
        "compress_pdf_generating": "⏳ Compressing PDF file, please wait...",
        "compress_pdf_ready": "✅ <b>PDF file successfully compressed!</b>",
        "processing": "⏳ Processing, please wait...",
        "btn_passport_photo": "👔 3x4 Passport Photo",
        "passport_photo_prompt": (
            "👔 <b>Create 3x4 Passport & ID Photo</b>\n\n"
            "🎁 <b>This service is 100% FREE and unlimited!</b>\n\n"
            "Please send a clear front-facing selfie or portrait photo.\n\n"
            "<i>The bot aligns 3x4 cm proportions and creates a 6-photo printable sheet (PDF & JPG) and 1 single 3x4 HD photo.</i>"
        ),
        "passport_photo_generating": "⏳ Generating 3x4 passport photo, please wait...",
        "passport_photo_ready": "✅ <b>Your 3x4 ID Photos are ready!</b>",
        "passport_photo_error": "❌ Face could not be detected or an error occurred. Please try another photo.",
        "error_occurred": "❌ An error occurred. Please try again.",
        "fallback_text_prompt": "💡 Please select a section from the menu below 👇",
        "bot_description": "🤖 Image & PDF tools: AI Slides, quality upscaling, 3x4 ID photos.",
        "bot_short_description": "⚡️ Slides & PDF Bot",
    },
}


def t(key: str, lang: Optional[str] = None, **kwargs) -> str:
    """Get localized text by key and language code with fallback to DEFAULT_LANG."""
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
