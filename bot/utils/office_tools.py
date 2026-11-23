"""
100% Free Server-Local Office <-> PDF Conversion Engine:
1. PDF -> Word (.docx) using SmartPdf2Docx (extended pdf2docx):
   - Automatic character-gap & span-gap word spacing recovery (fixes glued words in
     justified / LaTeX / Uzbek / Russian / English PDFs).
   - Automatic inline overbar (A-bar / B-bar / C-bar) Unicode recovery + != normalization.
   - Automatic Smart Hybrid Math/Formula Region rendering: keeps all normal prose
     100% editable while rendering complex stacked fractions and boxed equations
     at crisp 300 DPI with proper padding so lines and numerators never clip or break.
   - Garbage vector-line artifact filter (eliminates stray black strips / empty line boxes).
   - Smart table handling (preserves real bordered tables, avoids chopping equations
     into broken borderless tables).
   - Post-processing DOCX XML cleanup (clamps negative kerning, prevents image overflow,
     collapses stray empty paragraphs).
   - Safe PyMuPDF + python-docx fallback if a PDF is malformed.
2. Word / Excel / PowerPoint -> PDF using isolated LibreOffice Headless with
   MS metric-compatible fonts (Liberation, Carlito, Caladea, DejaVu).
All temporary files and profiles are cleaned up immediately.
"""
import gc
import io
import os
import re
import shutil
import logging
import tempfile
import threading
import subprocess
import unicodedata
from pathlib import Path
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

SUPPORTED_OFFICE_EXTS = (
    ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".odt", ".ods", ".odp", ".rtf"
)
MAX_PDF_TO_WORD_PAGES = 100

_REGISTER_LOCK = threading.Lock()
_SMART_PDF2DOCX_REGISTERED = False

# Punctuation & character sets used for spacing heuristics
_APOSTROPHES = {"'", "’", "‘", "ʼ", "ʻ", "`", "´"}
_HYPHENS = {"-", "–", "—", "\u2010", "\u2011", "\xad"}
_NO_SPACE_BEFORE = set(".,;:!?)]}»”’'%°")
_NO_SPACE_AFTER = set("([{«“‘")
_SENTENCE_OR_LIST_PUNCT = set(".,;:!?)]}")
_MATH_FONT_HINTS = ("cmmi", "cmsy", "cmex", "cmr", "cambriamath", "math", "symbol", "stix", "asana", "mt extra")
_MATH_SYMBOLS = set("∑∫∏∅∩∪⊥≈≤≥≠±∞√∂∆∇⇒⇔∈∉⊂⊃⊆⊇∀∃⋅·×÷")
_MATH_SHORT_WORDS = {"sin", "cos", "tan", "cot", "sec", "csc", "log", "lim", "max", "min", "mod", "exp", "det", "deg", "arg"}


# ============================================================================
# 1. TEXT SPACING RECOVERY & UNICODE NORMALIZATION
# ============================================================================

def _is_combining_or_zero(ch: str) -> bool:
    if not ch:
        return True
    cat = unicodedata.category(ch)
    return cat in ("Mn", "Cf")


def _span_text(span: dict) -> str:
    chars = span.get("chars")
    if chars:
        return "".join(c.get("c", "") for c in chars)
    return span.get("text", "")


def _count_prose_words(text: str) -> int:
    """Count regular natural-language words (4+ letters, excluding math operators)."""
    words = re.findall(r"[A-Za-zА-Яа-яЁёЎўҚқҒғҲҳ]{4,}", text)
    return sum(1 for w in words if w.lower() not in _MATH_SHORT_WORDS)


def _normalize_span_chars(chars: list) -> list:
    """Fix LaTeX combining solidus (\u0338 + '=' -> '≠') and drop null/broken chars."""
    out = []
    i = 0
    n = len(chars)
    while i < n:
        c = chars[i]
        ch = c.get("c", "")
        if ch in ("", "\x00", "\ufffd"):
            i += 1
            continue
        # Combine '\u0338' + '=' or '=' + '\u0338' into clean '≠' with union bbox
        if ch == "\u0338" and i + 1 < n and chars[i + 1].get("c") == "=":
            nxt = dict(chars[i + 1])
            nxt["c"] = "≠"
            cb, nb = c.get("bbox"), nxt.get("bbox")
            if cb and nb:
                nxt["bbox"] = (min(cb[0], nb[0]), min(cb[1], nb[1]), max(cb[2], nb[2]), max(cb[3], nb[3]))
            out.append(nxt)
            i += 2
            continue
        if ch == "=" and i + 1 < n and chars[i + 1].get("c") == "\u0338":
            cur = dict(c)
            cur["c"] = "≠"
            cb, nb = c.get("bbox"), chars[i + 1].get("bbox")
            if cb and nb:
                cur["bbox"] = (min(cb[0], nb[0]), min(cb[1], nb[1]), max(cb[2], nb[2]), max(cb[3], nb[3]))
            out.append(cur)
            i += 2
            continue
        out.append(c)
        i += 1
    return out


