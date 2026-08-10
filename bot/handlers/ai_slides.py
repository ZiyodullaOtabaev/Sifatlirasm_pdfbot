"""
AI Presentation / Slide Generation Handler (Paid feature via python-pptx).
Supports Visual Template Gallery with photo previews, 12-Slide Standard Deck,
Author Metadata, References, and PPTX-to-PDF conversion.
"""
import os
import logging
from typing import Dict

from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto

from bot.database import (
    upsert_user,
    get_user_balance,
    deduct_user_balance,
    inc_uses_and_log,
    get_user_language,
    has_user_used_free_slide
)
from bot.i18n import t
from bot.keyboards import kb_cancel, kb_top_up, kb_top_up_slides, kb_template_gallery, kb_slide_result, kb_author_skip
from bot.states import get_state, set_state, STATE_WAIT_AI_SLIDES, STATE_WAIT_SLIDE_AUTHOR, STATE_NONE
from bot.handlers.menu import show_main_menu
from bot.utils.slides_generator import (
    create_presentation_slides,
    convert_pptx_to_pdf,
    generate_template_preview_image,
    SLIDE_THEMES,
    THEME_KEYS
)

logger = logging.getLogger(__name__)
router = Router(name="ai_slides")

# Temporary in-memory cache for user topic, author metadata, gallery state, and file themes
USER_SLIDE_DATA: Dict[int, Dict[str, str]] = {}
USER_GALLERY_INDEX: Dict[int, int] = {}
FILE_THEME_CACHE: Dict[str, str] = {}

SLIDE_COST = 7


async def _safe_answer(call: CallbackQuery):
    try:
        await call.answer()
    except Exception:
        pass


@router.callback_query(F.data == "act_ai_slides")
async def cb_ai_slides(call: CallbackQuery, bot: Bot):
    """Start AI Slides generation flow."""
    await _safe_answer(call)
    user = call.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user_id) or "uz"

    used_trial = has_user_used_free_slide(user_id)
    cost = 0 if not used_trial else SLIDE_COST

    balance = get_user_balance(user_id)
    if cost > 0 and balance < cost:
        await bot.send_message(
            user_id,
            t("ai_slides_insufficient_balance", lang, balance=balance),
            parse_mode="HTML",
            reply_markup=kb_top_up_slides(lang)
        )
        return

    if not used_trial:
        if lang == "ru":
            trial_text = "🎁 <b>У вас есть 1 БЕСПЛАТНАЯ пробная презентация!</b> (0 кредитов)"
        elif lang == "en":
            trial_text = "🎁 <b>You have 1 FREE trial presentation!</b> (0 credits)"
        else:
            trial_text = "🎁 <b>Sizda 1 ta BEPUL sinov taqdimoti bor!</b> (0 kredit)"
    else:
        if lang == "ru":
            trial_text = "📌 Стоимость презентации: <b>7 кредитов (2 000 сум или ⭐️ 20 Stars)</b>"
        elif lang == "en":
            trial_text = "📌 Presentation price: <b>7 credits (2,000 UZS or ⭐️ 20 Stars)</b>"
        else:
            trial_text = "📌 Taqdimot narxi: <b>7 kredit (2 000 so'm yoki ⭐️ 20 Stars)</b>"

    USER_SLIDE_DATA[user_id] = {}
    set_state(user_id, STATE_WAIT_AI_SLIDES)
    await bot.send_message(
        user_id,
        t("ai_slides_prompt", lang, balance=balance, trial_text=trial_text),
        parse_mode="HTML",
        reply_markup=kb_cancel(lang)
    )


