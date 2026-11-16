from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont


STYLES = {
    "classic": {"color": "#ffffff", "panel": (0, 0, 0), "shadow": True, "glow": False},
    "neon": {"color": "#00f0ff", "panel": (5, 10, 22), "shadow": True, "glow": True},
    "terminal": {"color": "#00ff9f", "panel": (0, 15, 10), "shadow": False, "glow": True},
    "hologram": {"color": "#d7c6ff", "panel": (35, 10, 60), "shadow": True, "glow": True},
    "minimal": {"color": "#ffffff", "panel": (0, 0, 0), "shadow": False, "glow": False},
    "paper": {"color": "#fff4d6", "panel": (35, 25, 12), "shadow": True, "glow": False},
    "sunset": {"color": "#ffd0a8", "panel": (70, 12, 28), "shadow": True, "glow": True},
    "ocean": {"color": "#b9f5ff", "panel": (5, 35, 55), "shadow": True, "glow": True},
    "matrix": {"color": "#6cff87", "panel": (0, 18, 4), "shadow": False, "glow": True},
    "glass": {"color": "#ffffff", "panel": (25, 35, 48), "shadow": True, "glow": False},
    "mono": {"color": "#eeeeee", "panel": (35, 35, 35), "shadow": True, "glow": False},
    "royal": {"color": "#f1d5ff", "panel": (45, 12, 70), "shadow": True, "glow": True},
    "ember": {"color": "#ffd2a1", "panel": (55, 18, 0), "shadow": True, "glow": True},
}


def _font(size: int, font_name: str = ""):
    candidates = []
    if font_name:
        candidates.append(Path(font_name))
    candidates += [Path(r"C:\Windows\Fonts\segoeui.ttf"), Path(r"C:\Windows\Fonts\arial.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def render_quote(source: Path, target: Path, quote: str, author: str, *, font_size: int = 42, text_color: str = "#ffffff", background_opacity: int = 45, width_percent: int = 68, hpos: int = 50, vpos: int = 78, style: str = "classic", font_name: str = "") -> Path:
    image = Image.open(source).convert("RGBA")
    width, height = image.size
    palette = STYLES.get(style, STYLES["classic"])
    color = text_color or palette["color"]
    size = max(14, min(160, int(font_size * max(1, width / 1920))))
    font = _font(size, font_name)
    author_font = _font(max(14, int(size * 0.56)), font_name)
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
    spacing = int(size * 0.25)
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing, align="center")
    quote_w, quote_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    author_text = f"— {author}" if author else ""
    author_box = draw.textbbox((0, 0), author_text, font=author_font) if author_text else (0, 0, 0, 0)
    total_h = quote_h + (author_box[3] - author_box[1] + size // 2 if author_text else 0)
    center_x = int(width * max(0, min(100, hpos)) / 100)
    top = int((height - total_h) * max(0, min(100, vpos)) / 100)
    left = center_x - quote_w // 2
    pad = max(18, size // 2)
    panel_alpha = max(0, min(100, background_opacity)) * 255 // 100
    draw.rounded_rectangle((left - pad, top - pad, left + quote_w + pad, top + total_h + pad), radius=pad // 2, fill=(*palette["panel"], panel_alpha))
    if palette["glow"]:
        glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow, "RGBA")
        glow_draw.multiline_text((center_x, top), text, font=font, fill=(*_rgb(color), 210), anchor="ma", align="center", spacing=spacing, stroke_width=max(3, size // 8), stroke_fill=(*_rgb(color), 180))
        image = Image.alpha_composite(image, glow.filter(ImageFilter.GaussianBlur(max(3, size // 10))))
        draw = ImageDraw.Draw(image, "RGBA")
    stroke = (0, 0, 0, 150) if palette["shadow"] else (0, 0, 0, 0)
    draw.multiline_text((center_x, top), text, font=font, fill=color, anchor="ma", align="center", spacing=spacing, stroke_width=1 if palette["shadow"] else 0, stroke_fill=stroke)
    if author_text:
        draw.text((center_x, top + quote_h + size // 3), author_text, font=author_font, fill=color, anchor="ma")
    target.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(target, quality=94, format="JPEG")
    return target


def _rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) != 6:
        return 255, 255, 255
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return 255, 255, 255
