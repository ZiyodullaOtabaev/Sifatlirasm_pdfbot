"""
PDF generation and manipulation utilities.
"""
import io
from typing import List

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from PyPDF2 import PdfMerger


def make_text_pdf_bytes(text: str) -> bytes:
    """Convert text to PDF bytes."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    margin = 50
    y = height - margin
    line_height = 14

    def wrap_line(s: str, max_chars: int = 95):
        s = s.strip("\n")
        if not s:
            return [""]
        out = []
        while len(s) > max_chars:
            cut = s.rfind(" ", 0, max_chars)
            if cut <= 0:
                cut = max_chars
            out.append(s[:cut].rstrip())
            s = s[cut:].lstrip()
        out.append(s)
        return out

    lines: List[str] = []
    for raw in text.splitlines():
        lines.extend(wrap_line(raw))

    c.setFont("Helvetica", 12)
    for line in lines:
        if y < margin:
            c.showPage()
            c.setFont("Helvetica", 12)
            y = height - margin
        c.drawString(margin, y, line)
        y -= line_height

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


def images_to_pdf(path_list: List[str], out_pdf_path: str):
    """Convert list of image paths to a single PDF."""
    imgs = [Image.open(p).convert("RGB") for p in path_list]
    if not imgs:
        raise RuntimeError("no images")
    first, rest = imgs[0], imgs[1:]
    first.save(out_pdf_path, save_all=True, append_images=rest)


def merge_pdfs(pdf_paths: List[str], out_pdf_path: str):
    """Merge multiple PDF files into one."""
    merger = PdfMerger()
    try:
        for p in pdf_paths:
            merger.append(p)
        with open(out_pdf_path, "wb") as f:
            merger.write(f)
    finally:
        try:
            merger.close()
        except Exception:
            pass
