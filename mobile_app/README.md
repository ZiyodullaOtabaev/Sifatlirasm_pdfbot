# Sifatli PDF — Mobile App (Flutter)

`@sifatlirasm_pdfbot` ekotizimining rasmiy **Android & iOS** mobil ilovasi.

## Arxitektura
- **Frontend:** Flutter (Dart 3, Material 3, MVVM: `ui/` · `domain/` · `data/`)
- **Tillar:** O'zbekcha (`uz`), Русский (`ru`), English (`en`) — 100% uch tilli
- **Backend API:** Oracle Cloud serveridagi yagona baza (`bot.db`), `SmartPdf2Docx` va `LibreOffice Headless` dvigatellari bilan sinxron ishlovchi REST API (`bot/api/`)
- **Tariflar:** Telegram bot bilan yagona VIP obuna, kunlik bepul limit, promokodlar va referral bonus tizimi