def _recover_spaces_in_text_blocks(text_blocks: list) -> list:
    """
    Restore missing word spaces caused by tight justified/LaTeX PDF kerning:
    1) Intra-span character-gap analysis (e.g. 'munosabato’rinlibo’lsa.' -> 'munosabat o’rinli bo’lsa.')
    2) Inter-span gap analysis on the same line (e.g. '1.Shartli' -> '1. Shartli', 'chunkiB' -> 'chunki B')
    Preserves Uzbek apostrophes (o‘, g‘, bo’lsa, ma’lum), decimals (0.41), and URLs.
    """
    for block in text_blocks:
        if block.get("type", 0) != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue

            # Pass 1: Intra-span space recovery
            for span in spans:
                raw_chars = span.get("chars")
                if not raw_chars:
                    continue
                chars = _normalize_span_chars(raw_chars)
                if len(chars) < 2:
                    span["chars"] = chars
                    continue

                font_size = float(span.get("size") or 10.0)
                new_chars = [chars[0]]

                for idx in range(1, len(chars)):
                    prev = new_chars[-1]
                    curr = chars[idx]
                    pc = prev.get("c", "")
                    cc = curr.get("c", "")

                    if (
                        pc
                        and cc
                        and not pc.isspace()
                        and not cc.isspace()
                        and not _is_combining_or_zero(pc)
                        and not _is_combining_or_zero(cc)
                        and cc not in _NO_SPACE_BEFORE
                        and pc not in _NO_SPACE_AFTER
                    ):
                        pb = prev.get("bbox")
                        cb = curr.get("bbox")
                        if pb and cb:
                            gap = cb[0] - pb[2]
                            # Check vertical overlap so stacked subscripts don't inject spaces
                            v_overlap = min(pb[3], cb[3]) - max(pb[1], cb[1])
                            min_h = max(1.0, min(pb[3] - pb[1], cb[3] - cb[1]))
                            if v_overlap > 0.25 * min_h:
                                # Strict threshold around apostrophes/hyphens (Uzbek o‘/g’/bo’lsa)
                                if pc in _APOSTROPHES or cc in _APOSTROPHES or pc in _HYPHENS or cc in _HYPHENS:
                                    thresh = max(2.2, 0.24 * font_size)
                                elif pc in _SENTENCE_OR_LIST_PUNCT and cc.isalpha():
                                    # Tighter threshold after sentence/list punctuation before a letter
                                    thresh = max(0.9, 0.10 * font_size)
                                else:
                                    thresh = max(1.4, 0.165 * font_size)

                                if gap > thresh:
                                    space_char = {
                                        "c": " ",
                                        "bbox": (pb[2], min(pb[1], cb[1]), cb[0], max(pb[3], cb[3])),
                                        "origin": (pb[2], prev.get("origin", (pb[2], pb[3]))[1]),
                                    }
                                    new_chars.append(space_char)

                    new_chars.append(curr)

                span["chars"] = new_chars

            # Pass 2: Inter-span space recovery on the same line
            for s_idx in range(len(spans) - 1):
                s1 = spans[s_idx]
                s2 = spans[s_idx + 1]
                c1 = s1.get("chars")
                c2 = s2.get("chars")
                if not c1 or not c2:
                    continue

                last_ch = c1[-1].get("c", "")
                first_ch = c2[0].get("c", "")
                if not last_ch or not first_ch or last_ch.isspace() or first_ch.isspace():
                    continue
                if first_ch in _NO_SPACE_BEFORE or last_ch in _NO_SPACE_AFTER:
                    continue
                if _is_combining_or_zero(first_ch):
                    continue

                b1 = s1.get("bbox")
                b2 = s2.get("bbox")
                if not b1 or not b2:
                    continue

                gap = b2[0] - b1[2]
                sz1 = float(s1.get("size") or 10.0)
                sz2 = float(s2.get("size") or 10.0)
                ref_sz = max(sz1, sz2)

                # Don't split tight sub/superscripts (e.g., A1, C^3, x_i)
                is_sub_or_sup = (sz2 < 0.85 * sz1) and (gap < 0.18 * ref_sz)
                if is_sub_or_sup:
                    continue

                if last_ch in _APOSTROPHES or first_ch in _APOSTROPHES or last_ch in _HYPHENS:
                    thresh = max(2.2, 0.24 * ref_sz)
                elif last_ch in _SENTENCE_OR_LIST_PUNCT and first_ch.isalpha():
                    thresh = max(0.8, 0.095 * ref_sz)
                else:
                    thresh = max(1.3, 0.155 * ref_sz)

                if gap > thresh:
                    pb = c1[-1].get("bbox", b1)
                    cb = c2[0].get("bbox", b2)
                    space_char = {
                        "c": " ",
                        "bbox": (b1[2], min(pb[1], cb[1]), b2[0], max(pb[3], cb[3])),
                        "origin": (b1[2], c1[-1].get("origin", (b1[2], pb[3]))[1]),
                    }
                    c1.append(space_char)
                    s1["bbox"] = (b1[0], b1[1], max(b1[2], b2[0]), b1[3])

    return text_blocks


# ============================================================================
# 2. GARBAGE VECTOR-LINE ARTIFACT FILTER
# ============================================================================

def _is_garbage_line_image(img_dict: dict) -> bool:
    """
    Detect stray vector-drawing artifacts clipped by pdf2docx:
    - Almost empty white boxes
    - Solid black thin bars/strips (e.g. converted fraction bar or overline)
    - Wide white boxes containing only a tiny thin horizontal/vertical dash '—'
    Preserves real charts, diagrams, illustrations, photos, and formula images.
    """
    try:
        from PIL import Image
        import numpy as np

        bbox = img_dict.get("bbox")
        raw_bytes = img_dict.get("image")
        if not bbox or not raw_bytes:
            return False

        bw = float(bbox[2] - bbox[0])
        bh = float(bbox[3] - bbox[1])
        if bw < 3.0 or bh < 3.0:
            return True

        im = Image.open(io.BytesIO(raw_bytes)).convert("L")
        arr = np.asarray(im)
        h_px, w_px = arr.shape
        if h_px == 0 or w_px == 0:
            return True

        dark = arr < 235
        dark_count = int(dark.sum())
        total_px = h_px * w_px
        dark_ratio = dark_count / total_px

        # 1. Nearly blank white box
        if dark_ratio < 0.0015:
            return True

        # 2. Solid black thin bar/strip (fraction bar or overbar rendered as solid black rect)
        aspect = max(bw / max(bh, 0.5), bh / max(bw, 0.5))
        if dark_ratio > 0.80 and (min(bw, bh) < 12.0 or aspect > 8.0):
            return True

        # 3. Measure actual ink bounding box inside the clipped image
        ys, xs = np.where(dark)
        ink_w_pt = ((int(xs.max()) - int(xs.min()) + 1) / w_px) * bw
        ink_h_pt = ((int(ys.max()) - int(ys.min()) + 1) / h_px) * bh

        # Stray single horizontal/vertical rule inside a padded white box
        if ink_h_pt < 4.5 or ink_w_pt < 4.5:
            return True

        return False
    except Exception:
        return False


