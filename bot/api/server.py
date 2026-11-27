"""
Sifatli PDF Mobile REST API (aiohttp.web) — Unified with @sifatlirasm_pdfbot & bot.db.
Provides:
- Device auth & 1-Tap Telegram Account Linking (?start=app_<token>)
- Live VIP, Daily Free Limit, Bonus Credits, Promo Codes & Referral sync
- All PDF & Office conversions (SmartPdf2Docx, LibreOffice Headless, Merge, Compress,
  PDF->Images ZIP, Watermark, Text->PDF, Images->PDF) with strict immediate temp cleanup
- In-App Card VIP Receipt upload -> Instant 1-Click Admin Approval in Telegram!
- Password-protected Super Admin Control Center endpoints
"""
import os
import io
import html
import shutil
import zipfile
import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

from aiohttp import web
from aiogram import Bot
from aiogram.types import FSInputFile

from bot.config import (
    API_PORT, DOWNLOAD_DIR, MAX_FILE_SIZE, ADMIN_IDS, ADMIN_ID,
)
from bot.database import (
    get_or_create_device_user, create_telegram_link_token, check_telegram_link_token,
    is_mobile_guest_id, get_user_full_info, get_user_language, set_user_language,
    has_active_img_pdf_pass, get_vip_until, get_user_daily_uses, get_user_balance,
    get_uses, get_referral_count, get_daily_free_limit, get_vip_prices,
    get_payment_card, is_maintenance_mode, is_user_banned, inc_uses_and_log,
    redeem_promo_code, get_admin_summary, get_finance_summary, get_action_stats,
    get_all_settings, set_setting, get_all_promo_codes, create_promo_code,
    delete_promo_code, resolve_user_id, activate_img_pdf_pass, add_user_balance,
    get_mobile_devices_count,
)
from bot.i18n import t
from bot.keyboards import kb_admin_approve_vip
from bot.handlers.payments import PENDING_VIP_PLAN
from bot.handlers.office_convert import CONVERSION_SEMAPHORE
from bot.utils.office_tools import pdf_to_word, office_to_pdf, SUPPORTED_OFFICE_EXTS
from bot.utils.pdf import merge_pdfs, images_to_pdf
from bot.utils.image import compress_pdf
from bot.utils.pdf_tools import pdf_to_images, watermark_pdf
from bot.utils.helpers import friendly_error
from bot.api.auth import create_jwt, verify_jwt, verify_super_admin_password

logger = logging.getLogger(__name__)

_API_RUNNER: Optional[web.AppRunner] = None
_BOT_USERNAME_CACHE: str = "sifatlirasm_pdfbot"


