#!/usr/bin/env python3
"""Generate a sanitized FlowFetch terminal demo GIF.

This script uses only fictional URLs, filenames, and paths. It must not read
the current username, hostname, working directory, or shell history.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1200
HEIGHT = 760
OUT_PATH = Path("assets/flowfetch-demo.gif")

BG = "#0B1220"
WINDOW = "#111827"
TITLE_BAR = "#1F2937"
PANEL = "#0F172A"
TEXT = "#F9FAFB"
MUTED = "#9CA3AF"
SOFT = "#D1D5DB"
BLUE = "#60A5FA"
GREEN = "#34D399"
BAR_BG = "#243041"
BAR_FILL = "#22C55E"

COMMAND = "./flowfetch https://downloads.example.com/demo.tar.gz"
DOWNLOAD_PATH = "./demo.tar.gz"
EXTRACT_DIR = "./demo/"


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


FONT_TITLE = load_font(22)
FONT_BODY = load_font(25)
FONT_META = load_font(20)
FONT_SMALL = load_font(18)


def draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fill: str, font, anchor: str | None = None) -> None:
    draw.text(xy, text, fill=fill, font=font, anchor=anchor)


def terminal_frame(progress: int, phase: str) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((0, 0, WIDTH - 1, HEIGHT - 1), radius=32, fill=BG)
    draw.rounded_rectangle((28, 28, WIDTH - 28, HEIGHT - 28), radius=24, fill=WINDOW)
    draw.rounded_rectangle((28, 28, WIDTH - 28, 86), radius=24, fill=TITLE_BAR)
    draw.rectangle((28, 56, WIDTH - 28, 86), fill=TITLE_BAR)

    for x, color in ((74, "#F87171"), (106, "#FBBF24"), (138, "#34D399")):
        draw.ellipse((x - 10, 47, x + 10, 67), fill=color)

    draw_text(draw, (WIDTH // 2, 61), "flowfetch demo session", SOFT, FONT_TITLE, anchor="mm")

    draw_text(draw, (70, 138), "$", BLUE, FONT_BODY)
    draw_text(draw, (98, 138), COMMAND, TEXT, FONT_BODY)

    if phase in {"inspect", "download", "extract", "done"}:
        draw_text(draw, (70, 188), "[info]", GREEN, FONT_BODY)
        draw_text(draw, (164, 188), "Inspecting remote metadata...", SOFT, FONT_BODY)

    meta_rows = [
        ("Name:", "demo.tar.gz"),
        ("Size:", "182.4 MB"),
        ("Target:", DOWNLOAD_PATH),
        ("Downloader:", "httpx"),
    ]

    if phase in {"download", "extract", "done"}:
        y = 230
        for label, value in meta_rows:
            draw_text(draw, (70, y), label, MUTED, FONT_META)
            draw_text(draw, (170 if label != "Downloader:" else 220, y), value, TEXT, FONT_META)
            y += 36

        draw.rounded_rectangle((70, 382, 970, 408), radius=13, fill=BAR_BG)
        fill_width = 900 * max(0, min(progress, 100)) / 100
        if fill_width > 0:
            draw.rounded_rectangle((70, 382, 70 + fill_width, 408), radius=13, fill=BAR_FILL)
        draw_text(draw, (995, 398), f"{progress}%", SOFT, FONT_META)

        draw_text(draw, (70, 450), "Speed:", MUTED, FONT_META)
        draw_text(draw, (170, 450), "28.6 MB/s", TEXT, FONT_META)
        draw_text(draw, (350, 450), "Elapsed:", MUTED, FONT_META)
        draw_text(draw, (470, 450), "00:06", TEXT, FONT_META)
        draw_text(draw, (610, 450), "Saved:", MUTED, FONT_META)
        draw_text(draw, (700, 450), DOWNLOAD_PATH, TEXT, FONT_META)

    if phase in {"extract", "done"}:
        draw_text(draw, (70, 508), "[ok]", GREEN, FONT_BODY)
        draw_text(draw, (140, 508), "Archive detected: tar.gz", SOFT, FONT_BODY)
        draw_text(draw, (70, 548), "[ok]", GREEN, FONT_BODY)
        draw_text(draw, (140, 548), "Extracting with Python safety checks...", SOFT, FONT_BODY)

    if phase == "done":
        draw_text(draw, (70, 588), "[done]", GREEN, FONT_BODY)
        draw_text(draw, (168, 588), f"Ready in {EXTRACT_DIR}", SOFT, FONT_BODY)

    draw.rounded_rectangle((70, 632, 1130, 694), radius=16, fill=PANEL)
    draw_text(draw, (100, 670), "Privacy:", BLUE, FONT_META)
    draw_text(
        draw,
        (194, 670),
        "this demo uses fictional URLs, filenames, and local paths only",
        SOFT,
        FONT_META,
    )

    return image


def build_frames() -> tuple[list[Image.Image], list[int]]:
    sequence = [
        (0, "inspect", 700),
        (12, "download", 120),
        (24, "download", 120),
        (39, "download", 120),
        (55, "download", 120),
        (71, "download", 120),
        (84, "download", 120),
        (93, "download", 140),
        (100, "download", 280),
        (100, "extract", 700),
        (100, "done", 1500),
    ]
    frames = [terminal_frame(progress, phase) for progress, phase, _ in sequence]
    durations = [duration for _, _, duration in sequence]
    return frames, durations


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    frames, durations = build_frames()
    frames[0].save(
        OUT_PATH,
        save_all=True,
        append_images=frames[1:],
        optimize=True,
        duration=durations,
        loop=0,
        disposal=2,
    )
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