# ============================================================================
# 3. SMART HYBRID DISPLAY-MATH / FORMULA REGION DETECTOR
# ============================================================================

def _extract_segments_and_boxes(drawings: list, page_w: float) -> Tuple[list, list, list]:
    """
    Parse PyMuPDF get_cdrawings() into:
    - h_bars: thin horizontal bars [(x0, y0, x1, y1)]
    - v_bars: thin vertical bars [(x0, y0, x1, y1)]
    - boxes: standalone rectangular frames [(x0, y0, x1, y1)]
    """
    h_bars = []
    v_bars = []
    boxes = []

    for d in drawings:
        rect = d.get("rect")
        if not rect:
            continue
        x0, y0, x1, y1 = float(rect[0]), float(rect[1]), float(rect[2]), float(rect[3])
        w = x1 - x0
        h = y1 - y0
        if w <= 0 and h <= 0:
            continue

        # Simple thin horizontal line or thin filled rectangle
        if h <= 2.8 and w >= 3.0:
            h_bars.append((x0, y0, x1, y1))
            continue
        # Simple thin vertical line or thin filled rectangle
        if w <= 2.8 and h >= 5.0:
            v_bars.append((x0, y0, x1, y1))
            continue

        # Check individual drawing items (some PDFs pack multiple segments in one path)
        items = d.get("items") or []
        is_stroked_rect = False
        if len(items) == 1 and items[0][0] == "re" and d.get("fill") is None:
            is_stroked_rect = True
        elif 4 <= len(items) <= 5 and all(it[0] == "l" for it in items) and d.get("fill") is None:
            is_stroked_rect = True

        if is_stroked_rect and 12.0 <= w <= 0.78 * page_w and 12.0 <= h <= 140.0:
            boxes.append((x0, y0, x1, y1))
            continue

        for it in items:
            op = it[0]
            if op == "l":
                p1, p2 = it[1], it[2]
                lx0, lx1 = min(p1[0], p2[0]), max(p1[0], p2[0])
                ly0, ly1 = min(p1[1], p2[1]), max(p1[1], p2[1])
                if (ly1 - ly0) <= 2.2 and (lx1 - lx0) >= 3.0:
                    h_bars.append((lx0, ly0, lx1, ly1))
                elif (lx1 - lx0) <= 2.2 and (ly1 - ly0) >= 5.0:
                    v_bars.append((lx0, ly0, lx1, ly1))
            elif op == "re":
                rr = it[1]
                rx0, ry0, rx1, ry1 = float(rr[0]), float(rr[1]), float(rr[2]), float(rr[3])
                rw, rh = rx1 - rx0, ry1 - ry0
                if rh <= 2.8 and rw >= 3.0:
                    h_bars.append((rx0, ry0, rx1, ry1))
                elif rw <= 2.8 and rh >= 5.0:
                    v_bars.append((rx0, ry0, rx1, ry1))
                elif d.get("fill") is None and 12.0 <= rw <= 0.78 * page_w and 12.0 <= rh <= 140.0:
                    boxes.append((rx0, ry0, rx1, ry1))

    # Also reconstruct closed boxes made from 4 separate H/V segments (common in LaTeX \boxed{})
    if len(h_bars) >= 2 and len(v_bars) >= 2:
        tol = 3.5
        for i in range(len(h_bars)):
            t_bar = h_bars[i]
            tw = t_bar[2] - t_bar[0]
            if not (12.0 <= tw <= 0.78 * page_w):
                continue
            for j in range(i + 1, len(h_bars)):
                b_bar = h_bars[j]
                if abs(t_bar[0] - b_bar[0]) > tol or abs(t_bar[2] - b_bar[2]) > tol:
                    continue
                top_y = min(t_bar[1], b_bar[1])
                bot_y = max(t_bar[3], b_bar[3])
                bh = bot_y - top_y
                if not (12.0 <= bh <= 140.0):
                    continue
                has_left = any(
                    abs(v[0] - t_bar[0]) <= tol and v[1] <= top_y + tol and v[3] >= bot_y - tol
                    for v in v_bars
                )
                has_right = any(
                    abs(v[0] - t_bar[2]) <= tol and v[1] <= top_y + tol and v[3] >= bot_y - tol
                    for v in v_bars
                )
                if has_left and has_right:
                    boxes.append((t_bar[0], top_y, t_bar[2], bot_y))

    return h_bars, v_bars, boxes


def _find_real_table_rects(h_bars: list, v_bars: list, page_w: float) -> list:
    """
    Identify genuine multi-row or multi-column bordered tables so we NEVER mistake
    table borders for math fraction bars or boxed equations.
    """
    table_rects = []
    if len(h_bars) < 2 or len(v_bars) < 2:
        return table_rects

    tol = 4.0
    # Group connected H and V bars that intersect each other into components
    segs = [("h", b) for b in h_bars] + [("v", b) for b in v_bars]
    n = len(segs)
    visited = [False] * n

    def _intersects(a, b):
        return (
            a[0] - tol <= b[2] and b[0] - tol <= a[2]
            and a[1] - tol <= b[3] and b[1] - tol <= a[3]
        )

    for i in range(n):
        if visited[i]:
            continue
        stack = [i]
        visited[i] = True
        comp_h = []
        comp_v = []
        while stack:
            cur = stack.pop()
            kind, box = segs[cur]
            if kind == "h":
                comp_h.append(box)
            else:
                comp_v.append(box)
            for nxt in range(n):
                if not visited[nxt] and _intersects(box, segs[nxt][1]):
                    visited[nxt] = True
                    stack.append(nxt)

        # A real bordered table has >= 3 distinct horizontal y-levels OR >= 3 distinct vertical x-levels
        if comp_h and comp_v:
            distinct_y = []
            for hb in sorted(comp_h, key=lambda r: r[1]):
                if not distinct_y or abs(hb[1] - distinct_y[-1]) > 5.0:
                    distinct_y.append(hb[1])
            distinct_x = []
            for vb in sorted(comp_v, key=lambda r: r[0]):
                if not distinct_x or abs(vb[0] - distinct_x[-1]) > 5.0:
                    distinct_x.append(vb[0])

            if len(distinct_y) >= 3 or len(distinct_x) >= 3:
                all_b = comp_h + comp_v
                tx0 = min(b[0] for b in all_b)
                ty0 = min(b[1] for b in all_b)
                tx1 = max(b[2] for b in all_b)
                ty1 = max(b[3] for b in all_b)
                if (tx1 - tx0) > 0.25 * page_w:
                    table_rects.append((tx0 - 2, ty0 - 2, tx1 + 2, ty1 + 2))

    return table_rects


