# Rasm PDF Bot

Telegram bot — rasmlar va matnni PDF ga aylantirish, sifat oshirish, PDF birlashtirish/siqish, fon olib tashlash, AI rasm generatsiya va OCR.

## Imkoniyatlar

| Funksiya | Tavsif |
|----------|--------|
| 📊 AI Slayd Yaratish | 12 betli standart akademik PowerPoint va FLUX AI rasmlari |
| 📝 Matn → PDF | Matnni PDF faylga aylantirish |
| 🖼 Rasm → PDF | Bir yoki bir necha rasmni PDF ga aylantirish |
| ✨ Sifat oshirish | Rasm sifatini AI orqali yaxshilash |
| 📎 PDF birlashtirish | Bir necha PDF ni bittaga qo'shish |
| 🗜 PDF siqish | PDF hajmini sifatga zarar bermasdan kichraytirish |
| 📄 Smart Scan | Hujjat skanerlash (perspektiv to'g'rilash) |
| 🎨 Fon olib tashlash | Rasmdan fonni AI orqali olib tashlash |
| 🤖 AI rasm | Sun'iy intellekt bilan rasm generatsiya |
| 📖 OCR | Rasmdan matn ajratish (ingliz, rus) |
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
- **EasyOCR** — Rasmdan matn aniqlash
- **Replicate API** — AI upscale, fon olib tashlash, rasm generatsiya

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
│   │   ├── bg_remove.py    # Fon olib tashlash
│   │   ├── ai_image.py     # AI rasm generatsiya
│   │   ├── ocr.py          # OCR (matn ajratish)
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
# .env faylni tahrirlang — BOT_TOKEN va REPLICATE_API_TOKEN kiriting

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
| `REPLICATE_API_TOKEN` | Replicate API kaliti | *majburiy (AI uchun)* |
| `CHANNEL_USER` | Obuna tekshirish kanali | `@xonziyy` |
| `FREE_USES_BEFORE_SUB` | Obunagacha bepul foydalanish | `15` |
| `ADMIN_IDS` | Admin ID'lar (vergul bilan) | `""` |
| `MAX_FILE_SIZE` | Maksimal fayl hajmi (bayt) | `20971520` |
| `DB_PATH` | SQLite baza fayli | `bot.db` |
| `DOWNLOAD_DIR` | Vaqtinchalik fayllar papkasi | `downloads` |
| `ENABLE_REAL_AI` | AI upscale yoqish | `1` |
| `UPSCALE_TARGET_HEIGHT` | Upscale maqsad balandligi (px) | `1080` |
| `BROADCAST_RATE` | Broadcast tezligi (xabar/sek) | `25` |

## Admin buyruqlar

- `/admin` — Statistika dashboard
- `/top` — Top 30 foydalanuvchi
- `/broadcast` — Barcha foydalanuvchilarga xabar

## Litsenziya

MIT
