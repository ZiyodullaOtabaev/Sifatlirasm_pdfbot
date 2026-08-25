"""
User state constants and state management.
"""
from typing import Dict

STATE_NONE = "none"
STATE_WAIT_TEXT = "wait_text"
STATE_WAIT_IMG_PDF = "wait_img_pdf"
STATE_WAIT_UPSCALE = "wait_upscale"
STATE_WAIT_PDF_MERGE = "wait_pdf_merge"
STATE_WAIT_BG_REMOVE = "wait_bg_remove"
STATE_WAIT_AI_IMAGE = "wait_ai_image"
STATE_WAIT_OCR = "wait_ocr"
STATE_WAIT_COMPRESS_PDF = "wait_compress_pdf"
STATE_WAIT_AI_VIDEO = "wait_ai_video"
STATE_WAIT_BROADCAST = "wait_broadcast"
STATE_WAIT_ADMIN_BALANCE_INPUT = "wait_admin_balance_input"
STATE_WAIT_SEARCH = "wait_search"
STATE_WAIT_AI_SLIDES = "wait_ai_slides"
STATE_WAIT_SLIDE_AUTHOR = "wait_slide_author"
STATE_WAIT_PASSPORT_PHOTO = "wait_passport_photo"
STATE_WAIT_VOICE_TO_TEXT = "wait_voice_to_text"
STATE_WAIT_ADMIN_CHANNEL_ID = "wait_admin_channel_id"
STATE_WAIT_ADMIN_CHANNEL_TARGET = "wait_admin_channel_target"

# In-memory state storage
USER_STATE: Dict[int, str] = {}


def set_state(user_id: int, state: str):
    """Set user's current state."""
    USER_STATE[user_id] = state


def get_state(user_id: int) -> str:
    """Get user's current state."""
    return USER_STATE.get(user_id, STATE_NONE)