@router.message(lambda msg: msg.text and not msg.text.startswith("/") and get_state(msg.from_user.id) == STATE_WAIT_AI_SLIDES)
async def handle_ai_slides_topic(message: Message, bot: Bot):
    """Handle presentation topic input and ask for author metadata."""
    user = message.from_user
    user_id = user.id
    upsert_user(user_id, user.username, user.first_name, user.last_name)
    lang = get_user_language(user_id) or "uz"

    used_trial = has_user_used_free_slide(user_id)
    cost = 0 if not used_trial else SLIDE_COST

    balance = get_user_balance(user_id)
    if cost > 0 and balance < cost:
        await message.answer(
            t("ai_slides_insufficient_balance", lang, balance=balance),
            parse_mode="HTML",
            reply_markup=kb_top_up(lang)
        )
        set_state(user_id, STATE_NONE)
        return

    topic = message.text.strip()
    if not topic:
        return

    USER_SLIDE_DATA[user_id] = {"topic": topic, "author": "", "institution": ""}
    set_state(user_id, STATE_WAIT_SLIDE_AUTHOR)

    await message.answer(
        t("ai_slides_author_prompt", lang),
        parse_mode="HTML",
        reply_markup=kb_author_skip(lang)
    )


@router.message(lambda msg: msg.text and not msg.text.startswith("/") and get_state(msg.from_user.id) == STATE_WAIT_SLIDE_AUTHOR)
async def handle_ai_slides_author_text(message: Message, bot: Bot):
    """Handle author and institution input text."""
    user_id = message.from_user.id
    lang = get_user_language(user_id) or "uz"

    author_input = message.text.strip()
    parts = [p.strip() for p in author_input.split("|")]
    author_name = parts[0] if len(parts) > 0 else author_input
    institution = parts[1] if len(parts) > 1 else ""

    if user_id not in USER_SLIDE_DATA:
        USER_SLIDE_DATA[user_id] = {"topic": "Taqdimot"}

    USER_SLIDE_DATA[user_id]["author"] = author_name
    USER_SLIDE_DATA[user_id]["institution"] = institution

    await _send_gallery_item(bot, user_id, index=0, lang=lang)


@router.callback_query(F.data == "act_skip_author")
async def cb_skip_author(call: CallbackQuery, bot: Bot):
    """Handle skipping author metadata step."""
    await _safe_answer(call)
    user_id = call.from_user.id
    lang = get_user_language(user_id) or "uz"

    if user_id not in USER_SLIDE_DATA:
        USER_SLIDE_DATA[user_id] = {"topic": "Taqdimot"}

    USER_SLIDE_DATA[user_id]["author"] = "Mutaxassis"
    USER_SLIDE_DATA[user_id]["institution"] = ""

    await _send_gallery_item(bot, user_id, index=0, lang=lang)


async def _send_gallery_item(bot: Bot, user_id: int, index: int, lang: str = "uz"):
    """Send visual template preview photo with gallery navigation keyboard."""
    total_count = len(THEME_KEYS)
    index = index % total_count
    USER_GALLERY_INDEX[user_id] = index

    theme_key = THEME_KEYS[index]
    theme_info = SLIDE_THEMES[theme_key]
    preview_img_path = generate_template_preview_image(theme_key)

    data = USER_SLIDE_DATA.get(user_id, {})
    topic = data.get("topic", "Taqdimot")
    author = data.get("author", "Ko'rsatilmagan")

    caption = (
        f"🖼 <b>Shablon {index + 1}/{total_count}: {theme_info['name']}</b>\n\n"
        f"📌 Mavzu: <b>{topic[:60]}</b>\n"
        f"👤 Muallif: <b>{author[:40]}</b>\n"
        f"📄 Slaydlar soni: <b>12 bet (FLUX AI Rasmlari bilan)</b>\n\n"
        f"👇 Shablonlarni ko'rish uchun strelkalardan foydalaning:"
    )

    photo_file = FSInputFile(preview_img_path)
    await bot.send_photo(
        user_id,
        photo_file,
        caption=caption,
        parse_mode="HTML",
        reply_markup=kb_template_gallery(index, total_count, theme_key, lang)
    )

    if os.path.exists(preview_img_path):
        try:
            os.remove(preview_img_path)
        except Exception:
            pass


