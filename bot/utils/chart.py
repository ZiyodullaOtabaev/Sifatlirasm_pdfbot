"""
Admin chart rendering utilities.
"""
import io
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont


def _get_fonts():
    """Load fonts with fallback."""
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 20)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 14)
        font_tiny = ImageFont.truetype("DejaVuSans.ttf", 12)
    except Exception:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_tiny = ImageFont.load_default()
    return font, font_small, font_tiny


def render_usage_chart_png(data: Dict[str, Dict[str, int]], title: str = "So'nggi 7 kun") -> bytes:
    """Render stacked bar chart of daily usage by action."""
    W, H = 1150, 520
    pad_l, pad_r, pad_t, pad_b = 70, 40, 70, 70

    bg = Image.new("RGB", (W, H), (250, 250, 252))
    d = ImageDraw.Draw(bg)
    font, font_small, font_tiny = _get_fonts()

    d.text((pad_l, 18), title, fill=(20, 20, 25), font=font)

    if not data:
        d.text((pad_l, 110), "Ma'lumot yo'q.", fill=(50, 50, 60), font=font_small)
        buf = io.BytesIO()
        bg.save(buf, format="PNG")
        return buf.getvalue()

    days_list = list(data.keys())
    actions = ["text_pdf", "img_pdf", "upscale", "pdf_merge", "word_pdf"]
    colors = {
        "text_pdf": (59, 130, 246),
        "img_pdf": (16, 185, 129),
        "upscale": (245, 158, 11),
        "pdf_merge": (168, 85, 247),
        "word_pdf": (239, 68, 68),
    }
    labels = {
        "text_pdf": "Matn->PDF",
        "img_pdf": "Rasm->PDF",
        "upscale": "Upscale",
        "pdf_merge": "PDF merge",
        "word_pdf": "Word->PDF",
    }

    totals = []
    max_total = 0
    for day in days_list:
        t = sum(data.get(day, {}).get(a, 0) for a in actions)
        totals.append(t)
        max_total = max(max_total, t)
    max_total = max_total or 1

    x0, y0 = pad_l, pad_t
    x1, y1 = W - pad_r, H - pad_b
    plot_w = x1 - x0
    plot_h = y1 - y0

    d.rounded_rectangle(
        [x0 - 10, y0 - 10, x1 + 10, y1 + 10],
        radius=18, fill=(255, 255, 255), outline=(230, 230, 235), width=2
    )

    # Grid lines
    grid_n = 5
    for i in range(grid_n + 1):
        y = y1 - int(plot_h * i / grid_n)
        d.line((x0, y, x1, y), fill=(235, 235, 240), width=1)
        val = int(max_total * i / grid_n)
        d.text((x0 - 48, y - 8), str(val), fill=(120, 120, 130), font=font_tiny)

    # Bars
    n = len(days_list)
    gap = 10
    bar_w = min(max(18, int((plot_w - gap * (n - 1)) / max(n, 1))), 90)
    total_bars_w = bar_w * n + gap * (n - 1)
    start_x = x0 + max(0, (plot_w - total_bars_w) // 2)

    for i, day in enumerate(days_list):
        x = start_x + i * (bar_w + gap)
        y_base = y1
        for a in actions:
            v = data.get(day, {}).get(a, 0)
            if v <= 0:
                continue
            h = int(plot_h * (v / max_total))
            y_top = y_base - h
            d.rounded_rectangle([x, y_top, x + bar_w, y_base], radius=10, fill=colors[a])
            y_base = y_top
        d.text((x + 4, y_base - 18), str(totals[i]), fill=(40, 40, 45), font=font_tiny)
        day_lbl = day[5:] if len(day) >= 10 else day
        d.text((x, y1 + 10), day_lbl, fill=(90, 90, 100), font=font_tiny)

    # Legend
    lx = x1 - 320
    ly = pad_t - 52
    d.rounded_rectangle([lx, ly, x1, ly + 48], radius=14,
                        fill=(255, 255, 255), outline=(230, 230, 235), width=2)
    cx, cy = lx + 12, ly + 14
    for a in actions:
        d.rectangle([cx, cy, cx + 14, cy + 14], fill=colors[a])
        d.text((cx + 20, cy - 2), labels[a], fill=(40, 40, 45), font=font_tiny)
        cx += 66

    buf = io.BytesIO()
    bg.save(buf, format="PNG")
    return buf.getvalue()


def render_growth_chart_png(data: List[Tuple[str, int]], title: str = "O'sish grafigi") -> bytes:
    """Render line chart for user growth."""
    W, H = 900, 400
    pad_l, pad_r, pad_t, pad_b = 70, 40, 60, 60

    bg = Image.new("RGB", (W, H), (250, 250, 252))
    d = ImageDraw.Draw(bg)
    font, font_small, font_tiny = _get_fonts()

    d.text((pad_l, 14), title, fill=(20, 20, 25), font=font)

    if not data:
        d.text((pad_l, 100), "Ma'lumot yo'q.", fill=(50, 50, 60), font=font_small)
        buf = io.BytesIO()
        bg.save(buf, format="PNG")
        return buf.getvalue()

    x0, y0 = pad_l, pad_t
    x1, y1 = W - pad_r, H - pad_b
    plot_w = x1 - x0
    plot_h = y1 - y0

    values = [v for _, v in data]
    max_val = max(values) or 1
    n = len(data)

    # Draw points and lines
    points = []
    for i, (day, val) in enumerate(data):
        x = x0 + int(plot_w * i / max(n - 1, 1))
        y = y1 - int(plot_h * val / max_val)
        points.append((x, y))

    if len(points) > 1:
        d.line(points, fill=(59, 130, 246), width=3)

    for x, y in points:
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(59, 130, 246))

    # X labels (show every few)
    step = max(1, n // 7)
    for i in range(0, n, step):
        day_lbl = data[i][0][5:] if len(data[i][0]) >= 10 else data[i][0]
        x = x0 + int(plot_w * i / max(n - 1, 1))
        d.text((x - 10, y1 + 10), day_lbl, fill=(90, 90, 100), font=font_tiny)

    buf = io.BytesIO()
    bg.save(buf, format="PNG")
    return buf.getvalue()


def render_stats_image(summary: dict, action_stats: Dict[str, int]) -> bytes:
    """Render admin statistics as image."""
    W, H = 800, 560
    bg = Image.new("RGB", (W, H), (250, 250, 252))
    d = ImageDraw.Draw(bg)
    font, font_small, font_tiny = _get_fonts()

    d.text((30, 20), "Admin Statistika", fill=(20, 20, 25), font=font)

    y = 65
    stats_lines = [
        f"Jami foydalanuvchilar: {summary.get('total_users', 0)}",
        f"Jami foydalanish: {summary.get('total_uses', 0)}",
        f"Aktiv 24h: {summary.get('active_24h', 0)}",
        f"Yangi 24h: {summary.get('new_24h', 0)}",
        f"Aktiv 7 kun: {summary.get('active_7d', 0)}",
        f"Yangi 7 kun: {summary.get('new_7d', 0)}",
        f"Aktiv 30 kun: {summary.get('active_30d', 0)}",
        f"Yangi 30 kun: {summary.get('new_30d', 0)}",
        f"Bugun ishlatilgan: {summary.get('uses_today', 0)}",
        f"Haftalik ishlatish: {summary.get('uses_week', 0)}",
    ]
    for line in stats_lines:
        d.text((40, y), line, fill=(40, 40, 50), font=font_small)
        y += 26

    y += 20
    d.text((40, y), "Funksiya statistikasi:", fill=(20, 20, 25), font=font_small)
    y += 30
    action_labels = {
        "text_pdf": "Matn -> PDF",
        "img_pdf": "Rasm -> PDF",
        "upscale": "Upscale",
        "pdf_merge": "PDF merge",
        "compress_pdf": "PDF siqish",
        "smart_scan": "Smart Scan",
    }
    for action, count in action_stats.items():
        label = action_labels.get(action, action)
        d.text((50, y), f"{label}: {count}", fill=(60, 60, 70), font=font_tiny)
        y += 22

    buf = io.BytesIO()
    bg.save(buf, format="PNG")
    return buf.getvalue()
