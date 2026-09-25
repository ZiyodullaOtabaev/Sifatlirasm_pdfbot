"""
PDF Tools Engine — 100% local, free, high-performance utilities.
Using PyMuPDF (fitz), pypdf, Pillow, and reportlab.
"""
import os
import zipfile
import io
import logging
from typing import List, Tuple, Optional

import fitz  # PyMuPDF
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color

logger = logging.getLogger(__name__)


def parse_page_ranges(range_str: str, total_pages: int) -> List[int]:
    """
    Parse page ranges like '1-3, 5, 8-10' or '1, 4' into 0-indexed page list.
    """
    cleaned = range_str.replace(" ", "").replace(";", ",")
    parts = cleaned.split(",")
    pages = []

    for part in parts:
        if not part:
            continue
        if "-" in part:
            sub = part.split("-")
            if len(sub) == 2 and sub[0].isdigit() and sub[1].isdigit():
                start = int(sub[0])
                end = int(sub[1])
                if start > end:
                    start, end = end, start
                for p in range(start, end + 1):
                    if 1 <= p <= total_pages and (p - 1) not in pages:
                        pages.append(p - 1)
            else:
                raise ValueError(f"Noto'g'ri oraliq: {part}")
        elif part.isdigit():
            p = int(part)
            if 1 <= p <= total_pages:
                if (p - 1) not in pages:
                    pages.append(p - 1)
            else:
                raise ValueError(f"Sahifa mavjud emas: {p} (Jami sahifalar: {total_pages})")
        else:
            raise ValueError(f"Noto'g'ri belgi: {part}")

    if not pages:
        raise ValueError("Hech qanday to'g'ri sahifa belgilanmadi.")
    return sorted(pages)


def pdf_to_images(input_pdf: str, output_dir: str, dpi: int = 150) -> Tuple[List[str], Optional[str]]:
    """
    Convert PDF pages to JPG images.
    Returns: (list_of_image_paths, zip_path_if_many)
    """
    if not os.path.exists(input_pdf):
        raise FileNotFoundError("PDF fayli topilmadi.")

    doc = fitz.open(input_pdf)
    image_paths = []
    base_name = os.path.splitext(os.path.basename(input_pdf))[0]

    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        img_name = f"{base_name}_page_{i + 1}.jpg"
        img_path = os.path.join(output_dir, img_name)
        pix.save(img_path)
        image_paths.append(img_path)

    doc.close()

    zip_path = None
    if len(image_paths) > 5:
        zip_name = f"{base_name}_all_images.zip"
        zip_path = os.path.join(output_dir, zip_name)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in image_paths:
                zf.write(p, arcname=os.path.basename(p))

    return image_paths, zip_path


def split_pdf(input_pdf: str, output_pdf: str, range_str: str) -> int:
    """
    Extract selected pages from input_pdf to output_pdf.
    Returns count of extracted pages.
    """
    reader = PdfReader(input_pdf)
    total = len(reader.pages)
    if total == 0:
        raise ValueError("PDF sahifalari bo'sh.")

    selected_pages = parse_page_ranges(range_str, total)
    writer = PdfWriter()

    for idx in selected_pages:
        writer.add_page(reader.pages[idx])

    with open(output_pdf, "wb") as f:
        writer.write(f)

    return len(selected_pages)


def delete_pdf_pages(input_pdf: str, output_pdf: str, delete_str: str) -> int:
    """
    Delete selected pages from input_pdf and write remainder to output_pdf.
    Returns count of remaining pages.
    """
    reader = PdfReader(input_pdf)
    total = len(reader.pages)
    if total == 0:
        raise ValueError("PDF sahifalari bo'sh.")

    to_delete = set(parse_page_ranges(delete_str, total))
    if len(to_delete) >= total:
        raise ValueError("Barcha sahifalarni o'chirib bo'lmaydi. Kamida 1 ta sahifa qolishi kerak.")

    writer = PdfWriter()
    remaining = 0
    for i in range(total):
        if i not in to_delete:
            writer.add_page(reader.pages[i])
            remaining += 1

    with open(output_pdf, "wb") as f:
        writer.write(f)

    return remaining


def watermark_pdf(input_pdf: str, output_pdf: str, watermark_text: str) -> int:
    """
    Stamp a diagonal semi-transparent text watermark across every page.
    Returns total pages watermarked.
    """
    reader = PdfReader(input_pdf)
    total = len(reader.pages)
    if total == 0:
        raise ValueError("PDF sahifalari bo'sh.")

    writer = PdfWriter()

    for page in reader.pages:
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)

        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(w, h))
        can.saveState()

        can.setFillColor(Color(0.5, 0.5, 0.5, alpha=0.08))
        font_size = max(14, min(int(w / 20), 28))
        can.setFont("Helvetica-Bold", font_size)

        can.translate(w / 2, h / 2)
        can.rotate(45)
        can.drawCentredString(0, 0, watermark_text)
        can.restoreState()
        can.save()

        packet.seek(0)
        watermark_pdf_reader = PdfReader(packet)
        watermark_page = watermark_pdf_reader.pages[0]

        page.merge_page(watermark_page)
        writer.add_page(page)

    with open(output_pdf, "wb") as f:
        writer.write(f)

    return total