def _make_unicode_text_pdf_bytes(text: str, title: str = "") -> bytes:
    """Create clean A4 PDF supporting Uzbek, Russian (Cyrillic), and English Unicode characters."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_name = "Helvetica"
    bold_name = "Helvetica-Bold"
    dejavu_reg = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    dejavu_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    try:
        if os.path.exists(dejavu_reg):
            if "DejaVuSans" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("DejaVuSans", dejavu_reg))
            font_name = "DejaVuSans"
        if os.path.exists(dejavu_bold):
            if "DejaVuSans-Bold" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", dejavu_bold))
            bold_name = "DejaVuSans-Bold"
    except Exception:
        pass

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    margin = 50
    max_w = width - 2 * margin
    y = height - margin

    def _wrap_width(line_str: str, f_name: str, f_size: float) -> list[str]:
        s = line_str.rstrip("\r\n")
        if not s:
            return [""]
        words = s.split(" ")
        lines_out = []
        cur = ""
        for w in words:
            cand = f"{cur} {w}".strip() if cur else w
            if c.stringWidth(cand, f_name, f_size) <= max_w:
                cur = cand
            else:
                if cur:
                    lines_out.append(cur)
                # Break very long single token if needed
                while c.stringWidth(w, f_name, f_size) > max_w and len(w) > 1:
                    cut = max(1, int(len(w) * (max_w / max(1.0, c.stringWidth(w, f_name, f_size)))))
                    lines_out.append(w[:cut])
                    w = w[cut:]
                cur = w
        if cur:
            lines_out.append(cur)
        return lines_out

    if title.strip():
        c.setFont(bold_name, 16)
        for tl in _wrap_width(title.strip(), bold_name, 16):
            if y < margin + 20:
                c.showPage()
                c.setFont(bold_name, 16)
                y = height - margin
            c.drawString(margin, y, tl)
            y -= 22
        y -= 8

    c.setFont(font_name, 12)
    for raw in text.splitlines():
        for wl in _wrap_width(raw, font_name, 12):
            if y < margin:
                c.showPage()
                c.setFont(font_name, 12)
                y = height - margin
            c.drawString(margin, y, wl)
            y -= 17

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


def _build_user_payload(user_id: int) -> Dict[str, Any]:
    """Construct complete synced user & billing profile dict for Mobile App."""
    info = get_user_full_info(user_id) or {}
    lang = info.get("language") or "uz"
    is_admin = (user_id in ADMIN_IDS) or (ADMIN_ID and user_id == ADMIN_ID)
    is_vip = is_admin or has_active_img_pdf_pass(user_id)
    vip_until = "∞" if is_admin else (get_vip_until(user_id) or None)
    daily_limit = get_daily_free_limit()
    daily_used = get_user_daily_uses(user_id)
    bonus_balance = get_user_balance(user_id)
    uses_count = get_uses(user_id)
    ref_count = get_referral_count(user_id)
    is_tg_linked = not is_mobile_guest_id(user_id)

    remaining_free = 999999 if (is_vip or daily_limit == 0) else max(0, daily_limit - daily_used) + bonus_balance

    return {
        "user_id": user_id,
        "is_telegram_linked": is_tg_linked,
        "username": info.get("username") or "",
        "first_name": info.get("first_name") or "",
        "language": lang,
        "is_vip": is_vip,
        "is_admin": bool(is_admin),
        "vip_until": vip_until,
        "daily_used": daily_used,
        "daily_limit": daily_limit,
        "bonus_balance": bonus_balance,
        "remaining_available": remaining_free,
        "uses_count": uses_count,
        "referral_count": ref_count,
        "referral_url": f"https://t.me/{_BOT_USERNAME_CACHE}?start=ref_{user_id}",
        "bot_username": _BOT_USERNAME_CACHE,
        "vip_prices": get_vip_prices(),
        "card_number": get_payment_card(),
        "maintenance_mode": is_maintenance_mode(),
    }


def _check_access_and_quota(user_id: int) -> Optional[web.Response]:
    """Verify maintenance mode, ban status, and daily free/VIP quota before conversion."""
    lang = get_user_language(user_id) or "uz"
    is_admin = (user_id in ADMIN_IDS) or (ADMIN_ID and user_id == ADMIN_ID)

    if not is_admin and is_maintenance_mode():
        return web.json_response(
            {"ok": False, "code": "MAINTENANCE", "error": _strip_html(t("maintenance_text", lang))},
            status=503,
        )

    if not is_admin and is_user_banned(user_id):
        return web.json_response(
            {"ok": False, "code": "BANNED", "error": _strip_html(t("banned_text", lang))},
            status=403,
        )

    if is_admin or has_active_img_pdf_pass(user_id):
        return None

    daily_limit = get_daily_free_limit()
    if daily_limit > 0:
        daily_used = get_user_daily_uses(user_id)
        bonus = get_user_balance(user_id)
        if daily_used >= daily_limit and bonus <= 0:
            limit_msgs = {
                "uz": f"Kunlik bepul limit tugadi ({daily_used}/{daily_limit}). Cheksiz ishlash uchun VIP obuna oling yoki promokod kiriting!",
                "ru": f"Дневной бесплатный лимит исчерпан ({daily_used}/{daily_limit}). Оформите VIP или введите промокод для безлимитной работы!",
                "en": f"Daily free limit reached ({daily_used}/{daily_limit}). Upgrade to VIP or redeem a promo code for unlimited access!",
            }
            return web.json_response(
                {
                    "ok": False,
                    "code": "DAILY_LIMIT_REACHED",
                    "error": limit_msgs.get(lang, limit_msgs["uz"]),
                    "user": _build_user_payload(user_id),
                },
                status=402,
            )

    return None


def _strip_html(s: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", s or "").strip()


def _require_user(request: web.Request) -> tuple[Optional[Dict[str, Any]], Optional[web.Response]]:
    auth_hdr = request.headers.get("Authorization", "")
    if not auth_hdr.startswith("Bearer "):
        return None, web.json_response({"ok": False, "error": "Unauthorized"}, status=401)
    claims = verify_jwt(auth_hdr[7:].strip())
    if not claims or "uid" not in claims:
        return None, web.json_response({"ok": False, "error": "Invalid or expired token"}, status=401)
    return claims, None


def _require_super_admin(request: web.Request) -> Optional[web.Response]:
    auth_hdr = request.headers.get("Authorization", "")
    if not auth_hdr.startswith("Bearer "):
        return web.json_response({"ok": False, "error": "Admin authorization required"}, status=401)
    claims = verify_jwt(auth_hdr[7:].strip())
    if not claims or not claims.get("super_admin"):
        return web.json_response({"ok": False, "error": "Forbidden: Super Admin only"}, status=403)
    return None


@web.middleware
async def cors_and_error_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        resp = web.Response(status=204)
    else:
        try:
            resp = await handler(request)
        except web.HTTPRequestEntityTooLarge:
            resp = web.json_response(
                {"ok": False, "error": f"File too large (max {MAX_FILE_SIZE // (1024 * 1024)} MB)"},
                status=413,
            )
        except web.HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"API unhandled error on {request.path}: {e}", exc_info=True)
            resp = web.json_response({"ok": False, "error": "Server error occurred"}, status=500)

    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept-Language"
    resp.headers["Access-Control-Expose-Headers"] = (
        "Content-Disposition, X-Pages, X-Scanned, X-Original-Size, X-Compressed-Size, X-Saved-Pct"
    )
    return resp


# ============================================================================
# ROUTE HANDLERS
# ============================================================================

async def handle_health(_request: web.Request) -> web.Response:
    return web.json_response({
        "ok": True,
        "service": "Sifatli PDF Mobile API",
        "version": "1.0.0",
        "bot": f"@{_BOT_USERNAME_CACHE}",
    })


async def handle_auth_device(request: web.Request) -> web.Response:
    """Register or restore mobile device session and issue JWT."""
    data = await request.json()
    device_id = str(data.get("device_id") or "").strip()
    platform = str(data.get("platform") or "android").strip()
    device_name = str(data.get("device_name") or "Mobile").strip()
    lang = str(data.get("lang") or "uz").strip().lower()
    if not device_id or len(device_id) < 6:
        return web.json_response({"ok": False, "error": "Valid device_id required"}, status=400)

    uid = get_or_create_device_user(device_id, platform=platform, device_name=device_name, lang=lang)
    token = create_jwt({"uid": uid, "dev": device_id})
    return web.json_response({
        "ok": True,
        "token": token,
        "user": _build_user_payload(uid),
    })


async def handle_tg_link_start(request: web.Request) -> web.Response:
    """Generate 1-tap Telegram account sync deep link (?start=app_<token>)."""
    claims, err = _require_user(request)
    if err:
        return err
    uid = int(claims["uid"])
    dev_id = str(claims.get("dev") or "")
    link_token = create_telegram_link_token(dev_id, uid)
    bot_url = f"https://t.me/{_BOT_USERNAME_CACHE}?start=app_{link_token}"
    tg_deep = f"tg://resolve?domain={_BOT_USERNAME_CACHE}&start=app_{link_token}"
    return web.json_response({
        "ok": True,
        "link_token": link_token,
        "bot_url": bot_url,
        "tg_deep_link": tg_deep,
    })


async def handle_tg_link_poll(request: web.Request) -> web.Response:
    """Check if user tapped Start in Telegram and issue synced JWT if linked."""
    claims, err = _require_user(request)
    if err:
        return err
    dev_id = str(claims.get("dev") or "")
    link_token = str(request.query.get("token") or "").strip()
    linked_uid = check_telegram_link_token(link_token, dev_id)
    if not linked_uid:
        return web.json_response({"ok": True, "linked": False})

    new_jwt = create_jwt({"uid": linked_uid, "dev": dev_id})
    return web.json_response({
        "ok": True,
        "linked": True,
        "token": new_jwt,
        "user": _build_user_payload(linked_uid),
    })


async def handle_get_me(request: web.Request) -> web.Response:
    claims, err = _require_user(request)
    if err:
        return err
    return web.json_response({"ok": True, "user": _build_user_payload(int(claims["uid"]))})


async def handle_set_language(request: web.Request) -> web.Response:
    claims, err = _require_user(request)
    if err:
        return err
    uid = int(claims["uid"])
    data = await request.json()
    lang = str(data.get("language") or "uz").strip().lower()
    if lang not in ("uz", "ru", "en"):
        lang = "uz"
    set_user_language(uid, lang)
    return web.json_response({"ok": True, "user": _build_user_payload(uid)})


async def handle_log_local_usage(request: web.Request) -> web.Response:
    """Check quota & log an on-device conversion (e.g. Image->PDF or Text->PDF)."""
    claims, err = _require_user(request)
    if err:
        return err
    uid = int(claims["uid"])
    quota_err = _check_access_and_quota(uid)
    if quota_err:
        return quota_err

    data = await request.json()
    action = str(data.get("action") or "img_pdf").strip()
    if action not in ("img_pdf", "text_pdf"):
        action = "img_pdf"
    inc_uses_and_log(uid, action)
    return web.json_response({"ok": True, "user": _build_user_payload(uid)})


async def handle_redeem_promo(request: web.Request) -> web.Response:
    claims, err = _require_user(request)
    if err:
        return err
    uid = int(claims["uid"])
    lang = get_user_language(uid) or "uz"
    data = await request.json()
    code = str(data.get("code") or "").strip()

    ok, status, info = redeem_promo_code(uid, code)
    if ok:
        if info["reward_type"] == "vip_days":
            msg = _strip_html(t("promo_success_vip", lang, value=info["reward_value"], vip_until=info.get("vip_until", "")))
        else:
            msg = _strip_html(t("promo_success_bonus", lang, value=info["reward_value"], new_balance=info.get("new_balance", 0)))
        return web.json_response({"ok": True, "message": msg, "user": _build_user_payload(uid)})

    key_map = {
        "not_found": "promo_not_found",
        "inactive": "promo_inactive",
        "exhausted": "promo_exhausted",
        "already_used": "promo_already_used",
    }
    msg = _strip_html(t(key_map.get(status, "promo_not_found"), lang))
    return web.json_response({"ok": False, "error": msg}, status=400)


async def handle_vip_receipt_upload(request: web.Request) -> web.Response:
    """Receive card payment receipt from Mobile App and send to Telegram Admins with 1-click approve buttons."""
    claims, err = _require_user(request)
    if err:
        return err
    uid = int(claims["uid"])
    lang = get_user_language(uid) or "uz"
    bot: Bot = request.app["bot"]

    reader = await request.multipart()
    days = 30
    saved_path: Optional[str] = None
    orig_name = "receipt.jpg"

    job_dir = tempfile.mkdtemp(prefix=f"app_rcpt_{uid}_", dir=DOWNLOAD_DIR)
    try:
        while True:
            part = await reader.next()
            if part is None:
                break
            if part.name == "days":
                val = (await part.text()).strip()
                days = 365 if val == "365" else 30
            elif part.name == "file":
                orig_name = Path(part.filename or "receipt.jpg").name
                ext = Path(orig_name).suffix.lower() or ".jpg"
                saved_path = os.path.join(job_dir, f"receipt{ext}")
                size = 0
                with open(saved_path, "wb") as f:
                    while True:
                        chunk = await part.read_chunk(65536)
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > MAX_FILE_SIZE:
                            return web.json_response({"ok": False, "error": "Receipt file too large"}, status=413)
                        f.write(chunk)

        if not saved_path or not os.path.exists(saved_path):
            return web.json_response({"ok": False, "error": "Receipt image required"}, status=400)

        PENDING_VIP_PLAN[uid] = days
        p = get_vip_prices()
        uzs_val = p["uzs_365"] if days >= 365 else p["uzs_30"]
        uzs_fmt = f"{uzs_val:,}".replace(",", " ")
        plan_str = f"👑 1 Yillik VIP ({uzs_fmt} so'm)" if days >= 365 else f"💎 1 Oylik VIP ({uzs_fmt} so'm)"

        u_info = get_user_full_info(uid) or {}
        safe_name = html.escape(u_info.get("first_name") or "Mobile User")
        uname_raw = u_info.get("username") or ""
        uname = f"@{html.escape(uname_raw)}" if uname_raw else ("Mobil Mehmon" if is_mobile_guest_id(uid) else "username yo'q")

        admin_caption = (
            f"📱 <b>Mobil Ilovadan Yangi VIP To'lov Cheki! (💳 Karta)</b>\n\n"
            f"👤 Foydalanuvchi: <b>{safe_name}</b> ({uname})\n"
            f"🆔 ID: <code>{uid}</code>\n"
            f"📦 Tanlagan tarifi: <b>{plan_str}</b>\n\n"
            f"👇 Tekshirib, quyidagi tugmalardan birini bosing:"
        )

        admins = set(ADMIN_IDS) | ({ADMIN_ID} if ADMIN_ID else set())
        ext_low = Path(saved_path).suffix.lower()
        for adm in admins:
            try:
                inp = FSInputFile(saved_path, filename=orig_name)
                if ext_low in (".jpg", ".jpeg", ".png", ".webp"):
                    await bot.send_photo(adm, photo=inp, caption=admin_caption, parse_mode="HTML", reply_markup=kb_admin_approve_vip(uid))
                else:
                    await bot.send_document(adm, document=inp, caption=admin_caption, parse_mode="HTML", reply_markup=kb_admin_approve_vip(uid))
            except Exception as send_err:
                logger.error(f"Failed forwarding mobile VIP receipt to admin {adm}: {send_err}")

        return web.json_response({
            "ok": True,
            "message": _strip_html(t("vip_receipt_received", lang)),
        })
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


# ============================================================================
# CONVERSION ENDPOINTS (Immediate Temp Cleanup in `finally:`)
# ============================================================================

async def _save_multipart_files(request: web.Request, job_dir: str) -> tuple[list[tuple[str, str]], Dict[str, str]]:
    """Read multipart fields and files into job_dir safely respecting MAX_FILE_SIZE."""
    reader = await request.multipart()
    files: list[tuple[str, str]] = []
    fields: Dict[str, str] = {}
    idx = 0
    while True:
        part = await reader.next()
        if part is None:
            break
        if part.filename:
            idx += 1
            orig_name = Path(part.filename).name
            ext = Path(orig_name).suffix.lower()
            local_path = os.path.join(job_dir, f"in_{idx}{ext}")
            total_b = 0
            with open(local_path, "wb") as f:
                while True:
                    chunk = await part.read_chunk(65536)
                    if not chunk:
                        break
                    total_b += len(chunk)
                    if total_b > MAX_FILE_SIZE:
                        raise web.HTTPRequestEntityTooLarge(max_size=MAX_FILE_SIZE, actual_size=total_b)
                    f.write(chunk)
            files.append((local_path, orig_name))
        elif part.name:
            fields[part.name] = (await part.text()).strip()
    return files, fields


def _file_bytes_response(path: str, download_name: str, content_type: str, extra_headers: Optional[Dict[str, str]] = None) -> web.Response:
    """Read output file into memory so job_dir can be deleted immediately in finally block."""
    with open(path, "rb") as f:
        body = f.read()
    safe_ascii = "".join(c if (c.isalnum() or c in "._- ") else "_" for c in download_name).strip() or "output"
    headers = {
        "Content-Disposition": f'attachment; filename="{safe_ascii}"',
    }
    if extra_headers:
        headers.update(extra_headers)
    return web.Response(body=body, content_type=content_type, headers=headers)


async def handle_convert_pdf_to_word(request: web.Request) -> web.Response:
    claims, err = _require_user(request)
    if err:
        return err
    uid = int(claims["uid"])
    lang = get_user_language(uid) or "uz"
    quota_err = _check_access_and_quota(uid)
    if quota_err:
        return quota_err

    job_dir = tempfile.mkdtemp(prefix=f"app_p2w_{uid}_", dir=DOWNLOAD_DIR)
    try:
        files, _ = await _save_multipart_files(request, job_dir)
        if not files or not files[0][0].lower().endswith(".pdf"):
            return web.json_response({"ok": False, "error": _strip_html(t("err_only_pdf", lang))}, status=400)

        in_pdf, orig_name = files[0]
        out_docx = os.path.join(job_dir, "converted.docx")
        async with CONVERSION_SEMAPHORE:
            pages, is_scanned = await asyncio.to_thread(pdf_to_word, in_pdf, out_docx)

        inc_uses_and_log(uid, "pdf_to_word")
        stem = Path(orig_name).stem or "document"
        return _file_bytes_response(
            out_docx,
            f"{stem}.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            {"X-Pages": str(pages), "X-Scanned": "1" if is_scanned else "0"},
        )
    except web.HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mobile pdf_to_word error for {uid}: {e}")
        return web.json_response({"ok": False, "error": _strip_html(friendly_error(e, lang))}, status=400)
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


async def handle_convert_office_to_pdf(request: web.Request) -> web.Response:
    claims, err = _require_user(request)
    if err:
        return err
    uid = int(claims["uid"])
    lang = get_user_language(uid) or "uz"
    quota_err = _check_access_and_quota(uid)
    if quota_err:
        return quota_err

    job_dir = tempfile.mkdtemp(prefix=f"app_o2p_{uid}_", dir=DOWNLOAD_DIR)
    try:
        files, _ = await _save_multipart_files(request, job_dir)
        if not files or Path(files[0][0]).suffix.lower() not in SUPPORTED_OFFICE_EXTS:
            return web.json_response({"ok": False, "error": _strip_html(t("err_only_office_file", lang))}, status=400)

        in_file, orig_name = files[0]
        async with CONVERSION_SEMAPHORE:
            out_pdf = await asyncio.to_thread(office_to_pdf, in_file, job_dir)

        inc_uses_and_log(uid, "office_to_pdf")
        stem = Path(orig_name).stem or "document"
        return _file_bytes_response(out_pdf, f"{stem}.pdf", "application/pdf")
    except web.HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mobile office_to_pdf error for {uid}: {e}")
        return web.json_response({"ok": False, "error": _strip_html(friendly_error(e, lang))}, status=400)
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


async def handle_convert_merge_pdf(request: web.Request) -> web.Response:
    claims, err = _require_user(request)
    if err:
        return err
    uid = int(claims["uid"])
    lang = get_user_language(uid) or "uz"
    quota_err = _check_access_and_quota(uid)
    if quota_err:
        return quota_err

    job_dir = tempfile.mkdtemp(prefix=f"app_mrg_{uid}_", dir=DOWNLOAD_DIR)
    try:
        files, _ = await _save_multipart_files(request, job_dir)
        pdf_paths = [p for p, _ in files if p.lower().endswith(".pdf")]
        if len(pdf_paths) < 2:
            return web.json_response({"ok": False, "error": _strip_html(t("err_min_two_pdfs", lang))}, status=400)

        out_pdf = os.path.join(job_dir, "merged.pdf")
        await asyncio.to_thread(merge_pdfs, pdf_paths, out_pdf)
        inc_uses_and_log(uid, "pdf_merge")
        return _file_bytes_response(out_pdf, "merged_sifatli.pdf", "application/pdf")
    except web.HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mobile merge_pdf error for {uid}: {e}")
        return web.json_response({"ok": False, "error": _strip_html(friendly_error(e, lang))}, status=400)
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


async def handle_convert_compress_pdf(request: web.Request) -> web.Response:
    claims, err = _require_user(request)
    if err:
        return err
    uid = int(claims["uid"])
    lang = get_user_language(uid) or "uz"
    quota_err = _check_access_and_quota(uid)
    if quota_err:
        return quota_err

    job_dir = tempfile.mkdtemp(prefix=f"app_cmp_{uid}_", dir=DOWNLOAD_DIR)
    try:
        files, _ = await _save_multipart_files(request, job_dir)
        if not files or not files[0][0].lower().endswith(".pdf"):
            return web.json_response({"ok": False, "error": _strip_html(t("err_only_pdf", lang))}, status=400)

        in_pdf, orig_name = files[0]
        out_pdf = os.path.join(job_dir, "compressed.pdf")
        await asyncio.to_thread(compress_pdf, in_pdf, out_pdf)

        orig_sz = os.path.getsize(in_pdf)
        comp_sz = os.path.getsize(out_pdf)
        saved_pct = round((1 - comp_sz / orig_sz) * 100, 1) if orig_sz > 0 else 0.0
        inc_uses_and_log(uid, "compress_pdf")
        stem = Path(orig_name).stem or "document"
        return _file_bytes_response(
            out_pdf,
            f"compressed_{stem}.pdf",
            "application/pdf",
            {
                "X-Original-Size": str(orig_sz),
                "X-Compressed-Size": str(comp_sz),
                "X-Saved-Pct": str(saved_pct),
            },
        )
    except web.HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mobile compress_pdf error for {uid}: {e}")
        return web.json_response({"ok": False, "error": _strip_html(friendly_error(e, lang))}, status=400)
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


async def handle_convert_pdf_to_images(request: web.Request) -> web.Response:
    claims, err = _require_user(request)
    if err:
        return err
    uid = int(claims["uid"])
    lang = get_user_language(uid) or "uz"
    quota_err = _check_access_and_quota(uid)
    if quota_err:
        return quota_err

    job_dir = tempfile.mkdtemp(prefix=f"app_p2i_{uid}_", dir=DOWNLOAD_DIR)
    try:
        files, _ = await _save_multipart_files(request, job_dir)
        if not files or not files[0][0].lower().endswith(".pdf"):
            return web.json_response({"ok": False, "error": _strip_html(t("err_only_pdf", lang))}, status=400)

        in_pdf, orig_name = files[0]
        images, _ = await asyncio.to_thread(pdf_to_images, in_pdf, job_dir, 180)
        if not images:
            return web.json_response({"ok": False, "error": _strip_html(t("err_pdf_no_pages", lang))}, status=400)

        zip_out = os.path.join(job_dir, "pages_images.zip")
        with zipfile.ZipFile(zip_out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for idx, img_p in enumerate(images, 1):
                zf.write(img_p, arcname=f"page_{idx:03d}.jpg")

        inc_uses_and_log(uid, "pdf_to_img")
        stem = Path(orig_name).stem or "pages"
        return _file_bytes_response(
            zip_out,
            f"{stem}_images.zip",
            "application/zip",
            {"X-Pages": str(len(images))},
        )
    except web.HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mobile pdf_to_images error for {uid}: {e}")
        return web.json_response({"ok": False, "error": _strip_html(friendly_error(e, lang))}, status=400)
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


async def handle_convert_watermark_pdf(request: web.Request) -> web.Response:
    claims, err = _require_user(request)
    if err:
        return err
    uid = int(claims["uid"])
    lang = get_user_language(uid) or "uz"
    quota_err = _check_access_and_quota(uid)
    if quota_err:
        return quota_err

    job_dir = tempfile.mkdtemp(prefix=f"app_wm_{uid}_", dir=DOWNLOAD_DIR)
    try:
        files, fields = await _save_multipart_files(request, job_dir)
        wm_text = (fields.get("text") or "SIFATLI PDF").strip()[:80]
        if not files or not files[0][0].lower().endswith(".pdf"):
            return web.json_response({"ok": False, "error": _strip_html(t("err_only_pdf", lang))}, status=400)

        in_pdf, orig_name = files[0]
        out_pdf = os.path.join(job_dir, "watermarked.pdf")
        total = await asyncio.to_thread(watermark_pdf, in_pdf, out_pdf, wm_text)
        inc_uses_and_log(uid, "watermark_pdf")
        stem = Path(orig_name).stem or "document"
        return _file_bytes_response(
            out_pdf,
            f"watermarked_{stem}.pdf",
            "application/pdf",
            {"X-Pages": str(total)},
        )
    except web.HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mobile watermark_pdf error for {uid}: {e}")
        return web.json_response({"ok": False, "error": _strip_html(friendly_error(e, lang))}, status=400)
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


async def handle_convert_images_to_pdf(request: web.Request) -> web.Response:
    claims, err = _require_user(request)
    if err:
        return err
    uid = int(claims["uid"])
    lang = get_user_language(uid) or "uz"
    quota_err = _check_access_and_quota(uid)
    if quota_err:
        return quota_err

    job_dir = tempfile.mkdtemp(prefix=f"app_i2p_{uid}_", dir=DOWNLOAD_DIR)
    try:
        files, _ = await _save_multipart_files(request, job_dir)
        img_paths = [p for p, _ in files]
        if not img_paths:
            return web.json_response({"ok": False, "error": "No images uploaded"}, status=400)

        out_pdf = os.path.join(job_dir, "images.pdf")
        await asyncio.to_thread(images_to_pdf, img_paths, out_pdf)
        inc_uses_and_log(uid, "img_pdf")
        return _file_bytes_response(out_pdf, "images_sifatli.pdf", "application/pdf")
    except web.HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mobile images_to_pdf error for {uid}: {e}")
        return web.json_response({"ok": False, "error": _strip_html(friendly_error(e, lang))}, status=400)
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


async def handle_convert_text_to_pdf(request: web.Request) -> web.Response:
    claims, err = _require_user(request)
    if err:
        return err
    uid = int(claims["uid"])
    lang = get_user_language(uid) or "uz"
    quota_err = _check_access_and_quota(uid)
    if quota_err:
        return quota_err

    try:
        data = await request.json()
        text = str(data.get("text") or "").strip()
        title = str(data.get("title") or "").strip()
        if not text:
            return web.json_response({"ok": False, "error": "Text is empty"}, status=400)

        pdf_bytes = await asyncio.to_thread(_make_unicode_text_pdf_bytes, text, title)
        inc_uses_and_log(uid, "text_pdf")
        return web.Response(
            body=pdf_bytes,
            content_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="text_sifatli.pdf"'},
        )
    except Exception as e:
        logger.error(f"Mobile text_to_pdf error for {uid}: {e}")
        return web.json_response({"ok": False, "error": _strip_html(friendly_error(e, lang))}, status=400)


# ============================================================================
# SUPER ADMIN ENDPOINTS (Password-Protected)
# ============================================================================

async def handle_admin_login(request: web.Request) -> web.Response:
    data = await request.json()
    password = str(data.get("password") or "")
    if not verify_super_admin_password(password):
        return web.json_response({"ok": False, "error": "Invalid Super Admin password"}, status=401)

    admin_token = create_jwt({"super_admin": True}, ttl_seconds=30 * 86400)
    return web.json_response({"ok": True, "admin_token": admin_token})


async def handle_admin_dashboard(request: web.Request) -> web.Response:
    err = _require_super_admin(request)
    if err:
        return err
    return web.json_response({
        "ok": True,
        "summary": get_admin_summary(),
        "mobile_devices": get_mobile_devices_count(),
        "finance": get_finance_summary(),
        "actions": get_action_stats(),
        "settings": get_all_settings(),
        "promos": get_all_promo_codes(),
    })


async def handle_admin_update_settings(request: web.Request) -> web.Response:
    err = _require_super_admin(request)
    if err:
        return err
    data = await request.json()
    allowed_keys = {
        "daily_free_limit", "vip_30_uzs", "vip_365_uzs",
        "vip_30_stars", "vip_365_stars", "card_number", "maintenance_mode",
    }
    for k, v in data.items():
        if k in allowed_keys and v is not None:
            set_setting(k, str(v))
    return web.json_response({"ok": True, "settings": get_all_settings()})


async def handle_admin_promo_create(request: web.Request) -> web.Response:
    err = _require_super_admin(request)
    if err:
        return err
    data = await request.json()
    code = str(data.get("code") or "").strip().upper()
    reward_type = str(data.get("reward_type") or "bonus_uses").strip()
    reward_value = int(data.get("reward_value") or 0)
    max_uses = int(data.get("max_uses") or 0)
    ok = create_promo_code(code, reward_type, reward_value, max_uses)
    if not ok:
        return web.json_response({"ok": False, "error": "Invalid or duplicate promo code"}, status=400)
    return web.json_response({"ok": True, "promos": get_all_promo_codes()})


async def handle_admin_promo_delete(request: web.Request) -> web.Response:
    err = _require_super_admin(request)
    if err:
        return err
    data = await request.json()
    promo_id = int(data.get("promo_id") or 0)
    delete_promo_code(promo_id)
    return web.json_response({"ok": True, "promos": get_all_promo_codes()})


async def handle_admin_grant_vip(request: web.Request) -> web.Response:
    err = _require_super_admin(request)
    if err:
        return err
    data = await request.json()
    query = str(data.get("query") or "").strip()
    days = int(data.get("days") or 30)
    u = resolve_user_id(query)
    if not u:
        return web.json_response({"ok": False, "error": f"User not found: {query}"}, status=404)
    activate_img_pdf_pass(u["user_id"], days=days)
    return web.json_response({"ok": True, "user": _build_user_payload(u["user_id"])})


async def handle_admin_add_bonus(request: web.Request) -> web.Response:
    err = _require_super_admin(request)
    if err:
        return err
    data = await request.json()
    query = str(data.get("query") or "").strip()
    amount = int(data.get("amount") or 5)
    u = resolve_user_id(query)
    if not u:
        return web.json_response({"ok": False, "error": f"User not found: {query}"}, status=404)
    add_user_balance(u["user_id"], amount)
    return web.json_response({"ok": True, "user": _build_user_payload(u["user_id"])})


# ============================================================================
# SERVER LIFECYCLE
# ============================================================================

def build_api_app(bot: Bot) -> web.Application:
    app = web.Application(
        middlewares=[cors_and_error_middleware],
        client_max_size=MAX_FILE_SIZE + 5 * 1024 * 1024,
    )
    app["bot"] = bot
    app.router.add_get("/api/v1/health", handle_health)
    app.router.add_post("/api/v1/auth/device", handle_auth_device)
    app.router.add_post("/api/v1/auth/telegram-link/start", handle_tg_link_start)
    app.router.add_get("/api/v1/auth/telegram-link/poll", handle_tg_link_poll)
    app.router.add_get("/api/v1/me", handle_get_me)
    app.router.add_post("/api/v1/me/language", handle_set_language)
    app.router.add_post("/api/v1/usage/log-local", handle_log_local_usage)
    app.router.add_post("/api/v1/billing/promo", handle_redeem_promo)
    app.router.add_post("/api/v1/billing/vip-receipt", handle_vip_receipt_upload)

    # Conversion routes
    app.router.add_post("/api/v1/convert/pdf-to-word", handle_convert_pdf_to_word)
    app.router.add_post("/api/v1/convert/office-to-pdf", handle_convert_office_to_pdf)
    app.router.add_post("/api/v1/convert/merge-pdf", handle_convert_merge_pdf)
    app.router.add_post("/api/v1/convert/compress-pdf", handle_convert_compress_pdf)
    app.router.add_post("/api/v1/convert/pdf-to-images", handle_convert_pdf_to_images)
    app.router.add_post("/api/v1/convert/watermark-pdf", handle_convert_watermark_pdf)
    app.router.add_post("/api/v1/convert/images-to-pdf", handle_convert_images_to_pdf)
    app.router.add_post("/api/v1/convert/text-to-pdf", handle_convert_text_to_pdf)

    # Super Admin routes
    app.router.add_post("/api/v1/admin/login", handle_admin_login)
    app.router.add_get("/api/v1/admin/dashboard", handle_admin_dashboard)
    app.router.add_post("/api/v1/admin/settings", handle_admin_update_settings)
    app.router.add_post("/api/v1/admin/promo/create", handle_admin_promo_create)
    app.router.add_post("/api/v1/admin/promo/delete", handle_admin_promo_delete)
    app.router.add_post("/api/v1/admin/user/grant-vip", handle_admin_grant_vip)
    app.router.add_post("/api/v1/admin/user/add-bonus", handle_admin_add_bonus)
    return app


async def start_api_server(bot: Bot, port: int = API_PORT):
    """Start aiohttp Mobile REST API non-blocking on 0.0.0.0:<port>."""
    global _API_RUNNER, _BOT_USERNAME_CACHE
    try:
        me = await bot.get_me()
        if me and me.username:
            _BOT_USERNAME_CACHE = me.username
    except Exception:
        pass

    app = build_api_app(bot)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    _API_RUNNER = runner
    logger.info(f"Mobile REST API listening on 0.0.0.0:{port}")


async def stop_api_server():
    global _API_RUNNER
    if _API_RUNNER:
        try:
            await _API_RUNNER.cleanup()
        except Exception:
            pass
        _API_RUNNER = None
