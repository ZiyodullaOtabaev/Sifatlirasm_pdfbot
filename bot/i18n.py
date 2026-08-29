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
            "• 📊 12 betlik professional AI Slaydlar\n"
            "• 🎬 5s HD Ovozli AI Video yaratish\n"
            "• 👔 3x4 Pasport & Hujjat rasmlari tayyorlash\n"
            "• 🎙 Ovozli xabarlarni matnga o'girish (Bepul)\n"
            "• 📝 PDF yaratish, birlashtirish va siqish\n\n"
            "⬇️ Kerakli bo'limni tanlang:"
        ),
        "btn_profile": "👤 Mening profilim",
        "btn_text_pdf": "📝 Matn → PDF",
        "btn_img_pdf": "🖼 Rasm → PDF",
        "btn_merge_pdf": "📎 PDF birlashtirish",
        "btn_compress_pdf": "🗜 PDF siqish",
        "btn_upscale": "✨ Sifat oshirish (AI)",
        "btn_ai_image": "🤖 AI rasm yaratish",
        "btn_ai_video": "🎬 AI Video yaratish",
        "btn_ai_slides": "📊 AI Slayd Yaratish",
        "btn_donate": "💖 Donat",
        "btn_change_lang": "🌐 Tilni o'zgartirish",
        "btn_home": "🏠 Bosh menyu",
        "btn_top_up": "💳 Balansni to'ldirish",
        "btn_share_ref": "🎁 Do'stlarni taklif qilish (+1 Kredit)",
        "btn_share_url": "📲 Telegram'da ulashish",
        "btn_confirm_ai_video": "✅ Tushundim, video yaratish",
        "btn_skip": "⏩ O'tkazib yuborish",
        "btn_convert_pdf": "📄 PDF shaklida yuklab olish",
        "btn_admin_pay": "👤 Admin orqali to'lash (@ziyodullame)",
        "donate_text": (
            "💖 <b>Bot Rivojiga O'z Hissangizni Qo'shing!</b>\n\n"
            "Ushbu bot sizga har doim tezkor, qulay va sifatli xizmat ko'rsatishi (AI slaydlar, AI video, 3x4 hujjat rasmi, ovozdan matn, PDF vositalari) hamda bepul imkoniyatlarni saqlab qolish uchun kuchli serverlar va yuqori tezlikdagi AI hisoblash quvvatlari (GPU) talab etiladi.\n\n"
            "Siz taqdim etgan har qanday ixtiyoriy <b>donat (ehson)</b>:\n"
            "🚀 <i>Botning ishlash va qayta ishlash tezligini oshirishga;</i>\n"
            "⚡️ <i>Yangi foydali sun'iy intellekt funksiyalarini joriy etishga;</i>\n"
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
            "💰 Hisob balansi: <b>{balance} kredit</b>\n"
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
        "referral_share_msg": "🤖 Zo'r AI Video, Slayd va PDF botini topdim! Siz ham sinab ko'ring:",
        "referral_bonus_notify": "🎉 <b>Yangi do'stingiz botga qo'shildi!</b>\n🎁 Sizga <b>+1 kredit bonus</b> berildi!",
        "ai_video_refund_notify": "⚠️ <b>Video yaratishda xatolik yuz berdi.</b>\n💰 Kredit balansingizga qaytarildi!",
        "top_up_info": (
            "💳 <b>Rasmiy Xizmat Tariflari va To'lovlar:</b>\n\n"
            "👔 <b>3x4 Hujjat Rasmi:</b> 2 kredit <i>(1 000 so'm yoki ⭐️ 10 Stars — 3 ta bepul)</i>\n"
            "🎙 <b>Ovozdan Matn:</b> 100% BEPUL <i>(Cheksiz)</i>\n"
            "🎬 <b>AI Video (1 ta):</b> 4 kredit <i>(1 500 so'm yoki ⭐️ 15 Stars — 2 ta bepul)</i>\n"
            "📊 <b>AI Slayd (12 bet):</b> 7 kredit <i>(2 000 so'm yoki ⭐️ 20 Stars — 1-si bepul)</i>\n"
            "🤖 <b>AI Rasm (1 ta):</b> 2 kredit <i>(500 so'm yoki ⭐️ 10 Stars — 7 ta bepul)</i>\n"
            "🖼 <b>Rasm ➡️ PDF:</b> 1 Yillik Cheksiz Pass <i>(5 000 so'm yoki ⭐️ 50 Stars — 50 ta bepul)</i>\n\n"
            "⭐️ <b>Telegram Stars</b> orqali pastdagi tugmalar bilan 1 soniyada to'lashingiz mumkin!\n"
            "💳 <b>Karta orqali to'lash</b> uchun admin @ziyodullame ga murojaat qiling 👇"
        ),
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
        "upscale_generating": "✦ AI rasm sifatini oshirmoqda, kuting...",
        "upscale_ready": "✨ <b>Rasm sifati oshirildi!</b>",
        "bg_remove_prompt": "🎨 Fonini olib tashlamoqchi bo'lgan rasmingizni yuboring:",
        "bg_remove_generating": "✦ Rasm foni olib tashlanmoqda, kuting...",
        "bg_remove_ready": "🎨 <b>Fon muvaffaqiyatli olib tashlandi!</b>",
        "ai_image_prompt": "🤖 AI rasm yaratish uchun tavsif (prompt) yuboring (O'zbek, Rus yoki Ingliz tilida):\n<i>Masalan: Koinotda uchayotgan mushuk, 8k photo</i>",
        "ai_image_generating": "✦ AI rasm yaratmoqda, kuting...",
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
        "ai_slides_select_template": (
            "🎨 <b>Slayd Dizayn Shablonini Tanlang:</b>\n\n"
            "Mavzu: <b>{topic}</b>\n"
            "Taqdimotchi: <b>{author}</b>\n\n"
            "O'zingizga ma'qul professional shablondan birini tanlang:"
        ),
        "ai_slides_insufficient_balance": (
            "📊 <b>AI Slayd Yaratish (Pullik xizmat)</b>\n\n"
            "📌 1 ta to'liq professional slayd (12 bet) narxi: <b>7 kredit (2 000 so'm yoki ⭐️ 20 Stars)</b>\n"
            "💰 Sizning balansingiz: <b>{balance} kredit</b>\n\n"
            "Davom etish uchun balansingizni to'ldiring 👇"
        ),
        "ai_slides_generating": "📊 Professional PowerPoint (.pptx) slayd taqdimoti yaratilmoqda, biroz kuting...",
        "pdf_converting_msg": "📄 PowerPoint slayd PDF shakliga o'tkazilmoqda, biroz kuting...",
        "ai_video_prompt": (
            "🎬 <b>AI Video yaratish</b>\n\n"
            "Qanday video hosil qilishni istaysiz? Tavsif (prompt) yuboring:\n"
            "<i>O'zbek, Rus yoki Ingliz tilida yozishingiz mumkin!</i>\n\n"
            "<i>Masalan: \"Koinotda uchayotgan mushuk, kinematik 4k video\"</i>"
        ),
        "ai_video_insufficient_balance": (
            "🎬 <b>AI Video yaratish (Pullik xizmat)</b>\n\n"
            "📌 1 ta AI video narxi: <b>4 kredit (1 500 so'm yoki ⭐️ 15 Stars)</b>\n"
            "💰 Sizning balansingiz: <b>{balance} kredit</b>\n\n"
            "❌ Balansingizda kredit yetarli emas.\n"
            "Telegram Stars yoki admin @ziyodullame orqali to'ldirishingiz mumkin 👇"
        ),
        "ai_video_generating": "🎬 AI Video yaratilmoqda... Bu jarayon 1-2 daqiqa vaqt olishi mumkin, kuting...",
        "merge_pdf_prompt": "📎 Birlashtirish uchun 2 yoki undan ortiq PDF fayllarni yuboring:",
        "merge_pdf_generating": "⏳ PDF fayllar birlashtirilmoqda, kuting...",
        "merge_pdf_ready": "✅ <b>PDF fayllar muvaffaqiyatli birlashtirildi!</b>",
        "compress_pdf_prompt": "🗜 Hajmini siqmoqchi bo'lgan PDF faylingizni yuboring:",
        "compress_pdf_generating": "⏳ PDF fayl siqilmoqda, kuting...",
        "compress_pdf_ready": "✅ <b>PDF fayl muvaffaqiyatli siqildi!</b>",
        "processing": "⏳ Qayta ishlanmoqda, kuting...",
        "btn_passport_photo": "👔 3x4 Hujjat rasmi",
        "btn_voice_to_text": "🎙 Ovozdan matn",
        "btn_voice_to_pdf": "📄 Matndan PDF qilish",
        "btn_voice_to_slides": "📊 12 betlik Slayd yasash",
        "passport_photo_prompt": (
            "👔 <b>3x4 Pasport va Hujjat Rasmi Yaratish</b>\n\n"
            "🎁 <b>Sizda 3 ta bepul imkoniyat bor!</b>\n\n"
            "Iltimos, to'g'riga qaragan sifatli selfi yoki portret rasm yuboring.\n\n"
            "<i>Bot fonni tozalab oq qiladi, 3x4 sm o'lchamga moslaydi va chop etishga tayyor 6 talik varaq (PDF va JPG) hamda 1 dona 3x4 HD rasm beradi.</i>"
        ),
        "passport_photo_generating": "⏳ 3x4 hujjat rasmi tayyorlanmoqda, iltimos kuting...",
        "passport_photo_ready": "✅ <b>3x4 Hujjat rasmingiz tayyor!</b>",
        "passport_photo_error": "❌ Rasmda inson yuzi aniqlanmadi yoki qayta ishlashda xatolik yuz berdi. Boshqa rasm bilan urinib ko'ring.",
        "voice_to_text_prompt": (
            "🎙 <b>Ovozni Matnga O'girish (Voice-to-Text)</b>\n\n"
            "🎁 <b>Ushbu xizmat mutlaqo BEPUL!</b>\n\n"
            "Iltimos, Telegram ovozli xabari (Voice) yoki audio fayl (mp3, m4a, ogg) yuboring.\n\n"
            "<i>O'zbek, Rus yoki Ingliz tilidagi nutq avtomatik aniqlanib, toza matnga aylantiriladi.</i>"
        ),
        "voice_to_text_generating": "⏳ Ovozli xabar tinglanmoqda va matnga o'girilmoqda...",
        "voice_to_text_ready": (
            "🎙 <b>Ovozli xabar matnga o'girildi:</b>\n\n"
            "<code>{text}</code>\n\n"
            "⬇️ <b>Ushbu matn bilan nima qilamiz?</b>"
        ),
        "voice_to_text_empty": "❌ Ovozdan matn ajratib bo'lmadi yoki audio juda past/qisqa.",
        "error_occurred": "❌ Xatolik yuz berdi. Qayta urinib ko'ring.",
        "fallback_text_prompt": "💡 Iltimos, pastdagi menyudan kerakli bo'limni tanlang 👇",
        "bot_description": "🤖 Rasmlar va PDF hujjatchalar bilan ishlash, AI Slayd, AI sifat oshirish, fon olib tashlash va AI Video bot.",
        "bot_short_description": "⚡️ PDF & AI Video Bot",
    },
    "ru": {
        "lang_select_prompt": "🌐 <b>Пожалуйста, выберите язык / Please select a language:</b>",
        "lang_selected": "✅ Язык успешно выбран: <b>Русский</b> 🇷🇺",
        "welcome_text": (
            "👋 <b>Здравствуйте!</b>\n\n"
            "🛠 Я помогу вам в следующем:\n"
            "• 📊 Презентации из 12 слайдов (AI)\n"
            "• 🎬 Создание HD AI видео со звуком\n"
            "• 👔 Создание фото 3x4 на документы\n"
            "• 🎙 Перевод голоса в текст (Бесплатно)\n"
            "• 📝 Создание, объединение и сжатие PDF\n\n"
            "⬇️ Выберите нужный раздел:"
        ),
        "btn_profile": "👤 Мой профиль",
        "btn_text_pdf": "📝 Текст → PDF",
        "btn_img_pdf": "🖼 Фото → PDF",
        "btn_merge_pdf": "📎 Объединить PDF",
        "btn_compress_pdf": "🗜 Сжать PDF",
        "btn_upscale": "✨ Улучшить качество (AI)",
        "btn_ai_image": "🤖 AI Генерация фото",
        "btn_ai_video": "🎬 AI Генерация видео",
        "btn_ai_slides": "📊 AI Создание слайдов",
        "btn_donate": "💖 Донат",
        "btn_change_lang": "🌐 Сменить язык",
        "btn_home": "🏠 Главное меню",
        "btn_top_up": "💳 Пополнить баланс",
        "btn_share_ref": "🎁 Пригласить друзей (+1 Кредит)",
        "btn_share_url": "📲 Поделиться в Telegram",
        "btn_confirm_ai_video": "✅ Понятно, создать видео",
        "btn_skip": "⏩ Пропустить",
        "btn_convert_pdf": "📄 Скачать в формате PDF",
        "btn_admin_pay": "👤 Оплата через админа (@ziyodullame)",
        "donate_text": (
            "💖 <b>Поддержите Развитие Проекта!</b>\n\n"
            "Чтобы бот продолжал работать быстро, стабильно и качественно (AI слайды, AI видео, фото 3x4, голос в текст, PDF инструменты), требуются мощные серверы и высокоскоростные мощности AI (GPU).\n\n"
            "Каждый ваш добровольный <b>донат</b> напрямую помогает:\n"
            "🚀 <i>Увеличить скорость обработки запросов в боте;</i>\n"
            "⚡️ <i>Внедрять новые полезные функции искусственного интеллекта;</i>\n"
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
            "💰 Баланс аккаунта: <b>{balance} кредитов</b>\n"
            "👥 Приглашено друзей: <b>{referral_count} чел.</b>"
        ),
        "referral_page_text": (
            "🎁 <b>Приглашайте друзей и получайте кредиты!</b>\n\n"
            "За каждого друга, перешедшего по вашей ссылке, вы получаете <b>+1 кредит бонус</b>!\n\n"
            "🔗 <b>Ваша реферальная ссылка:</b>\n"
            "<code>https://t.me/{bot_username}?start=ref_{user_id}</code>\n\n"
            "👥 Всего приглашено: <b>{referral_count} чел.</b>\n\n"
            "👇 Нажмите кнопку ниже, чтобы поделиться ссылкой:"
        ),
        "referral_share_msg": "🤖 Нашел отличного бота для создания AI видео, презентаций и PDF! Попробуй:",
        "referral_bonus_notify": "🎉 <b>Новый друг присоединился по вашей ссылке!</b>\n🎁 Вам начислен <b>+1 кредит бонус</b>!",
        "ai_video_refund_notify": "⚠️ <b>Ошибка при создании видео.</b>\n💰 Кредиты возвращены на ваш баланс!",
        "top_up_info": (
            "💳 <b>Официальные Тарифы и Оплата Услуг:</b>\n\n"
            "👔 <b>Фото 3x4 на Документы:</b> 2 кредита <i>(1 000 сум или ⭐️ 10 Stars — 3 бесплатно)</i>\n"
            "🎙 <b>Голос в Текст:</b> 100% БЕСПЛАТНО <i>(Безлимит)</i>\n"
            "🎬 <b>AI Видео (1 шт):</b> 4 кредита <i>(1 500 сум или ⭐️ 15 Stars — 2 бесплатно)</i>\n"
            "📊 <b>AI Слайды (12 стр):</b> 7 кредитов <i>(2 000 сум или ⭐️ 20 Stars — 1-я бесплатно)</i>\n"
            "🤖 <b>AI Фото (1 шт):</b> 2 кредита <i>(500 сум или ⭐️ 10 Stars — 7 бесплатно)</i>\n"
            "🖼 <b>Фото ➡️ PDF:</b> Безлимит на 1 год <i>(5 000 сум или ⭐️ 50 Stars — 50 бесплатно)</i>\n\n"
            "⭐️ Оплата через <b>Telegram Stars</b> моментально по кнопкам ниже!\n"
            "💳 Для оплаты картой напишите админу @ziyodullame 👇"
        ),
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
        "upscale_generating": "✦ ИИ улучшает качество изображения, подождите...",
        "upscale_ready": "✨ <b>Качество изображения успешно улучшено!</b>",
        "bg_remove_prompt": "🎨 Отправьте изображение, чтобы удалить фон:",
        "bg_remove_generating": "✦ ИИ удаляет фон с изображения, подождите...",
        "bg_remove_ready": "🎨 <b>Фон успешно удален!</b>",
        "ai_image_prompt": "🤖 Отправьте описание (промпт) для генерации фото (на Узбекском, Русском или Английском):\n<i>Например: Кот летящий в космосе, 8k photo</i>",
        "ai_image_generating": "✦ ИИ генерирует изображение, подождите...",
        "ai_slides_prompt": (
            "📊 <b>AI Генератор презентаций</b>\n\n"
            "🤖 Презентация на 12 слайдов создается автоматически на базе <b>Google Gemini & FLUX AI</b>!\n\n"
            "{trial_text}\n"
            "💰 Ваш баланс: <b>{balance} кредитов</b>\n\n"
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
        "ai_slides_insufficient_balance": (
            "📊 <b>AI Генератор слайдов (Платная услуга)</b>\n\n"
            "📌 Стоимость презентации (12 слайдов): <b>7 кредитов (2 000 сум или ⭐️ 20 Stars)</b>\n"
            "💰 Ваш баланс: <b>{balance} кредитов</b>\n\n"
            "Для продолжения пополните баланс 👇"
        ),
        "ai_slides_generating": "📊 Создается профессиональная презентация PowerPoint (.pptx), пожалуйста подождите...",
        "pdf_converting_msg": "📄 Презентация конвертируется в формат PDF, пожалуйста подождите...",
        "ai_video_prompt": (
            "🎬 <b>AI Генерация видео</b>\n\n"
            "Отправьте описание (промпт) для видео:\n"
            "<i>Вы можете писать на Узбекском, Русском или Английском языке!</i>\n\n"
            "<i>Например: \"Кот летящий в космосе, кинематографическое 4k видео\"</i>"
        ),
        "ai_video_insufficient_balance": (
            "🎬 <b>AI Генерация видео (Платная услуга)</b>\n\n"
            "📌 Стоимость 1 ИИ видео: <b>4 кредита (1 500 сум или ⭐️ 15 Stars)</b>\n"
            "💰 Ваш баланс: <b>{balance} кредитов</b>\n\n"
            "❌ На вашем балансе недостаточно кредитов.\n"
            "Вы можете пополнить баланс через Telegram Stars или написав админу @ziyodullame 👇"
        ),
        "ai_video_generating": "🎬 Создание ИИ видео... Это может занять 1-2 минуты, пожалуйста подождите...",
        "merge_pdf_prompt": "📎 Отправьте 2 или более PDF-файла для объединения:",
        "merge_pdf_generating": "⏳ Объединение PDF файлов, пожалуйста подождите...",
        "merge_pdf_ready": "✅ <b>PDF файлы успешно объединены!</b>",
        "compress_pdf_prompt": "🗜 Отправьте PDF-файл, который вы хотите сжать:",
        "compress_pdf_generating": "⏳ Сжатие PDF файла, пожалуйста подождите...",
        "compress_pdf_ready": "✅ <b>PDF файл успешно сжат!</b>",
        "processing": "⏳ Обработка, пожалуйста подождите...",
        "btn_passport_photo": "👔 Фото 3x4 на документы",
        "btn_voice_to_text": "🎙 Голос в текст",
        "btn_voice_to_pdf": "📄 Создать PDF из текста",
        "btn_voice_to_slides": "📊 12 слайдов презентация",
        "passport_photo_prompt": (
            "👔 <b>Создание Фото 3x4 на Документы</b>\n\n"
            "🎁 <b>У вас 3 бесплатные попытки!</b>\n\n"
            "Пожалуйста, отправьте четкое селфи или портретное фото.\n\n"
            "<i>Бот сделает белый фон, выровняет пропорции 3x4 и создаст готовый лист на 6 фото для печати (PDF и JPG) и 1 одиночное фото 3x4 HD.</i>"
        ),
        "passport_photo_generating": "⏳ Создается фото 3x4, пожалуйста подождите...",
        "passport_photo_ready": "✅ <b>Ваши фото 3x4 готовы!</b>",
        "passport_photo_error": "❌ Лицо на фото не обнаружено или произошла ошибка. Попробуйте другое фото.",
        "voice_to_text_prompt": (
            "🎙 <b>Перевод Голоса в Текст (Voice-to-Text)</b>\n\n"
            "🎁 <b>Эта услуга абсолютно БЕСПЛАТНА!</b>\n\n"
            "Пожалуйста, отправьте голосовое сообщение (Voice) или аудиофайл (mp3, m4a, ogg).\n\n"
            "<i>Узбекская, русская или английская речь будет автоматически переведена в чистый текст.</i>"
        ),
        "voice_to_text_generating": "⏳ Распознаем речь и переводим в текст...",
        "voice_to_text_ready": (
            "🎙 <b>Распознанный текст:</b>\n\n"
            "<code>{text}</code>\n\n"
            "⬇️ <b>Что сделать с этим текстом?</b>"
        ),
        "voice_to_text_empty": "❌ Не удалось распознать речь или запись слишком тихая.",
        "error_occurred": "❌ Произошла ошибка. Попробуйте снова.",
        "fallback_text_prompt": "💡 Пожалуйста, выберите нужный раздел в меню ниже 👇",
        "bot_description": "🤖 Бот для работы с фото и PDF, создание AI слайдов, улучшение качества, удаление фона и AI видео.",
        "bot_short_description": "⚡️ PDF & AI Video Bot",
    },
    "en": {
        "lang_select_prompt": "🌐 <b>Please select a language:</b>",
        "lang_selected": "✅ Language successfully set to: <b>English</b> 🇬🇧",
        "welcome_text": (
            "👋 <b>Welcome!</b>\n\n"
            "🛠 I can help you with:\n"
            "• 📊 12-Slide AI Presentations\n"
            "• 🎬 5s HD AI Video Generator with Audio\n"
            "• 👔 3x4 Passport & ID Photo Maker\n"
            "• 🎙 Voice to Text Transcriber (Free)\n"
            "• 📝 PDF creation, merging & compression\n\n"
            "⬇️ Select an option below:"
        ),
        "btn_profile": "👤 My Profile",
        "btn_text_pdf": "📝 Text → PDF",
        "btn_img_pdf": "🖼 Image → PDF",
        "btn_merge_pdf": "📎 Merge PDF",
        "btn_compress_pdf": "🗜 Compress PDF",
        "btn_upscale": "✨ Upscale Quality (AI)",
        "btn_ai_image": "🤖 AI Image Generator",
        "btn_ai_video": "🎬 AI Video Generator",
        "btn_ai_slides": "📊 AI Slides Generator",
        "btn_donate": "💖 Donate",
        "btn_change_lang": "🌐 Change Language",
        "btn_home": "🏠 Main Menu",
        "btn_top_up": "💳 Top-up Balance",
        "btn_share_ref": "🎁 Invite Friends (+1 Credit)",
        "btn_share_url": "📲 Share via Telegram",
        "btn_confirm_ai_video": "✅ I understand, create video",
        "btn_skip": "⏩ Skip",
        "btn_convert_pdf": "📄 Download as PDF",
        "btn_admin_pay": "👤 Pay via Admin (@ziyodullame)",
        "donate_text": (
            "💖 <b>Support the Bot Development!</b>\n\n"
            "To ensure the bot keeps delivering fast, high-quality, and seamless services (AI slides, AI video, 3x4 passport photos, voice-to-text, PDF tools), high-performance cloud servers and advanced AI GPUs are utilized 24/7.\n\n"
            "Any voluntary <b>donation</b> directly contributes to:\n"
            "🚀 <i>Boosting the bot's speed and response time;</i>\n"
            "⚡️ <i>Implementing brand new cutting-edge AI features;</i>\n"
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
            "💰 Account Balance: <b>{balance} credits</b>\n"
            "👥 Invited Friends: <b>{referral_count} users</b>"
        ),
        "referral_page_text": (
            "🎁 <b>Invite Friends & Earn Credits!</b>\n\n"
            "For every friend who joins the bot using your link, you will receive a <b>+1 credit bonus</b>!\n\n"
            "🔗 <b>Your referral link:</b>\n"
            "<code>https://t.me/{bot_username}?start=ref_{user_id}</code>\n\n"
            "👥 Total invited friends: <b>{referral_count} users</b>\n\n"
            "👇 Click the button below to share with friends:"
        ),
        "referral_share_msg": "🤖 Found an amazing AI Video, Slides and PDF bot! Try it out:",
        "referral_bonus_notify": "🎉 <b>A new friend joined using your link!</b>\n🎁 You received a <b>+1 credit bonus</b>!",
        "ai_video_refund_notify": "⚠️ <b>An error occurred during video generation.</b>\n💰 Credits refunded to your balance!",
        "top_up_info": (
            "💳 <b>Official Tariffs and Payments:</b>\n\n"
            "👔 <b>3x4 Passport Photo:</b> 2 credits <i>(1,000 UZS or ⭐️ 10 Stars — 3 free)</i>\n"
            "🎙 <b>Voice to Text:</b> 100% FREE <i>(Unlimited)</i>\n"
            "🎬 <b>AI Video (1 video):</b> 4 credits <i>(1,500 UZS or ⭐️ 15 Stars — 2 free trial)</i>\n"
            "📊 <b>AI Slides (12 pages):</b> 7 credits <i>(2,000 UZS or ⭐️ 20 Stars — 1st free)</i>\n"
            "🤖 <b>AI Image (1 image):</b> 2 credits <i>(500 UZS or ⭐️ 10 Stars — 7 free)</i>\n"
            "🖼 <b>Image ➡️ PDF:</b> 1-Year Unlimited Pass <i>(5,000 UZS or ⭐️ 50 Stars — 50 free)</i>\n\n"
            "⭐️ Instant top-up via <b>Telegram Stars</b> using the buttons below!\n"
            "💳 To pay via Card/Admin, contact @ziyodullame 👇"
        ),
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
        "upscale_generating": "✦ AI is enhancing image quality, please wait...",
        "upscale_ready": "✨ <b>Image quality successfully enhanced!</b>",
        "bg_remove_prompt": "🎨 Send an image to remove its background:",
        "bg_remove_generating": "✦ AI is removing background, please wait...",
        "bg_remove_ready": "🎨 <b>Background successfully removed!</b>",
        "ai_image_prompt": "🤖 Send a prompt description for AI image generation (in Uzbek, Russian or English):\n<i>Example: A cat flying in space, 8k photo</i>",
        "ai_image_generating": "✦ AI is generating your image, please wait...",
        "ai_slides_prompt": (
            "📊 <b>AI Presentation Generator</b>\n\n"
            "🤖 A standard 12-page presentation is automatically generated using <b>Google Gemini & FLUX AI Engine</b>!\n\n"
            "{trial_text}\n"
            "💰 Your balance: <b>{balance} credits</b>\n\n"
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
        "ai_slides_insufficient_balance": (
            "📊 <b>AI Presentation Generator (Paid Service)</b>\n\n"
            "📌 Full presentation (12 pages) price: <b>7 credits (2,000 UZS or ⭐️ 20 Stars)</b>\n"
            "💰 Your balance: <b>{balance} credits</b>\n\n"
            "Top up your balance to continue 👇"
        ),
        "ai_slides_generating": "📊 Generating professional PowerPoint (.pptx) presentation, please wait...",
        "pdf_converting_msg": "📄 Converting PowerPoint presentation to PDF, please wait...",
        "ai_video_prompt": (
            "🎬 <b>AI Video Generator</b>\n\n"
            "Send a prompt description for your video:\n"
            "<i>You can type in Uzbek, Russian, or English!</i>\n\n"
            "<i>Example: \"A cat flying in space, cinematic 4k video\"</i>"
        ),
        "ai_video_insufficient_balance": (
            "🎬 <b>AI Video Generator (Paid Service)</b>\n\n"
            "📌 Price per 1 AI Video: <b>4 credits (1,500 UZS or ⭐️ 15 Stars)</b>\n"
            "💰 Your balance: <b>{balance} credits</b>\n\n"
            "❌ Insufficient credits on your balance.\n"
            "You can top up via Telegram Stars or by contacting admin @ziyodullame 👇"
        ),
        "ai_video_generating": "🎬 Generating AI Video... This may take 1-2 minutes, please wait...",
        "merge_pdf_prompt": "📎 Send 2 or more PDF files to merge together:",
        "merge_pdf_generating": "⏳ Merging PDF files, please wait...",
        "merge_pdf_ready": "✅ <b>PDF files successfully merged!</b>",
        "compress_pdf_prompt": "🗜 Send the PDF file you want to compress:",
        "compress_pdf_generating": "⏳ Compressing PDF file, please wait...",
        "compress_pdf_ready": "✅ <b>PDF file successfully compressed!</b>",
        "processing": "⏳ Processing, please wait...",
        "btn_passport_photo": "👔 3x4 Passport Photo",
        "btn_voice_to_text": "🎙 Voice to Text",
        "btn_voice_to_pdf": "📄 Convert to PDF",
        "btn_voice_to_slides": "📊 12 Slides Presentation",
        "passport_photo_prompt": (
            "👔 <b>Create 3x4 Passport & ID Photo</b>\n\n"
            "🎁 <b>You have 3 free generations!</b>\n\n"
            "Please send a clear front-facing selfie or portrait photo.\n\n"
            "<i>The bot cleans the background to white, aligns 3x4 cm proportions, and creates a 6-photo printable sheet (PDF & JPG) and 1 single 3x4 HD photo.</i>"
        ),
        "passport_photo_generating": "⏳ Generating 3x4 passport photo, please wait...",
        "passport_photo_ready": "✅ <b>Your 3x4 ID Photos are ready!</b>",
        "passport_photo_error": "❌ Face could not be detected or an error occurred. Please try another photo.",
        "voice_to_text_prompt": (
            "🎙 <b>Voice to Text Transcriber</b>\n\n"
            "🎁 <b>This service is 100% FREE!</b>\n\n"
            "Please send a voice message (Voice) or audio file (mp3, m4a, ogg).\n\n"
            "<i>Uzbek, Russian, or English speech will be accurately transcribed into text.</i>"
        ),
        "voice_to_text_generating": "⏳ Transcribing audio, please wait...",
        "voice_to_text_ready": (
            "🎙 <b>Transcribed Text:</b>\n\n"
            "<code>{text}</code>\n\n"
            "⬇️ <b>What would you like to do with this text?</b>"
        ),
        "voice_to_text_empty": "❌ Could not recognize any speech or audio is too quiet.",
        "error_occurred": "❌ An error occurred. Please try again.",
        "fallback_text_prompt": "💡 Please select a section from the menu below 👇",
        "bot_description": "🤖 Image & PDF tools, AI Slides, AI Upscaling, Background Removal & AI Video bot.",
        "bot_short_description": "⚡️ PDF & AI Video Bot",
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
