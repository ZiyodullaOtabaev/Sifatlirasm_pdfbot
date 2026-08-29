"""
Bot handlers package.
"""
from aiogram import Router

from bot.handlers.start import router as start_router
from bot.handlers.text_pdf import router as text_pdf_router
from bot.handlers.img_pdf import router as img_pdf_router
from bot.handlers.upscale import router as upscale_router
from bot.handlers.merge_pdf import router as merge_pdf_router
from bot.handlers.ai_image import router as ai_image_router
from bot.handlers.ai_video import router as ai_video_router
from bot.handlers.ai_slides import router as ai_slides_router
from bot.handlers.compress import router as compress_router
from bot.handlers.passport_photo import router as passport_photo_router
from bot.handlers.voice_to_text import router as voice_to_text_router
from bot.handlers.admin import router as admin_router
from bot.handlers.profile import router as profile_router
from bot.handlers.payments import router as payments_router
from bot.handlers.menu import router as menu_router


def get_all_routers() -> list[Router]:
    """Return all handler routers in priority order."""
    return [
        start_router,
        admin_router,
        profile_router,
        payments_router,
        passport_photo_router,
        voice_to_text_router,
        text_pdf_router,
        img_pdf_router,
        upscale_router,
        merge_pdf_router,
        ai_image_router,
        ai_video_router,
        ai_slides_router,
        compress_router,
        menu_router,  # menu eng oxirida — callback'larni ushlaydi
    ]
