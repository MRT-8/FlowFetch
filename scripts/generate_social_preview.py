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

BG = "#07111E"
SURFACE = "#0D1727"
PANEL = "#101B2D"
PANEL_SOFT = "#162338"
PANEL_LINE = "#223551"
TEXT = "#F8FAFC"
MUTED = "#A5B4C6"
BLUE = "#67B7FF"
GREEN = "#34D399"
ACCENT = "#93D5FF"
PILL = "#14253C"
GLOW = "#0F2B4C"


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


FONT_KICKER = load_font(20)
FONT_TITLE = load_font(62)
FONT_SUBTITLE = load_font(24)
FONT_BODY = load_font(22)
FONT_META = load_font(18)
FONT_TERMINAL = load_font(21)


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    fill: str,
    font,
    anchor: str | None = None,
) -> None:
    draw.text(xy, text, fill=fill, font=font, anchor=anchor)


def pill(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], text: str) -> None:
    draw.rounded_rectangle(xy, radius=18, fill=PILL, outline=PANEL_LINE, width=1)
    draw_text(draw, (xy[0] + 22, xy[1] + 18), text, ACCENT, FONT_META)


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)

    draw.ellipse((840, -80, 1320, 400), fill=GLOW)
    draw.rounded_rectangle((28, 28, WIDTH - 28, HEIGHT - 28), radius=36, fill=SURFACE)
    draw.rounded_rectangle((46, 46, WIDTH - 46, HEIGHT - 46), radius=32, outline=PANEL_LINE, width=1)

    pill(draw, (92, 82, 252, 122), "LINUX CLI")
    pill(draw, (266, 82, 510, 122), "SINGLE-FILE RELEASE")

    draw_text(draw, (92, 188), "FlowFetch", TEXT, FONT_TITLE)
    draw_text(draw, (92, 246), "Download direct file URLs with progress,", ACCENT, FONT_SUBTITLE)
    draw_text(draw, (92, 282), "safe extraction, and a ready-to-run Linux binary.", MUTED, FONT_SUBTITLE)

    highlights = [
        "Validate links and probe metadata before download",
        "Protect extraction with traversal and link checks",
        "Ship as flowfetch-linux-x86_64.tar.gz on GitHub Releases",
    ]
    y = 362
    for line in highlights:
        draw.ellipse((96, y - 8, 108, y + 4), fill=GREEN)
        draw_text(draw, (128, y - 16), line, TEXT, FONT_BODY)
        y += 52

    draw.rounded_rectangle((92, 520, 426, 578), radius=18, fill=PANEL)
    draw_text(draw, (118, 555), "github.com/MRT-8/FlowFetch", BLUE, FONT_BODY)

    draw.rounded_rectangle((736, 88, 1188, 548), radius=28, fill=PANEL)
    draw.rounded_rectangle((736, 88, 1188, 146), radius=28, fill="#1B2A43")
    draw.rectangle((736, 116, 1188, 146), fill="#1B2A43")
    for x, color in ((776, "#F87171"), (808, "#FBBF24"), (840, "#34D399")):
        draw.ellipse((x - 9, 103, x + 9, 121), fill=color)
    draw_text(draw, (962, 116), "flowfetch release", MUTED, FONT_META, anchor="mm")

    draw_text(draw, (770, 196), "$", BLUE, FONT_TERMINAL)
    draw_text(draw, (798, 196), "./flowfetch demo.tar.gz", TEXT, FONT_TERMINAL)
    draw_text(draw, (770, 240), "[info]", GREEN, FONT_TERMINAL)
    draw_text(draw, (858, 240), "Inspecting metadata...", TEXT, FONT_TERMINAL)
    draw_text(draw, (770, 282), "asset", MUTED, FONT_META)
    draw_text(draw, (840, 282), "flowfetch-linux-x86_64.tar.gz", TEXT, FONT_META)
    draw_text(draw, (770, 324), "progress", MUTED, FONT_META)
    draw.rounded_rectangle((770, 354, 1118, 378), radius=12, fill="#243041")
    draw.rounded_rectangle((770, 354, 1104, 378), radius=12, fill=GREEN)
    draw_text(draw, (1132, 366), "100%", TEXT, FONT_META, anchor="lm")
    draw_text(draw, (770, 426), "[done]", GREEN, FONT_TERMINAL)
    draw_text(draw, (864, 426), "Ready in ./demo/", TEXT, FONT_TERMINAL)
    draw_text(draw, (770, 486), "privacy-safe synthetic preview", MUTED, FONT_META)

    image.save(OUT_PATH, optimize=True)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