def _rect_inside_any(r: tuple, rects: list, tol: float = 3.0) -> bool:
    for b in rects:
        if r[0] >= b[0] - tol and r[1] >= b[1] - tol and r[2] <= b[2] + tol and r[3] <= b[3] + tol:
            return True
    return False


def _rects_overlap(a: tuple, b: tuple, pad: float = 0.0) -> bool:
    return (
        a[0] - pad < b[2] and b[0] - pad < a[2]
        and a[1] - pad < b[3] and b[1] - pad < a[3]
    )


def _flatten_lines(text_blocks: list) -> list:
    """Return list of line descriptors with bbox, text, prose_words, and block/line refs."""
    lines_info = []
    for block in text_blocks:
        if block.get("type", 0) != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            txt = "".join(_span_text(s) for s in spans).strip()
            if not txt:
                continue
            lb = line.get("bbox")
            if not lb:
                continue
            lines_info.append({
                "bbox": tuple(lb),
                "text": txt,
                "prose_words": _count_prose_words(txt),
                "spans": spans,
                "line_ref": line,
            })
    return lines_info


def _is_prose_line(line_info: dict, page_w: float) -> bool:
    """True if a line is regular narrative prose or a short intro label rather than a display equation."""
    txt = line_info["text"]
    w = line_info["bbox"][2] - line_info["bbox"][0]
    pw = line_info["prose_words"]
    if pw >= 4:
        return True
    if pw >= 3 and w > 0.50 * page_w and not any(ch in txt for ch in "=≈∑∫"):
        return True
    # Short intro labels / headings like "Demak,", "Javob:", "Bu yerda", "1-masala.[1]", "Foizlarda:"
    if (
        pw >= 1
        and not any(ch in txt for ch in "=≈∑∫∏∅∩∪⊥≤≥≠±/·|")
        and not re.search(r"\b[A-Z]\([A-Za-z0-9]", txt)
    ):
        return True
    return False


