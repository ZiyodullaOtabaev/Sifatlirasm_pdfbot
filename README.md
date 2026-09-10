# Rasm PDF Bot

Telegram bot — rasmlar va matnni PDF ga aylantirish, sifat oshirish, PDF birlashtirish/siqish, 3x4 hujjat rasmi va professional taqdimot (slayd) yaratish. Barcha funksiyalar 100% bepul — hech qanday pullik API xizmati ishlatilmaydi.

## Imkoniyatlar

| Funksiya | Tavsif |
|----------|--------|
| 📊 Slayd Yaratish | 12 betli standart akademik PowerPoint (10 ta professional shablon, PPTX + PDF) |
| 📝 Matn → PDF | Matnni PDF faylga aylantirish |
| 🖼 Rasm → PDF | Bir yoki bir necha rasmni PDF ga aylantirish (cheksiz) |
| ✨ Sifat oshirish | Rasm sifatini lokal usulda yaxshilash (Real-ESRGAN/Pillow) |
| 📎 PDF birlashtirish | Bir necha PDF ni bittaga qo'shish |
| 🗜 PDF siqish | PDF hajmini sifatga zarar bermasdan kichraytirish |
| 👔 3x4 Hujjat rasmi | Pasport/hujjat uchun 3x4 foto + 10x15 chop varag'i |
| 📢 Broadcast | Admin barcha foydalanuvchilarga xabar yuborish |
| 🛠 Admin panel | Statistika, grafiklar, top foydalanuvchilar |

## Texnologiyalar

- **Python 3.11+**
- **Aiogram 3.x** — Telegram Bot API
- **SQLite** — Ma'lumotlar bazasi
- **Pillow** — Rasm qayta ishlash
- **ReportLab** — PDF yaratish
- **PyPDF2** — PDF birlashtirish
- **PyMuPDF** — PDF siqish
- **OpenCV** — Smart scan, rasm qayta ishlash
- **python-pptx** — PowerPoint taqdimot yaratish

## Loyiha strukturasi

```
rasm_pdf_bot/
├── bot/
│   ├── __init__.py
│   ├── config.py           # .env konfiguratsiya
│   ├── database.py         # SQLite operatsiyalari
│   ├── keyboards.py        # Inline klaviaturalar
│   ├── states.py           # Foydalanuvchi holatlari
│   ├── main.py             # Entry point (dispatcher, polling)
│   ├── handlers/
│   │   ├── __init__.py     # Router registratsiyasi
│   │   ├── start.py        # /start buyrug'i
│   │   ├── menu.py         # Menyu navigatsiyasi
│   │   ├── text_pdf.py     # Matn → PDF
│   │   ├── img_pdf.py      # Rasm → PDF
│   │   ├── upscale.py      # Sifat oshirish
│   │   ├── merge_pdf.py    # PDF birlashtirish
│   │   ├── compress.py     # PDF siqish
│   │   ├── ai_slides.py    # Taqdimot (slayd) generator
│   │   ├── passport_photo.py # 3x4 hujjat rasmi
│   │   ├── profile.py      # Foydalanuvchi profili
│   │   └── admin.py        # Admin panel & broadcast
│   └── utils/
│       ├── __init__.py
│       ├── pdf.py           # PDF yordamchi funksiyalar
│       ├── image.py         # Rasm qayta ishlash
│       ├── chart.py         # Admin grafiklar
│       ├── cleanup.py       # Fayl tozalash worker
│       └── helpers.py       # Umumiy yordamchilar
├── downloads/               # Vaqtinchalik fayllar (gitignore)
├── .env.example             # Muhit o'zgaruvchilari namunasi
├── .gitignore
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## O'rnatish

### Talablar

- Python 3.11+
- pip

### Lokal ishga tushirish

```bash
# Virtual muhit yaratish
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# Paketlarni o'rnatish
pip install -r requirements.txt

# .env sozlash
copy .env.example .env
# .env faylni tahrirlang — BOT_TOKEN kiriting

# Botni ishga tushirish
python -m bot.main
```

### Docker orqali

```bash
docker-compose up -d          # Ishga tushirish
docker-compose logs -f bot    # Loglar
docker-compose down           # To'xtatish
```

## Konfiguratsiya (.env)

| O'zgaruvchi | Tavsif | Default |
|-------------|--------|---------|
| `BOT_TOKEN` | Telegram bot token (@BotFather) | *majburiy* |
| `CHANNEL_USER` | Obuna tekshirish kanali | `@xonziyy` |
| `FREE_USES_BEFORE_SUB` | Obunagacha bepul foydalanish | `15` |
| `ADMIN_IDS` | Admin ID'lar (vergul bilan) | `""` |
| `MAX_FILE_SIZE` | Maksimal fayl hajmi (bayt) | `20971520` |
| `DB_PATH` | SQLite baza fayli | `bot.db` |
| `DOWNLOAD_DIR` | Vaqtinchalik fayllar papkasi | `downloads` |
| `ENABLE_REAL_AI` | Lokal Real-ESRGAN upscale yoqish | `1` |
| `REAL_ESRGAN_BIN` | Real-ESRGAN binary yo'li (ixtiyoriy) | `""` |
| `BROADCAST_RATE` | Broadcast tezligi (xabar/sek) | `25` |

## Admin buyruqlar

- `/admin` — Statistika dashboard
- `/top` — Top 30 foydalanuvchi
- `/broadcast` — Barcha foydalanuvchilarga xabar

## Litsenziya

MIT
