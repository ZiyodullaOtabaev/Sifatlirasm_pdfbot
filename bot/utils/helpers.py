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
    """Automatically translate Uzbek or Russian prompt to English using Google Translate API."""
    if not text or len(text.strip()) < 2:
        return text
    try:
        import urllib.parse
        import httpx
        url = (
            "https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl=auto&tl=en&dt=t&q={urllib.parse.quote(text)}"
        )
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(url)
            if res.status_code == 200:
                data = res.json()
                translated = "".join([chunk[0] for chunk in data[0] if chunk and chunk[0]])
                if translated:
                    return translated.strip()
    except Exception:
        pass
    return text


async def enhance_video_prompt(user_prompt: str) -> str:
    """
    Enhance user prompt into a rich, detailed, cinematic English video generation prompt.
    Uses Llama 3 70B via Replicate with 30s timeout and fallback to simple translation.
    """
    if not user_prompt or len(user_prompt.strip()) < 2:
        return user_prompt

    from bot.config import REPLICATE_API_TOKEN

    if not REPLICATE_API_TOKEN:
        return await auto_translate_to_en(user_prompt)

    try:
        import httpx
        import gc

        system_prompt = (
            "You are an expert AI video prompt engineer. "
            "Translate the input from Uzbek, Russian, or English into English and transform it into a single, "
            "highly detailed, cinematic video generation prompt for AI video generators. "
            "Describe subject, background, lighting, camera movement, style and atmosphere. "
            "Do NOT include conversational text, quotes, or markdown. Output ONLY the raw prompt string."
        )

        payload = {
            "model": "meta/meta-llama-3-70b-instruct",
            "input": {
                "prompt": f"{system_prompt}\nUser Input: {user_prompt}\nEnhanced Prompt:",
                "max_tokens": 150,
                "temperature": 0.7,
            },
        }

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(35.0, connect=10.0)
        ) as client:
            create_resp = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={
                    "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
                    "Content-Type": "application/json",
                    "Prefer": "wait",
                },
                json=payload,
            )

            if create_resp.status_code in (429, 503):
                # Rate-limited — fall back to simple translation
                return await auto_translate_to_en(user_prompt)

            if create_resp.status_code == 200 or create_resp.status_code == 201:
                prediction = create_resp.json()
                pred_id = prediction.get("id")

                if prediction.get("status") == "succeeded":
                    output = prediction.get("output", [])
                    enhanced = "".join(output).strip()
                    if len(enhanced) > 15:
                        gc.collect()
                        return enhanced

                # Poll quickly for up to 30s
                for _ in range(15):
                    await asyncio.sleep(2)
                    poll = await client.get(
                        f"https://api.replicate.com/v1/predictions/{pred_id}",
                        headers={"Authorization": f"Bearer {REPLICATE_API_TOKEN}"},
                    )
                    data = poll.json()
                    if data.get("status") == "succeeded":
                        output = data.get("output", [])
                        enhanced = "".join(output).strip()
                        if len(enhanced) > 15:
                            gc.collect()
                            return enhanced
                        break
                    elif data.get("status") in ("failed", "canceled"):
                        break

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"enhance_video_prompt fallback: {e}")

    # Fallback to simple Google Translate
    return await auto_translate_to_en(user_prompt)
