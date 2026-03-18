#!/usr/bin/env python3
"""Generate a GitHub social preview image for FlowFetch.

The output is a privacy-safe static PNG intended for manual upload in the
repository Settings -> Social preview section.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1280
HEIGHT = 640
OUT_PATH = Path("assets/social-preview.png")

BG = "#08111F"
PANEL = "#101B2D"
PANEL_SOFT = "#162338"
TEXT = "#F8FAFC"
MUTED = "#A5B4C6"
BLUE = "#66B3FF"
GREEN = "#32D296"
ACCENT = "#8AD4FF"


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


FONT_TITLE = load_font(54)
FONT_SUBTITLE = load_font(24)
FONT_BODY = load_font(22)
FONT_META = load_font(18)


def draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fill: str, font, anchor: str | None = None) -> None:
    draw.text(xy, text, fill=fill, font=font, anchor=anchor)


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((28, 28, WIDTH - 28, HEIGHT - 28), radius=36, fill=PANEL)
    draw.rounded_rectangle((720, 96, 1188, 520), radius=28, fill=PANEL_SOFT)
    draw.rounded_rectangle((720, 96, 1188, 150), radius=28, fill="#1D2C46")
    draw.rectangle((720, 122, 1188, 150), fill="#1D2C46")

    for x, color in ((760, "#F87171"), (792, "#FBBF24"), (824, "#34D399")):
        draw.ellipse((x - 9, 111, x + 9, 129), fill=color)

    draw_text(draw, (954, 122), "flowfetch", MUTED, FONT_META, anchor="mm")

    draw_text(draw, (92, 154), "FlowFetch", TEXT, FONT_TITLE)
    draw_text(draw, (92, 214), "Linux-first CLI downloader for direct file URLs", ACCENT, FONT_SUBTITLE)
    draw_text(draw, (92, 280), "Validate links, show progress, and safely extract", MUTED, FONT_SUBTITLE)
    draw_text(draw, (92, 316), "common archives from a single command.", MUTED, FONT_SUBTITLE)

    bullets = [
        "Direct file downloads with metadata probing",
        "Safe archive extraction with traversal checks",
        "Release-ready Linux single-file binary",
    ]
    y = 392
    for bullet in bullets:
        draw.ellipse((94, y - 9, 108, y + 5), fill=GREEN)
        draw_text(draw, (126, y - 16), bullet, TEXT, FONT_BODY)
        y += 54

    draw.rounded_rectangle((92, 520, 544, 578), radius=18, fill="#0D1727")
    draw_text(draw, (122, 555), "github.com/MRT-8/FlowFetch", BLUE, FONT_BODY)

    draw_text(draw, (756, 198), "$", BLUE, FONT_BODY)
    draw_text(draw, (786, 198), "./flowfetch demo.tar.gz", TEXT, FONT_BODY)
    draw_text(draw, (756, 244), "[info]", GREEN, FONT_BODY)
    draw_text(draw, (846, 244), "Inspecting metadata...", TEXT, FONT_BODY)
    draw_text(draw, (756, 286), "Progress", MUTED, FONT_META)
    draw.rounded_rectangle((756, 316, 1124, 340), radius=12, fill="#243041")
    draw.rounded_rectangle((756, 316, 1104, 340), radius=12, fill=GREEN)
    draw_text(draw, (1138, 328), "100%", TEXT, FONT_META, anchor="lm")
    draw_text(draw, (756, 382), "[done]", GREEN, FONT_BODY)
    draw_text(draw, (854, 382), "Ready in ./demo/", TEXT, FONT_BODY)
    draw_text(draw, (756, 450), "privacy-safe synthetic demo", MUTED, FONT_META)

    image.save(OUT_PATH, optimize=True)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