def _detect_math_regions_and_overbars(
    page,
    text_blocks: list,
    drawings: list,
) -> Tuple[List[tuple], List[tuple]]:
    """
    Analyze page drawings + text spans to find:
    1) display_formula_rects: bounding boxes of complex display equations (stacked fractions,
       boxed answers, multi-level Bayes formulas) to render at crisp 300 DPI.
    2) handled_overbar_rects: tiny inline overbars (A-bar, B-bar, C-bar) converted into
       real Unicode combining macrons ('\\u0304') so they don't spawn black bar PNGs.
    """
    page_w = float(page.rect.width)
    page_h = float(page.rect.height)
    if not drawings or not text_blocks:
        return [], []

    h_bars, v_bars, boxes = _extract_segments_and_boxes(drawings, page_w)
    if not h_bars and not boxes:
        return [], []

    table_rects = _find_real_table_rects(h_bars, v_bars, page_w)
    lines_info = _flatten_lines(text_blocks)
    if not lines_info:
        return [], []

    # Flatten spans for tight numerator/denominator checks
    all_spans = []
    for li in lines_info:
        for sp in li["spans"]:
            sb = sp.get("bbox")
            st = _span_text(sp).strip()
            if sb and st:
                all_spans.append((tuple(sb), st, sp, li))

    # 1. Classify horizontal bars: fraction bars vs inline overbars
    fraction_seeds = []
    inline_overbars = []

    for hb in h_bars:
        if _rect_inside_any(hb, table_rects):
            continue
        bw = hb[2] - hb[0]
        if bw > 0.58 * page_w:
            continue

        # Check spans directly above and directly below this horizontal bar
        above = [
            s for s in all_spans
            if min(s[0][2], hb[2] + 4.0) - max(s[0][0], hb[0] - 4.0) > 0
            and (hb[1] - 26.0) <= s[0][3] <= (hb[1] + 4.0)
        ]
        below = [
            s for s in all_spans
            if min(s[0][2], hb[2] + 4.0) - max(s[0][0], hb[0] - 4.0) > 0
            and (hb[3] - 4.0) <= s[0][1] <= (hb[3] + 26.0)
        ]

        if bw >= 5.5 and above and below:
            # Verify neither the above nor below band is a full prose paragraph
            band_lines = [
                li for li in lines_info
                if (hb[1] - 10.0) <= ((li["bbox"][1] + li["bbox"][3]) / 2.0) <= (hb[3] + 10.0)
            ]
            band_prose_words = sum(li["prose_words"] for li in band_lines)
            if band_prose_words >= 4:
                # Inline fraction inside a normal prose sentence (e.g. "ehtimolini 1/2, kimyo...") -> leave prose editable!
                continue

            xs0 = [hb[0]] + [s[0][0] for s in above] + [s[0][0] for s in below]
            ys0 = [hb[1]] + [s[0][1] for s in above] + [s[0][1] for s in below]
            xs1 = [hb[2]] + [s[0][2] for s in above] + [s[0][2] for s in below]
            ys1 = [hb[3]] + [s[0][3] for s in above] + [s[0][3] for s in below]
            fraction_seeds.append((min(xs0), min(ys0), max(xs1), max(ys1)))
        elif 3.0 <= bw <= 16.0 and not above and below:
            # Candidate overbar (e.g. A-bar, B-bar, C-bar)
            inline_overbars.append((hb, below))

    # 2. Classify standalone boxed math answers (e.g. \boxed{P(A|B) = 12/37})
    box_seeds = []
    for bx in boxes:
        if _rect_inside_any(bx, table_rects):
            continue
        inside = [s for s in all_spans if _rects_overlap(bx, s[0], pad=2.0)]
        if not inside:
            continue
        joined = " ".join(s[1] for s in inside)
        if _count_prose_words(joined) >= 4:
            continue
        has_math = any(ch in joined for ch in "=≈%0123456789") or any(
            _rects_overlap(bx, fs, pad=2.0) for fs in fraction_seeds
        )
        if has_math:
            box_seeds.append(bx)

    # 2b. Also detect big math operators (∑, ∏, ∫, ⋃, ⋂) with stacked limits above/below on display lines
    big_op_seeds = []
    big_ops = {"∑", "∏", "∫", "⋃", "⋂"}
    for sb, st, _sp, li in all_spans:
        if any(op in st for op in big_ops) and not _is_prose_line(li, page_w):
            has_limit = any(
                min(s2[0][2], sb[2] + 8.0) - max(s2[0][0], sb[0] - 8.0) > 0
                and s2[0] != sb
                and (
                    (sb[1] - 20.0 <= s2[0][3] <= sb[1] + 4.0)
                    or (sb[3] - 4.0 <= s2[0][1] <= sb[3] + 20.0)
                )
                for s2 in all_spans
            )
            if has_limit:
                big_op_seeds.append(sb)

    seeds = fraction_seeds + box_seeds + big_op_seeds
    if not seeds:
        # Still recover inline overbars even on pages with no display fractions!
        handled_ob = _apply_inline_overbars(inline_overbars, [])
        return [], handled_ob

    # 3. Expand each seed into its complete Display Formula Region (without swallowing prose!)
    prose_lines = [li for li in lines_info if _is_prose_line(li, page_w)]
    non_prose_lines = [li for li in lines_info if not _is_prose_line(li, page_w)]

    expanded = []
    for seed in seeds:
        rx0, ry0, rx1, ry1 = seed
        # Expand iteratively to pull in all math spans/lines on the same equation band
        changed = True
        while changed:
            changed = False
            for li in non_prose_lines:
                lb = li["bbox"]
                # Vertically intersects or is tightly stacked within same display equation
                v_overlap = min(ry1, lb[3]) - max(ry0, lb[1])
                v_gap = max(lb[1] - ry1, ry0 - lb[3], 0.0)
                h_overlap = min(rx1, lb[2]) - max(rx0, lb[0])

                # Same horizontal band (e.g., "P(A|B) =", "= 0.5", "(1)" equation number)
                same_band = v_overlap > 0 or v_gap <= 2.5
                # Vertically stacked math pieces (e.g. multi-level fraction numerator/denominator/limits)
                stacked_math = (v_gap <= 9.0) and (h_overlap > -15.0)

                if same_band or stacked_math:
                    cand = (min(rx0, lb[0]), min(ry0, lb[1]), max(rx1, lb[2]), max(ry1, lb[3]))
                    # Make sure expanding does NOT swallow any prose line!
                    if not any(_rects_overlap(cand, pl["bbox"], pad=-1.5) for pl in prose_lines):
                        if cand != (rx0, ry0, rx1, ry1):
                            rx0, ry0, rx1, ry1 = cand
                            changed = True

            # Pull in any enclosing box frame or adjacent overbars/fraction bars
            for bx in box_seeds:
                if _rects_overlap((rx0, ry0, rx1, ry1), bx, pad=3.0):
                    cand = (min(rx0, bx[0]), min(ry0, bx[1]), max(rx1, bx[2]), max(ry1, bx[3]))
                    if cand != (rx0, ry0, rx1, ry1):
                        rx0, ry0, rx1, ry1 = cand
                        changed = True

            for hb in h_bars:
                if _rect_inside_any(hb, table_rects) or (hb[2] - hb[0]) > 0.58 * page_w:
                    continue
                if _rects_overlap((rx0, ry0, rx1, ry1), hb, pad=4.0):
                    cand = (min(rx0, hb[0]), min(ry0, hb[1]), max(rx1, hb[2]), max(ry1, hb[3]))
                    if not any(_rects_overlap(cand, pl["bbox"], pad=-1.5) for pl in prose_lines):
                        if cand != (rx0, ry0, rx1, ry1):
                            rx0, ry0, rx1, ry1 = cand
                            changed = True

        expanded.append((rx0, ry0, rx1, ry1))

    # 4. Merge overlapping or tightly adjacent display formula regions (without crossing prose!)
    expanded.sort(key=lambda r: (r[1], r[0]))
    merged: List[tuple] = []
    for r in expanded:
        if not merged:
            merged.append(r)
            continue
        prev = merged[-1]
        v_gap = r[1] - prev[3]
        can_merge = _rects_overlap(prev, r, pad=2.0) or (v_gap <= 8.0)
        if can_merge:
            cand = (min(prev[0], r[0]), min(prev[1], r[1]), max(prev[2], r[2]), max(prev[3], r[3]))
            if not any(_rects_overlap(cand, pl["bbox"], pad=-1.5) for pl in prose_lines):
                merged[-1] = cand
                continue
        merged.append(r)

    # 5. Apply clean safe padding around each formula region (never clipping prose lines)
    final_rects = []
    for r in merged:
        pad_x = 5.0
        pad_y = 3.5
        px0 = max(0.0, r[0] - pad_x)
        py0 = max(0.0, r[1] - pad_y)
        px1 = min(page_w, r[2] + pad_x)
        py1 = min(page_h, r[3] + pad_y)

        # Keep strictly clear of prose lines immediately above or below
        for pl in prose_lines:
            pb = pl["bbox"]
            if pb[3] <= r[1] + 1.0 and pb[3] > py0:
                py0 = max(py0, pb[3] + 0.5)
            if pb[1] >= r[3] - 1.0 and pb[1] < py1:
                py1 = min(py1, pb[1] - 0.5)

        if (px1 - px0) >= 8.0 and (py1 - py0) >= 8.0:
            final_rects.append((px0, py0, px1, py1))

    # 6. Recover inline overbars outside display formula regions
    handled_ob = _apply_inline_overbars(inline_overbars, final_rects)

    return final_rects, handled_ob


