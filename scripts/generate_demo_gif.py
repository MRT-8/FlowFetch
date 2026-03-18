#!/usr/bin/env python3
"""Generate a sanitized FlowFetch terminal demo GIF.

This script uses only fictional URLs, filenames, and paths. It must not read
the current username, hostname, working directory, or shell history.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

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
CURSOR = "#E5E7EB"

COMMAND = "./flowfetch https://downloads.example.com/demo.tar.gz"
DOWNLOAD_PATH = "./demo.tar.gz"
EXTRACT_DIR = "./demo/"


@dataclass(frozen=True)
class Scene:
    typed_chars: int
    duration: int
    cursor_visible: bool = False
    show_info: bool = False
    meta_rows: int = 0
    progress: Optional[int] = None
    speed: str = ""
    elapsed: str = ""
    show_archive: bool = False
    show_extract: bool = False
    show_done: bool = False


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


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[int, int],
    text: str,
    fill: str,
    font,
    anchor: Optional[str] = None,
) -> None:
    draw.text(xy, text, fill=fill, font=font, anchor=anchor)


def draw_cursor(draw: ImageDraw.ImageDraw, x: float, y: int) -> None:
    draw.rounded_rectangle((x, y - 22, x + 14, y + 4), radius=3, fill=CURSOR)


def terminal_frame(scene: Scene) -> Image.Image:
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
    typed = COMMAND[: scene.typed_chars]
    draw_text(draw, (98, 138), typed, TEXT, FONT_BODY)
    if scene.cursor_visible:
        cursor_x = 98 + draw.textlength(typed, font=FONT_BODY) + 6
        draw_cursor(draw, cursor_x, 138)

    if scene.show_info:
        draw_text(draw, (70, 188), "[info]", GREEN, FONT_BODY)
        draw_text(draw, (164, 188), "Inspecting remote metadata...", SOFT, FONT_BODY)

    meta_rows = [
        ("Name:", "demo.tar.gz", 170),
        ("Size:", "182.4 MB", 170),
        ("Target:", DOWNLOAD_PATH, 170),
        ("Downloader:", "httpx", 220),
    ]

    if scene.meta_rows > 0:
        y = 230
        for label, value, value_x in meta_rows[: scene.meta_rows]:
            draw_text(draw, (70, y), label, MUTED, FONT_META)
            draw_text(draw, (value_x, y), value, TEXT, FONT_META)
            y += 36

    if scene.progress is not None:
        draw.rounded_rectangle((70, 382, 970, 408), radius=13, fill=BAR_BG)
        fill_width = 900 * max(0, min(scene.progress, 100)) / 100
        if fill_width > 0:
            draw.rounded_rectangle((70, 382, 70 + fill_width, 408), radius=13, fill=BAR_FILL)
        draw_text(draw, (995, 398), f"{scene.progress}%", SOFT, FONT_META)

        draw_text(draw, (70, 450), "Speed:", MUTED, FONT_META)
        draw_text(draw, (170, 450), scene.speed, TEXT, FONT_META)
        draw_text(draw, (350, 450), "Elapsed:", MUTED, FONT_META)
        draw_text(draw, (470, 450), scene.elapsed, TEXT, FONT_META)
        draw_text(draw, (610, 450), "Saved:", MUTED, FONT_META)
        draw_text(draw, (700, 450), DOWNLOAD_PATH, TEXT, FONT_META)

    if scene.show_archive:
        draw_text(draw, (70, 508), "[ok]", GREEN, FONT_BODY)
        draw_text(draw, (140, 508), "Archive detected: tar.gz", SOFT, FONT_BODY)

    if scene.show_extract:
        draw_text(draw, (70, 548), "[ok]", GREEN, FONT_BODY)
        draw_text(draw, (140, 548), "Extracting with Python safety checks...", SOFT, FONT_BODY)

    if scene.show_done:
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


def typing_sequence() -> List[Scene]:
    steps = [0, 6, 12, 19, 27, 35, 43, 50, len(COMMAND)]
    scenes: List[Scene] = []
    for index, length in enumerate(steps):
        scenes.append(
            Scene(
                typed_chars=length,
                duration=90 if index < len(steps) - 1 else 140,
                cursor_visible=index != len(steps) - 1,
            )
        )
    scenes.extend(
        [
            Scene(typed_chars=len(COMMAND), duration=120, cursor_visible=True),
            Scene(typed_chars=len(COMMAND), duration=120, cursor_visible=False),
        ]
    )
    return scenes


def metadata_sequence() -> List[Scene]:
    return [
        Scene(typed_chars=len(COMMAND), duration=260, show_info=True, meta_rows=0),
        Scene(typed_chars=len(COMMAND), duration=140, show_info=True, meta_rows=1),
        Scene(typed_chars=len(COMMAND), duration=140, show_info=True, meta_rows=2),
        Scene(typed_chars=len(COMMAND), duration=140, show_info=True, meta_rows=3),
        Scene(typed_chars=len(COMMAND), duration=180, show_info=True, meta_rows=4),
    ]


def progress_sequence() -> List[Scene]:
    checkpoints = [
        (3, "05.1 MB/s", "00:01"),
        (8, "11.8 MB/s", "00:01"),
        (14, "16.4 MB/s", "00:01"),
        (21, "19.7 MB/s", "00:02"),
        (29, "22.1 MB/s", "00:02"),
        (38, "24.9 MB/s", "00:02"),
        (48, "25.7 MB/s", "00:03"),
        (59, "26.2 MB/s", "00:03"),
        (70, "27.0 MB/s", "00:04"),
        (80, "27.8 MB/s", "00:04"),
        (89, "28.1 MB/s", "00:05"),
        (95, "28.4 MB/s", "00:05"),
        (100, "28.6 MB/s", "00:06"),
    ]
    scenes: List[Scene] = []
    for progress, speed, elapsed in checkpoints:
        scenes.append(
            Scene(
                typed_chars=len(COMMAND),
                duration=90 if progress < 100 else 220,
                show_info=True,
                meta_rows=4,
                progress=progress,
                speed=speed,
                elapsed=elapsed,
            )
        )
    return scenes


def extraction_sequence() -> List[Scene]:
    base = dict(
        typed_chars=len(COMMAND),
        show_info=True,
        meta_rows=4,
        progress=100,
        speed="28.6 MB/s",
        elapsed="00:06",
    )
    return [
        Scene(**base, duration=260, show_archive=True),
        Scene(**base, duration=420, show_archive=True, show_extract=True),
        Scene(**base, duration=1600, show_archive=True, show_extract=True, show_done=True),
    ]


def build_frames() -> Tuple[List[Image.Image], List[int]]:
    sequence = typing_sequence() + metadata_sequence() + progress_sequence() + extraction_sequence()
    frames = [terminal_frame(scene) for scene in sequence]
    durations = [scene.duration for scene in sequence]
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
