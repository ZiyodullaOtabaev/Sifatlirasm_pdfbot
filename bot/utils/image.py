"""
Image processing utilities: upscale (local), smart scan, compress PDF.
"""
import os
import logging
import subprocess

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None
from PIL import Image

from bot.config import (
    ENABLE_REAL_AI, REAL_ESRGAN_BIN, REAL_ESRGAN_MODELS,
)

logger = logging.getLogger(__name__)


# ======================
#   UPSCALE (local)
# ======================

async def ai_upscale(in_path: str, out_path: str) -> bool:
    """
    Rasm sifatini oshirish (to'liq bepul, lokal).
    Tartib:
      1. Real-ESRGAN ncnn binary (agar o'rnatilgan bo'lsa)
      2. Pillow LANCZOS (fallback)

    Returns True if successful.
    """
    # 1-usul: Real-ESRGAN ncnn binary (lokal, offline)
    if ENABLE_REAL_AI and REAL_ESRGAN_BIN:
        try:
            success = _try_realesrgan_binary(in_path, out_path)
            if success:
                logger.info("Upscale via Real-ESRGAN binary - success")
                return True
        except Exception as e:
            logger.warning(f"Real-ESRGAN binary error: {e}")

    # 2-usul: Pillow LANCZOS fallback
    _pillow_upscale(in_path, out_path)
    logger.info("Upscale via Pillow LANCZOS (fallback)")
    return True


# ======================
#   Real-ESRGAN Binary (offline)
# ======================

def _try_realesrgan_binary(in_path: str, out_path: str) -> bool:
    """Real-ESRGAN ncnn-vulkan binary orqali upscale."""
    if not REAL_ESRGAN_BIN or not os.path.exists(REAL_ESRGAN_BIN):
        return False
    model_dir = REAL_ESRGAN_MODELS if REAL_ESRGAN_MODELS else "models"
    if REAL_ESRGAN_MODELS and not os.path.exists(REAL_ESRGAN_MODELS):
        return False
    cmd = [
        REAL_ESRGAN_BIN, "-i", in_path, "-o", out_path,
        "-s", "4", "-n", "realesrgan-x4plus", "-m", model_dir
    ]
    try:
        p = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=180
        )
        return p.returncode == 0 and os.path.exists(out_path)
    except Exception:
        return False


# ======================
#   Pillow Fallback
# ======================

def _pillow_upscale(in_path: str, out_path: str):
    """Pillow LANCZOS orqali 2x upscale (fallback)."""
    img = Image.open(in_path)
    new_size = (img.width * 2, img.height * 2)
    up = img.resize(new_size, Image.LANCZOS)
    up.save(out_path, quality=95, optimize=True)


# Legacy funksiyalar (eski handler'lar uchun moslik)
def pillow_upscale_2x(in_path: str, out_path: str):
    """Backward compatible wrapper."""
    _pillow_upscale(in_path, out_path)


def try_realesrgan(in_path: str, out_path: str) -> bool:
    """Backward compatible wrapper."""
    return _try_realesrgan_binary(in_path, out_path)


# ======================
#   SMART SCAN
# ======================

def smart_scan_document(input_path: str, output_path: str):
    """Scan document with perspective correction and quality enhancement."""
    image = cv2.imread(input_path)
    if image is None:
        raise Exception("Image topilmadi")

    original = image.copy()
    ratio = image.shape[0] / 1000.0
    resized = cv2.resize(image, (int(image.shape[1] / ratio), 1000))

    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blur, 50, 150)

    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

    doc_contour = None
    for contour in contours:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        if len(approx) == 4:
            doc_contour = approx
            break

    if doc_contour is None:
        cropped = original
    else:
        pts = doc_contour.reshape(4, 2) * ratio
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        (tl, tr, br, bl) = rect
        maxWidth = max(int(np.linalg.norm(br - bl)), int(np.linalg.norm(tr - tl)))
        maxHeight = max(int(np.linalg.norm(tr - br)), int(np.linalg.norm(tl - bl)))

        dst = np.array([
            [0, 0], [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]
        ], dtype="float32")

        matrix = cv2.getPerspectiveTransform(rect, dst)
        cropped = cv2.warpPerspective(original, matrix, (maxWidth, maxHeight))

    # Quality enhancement
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    denoise = cv2.fastNlMeansDenoising(gray, None, 8, 7, 21)
    clahe = cv2.createCLAHE(clipLimit=2.8, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoise)
    blur = cv2.GaussianBlur(enhanced, (0, 0), 1.5)
    sharp = cv2.addWeighted(enhanced, 1.65, blur, -0.65, 0)

    kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    sharp = cv2.filter2D(sharp, -1, kernel)

    cv2.imwrite(output_path, sharp, [cv2.IMWRITE_JPEG_QUALITY, 95])


# ======================
#   PDF COMPRESS
# ======================

def compress_pdf(input_path: str, output_path: str):
    """
    Compress PDF using pypdf — the most reliable approach.

    Strategy:
    - Lossless: compress content streams + deduplicate objects
    - Lossy (only if beneficial): replace images with lower quality JPEG
    - Safety: if compressed file is larger than original, save lossless-only version
    """
    from pypdf import PdfWriter
    from PIL import Image as PILImage
    import io
    import shutil

    if not os.path.exists(input_path):
        raise FileNotFoundError("PDF topilmadi")

    original_size = os.path.getsize(input_path)

    writer = PdfWriter(clone_from=input_path)

    # Image compression via pypdf's built-in API
    for page in writer.pages:
        # Compress content streams (lossless)
        page.compress_content_streams(level=9)

        # Replace images with lower quality versions
        for img in page.images:
            try:
                pil_img = img.image

                # Skip small images (< 50KB)
                raw_data = img.data
                if len(raw_data) < 50_000:
                    continue

                # Skip transparent images
                if pil_img.mode in ("RGBA", "PA", "LA"):
                    continue

                # Convert to RGB
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")

                # Downscale very large images
                w, h = pil_img.size
                if max(w, h) > 1800:
                    ratio = 1800 / max(w, h)
                    pil_img = pil_img.resize(
                        (int(w * ratio), int(h * ratio)),
                        PILImage.LANCZOS
                    )

                # Siqilgan versiyani yaratish
                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=65, optimize=True)
                compressed_size = buf.tell()

                # Faqat kichraygan bo'lsa almashtirish (kamida 10% tejash)
                if compressed_size < len(raw_data) * 0.90:
                    img.replace(pil_img, quality=65)

            except Exception:
                continue

    # Remove duplicates and unreferenced objects
    writer.compress_identical_objects(
        remove_duplicates=True,
        remove_unreferenced=True,
    )

    with open(output_path, "wb") as f:
        writer.write(f)

    # Xavfsizlik: agar natija kattaroq bo'lsa — faqat lossless versiya
    if os.path.exists(output_path) and os.path.getsize(output_path) >= original_size:
        # Faqat lossless (rasmlarni o'zgartirmasdan)
        os.unlink(output_path)
        writer2 = PdfWriter(clone_from=input_path)
        for page in writer2.pages:
            page.compress_content_streams(level=9)
        writer2.compress_identical_objects(
            remove_duplicates=True,
            remove_unreferenced=True,
        )
        with open(output_path, "wb") as f:
            writer2.write(f)

    # Agar hali ham kattaroq — original nusxa
    if os.path.exists(output_path) and os.path.getsize(output_path) >= original_size:
        os.unlink(output_path)
        shutil.copy2(input_path, output_path)

    if not os.path.exists(output_path):
        raise RuntimeError("PDF siqilmadi")