def _apply_inline_overbars(inline_overbars: list, formula_rects: list) -> list:
    """
    For tiny horizontal bars sitting directly above a single math letter (A, B, C, etc.)
    OUTSIDE display formula regions, attach Unicode combining overline ('\\u0304')
    to the letter and return the overbar rects so they can be suppressed from shapes.
    """
    handled = []
    for hb, below_spans in inline_overbars:
        if any(_rects_overlap(hb, fr, pad=2.0) for fr in formula_rects):
            continue
        bx_mid = (hb[0] + hb[2]) / 2.0
        attached = False
        for sb, st, span, _li in below_spans:
            chars = span.get("chars")
            if not chars:
                continue
            for idx, ch_dict in enumerate(chars):
                ch = ch_dict.get("c", "")
                cb = ch_dict.get("bbox")
                if not cb or not ch.isalnum():
                    continue
                if (cb[0] - 2.5) <= bx_mid <= (cb[2] + 2.5) and (hb[3] - 2.0) <= cb[1] <= (hb[3] + 7.5):
                    # Avoid duplicating combining macron if already present
                    if idx + 1 < len(chars) and chars[idx + 1].get("c") in ("\u0304", "\u0305"):
                        attached = True
                        break
                    macron = {
                        "c": "\u0304",
                        "bbox": (cb[0], hb[1], cb[2], cb[3]),
                        "origin": ch_dict.get("origin", (cb[0], cb[3])),
                    }
                    chars.insert(idx + 1, macron)
                    attached = True
                    break
            if attached:
                break
        if attached:
            handled.append(hb)
    return handled


def _render_formula_pixmap_block(page, rect: tuple, zoom: float = 4.0) -> Optional[dict]:
    """Render a display formula region at crisp 300 DPI and trim excessive outer whitespace."""
    import fitz
    import numpy as np
    from PIL import Image
    from pdf2docx.image.ImagesExtractor import ImagesExtractor

    clip = fitz.Rect(rect)
    pix = page.get_pixmap(clip=clip, matrix=fitz.Matrix(zoom, zoom), alpha=False)
    if pix.width <= 2 or pix.height <= 2:
        return None

    # Auto-trim excess blank whitespace while preserving crisp 2pt breathing margin
    try:
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        gray = np.asarray(im.convert("L"))
        dark = gray < 245
        if not dark.any():
            return None
        ys, xs = np.where(dark)
        pad_px = max(4, int(round(2.0 * zoom)))
        x0_px = max(0, int(xs.min()) - pad_px)
        y0_px = max(0, int(ys.min()) - pad_px)
        x1_px = min(pix.width, int(xs.max()) + 1 + pad_px)
        y1_px = min(pix.height, int(ys.max()) + 1 + pad_px)

        cropped = im.crop((x0_px, y0_px, x1_px, y1_px))
        buf = io.BytesIO()
        cropped.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        # Map trimmed pixel bounds back into PDF point coordinates
        new_rect = fitz.Rect(
            clip.x0 + x0_px / zoom,
            clip.y0 + y0_px / zoom,
            clip.x0 + x1_px / zoom,
            clip.y0 + y1_px / zoom,
        )
        from pdf2docx.common.share import BlockType
        return {
            "type": BlockType.IMAGE.value,
            "bbox": tuple(new_rect),
            "width": cropped.width,
            "height": cropped.height,
            "image": png_bytes,
        }
    except Exception as e:
        logger.debug(f"Formula trim fallback: {e}")
        return ImagesExtractor._to_raw_dict(pix, clip)


def _split_text_blocks_around_formulas(text_blocks: list, formula_rects: list) -> list:
    """
    Remove text lines covered by rendered display formula regions.
    If a single text block spans BOTH above and below a formula region, split it cleanly
    into separate upper/lower blocks so reading order in Word stays 100% intact.
    """
    if not formula_rects:
        return text_blocks

    result_blocks = []
    for block in text_blocks:
        if block.get("type", 0) != 0:
            result_blocks.append(block)
            continue

        lines = block.get("lines", [])
        if not lines:
            continue

        # Check if any line in this block overlaps a formula rect
        kept_groups: List[list] = [[]]
        for line in lines:
            lb = line.get("bbox")
            if not lb:
                continue
            cx = (lb[0] + lb[2]) / 2.0
            cy = (lb[1] + lb[3]) / 2.0
            in_formula = any(
                (fr[0] - 2.0) <= cx <= (fr[2] + 2.0) and (fr[1] - 2.0) <= cy <= (fr[3] + 2.0)
                for fr in formula_rects
            )
            if in_formula:
                if kept_groups[-1]:
                    kept_groups.append([])
            else:
                kept_groups[-1].append(line)

        for grp in kept_groups:
            if not grp:
                continue
            bx0 = min(l["bbox"][0] for l in grp)
            by0 = min(l["bbox"][1] for l in grp)
            bx1 = max(l["bbox"][2] for l in grp)
            by1 = max(l["bbox"][3] for l in grp)
            new_b = dict(block)
            new_b["lines"] = grp
            new_b["bbox"] = (bx0, by0, bx1, by1)
            result_blocks.append(new_b)

    return result_blocks


# ============================================================================
# 4. SMART pdf2docx SUBCLASS REGISTRATION (Thread-Safe)
# ============================================================================

