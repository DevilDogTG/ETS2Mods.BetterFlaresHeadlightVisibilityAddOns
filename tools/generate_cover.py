#!/usr/bin/env python3
"""
Generates the mod's cover/thumbnail image for the ETS2 Mod Manager listing.
Convention observed from the source BetterFlares packages: 276x162 JPEG,
referenced via manifest.sii's `icon:` field.

Composited at 4x (1104x648) then downscaled for anti-aliasing.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = ROOT / "logo.png"
OUT_PATH = ROOT / "src" / "bf_headlight_addon_cover.jpg"

SCALE = 4
FINAL_SIZE = (276, 162)
CANVAS_SIZE = (FINAL_SIZE[0] * SCALE, FINAL_SIZE[1] * SCALE)

FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
FONT_REG = r"C:\Windows\Fonts\arial.ttf"

BG_TOP = (8, 10, 16)
BG_BOTTOM = (18, 22, 32)
BEAM_COLOR = (255, 214, 120)
TITLE_COLOR = (255, 255, 255)
SUBTITLE_COLOR = (255, 196, 84)


def make_background(size):
    w, h = size
    img = Image.new("RGB", size, BG_BOTTOM)
    px = img.load()
    for y in range(h):
        t = y / (h - 1)
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        for x in range(w):
            px[x, y] = (r, g, b)
    return img


def add_headlight_beams(img):
    w, h = img.size
    beam_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(beam_layer)

    for origin_x in (int(w * 0.12), int(w * 0.34)):
        origin_y = int(h * 1.05)
        spread = w * 0.22
        length = h * 1.35
        tip_x = origin_x
        tip_y = origin_y - length
        poly = [
            (origin_x - spread * 0.18, origin_y),
            (origin_x + spread * 0.18, origin_y),
            (tip_x + spread, tip_y),
            (tip_x - spread, tip_y),
        ]
        draw.polygon(poly, fill=(*BEAM_COLOR, 46))

    beam_layer = beam_layer.filter(ImageFilter.GaussianBlur(radius=w * 0.02))
    img.paste(Image.alpha_composite(img.convert("RGBA"), beam_layer).convert("RGB"), (0, 0))
    return img


def add_road(img):
    w, h = img.size
    draw = ImageDraw.Draw(img)
    road_top_y = int(h * 0.72)
    draw.polygon(
        [
            (w * 0.30, h),
            (w * 0.70, h),
            (w * 0.56, road_top_y),
            (w * 0.44, road_top_y),
        ],
        fill=(28, 30, 36),
    )
    # center dashes
    dash_w = w * 0.01
    for i in range(4):
        t0 = i / 4
        t1 = (i + 0.5) / 4
        y0 = int(h - (h - road_top_y) * t0)
        y1 = int(h - (h - road_top_y) * t1)
        x0 = w * 0.50 - dash_w * (1 - t0) * 0.5
        x1 = w * 0.50 + dash_w * (1 - t0) * 0.5
        draw.rectangle([x0, y1, x1, y0], fill=(120, 110, 90))
    return img


def paste_logo(img):
    logo = Image.open(LOGO_PATH).convert("RGBA")
    target_h = int(img.height * 0.62)
    ratio = target_h / logo.height
    target_w = int(logo.width * ratio)
    logo = logo.resize((target_w, target_h), Image.LANCZOS)

    pad = int(img.height * 0.06)
    pos = (pad, pad)

    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow_logo = Image.new("RGBA", logo.size, (0, 0, 0, 160))
    shadow_logo.putalpha(logo.split()[3])
    shadow.paste(shadow_logo, (pos[0] + 6, pos[1] + 6), shadow_logo)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=8))

    base = img.convert("RGBA")
    base = Image.alpha_composite(base, shadow)
    base.paste(logo, pos, logo)
    return base.convert("RGB")


def fit_font(draw, text, font_path, max_width, start_size, min_size=10):
    size = start_size
    while size > min_size:
        font = ImageFont.truetype(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font
        size -= 2
    return ImageFont.truetype(font_path, min_size)


def draw_with_outline(draw, pos, text, font, fill, outline=(0, 0, 0), width=2):
    x, y = pos
    for dx in range(-width, width + 1):
        for dy in range(-width, width + 1):
            if dx or dy:
                draw.text((x + dx, y + dy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


def add_text(img):
    draw = ImageDraw.Draw(img)
    w, h = img.size

    x_start = w * 0.40
    max_width = w * 0.97 - x_start

    title_lines = ["Headlight", "Visibility Add-on"]
    subtitle = "for Better Flares — DOT 7500K"

    title_size = int(h * 0.135)
    title_font = None
    for line in title_lines:
        f = fit_font(draw, line, FONT_BOLD, max_width, title_size)
        title_size = min(title_size, f.size)
        title_font = f
    title_font = ImageFont.truetype(FONT_BOLD, title_size)

    subtitle_font = fit_font(draw, subtitle, FONT_REG, max_width, int(h * 0.06))

    line_bbox = draw.textbbox((0, 0), "Ag", font=title_font)
    line_h = (line_bbox[3] - line_bbox[1]) * 1.15

    total_h = line_h * len(title_lines) + line_h * 0.9
    y = h * 0.50 - total_h / 2

    for line in title_lines:
        draw_with_outline(draw, (x_start, y), line, title_font, TITLE_COLOR, width=3)
        y += line_h

    y += line_h * 0.15
    draw_with_outline(draw, (x_start, y), subtitle, subtitle_font, SUBTITLE_COLOR, width=2)
    return img


def main():
    img = make_background(CANVAS_SIZE)
    img = add_road(img)
    img = add_headlight_beams(img)
    img = paste_logo(img)
    img = add_text(img)
    img = img.resize(FINAL_SIZE, Image.LANCZOS)
    img.save(OUT_PATH, "JPEG", quality=92)
    print(f"Wrote {OUT_PATH} ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()
