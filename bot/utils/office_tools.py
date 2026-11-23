"""
100% Free Server-Local Office <-> PDF Conversion Engine:
1. PDF -> Word (.docx) using pdf2docx (preserving tables, columns, images, fonts, colors)
   with safe PyMuPDF+python-docx fallback on malformed PDFs.
2. Word / Excel / PowerPoint -> PDF using isolated LibreOffice Headless with
   MS metric-compatible fonts (Liberation, Carlito, Caladea, DejaVu).
All temporary files and profiles are cleaned up immediately.
"""
import gc
import io
import os
import shutil
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)

SUPPORTED_OFFICE_EXTS = (
    ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".odt", ".ods", ".odp", ".rtf"
)
MAX_PDF_TO_WORD_PAGES = 100


def _fallback_fitz_to_docx(in_pdf: str, out_docx: str, max_pages: int = MAX_PDF_TO_WORD_PAGES) -> int:
    """Fallback converter using PyMuPDF + python-docx if pdf2docx fails on a corrupted PDF structure."""
    import fitz
    from docx import Document
    from docx.shared import Inches

    doc_pdf = fitz.open(in_pdf)
    word = Document()
    pages_to_process = min(len(doc_pdf), max_pages)

    for page_idx in range(pages_to_process):
        page = doc_pdf[page_idx]
        text = page.get_text("text").strip()
        if text:
            for line in text.split("\n"):
                word.add_paragraph(line)
        else:
            # Render scanned page as image into Word
            pix = page.get_pixmap(dpi=150)
            img_stream = io.BytesIO(pix.tobytes("png"))
            word.add_picture(img_stream, width=Inches(6.2))
        if page_idx < pages_to_process - 1:
            word.add_page_break()

    doc_pdf.close()
    word.save(out_docx)
    return pages_to_process


def pdf_to_word(in_pdf: str, out_docx: str) -> Tuple[int, bool]:
    """
    Convert PDF file to editable Word (.docx) preserving layout, tables, images, and styles.
    Returns (converted_pages, is_scanned_pdf).
    """
    import fitz

    doc = fitz.open(in_pdf)
    try:
        if doc.is_encrypted:
            raise ValueError("PDF is password protected / encrypted")
        total_pages = len(doc)
        if total_pages == 0:
            raise ValueError("Corrupted or empty PDF")

        # Check first 5 pages to see whether PDF has digital text or is image-only (scanned)
        sample_chars = 0
        for idx in range(min(total_pages, 5)):
            sample_chars += len(doc[idx].get_text("text").strip())
        is_scanned = sample_chars < 20
    finally:
        doc.close()

    pages_limit = min(total_pages, MAX_PDF_TO_WORD_PAGES)

    try:
        from pdf2docx import Converter

        cv = Converter(in_pdf)
        try:
            cv.convert(out_docx, start=0, end=pages_limit)
        finally:
            cv.close()
    except Exception as e:
        logger.warning(f"pdf2docx primary conversion failed ({e}), using PyMuPDF fallback")
        _fallback_fitz_to_docx(in_pdf, out_docx, max_pages=pages_limit)
    finally:
        gc.collect()

    if not os.path.exists(out_docx) or os.path.getsize(out_docx) == 0:
        raise RuntimeError("Could not generate Word document from PDF")

    return pages_limit, is_scanned


def office_to_pdf(in_file: str, out_dir: str) -> str:
    """
    Convert Word/Excel/PowerPoint document (.docx, .doc, .xlsx, .xls, .pptx, .ppt, etc.)
    to PDF using LibreOffice headless in an isolated per-job user profile.
    Returns absolute path to generated .pdf file.
    """
    lo_bin = shutil.which("libreoffice") or shutil.which("soffice")
    if not lo_bin:
        raise RuntimeError("LibreOffice is not installed on the server")

    os.makedirs(out_dir, exist_ok=True)
    lo_profile = tempfile.mkdtemp(prefix="lo_prof_")
    profile_uri = Path(lo_profile).as_uri()

    try:
        cmd = [
            lo_bin,
            "--headless",
            "--nologo",
            "--nofirststartwizard",
            "--norestore",
            f"-env:UserInstallation={profile_uri}",
            "--convert-to",
            "pdf",
            "--outdir",
            out_dir,
            in_file,
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=90,
            check=False,
        )

        expected_pdf = os.path.join(out_dir, f"{Path(in_file).stem}.pdf")
        if os.path.exists(expected_pdf) and os.path.getsize(expected_pdf) > 0:
            return expected_pdf

        err_out = result.stderr.decode("utf-8", errors="ignore").strip()
        logger.error(f"LibreOffice conversion failed (code={result.returncode}): {err_out}")
        raise RuntimeError(f"Office conversion failed: {err_out or 'unknown error'}")
    except subprocess.TimeoutExpired:
        raise TimeoutError("Office conversion timed out")
    finally:
        shutil.rmtree(lo_profile, ignore_errors=True)
        gc.collect()