def _ensure_smart_pdf2docx_registered():
    """Register SmartRawPageFitz once on pdf2docx's RawPageFactory."""
    global _SMART_PDF2DOCX_REGISTERED
    if _SMART_PDF2DOCX_REGISTERED:
        return
    with _REGISTER_LOCK:
        if _SMART_PDF2DOCX_REGISTERED:
            return

        import fitz
        from pdf2docx.page.RawPageFitz import RawPageFitz
        from pdf2docx.page.RawPageFactory import RawPageFactory
        from pdf2docx.common.constants import FACTOR_A_HALF
        from pdf2docx.common.Element import Element
        from pdf2docx.common.algorithm import get_area

        class SmartRawPageFitz(RawPageFitz):
            """Enhanced PyMuPDF RawPage with space recovery, hybrid math rendering, and artifact filtering."""

            def _preprocess_text(self, **settings):
                ocr = settings["ocr"]
                if ocr == 1:
                    raise SystemExit("OCR feature is planned but not implemented yet.")

                sort = settings.get("sort")
                raw = self.page_engine.get_text(
                    "rawdict",
                    flags=(
                        fitz.TEXT_PRESERVE_WHITESPACE
                        | fitz.TEXT_MEDIABOX_CLIP
                        | fitz.TEXT_CID_FOR_UNKNOWN_UNICODE
                    ),
                    sort=sort,
                )
                text_blocks = raw.get("blocks", [])

                try:
                    spans = self.page_engine.get_texttrace()
                except SystemError:
                    spans = []

                if spans:
                    if ocr == 2:
                        filtered_spans = [sp for sp in spans if sp["type"] != 3]
                    else:
                        filtered_spans = [sp for sp in spans if sp["type"] == 3]

                    if filtered_spans:
                        def span_area(bbox):
                            return max(1e-6, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))

                        blocks = []
                        for block in text_blocks:
                            intersected = False
                            for line in block.get("lines", []):
                                for span in line.get("spans", []):
                                    for fsp in filtered_spans:
                                        if (
                                            get_area(span["bbox"], fsp["bbox"]) / span_area(span["bbox"]) >= FACTOR_A_HALF
                                            and span["font"] == fsp["font"]
                                        ):
                                            intersected = True
                                            break
                                    if intersected:
                                        break
                                if intersected:
                                    break
                            if not intersected:
                                blocks.append(block)
                        text_blocks = blocks

                # Restore missing word spaces (justified/LaTeX PDFs) and normalize !=
                return _recover_spaces_in_text_blocks(text_blocks)

            def extract_raw_dict(self, **settings):
                raw_dict = {}
                if not self.page_engine:
                    return raw_dict

                *_, w, h = self.page_engine.rect
                raw_dict.update({"width": w, "height": h})
                self.width, self.height = w, h

                text_blocks = self._preprocess_text(**settings)

                # Hybrid Display Formula & Inline Overbar detection (upright pages only)
                formula_rects: List[tuple] = []
                handled_overbars: List[tuple] = []
                formula_img_blocks: List[dict] = []

                if self.page_engine.rotation == 0:
                    try:
                        drawings = self.page_engine.get_cdrawings()
                        formula_rects, handled_overbars = _detect_math_regions_and_overbars(
                            self.page_engine, text_blocks, drawings
                        )
                    except Exception as me:
                        logger.debug(f"Math region scan skipped on page: {me}")

                if formula_rects:
                    zoom = float(settings.get("clip_image_res_ratio", 4.0))
                    valid_rects = []
                    for fr in formula_rects:
                        img_blk = _render_formula_pixmap_block(self.page_engine, fr, zoom=zoom)
                        if img_blk:
                            formula_img_blocks.append(img_blk)
                            valid_rects.append(fr)
                    formula_rects = valid_rects
                    text_blocks = _split_text_blocks_around_formulas(text_blocks, formula_rects)

                raw_dict["blocks"] = list(text_blocks)

                image_blocks = self._preprocess_images(**settings)
                if formula_rects:
                    image_blocks = [
                        ib for ib in image_blocks
                        if not any(_rects_overlap(ib.get("bbox", (0, 0, 0, 0)), fr, pad=1.0) for fr in formula_rects)
                    ]
                raw_dict["blocks"].extend(image_blocks)

                shapes, shape_images = self._preprocess_shapes(**settings)

                # Suppress shapes/SVG images already covered by rendered formulas or recovered inline overbars
                suppress_rects = formula_rects + handled_overbars
                if suppress_rects:
                    shapes = [
                        sh for sh in shapes
                        if not any(_rects_overlap(sh.get("bbox", (0, 0, 0, 0)), sr, pad=2.0) for sr in suppress_rects)
                    ]
                    shape_images = [
                        si for si in shape_images
                        if not any(_rects_overlap(si.get("bbox", (0, 0, 0, 0)), sr, pad=2.0) for sr in suppress_rects)
                    ]

                # Filter out stray line-only/solid-black vector garbage PNGs
                shape_images = [si for si in shape_images if not _is_garbage_line_image(si)]

                raw_dict["shapes"] = shapes
                raw_dict["blocks"].extend(shape_images)
                raw_dict["blocks"].extend(formula_img_blocks)

                hyperlinks = self._preprocess_hyperlinks()
                raw_dict["shapes"].extend(hyperlinks)

                Element.set_rotation_matrix(self.page_engine.rotation_matrix)
                return raw_dict

        RawPageFactory.MAP["PYMUPDF"] = SmartRawPageFitz
        _SMART_PDF2DOCX_REGISTERED = True
        logger.info("Registered SmartRawPageFitz for enhanced PDF->Word conversion")


