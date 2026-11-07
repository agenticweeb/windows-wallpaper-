from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def _font(size: int):
    candidates = [
        Path(r"C:\Windows\Fonts\segoeui.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def render_quote(source: Path, target: Path, quote: str, author: str, *, font_size: int = 42, text_color: str = "#ffffff", background_opacity: int = 45, width_percent: int = 68, hpos: int = 50, vpos: int = 78) -> Path:
    image = Image.open(source).convert("RGBA")
    width, height = image.size
    size = max(14, min(160, int(font_size * max(1, width / 1920))))
    font = _font(size)
    author_font = _font(max(14, int(size * 0.56)))
    max_width = max(200, int(width * max(10, min(95, width_percent)) / 100))
    draw = ImageDraw.Draw(image, "RGBA")
    words = quote.split()
    lines, line = [], ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width or not line:
            line = candidate
        else:
            lines.append(line); line = word
    if line: lines.append(line)
    lines = lines[:8]
    text = "\n".join(lines)
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=int(size * 0.25), align="center")
    quote_w, quote_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    author_text = f"— {author}" if author else ""
    author_box = draw.textbbox((0, 0), author_text, font=author_font) if author_text else (0, 0, 0, 0)
    total_h = quote_h + (author_box[3] - author_box[1] + size // 2 if author_text else 0)
    center_x = int(width * max(0, min(100, hpos)) / 100)
    top = int((height - total_h) * max(0, min(100, vpos)) / 100)
    left = center_x - quote_w // 2
    pad = max(18, size // 2)
    draw.rounded_rectangle((left - pad, top - pad, left + quote_w + pad, top + total_h + pad), radius=pad // 2, fill=(0, 0, 0, max(0, min(100, background_opacity)) * 255 // 100))
    draw.multiline_text((center_x, top), text, font=font, fill=text_color, anchor="ma", align="center", spacing=int(size * 0.25), stroke_width=1, stroke_fill=(0, 0, 0, 120))
    if author_text:
        draw.text((center_x, top + quote_h + size // 3), author_text, font=author_font, fill=text_color, anchor="ma")
    target.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(target, quality=94, format="JPEG")
    return target