@router.callback_query(F.data.startswith("gallery_nav_"))
async def cb_gallery_nav(call: CallbackQuery, bot: Bot):
    """Navigate to previous/next template preview in gallery."""
    await _safe_answer(call)
    user_id = call.from_user.id
    lang = get_user_language(user_id) or "uz"

    try:
        new_index = int(call.data.replace("gallery_nav_", ""))
    except ValueError:
        new_index = 0

    total_count = len(THEME_KEYS)
    new_index = new_index % total_count
    USER_GALLERY_INDEX[user_id] = new_index

    theme_key = THEME_KEYS[new_index]
    theme_info = SLIDE_THEMES[theme_key]
    preview_img_path = generate_template_preview_image(theme_key)

    data = USER_SLIDE_DATA.get(user_id, {})
    topic = data.get("topic", "Taqdimot")
    author = data.get("author", "Ko'rsatilmagan")

    caption = (
        f"🖼 <b>Shablon {new_index + 1}/{total_count}: {theme_info['name']}</b>\n\n"
        f"📌 Mavzu: <b>{topic[:60]}</b>\n"
        f"👤 Muallif: <b>{author[:40]}</b>\n"
        f"📄 Slaydlar soni: <b>12 bet (FLUX AI Rasmlari bilan)</b>\n\n"
        f"👇 Shablonlarni ko'rish uchun strelkalardan foydalaning:"
    )

    try:
        photo_file = FSInputFile(preview_img_path)
        media = InputMediaPhoto(media=photo_file, caption=caption, parse_mode="HTML")
        await bot.edit_message_media(
            chat_id=user_id,
            message_id=call.message.message_id,
            media=media,
            reply_markup=kb_template_gallery(new_index, total_count, theme_key, lang)
        )
    except Exception:
        await _send_gallery_item(bot, user_id, new_index, lang)
    finally:
        if os.path.exists(preview_img_path):
            try:
                os.remove(preview_img_path)
            except Exception:
                pass


@router.callback_query(F.data.startswith("gallery_select_"))
async def cb_select_gallery_template(call: CallbackQuery, bot: Bot):
    """Handle template selection from gallery, generate 12-slide PPTX with FLUX AI images, deduct cost, and send file."""
    await _safe_answer(call)
    user = call.from_user
    user_id = user.id
    lang = get_user_language(user_id) or "uz"

    theme_name = call.data.replace("gallery_select_", "")
    data = USER_SLIDE_DATA.get(user_id, {})
    topic = data.get("topic", "Taqdimot")
    author_name = data.get("author", "")
    institution = data.get("institution", "")

    used_trial = has_user_used_free_slide(user_id)
    cost = 0 if not used_trial else SLIDE_COST

    balance = get_user_balance(user_id)
    if cost > 0 and balance < cost:
        await bot.send_message(
            user_id,
            t("ai_slides_insufficient_balance", lang, balance=balance),
            parse_mode="HTML",
            reply_markup=kb_top_up_slides(lang)
        )
        set_state(user_id, STATE_NONE)
        return

    status = await bot.send_message(user_id, t("ai_slides_generating", lang))
    pptx_path = None

    try:
        pptx_path = create_presentation_slides(
            topic=topic,
            theme_name=theme_name,
            author_name=author_name,
            institution=institution
        )
        
        # Deduct cost (0 if free trial, 3 if paid) & log usage
        if cost > 0:
            deduct_user_balance(user_id, cost)
        inc_uses_and_log(user_id, "ai_slides")

        remaining = get_user_balance(user_id)
        theme_title = SLIDE_THEMES.get(theme_name, {}).get("name", theme_name)

        cost_notice = "🎁 <b>1-Sinov taqdimotingiz BEPUL berildi!</b>" if cost == 0 else f"💰 Yechildi: <b>7 kredit</b> | Qolgan balans: <b>{remaining} kredit</b>"

        caption = (
            f"📊 <b>{topic[:60]}</b>\n"
            f"🤖 AI Engine: <b>Google Gemini & FLUX AI</b>\n"
            f"🎨 Shablon: <b>{theme_title}</b>\n"
            f"👤 Muallif: <b>{author_name or 'Mutaxassis'}</b>\n"
            f"📄 Slaydlar: <b>12 bet (FLUX AI Rasmlari bilan)</b>\n\n"
            f"{cost_notice}"
        )

        file_id = os.path.basename(pptx_path).replace(".pptx", "")
        FILE_THEME_CACHE[file_id] = theme_name

        doc_file = FSInputFile(pptx_path, filename=f"taqdimot_{topic[:20]}.pptx")
        await bot.send_document(
            user_id,
            doc_file,
            caption=caption,
            parse_mode="HTML",
            reply_markup=kb_slide_result(lang, file_id)
        )
        logger.info(f"User {user_id}: generated 12-slide presentation '{topic}' [theme={theme_name}] (cost={cost} credits)")

    except Exception as e:
        logger.error(f"AI Slides generation error for user {user_id}: {e}")
        from bot.utils.helpers import friendly_error
        await bot.send_message(
            user_id,
            f"❌ {friendly_error(e)}\n\n" + t("ai_video_refund_notify", lang),
            parse_mode="HTML"
        )
    finally:
        try:
            await status.delete()
        except Exception:
            pass
        # Instant File Cleanup to keep server disk space at 0MB
        if pptx_path and os.path.exists(pptx_path):
            try:
                os.remove(pptx_path)
                logger.info(f"Instantly deleted PPTX file from server: {pptx_path}")
            except Exception as remove_err:
                logger.warning(f"Could not delete PPTX file: {remove_err}")

    set_state(user_id, STATE_NONE)