def _document_has_math_layout(doc) -> bool:
    """Inspect first few pages to detect whether PDF is math/formula heavy."""
    math_hits = 0
    for idx in range(min(len(doc), 5)):
        page = doc[idx]
        txt = page.get_text("text")
        if sum(1 for ch in txt if ch in _MATH_SYMBOLS) >= 3:
            math_hits += 1
        try:
            fonts = page.get_fonts()
            if any(any(h in (f[3] or "").lower() for h in _MATH_FONT_HINTS) for f in fonts):
                math_hits += 1
        except Exception:
            pass
        try:
            # Also detect equation-style short horizontal bars (e.g. MS Word equations without CM fonts)
            pw = float(page.rect.width)
            drawings = page.get_cdrawings()
            short_h = sum(
                1 for d in drawings
                if d.get("rect")
                and (d["rect"][3] - d["rect"][1]) <= 2.5
                and 6.0 <= (d["rect"][2] - d["rect"][0]) <= 0.45 * pw
            )
            if short_h >= 3:
                math_hits += 1
        except Exception:
            pass
    return math_hits >= 2


# ============================================================================
# 5. DOCX XML POST-PROCESSING CLEANER
# ============================================================================

def _postprocess_docx(docx_path: str):
    """
    Polish generated .docx XML for clean MS Word / WPS / Google Docs editing:
    - Clamp extreme negative character kerning (w:spacing) that visually glues letters.
    - Replace lingering '\u0338=' with clean '≠' and strip null/replacement chars.
    - Scale down any oversized inline image exceeding printable page width.
    - Collapse runs of 3+ consecutive empty paragraphs.
    """
    from docx import Document
    from docx.oxml.ns import qn

    doc = Document(docx_path)

    # Calculate max printable width in EMUs from first section
    max_width_emu = None
    if doc.sections:
        sec = doc.sections[0]
        if sec.page_width and sec.left_margin is not None and sec.right_margin is not None:
            usable = int(sec.page_width) - int(sec.left_margin) - int(sec.right_margin)
            if usable > 100000:
                max_width_emu = usable

    def _clean_paragraph_xml(p_elem):
        # 1. Clean runs: clamp negative spacing & normalize Unicode
        for r_elem in p_elem.findall(qn("w:r")):
            rpr = r_elem.find(qn("w:rPr"))
            if rpr is not None:
                sp = rpr.find(qn("w:spacing"))
                if sp is not None:
                    val = sp.get(qn("w:val"))
                    try:
                        if val is not None and int(val) < -4:
                            rpr.remove(sp)
                    except (ValueError, TypeError):
                        pass

            for t_elem in r_elem.findall(qn("w:t")):
                if t_elem.text:
                    cleaned = (
                        t_elem.text
                        .replace("\u0338=", "≠")
                        .replace("=\u0338", "≠")
                        .replace("\ufffd", "")
                        .replace("\x00", "")
                    )
                    if cleaned != t_elem.text:
                        t_elem.text = cleaned

        # 2. Prevent inline images from overflowing right page margin
        if max_width_emu:
            for extent in p_elem.iter(qn("wp:extent")):
                try:
                    cx = int(extent.get("cx", "0"))
                    cy = int(extent.get("cy", "0"))
                    if cx > max_width_emu and cy > 0:
                        scale = max_width_emu / cx
                        new_cx = int(max_width_emu)
                        new_cy = max(1, int(cy * scale))
                        extent.set("cx", str(new_cx))
                        extent.set("cy", str(new_cy))
                        # Also update matching a:ext inside pic:spPr if present
                        parent_inline = extent.getparent()
                        if parent_inline is not None:
                            for a_ext in parent_inline.iter(qn("a:ext")):
                                if a_ext.get("cx") == str(cx):
                                    a_ext.set("cx", str(new_cx))
                                    a_ext.set("cy", str(new_cy))
                except (ValueError, TypeError):
                    pass

    # Clean body paragraphs and collapse 3+ consecutive empty paragraphs
    body = doc.element.body
    empty_run = 0
    to_remove = []

    for child in list(body):
        if child.tag == qn("w:p"):
            _clean_paragraph_xml(child)
            has_text = any((t.text or "").strip() for t in child.iter(qn("w:t")))
            has_media = (
                child.find(".//" + qn("w:drawing")) is not None
                or child.find(".//" + qn("w:pict")) is not None
                or child.find(".//" + qn("w:br")) is not None
                or child.find(".//" + qn("w:sectPr")) is not None
            )
            if not has_text and not has_media:
                empty_run += 1
                if empty_run >= 3:
                    to_remove.append(child)
            else:
                empty_run = 0
        elif child.tag == qn("w:tbl"):
            empty_run = 0
            for p_elem in child.iter(qn("w:p")):
                _clean_paragraph_xml(p_elem)

    for el in to_remove:
        body.remove(el)

    doc.save(docx_path)


# ============================================================================
# 6. FALLBACK & PUBLIC CONVERSION FUNCTIONS
# ============================================================================

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
    Convert PDF file to editable Word (.docx) with SmartPdf2Docx:
    - Exact word spacing recovery for Uzbek/Russian/English justified & LaTeX PDFs
    - Hybrid 300-DPI formula rendering for stacked fractions & boxed equations
    - Garbage vector-line PNG filtering + DOCX XML cleanup
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
        is_math_doc = (not is_scanned) and _document_has_math_layout(doc)
    finally:
        doc.close()

    pages_limit = min(total_pages, MAX_PDF_TO_WORD_PAGES)

    try:
        _ensure_smart_pdf2docx_registered()
        from pdf2docx import Converter

        convert_kwargs = {
            "start": 0,
            "end": pages_limit,
            "delete_end_line_hyphen": True,
            "list_not_table": True,
            "parse_lattice_table": True,
            # Disable error-prone borderless stream-table guessing on math/equation PDFs
            "parse_stream_table": not is_math_doc,
            "clip_image_res_ratio": 4.0,
        }

        cv = Converter(in_pdf)
        try:
            cv.convert(out_docx, **convert_kwargs)
        finally:
            cv.close()

        if os.path.exists(out_docx) and os.path.getsize(out_docx) > 0:
            try:
                _postprocess_docx(out_docx)
            except Exception as pe:
                logger.warning(f"DOCX post-processing skipped ({pe})")
    except Exception as e:
        logger.warning(f"SmartPdf2Docx conversion failed ({e}), using PyMuPDF fallback")
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
