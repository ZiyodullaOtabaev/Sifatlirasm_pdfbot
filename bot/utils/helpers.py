"""
Common helper functions.
"""
import os
import re

from aiogram.types import User


def safe_remove(path: str):
    """Safely remove a file, ignoring errors."""
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def _sanitize_filename_base(s: str) -> str:
    """Sanitize a string for use in filename."""
    s = (s or "").strip()
    if not s:
        return ""
    out = []
    for ch in s:
        if ch.isalnum() or ch in ("_", "-", "."):
            out.append(ch)
        else:
            out.append("_")
    base = "".join(out).strip("._-")
    base = re.sub(r"_+", "_", base)
    return base[:40] if base else ""


def user_pdf_filename(user: User) -> str:
    """Generate PDF filename from user info."""
    base = (
        _sanitize_filename_base(getattr(user, "username", "") or "")
        or _sanitize_filename_base(getattr(user, "first_name", "") or "")
    )
    if not base:
        base = f"user_{user.id}"
    return f"{base}.pdf"


def friendly_error(e: Exception) -> str:
    """Convert exception to user-friendly error message in Uzbek."""
    error_str = str(e).lower()

    # Timeout / connection errors
    if any(x in error_str for x in ("timeout", "timed out", "connecttimeout")):
        return "⏱ Server javob bermadi. 10-15 soniyadan keyin qayta urinib ko'ring."

    # Rate limit
    if any(x in error_str for x in ("rate limit", "too many requests", "429")):
        return "⚡ Juda ko'p so'rov. 1 daqiqadan keyin qayta urinib ko'ring."

    # API token / auth
    if any(x in error_str for x in ("unauthorized", "401", "forbidden", "403", "api_key", "token")):
        return "🔑 AI xizmati vaqtinchalik mavjud emas. Keyinroq urinib ko'ring."

    # Model not found / version
    if any(x in error_str for x in ("not found", "404", "version", "does not exist")):
        return "🔧 Xizmat yangilanmoqda. Keyinroq urinib ko'ring."

    # File too large
    if any(x in error_str for x in ("too large", "file size", "payload")):
        return "📦 Fayl juda katta. Kichikroq fayl yuboring."

    # Network errors
    if any(x in error_str for x in ("connection", "network", "dns", "ssl")):
        return "🌐 Internet bilan muammo. Qayta urinib ko'ring."

    # Memory / processing
    if any(x in error_str for x in ("memory", "oom", "killed")):
        return "💾 Fayl juda murakkab. Kichikroq fayl yuboring."

    # PDF specific
    if any(x in error_str for x in ("password", "encrypted", "parol")):
        return "🔒 Bu PDF parol bilan himoyalangan."

    if any(x in error_str for x in ("corrupted", "invalid pdf", "broken")):
        return "📄 PDF fayl buzilgan. Boshqa fayl yuboring."

    # Generic
    return "❌ Xatolik yuz berdi. Qayta urinib ko'ring."


async def auto_translate_to_en(text: str) -> str:
    """Automatically translate Uzbek or Russian prompt to English for AI models."""
    if not text or len(text.strip()) < 2:
        return text
    try:
        import urllib.parse
        import httpx
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=en&dt=t&q={urllib.parse.quote(text)}"
        async with httpx.AsyncClient(timeout=5) as client:
            res = await client.get(url)
            if res.status_code == 200:
                data = res.json()
                translated = "".join([chunk[0] for chunk in data[0] if chunk and chunk[0]])
                if translated:
                    return translated.strip()
    except Exception:
        pass
    return text