@router.callback_query(F.data.startswith("convert_slide_pdf_"))
async def cb_convert_slide_pdf(call: CallbackQuery, bot: Bot):
    """Convert generated PPTX file into PDF and deliver to user."""
    await _safe_answer(call)
    user_id = call.from_user.id
    lang = get_user_language(user_id) or "uz"

    file_id = call.data.replace("convert_slide_pdf_", "")
    pptx_path = os.path.join("downloads", f"{file_id}.pptx")

    data = USER_SLIDE_DATA.get(user_id, {})
    topic = data.get("topic", "Taqdimot")

    status = await bot.send_message(user_id, t("pdf_converting_msg", lang))
    pdf_path = None
    temp_created_pptx = False

    try:
        if not os.path.exists(pptx_path):
            # Re-generate clean PPTX in memory for PDF conversion if deleted
            theme_name = FILE_THEME_CACHE.get(file_id, "oxford_navy")
            pptx_path = create_presentation_slides(
                topic=topic,
                theme_name=theme_name,
                author_name=data.get("author", ""),
                institution=data.get("institution", "")
            )
            temp_created_pptx = True

        theme_name = FILE_THEME_CACHE.get(file_id, "oxford_navy")
        pdf_path = convert_pptx_to_pdf(pptx_path, theme_name=theme_name)

        doc_file = FSInputFile(pdf_path, filename=f"{topic[:20]}.pdf")
        await bot.send_document(
            user_id,
            doc_file,
            caption="📄 <b>Slaydning tayyor PDF versiyasi!</b>",
            parse_mode="HTML"
        )
        logger.info(f"Converted PPTX {file_id} to PDF for user {user_id}")

    except Exception as e:
        logger.error(f"Error converting PPTX to PDF for user {user_id}: {e}")
        from bot.utils.helpers import friendly_error
        await bot.send_message(user_id, f"❌ PDF ga o'tkazishda xatolik: {friendly_error(e)}")
    finally:
        try:
            await status.delete()
        except Exception:
            pass
        # Instant File Cleanup for PDF and temporary PPTX
        for cleanup_f in [pdf_path, pptx_path if temp_created_pptx else None]:
            if cleanup_f and os.path.exists(cleanup_f):
                try:
                    os.remove(cleanup_f)
                    logger.info(f"Instantly deleted PDF/PPTX file from server: {cleanup_f}")
                except Exception:
                    pass
