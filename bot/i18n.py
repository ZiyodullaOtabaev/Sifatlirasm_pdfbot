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
            "🛠 <b>PDF Asboblar Botiga Xush Kelibsiz!</b>\n"
            "Men sizga barcha turdagi PDF hujjatlar bilan ishlashda yordam beraman:\n\n"
            "• 📝 <b>Matn → PDF</b> — Matnlarni chiroyli PDF hujjatga aylantirish\n"
            "• 🖼 <b>Rasm → PDF</b> — Rasmlardan sifatli va tartibli PDF yaratish\n"
            "• 📎 <b>PDF birlashtirish</b> — Bir nechta faylni bitta PDF qilish\n"
            "• 🗜 <b>PDF siqish</b> — Sifatni saqlagan holda fayl hajmini kichraytirish\n\n"
            "⬇️ Kerakli bo'limni tanlang:"
        ),
        "btn_profile": "👤 Mening profilim",
        "btn_text_pdf": "📝 Matn → PDF",
        "btn_img_pdf": "🖼 Rasm → PDF",
        "btn_pdf_to_img": "🖼 PDF → Rasm",
        "btn_split_pdf": "✂️ PDF ajratish",
        "btn_delete_pages": "🗑 Sahifa o'chirish",
        "btn_watermark_pdf": "💧 Suv belgisi",
        "btn_merge_pdf": "📎 PDF birlashtirish",
        "btn_compress_pdf": "🗜 PDF siqish",
        "btn_upscale": "✨ Sifat oshirish (AI)",
        "btn_ai_image": "🤖 AI rasm yaratish",
        "btn_ai_video": "🎬 AI Video yaratish",
        "btn_ai_slides": "📊 AI Slayd Yaratish",
        "btn_change_lang": "🌐 Tilni o'zgartirish",
        "btn_home": "🏠 Bosh menyu",
        "btn_top_up": "💳 Balansni to'ldirish",
        "btn_share_ref": "🎁 Do'stlarga ulashish",
        "btn_share_url": "📲 Telegram'da ulashish",
        "btn_confirm_ai_video": "✅ Tushundim",
        "btn_skip": "⏩ O'tkazib yuborish",
        "btn_convert_pdf": "📄 PDF shaklida yuklab olish",
        "btn_admin_pay": "👤 Admin (@ziyodullame)",
        "profile_text": (
            "👤 <b>Foydalanuvchi Profili</b>\n\n"
            "🆔 ID: <code>{user_id}</code>\n"
            "🌐 Til: <b>{lang_name}</b>\n"
            "📊 Ishlatilgan xizmatlar: <b>{uses_count} marta</b>\n"
            "👥 Taklif qilgan do'stlaringiz: <b>{referral_count} ta</b>\n"
            "🌐 Jami foydalanuvchilarimiz: <b>{total_users:,} ta</b>"
        ),
        "referral_page_text": (
            "🎁 <b>Do'stlarni Taklif Qiling!</b>\n\n"
            "Botingizni yaqinlaringiz va do'stlaringizga ulashing, ularga ham tezkor va bepul PDF xizmatlaridan foydalanishga yordam bering!\n\n"
            "🔗 <b>Sizning shaxsiy havolangiz:</b>\n"
            "<code>https://t.me/{bot_username}?start=ref_{user_id}</code>\n\n"
            "👥 Jami taklif qilgan do'stlaringiz: <b>{referral_count} ta</b>\n\n"
            "👇 Do'stlaringizga ulashish uchun pastdagi tugmani bosing:"
        ),
        "referral_share_msg": "🤖 Eng qulay va sifatli bepul PDF botini topdim! Siz ham sinab ko'ring:",
        "referral_bonus_notify": "🎉 <b>Yangi do'stingiz botga qo'shildi!</b>",
        "ai_video_refund_notify": "⚠️ <b>Xatolik yuz berdi.</b>\n💰 Kredit balansingizga qaytarildi!",
        "top_up_info": (
            "💳 <b>Rasmiy Xizmat Tariflari va VIP Pass:</b>\n\n"
            "🖼 <b>Rasm ➡️ PDF 1 Yillik VIP Pass:</b> 5 000 so'm yoki ⭐️ 50 Stars <i>(50 ta bepul)</i>\n"
            "📝 <b>Matn ➡️ PDF:</b> 100% BEPUL\n"
            "📎 <b>PDF Birlashtirish:</b> 100% BEPUL\n"
            "🗜 <b>PDF Siqish:</b> 100% BEPUL\n\n"
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
        "pdf_to_img_prompt": "🖼 <b>PDF ➡️ Rasm xizmati:</b>\n\nRasmga aylantirmoqchi bo'lgan PDF faylingizni yuboring:",
        "pdf_to_img_generating": "⏳ <i>PDF sahifalari rasmga aylantirilmoqda, kuting...</i>",
        "pdf_to_img_ready": "✅ <b>PDF sahifalari rasmga aylantirildi!</b>",
        "split_pdf_prompt": "✂️ <b>PDF Sahifalarini Ajratish:</b>\n\nKerakli sahifalarini ajratib olmoqchi bo'lgan PDF faylingizni yuboring:",
        "split_pdf_pages_prompt": "📄 <b>Faylda jami {total} ta sahifa bor.</b>\n\nQaysi sahifalarni ajratib olmoqchisiz?\nOraliq yoki raqamlarni yozing (masalan: <code>1-3, 5, 8</code>):",
        "split_pdf_generating": "⏳ <i>Tanlangan sahifalar ajratilmoqda...</i>",
        "split_pdf_ready": "✅ <b>Tanlangan {count} ta sahifa muvaffaqiyatli ajratib olindi!</b>",
        "delete_pages_prompt": "🗑 <b>PDF dan Sahifa O'chirish:</b>\n\nSahifalarini o'chirmoqchi bo'lgan PDF faylingizni yuboring:",
        "delete_pages_input_prompt": "📄 <b>Faylda jami {total} ta sahifa bor.</b>\n\nQaysi sahifalarni o'chirmoqchisiz?\nRaqamlarni vergul bilan yozing (masalan: <code>2, 5</code> yoki <code>3-6</code>):",
        "delete_pages_generating": "⏳ <i>Belgilangan sahifalar o'chirilmoqda...</i>",
        "delete_pages_ready": "✅ <b>Sahifalar olib tashlandi! Qolgan sahifalar: {count} ta</b>",
        "watermark_prompt": "💧 <b>PDF ga Suv Belgisi Qo'yish:</b>\n\nSuv belgisi qo'ymoqchi bo'lgan PDF faylingizni yuboring:",
        "watermark_text_prompt": "✍️ <b>Suv belgisi matnini yuboring:</b>\n\nMasalan: <i>@kanalingiz</i> yoki <i>MAXFIY</i>",
        "watermark_generating": "⏳ <i>Sahifalarga suv belgisi tushirilmoqda...</i>",
        "watermark_ready": "✅ <b>Suv belgisi barcha {count} ta sahifaga muvaffaqiyatli qo'yildi!</b>",
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
        "bot_description": "🤖 Rasmlar va matnlarni PDF qilish, PDF fayllarni birlashtirish va hajmini sifatli siqish boti.",
        "bot_short_description": "⚡️ Sifatli PDF Bot",
    },
    "ru": {
        "lang_select_prompt": "🌐 <b>Пожалуйста, выберите язык / Please select a language:</b>",
        "lang_selected": "✅ Язык успешно выбран: <b>Русский</b> 🇷🇺",
        "welcome_text": (
            "👋 <b>Здравствуйте!</b>\n\n"
            "🛠 <b>Добро пожаловать в PDF Инструменты!</b>\n"
            "Я помогу вам быстро и удобно работать с PDF документами:\n\n"
            "• 📝 <b>Текст → PDF</b> — Конвертация текста в аккуратный PDF документ\n"
            "• 🖼 <b>Фото → PDF</b> — Создание качественного PDF из ваших фото\n"
            "• 📎 <b>Объединить PDF</b> — Слияние нескольких файлов в один PDF\n"
            "• 🗜 <b>Сжать PDF</b> — Уменьшение размера файлов без потери качества\n\n"
            "⬇️ Выберите нужный раздел:"
        ),
        "btn_profile": "👤 Мой профиль",
        "btn_text_pdf": "📝 Текст → PDF",
        "btn_img_pdf": "🖼 Фото → PDF",
        "btn_pdf_to_img": "🖼 PDF → Фото",
        "btn_split_pdf": "✂️ Разделить PDF",
        "btn_delete_pages": "🗑 Удалить страницы",
        "btn_watermark_pdf": "💧 Водяной знак",
        "btn_merge_pdf": "📎 Объединить PDF",
        "btn_compress_pdf": "🗜 Сжать PDF",
        "btn_upscale": "✨ Улучшить качество (AI)",
        "btn_ai_image": "🤖 AI Генерация фото",
        "btn_ai_video": "🎬 AI Генерация видео",
        "btn_ai_slides": "📊 AI Создание слайдов",
        "btn_change_lang": "🌐 Сменить язык",
        "btn_home": "🏠 Главное меню",
        "btn_top_up": "💳 Пополнить баланс",
        "btn_share_ref": "🎁 Поделиться с друзьями",
        "btn_share_url": "📲 Поделиться в Telegram",
        "btn_confirm_ai_video": "✅ Понятно",
        "btn_skip": "⏩ Пропустить",
        "btn_convert_pdf": "📄 Скачать в формате PDF",
        "btn_admin_pay": "👤 Админ (@ziyodullame)",
        "profile_text": (
            "👤 <b>Профиль пользователя</b>\n\n"
            "🆔 ID: <code>{user_id}</code>\n"
            "🌐 Язык: <b>{lang_name}</b>\n"
            "📊 Использовано сервисов: <b>{uses_count} раз</b>\n"
            "👥 Приглашено друзей: <b>{referral_count} чел.</b>\n"
            "🌐 Всего пользователей бота: <b>{total_users:,}</b>"
        ),
        "referral_page_text": (
            "🎁 <b>Приглашайте друзей!</b>\n\n"
            "Поделитесь ботом с друзьями и коллегами, чтобы они также могли удобно и бесплатно работать с PDF!\n\n"
            "🔗 <b>Ваша реферальная ссылка:</b>\n"
            "<code>https://t.me/{bot_username}?start=ref_{user_id}</code>\n\n"
            "👥 Всего приглашено: <b>{referral_count} чел.</b>\n\n"
            "👇 Нажмите кнопку ниже, чтобы поделиться ссылкой:"
        ),
        "referral_share_msg": "🤖 Нашел отличного и бесплатного PDF бота! Попробуй:",
        "referral_bonus_notify": "🎉 <b>Новый друг присоединился по вашей ссылке!</b>",
        "ai_video_refund_notify": "⚠️ <b>Произошла ошибка.</b>\n💰 Кредиты возвращены на ваш баланс!",
        "top_up_info": (
            "💳 <b>Официальные Тарифы и VIP Pass:</b>\n\n"
            "🖼 <b>Фото ➡️ PDF VIP Pass на 1 год:</b> 5 000 сум или ⭐️ 50 Stars <i>(50 бесплатно)</i>\n"
            "📝 <b>Текст ➡️ PDF:</b> 100% БЕСПЛАТНО\n"
            "📎 <b>Объединение PDF:</b> 100% БЕСПЛАТНО\n"
            "🗜 <b>Сжатие PDF:</b> 100% БЕСПЛАТНО\n\n"
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
        "pdf_to_img_prompt": "🖼 <b>PDF ➡️ Фото:</b>\n\nОтправьте PDF файл для конвертации в изображения:",
        "pdf_to_img_generating": "⏳ <i>Страницы конвертируются в фото, подождите...</i>",
        "pdf_to_img_ready": "✅ <b>Страницы успешно конвертированы в изображения!</b>",
        "split_pdf_prompt": "✂️ <b>Разделение PDF:</b>\n\nОтправьте PDF файл, из которого нужно извлечь страницы:",
        "split_pdf_pages_prompt": "📄 <b>В документе всего {total} стр.</b>\n\nКакие страницы извлечь?\nУкажите диапазон или номера (например: <code>1-3, 5, 8</code>):",
        "split_pdf_generating": "⏳ <i>Извлечение выбранных страниц...</i>",
        "split_pdf_ready": "✅ <b>Выбранные {count} стр. успешно извлечены!</b>",
        "delete_pages_prompt": "🗑 <b>Удаление страниц из PDF:</b>\n\nОтправьте PDF файл для удаления страниц:",
        "delete_pages_input_prompt": "📄 <b>В документе всего {total} стр.</b>\n\nКакие страницы удалить?\nУкажите номера через запятую (например: <code>2, 5</code> или <code>3-6</code>):",
        "delete_pages_generating": "⏳ <i>Удаление указанных страниц...</i>",
        "delete_pages_ready": "✅ <b>Страницы удалены! Осталось страниц: {count}</b>",
        "watermark_prompt": "💧 <b>Водяной знак на PDF:</b>\n\nОтправьте PDF файл для добавления водяного знака:",
        "watermark_text_prompt": "✍️ <b>Отправьте текст водяного знака:</b>\n\nНапример: <i>@ваш_канал</i> или <i>КОПИЯ</i>",
        "watermark_generating": "⏳ <i>Нанесение водяного знака...</i>",
        "watermark_ready": "✅ <b>Водяной знак успешно нанесен на все {count} стр.!</b>",
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
        "bot_description": "🤖 Бот для конвертации фото и текста в PDF, объединения файлов и качественного сжатия PDF.",
        "bot_short_description": "⚡️ Sifatli PDF Bot",
    },
    "en": {
        "lang_select_prompt": "🌐 <b>Please select a language:</b>",
        "lang_selected": "✅ Language successfully set to: <b>English</b> 🇬🇧",
        "welcome_text": (
            "👋 <b>Welcome!</b>\n\n"
            "🛠 <b>Welcome to PDF Toolkit Bot!</b>\n"
            "I can assist you with all your PDF document needs:\n\n"
            "• 📝 <b>Text → PDF</b> — Convert text into neatly formatted PDF documents\n"
            "• 🖼 <b>Image → PDF</b> — Convert single or album images into crisp PDFs\n"
            "• 📎 <b>Merge PDF</b> — Combine multiple PDF files into one\n"
            "• 🗜 <b>Compress PDF</b> — Reduce PDF file size without sacrificing quality\n\n"
            "⬇️ Select an option below:"
        ),
        "btn_profile": "👤 My Profile",
        "btn_text_pdf": "📝 Text → PDF",
        "btn_img_pdf": "🖼 Image → PDF",
        "btn_pdf_to_img": "🖼 PDF → Images",
        "btn_split_pdf": "✂️ Split PDF",
        "btn_delete_pages": "🗑 Delete Pages",
        "btn_watermark_pdf": "💧 Watermark",
        "btn_merge_pdf": "📎 Merge PDF",
        "btn_compress_pdf": "🗜 Compress PDF",
        "btn_upscale": "✨ Upscale Quality (AI)",
        "btn_ai_image": "🤖 AI Image Generator",
        "btn_ai_video": "🎬 AI Video Generator",
        "btn_ai_slides": "📊 AI Slides Generator",
        "btn_change_lang": "🌐 Change Language",
        "btn_home": "🏠 Main Menu",
        "btn_top_up": "💳 Top-up Balance",
        "btn_share_ref": "🎁 Share with Friends",
        "btn_share_url": "📲 Share via Telegram",
        "btn_confirm_ai_video": "✅ Got it",
        "btn_skip": "⏩ Skip",
        "btn_convert_pdf": "📄 Download as PDF",
        "btn_admin_pay": "👤 Admin (@ziyodullame)",
        "profile_text": (
            "👤 <b>User Profile</b>\n\n"
            "🆔 ID: <code>{user_id}</code>\n"
            "🌐 Language: <b>{lang_name}</b>\n"
            "📊 Services Used: <b>{uses_count} times</b>\n"
            "👥 Invited Friends: <b>{referral_count} users</b>\n"
            "🌐 Total Bot Users: <b>{total_users:,}</b>"
        ),
        "referral_page_text": (
            "🎁 <b>Invite Friends!</b>\n\n"
            "Share the bot with your friends and colleagues so they can enjoy fast and free PDF tools as well!\n\n"
            "🔗 <b>Your referral link:</b>\n"
            "<code>https://t.me/{bot_username}?start=ref_{user_id}</code>\n\n"
            "👥 Total invited friends: <b>{referral_count} users</b>\n\n"
            "👇 Click the button below to share:"
        ),
        "referral_share_msg": "🤖 Found an amazing free PDF toolkit bot! Try it out:",
        "referral_bonus_notify": "🎉 <b>A new friend joined using your link!</b>",
        "ai_video_refund_notify": "⚠️ <b>An error occurred.</b>\n💰 Credits refunded to your balance!",
        "top_up_info": (
            "💳 <b>Official Tariffs and VIP Pass:</b>\n\n"
            "🖼 <b>Image ➡️ PDF 1-Year VIP Pass:</b> 5,000 UZS or ⭐️ 50 Stars <i>(50 free)</i>\n"
            "📝 <b>Text ➡️ PDF:</b> 100% FREE\n"
            "📎 <b>Merge PDF:</b> 100% FREE\n"
            "🗜 <b>Compress PDF:</b> 100% FREE\n\n"
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
        "pdf_to_img_prompt": "🖼 <b>PDF ➡️ Images:</b>\n\nSend the PDF file you want to convert to images:",
        "pdf_to_img_generating": "⏳ <i>Converting pages to images, please wait...</i>",
        "pdf_to_img_ready": "✅ <b>PDF pages converted to images successfully!</b>",
        "split_pdf_prompt": "✂️ <b>Split PDF:</b>\n\nSend the PDF file you want to extract pages from:",
        "split_pdf_pages_prompt": "📄 <b>The document has {total} pages.</b>\n\nWhich pages would you like to extract?\nEnter range or page numbers (e.g. <code>1-3, 5, 8</code>):",
        "split_pdf_generating": "⏳ <i>Extracting selected pages...</i>",
        "split_pdf_ready": "✅ <b>Selected {count} pages extracted successfully!</b>",
        "delete_pages_prompt": "🗑 <b>Delete PDF Pages:</b>\n\nSend the PDF file to remove pages from:",
        "delete_pages_input_prompt": "📄 <b>The document has {total} pages.</b>\n\nWhich pages would you like to delete?\nEnter page numbers (e.g. <code>2, 5</code> or <code>3-6</code>):",
        "delete_pages_generating": "⏳ <i>Deleting specified pages...</i>",
        "delete_pages_ready": "✅ <b>Pages deleted! Remaining pages: {count}</b>",
        "watermark_prompt": "💧 <b>Add Watermark to PDF:</b>\n\nSend the PDF file to watermark:",
        "watermark_text_prompt": "✍️ <b>Send the watermark text:</b>\n\ne.g. <i>@yourchannel</i> or <i>CONFIDENTIAL</i>",
        "watermark_generating": "⏳ <i>Applying watermark to pages...</i>",
        "watermark_ready": "✅ <b>Watermark successfully applied to all {count} pages!</b>",
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
        "bot_description": "🤖 Fast image and text to PDF conversion, PDF merging and high quality PDF compression bot.",
        "bot_short_description": "⚡️ Sifatli PDF Bot",
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
