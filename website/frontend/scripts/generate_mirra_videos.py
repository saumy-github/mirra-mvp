#!/usr/bin/env python3
"""Render Mirra's deterministic, silent website video library.

The renderer intentionally uses only local, reproducible ingredients:

* approved Mirra still plates in ``public/mirra/plates`` and ``public/profile``;
* Pillow/OpenCV vector and interface choreography;
* OpenCV's bundled FFmpeg/libx264 encoder.

Output is H.264 High Profile, yuv420p, 24 fps MP4 plus a WebP first-frame
poster for every placement.  The MP4 ``moov`` atom is relocated before media
data so each file can begin playing before the full download completes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


FRONTEND_ROOT: Final = Path(__file__).resolve().parents[1]
PUBLIC_ROOT: Final = FRONTEND_ROOT / "public"
MIRRA_ROOT: Final = PUBLIC_ROOT / "mirra"
VIDEO_ROOT: Final = MIRRA_ROOT / "video"
POSTER_ROOT: Final = MIRRA_ROOT / "posters"
MANIFEST_PATH: Final = MIRRA_ROOT / "video-manifest.json"

FPS: Final = 24
WIDE: Final = (1280, 720)
OUTCOME: Final = (1600, 900)
CARD: Final = (1200, 1000)

INK: Final = (25, 26, 25, 255)
PAPER: Final = (246, 244, 239, 246)
WHITE: Final = (255, 255, 255, 246)
GRAPHITE: Final = (103, 104, 98, 255)
LIME: Final = (201, 255, 96, 255)
MINT: Final = (155, 226, 198, 255)
BLUE: Final = (120, 169, 255, 255)
PLUM: Final = (108, 35, 69, 255)

FONT_REGULAR: Final = "/System/Library/Fonts/SFNS.ttf"
FONT_MONO: Final = "/System/Library/Fonts/SFNSMono.ttf"
FONT_DISPLAY: Final = "/System/Library/Fonts/NewYork.ttf"

PLATES: Final = {
    "material": MIRRA_ROOT / "plates" / "material-study.png",
    "rail": MIRRA_ROOT / "plates" / "garment-rail.png",
    "parcels": MIRRA_ROOT / "plates" / "packing-table.png",
    "devices": MIRRA_ROOT / "plates" / "storefront-devices.png",
    "structured": PUBLIC_ROOT / "profile" / "signature-work.jpg",
    "fluid": PUBLIC_ROOT / "profile" / "signature-evening.jpg",
    "knit": PUBLIC_ROOT / "profile" / "signature-everyday.jpg",
    "avatar": PUBLIC_ROOT / "profile" / "avatar-profile.jpg",
}


@dataclass(frozen=True)
class VideoSpec:
    id: str
    slug: str
    family: str
    concept: str
    plate: str
    aspect: str
    duration: float
    motion: str
    overlay: str
    accent: str = "paper"
    secondary_plate: str | None = None
    focus_x: float = 0.5
    focus_y: float = 0.5

    @property
    def size(self) -> tuple[int, int]:
        if self.family == "outcome":
            return OUTCOME
        return CARD if self.aspect == "6:5" else WIDE

    @property
    def video_name(self) -> str:
        return f"{self.slug}.mp4"

    @property
    def poster_name(self) -> str:
        return f"{self.slug}.webp"


SPECS: Final = (
    VideoSpec("S01", "s01-hero-garment-rail", "hero", "A catalogue becoming try-on ready", "rail", "16:9", 6, "rail-dolly", "rail-register", "lime"),
    VideoSpec("S02", "s02-hero-structured-jacket", "hero", "Tailoring mapped to a precise fit", "structured", "16:9", 6, "portrait-left", "fit-map", "mint"),
    VideoSpec("S03", "s03-hero-satin-drape", "hero", "Satin drape read as material behavior", "material", "16:9", 6, "macro-orbit", "drape-contour", "plum", focus_x=0.7),
    VideoSpec("S04", "s04-hero-product-page-entry", "hero", "The try-on begins on the product page", "devices", "16:9", 6, "desk-push", "product-entry", "lime", focus_x=0.58),
    VideoSpec("S05", "s05-hero-fluid-garment", "hero", "A fluid evening garment resolves on-body", "fluid", "16:9", 6, "portrait-right", "garment-resolve", "blue"),
    VideoSpec("S06", "s06-hero-knit-drape", "hero", "Everyday knit translated without spectacle", "knit", "16:9", 6, "portrait-rise", "knit-grid", "paper"),
    VideoSpec("S07", "s07-hero-avatar-view", "hero", "A calm front-view avatar inspection", "avatar", "16:9", 6, "portrait-center", "avatar-view", "mint"),
    VideoSpec("S08", "s08-hero-outerwear", "hero", "Outerwear volume and layering called out", "rail", "16:9", 6, "rail-push", "outerwear-focus", "blue", focus_x=0.76),
    VideoSpec("S09", "s09-hero-size-choice", "hero", "Three sizes resolve into one recommendation", "structured", "16:9", 6, "portrait-left", "size-choice", "lime"),
    VideoSpec("S10", "s10-hero-body-representation", "hero", "Body representation stays neutral and exact", "avatar", "16:9", 6, "portrait-center", "body-coordinates", "paper"),
    VideoSpec("S11", "s11-hero-seam-to-interface", "hero", "A garment seam becomes an interface path", "material", "16:9", 6, "macro-slide", "seam-interface", "plum", secondary_plate="devices", focus_x=0.34),
    VideoSpec("S12", "s12-hero-browser-continuity", "hero", "The storefront remains continuous", "devices", "16:9", 6, "desk-pan", "browser-continuity", "blue"),
    VideoSpec("S13", "s13-hero-confident-parcel", "hero", "One confident order leaves the studio", "parcels", "16:9", 6, "overhead-breathe", "parcel-confirmed", "lime"),
    VideoSpec("S14", "s14-outcome-fit-decision", "outcome", "Fit uncertainty resolves before checkout", "devices", "16:9", 8, "desk-push", "decision-meter", "mint"),
    VideoSpec("S15", "s15-outcome-one-size", "outcome", "Backup sizes collapse into one order", "parcels", "16:9", 8, "overhead-slide", "one-size", "lime"),
    VideoSpec("S16", "s16-outcome-retained-margin", "outcome", "Return logistics rewind into retained margin", "parcels", "16:9", 8, "overhead-orbit", "margin-retained", "blue"),
    VideoSpec("S17", "s17-feature-one-button", "feature", "A single product-page control opens Mirra", "devices", "6:5", 6, "desk-push", "try-on-button", "lime", focus_x=0.58),
    VideoSpec("S18", "s18-feature-existing-catalogue", "feature", "Five existing garments register automatically", "rail", "6:5", 7, "rail-dolly", "catalogue-sync", "mint"),
    VideoSpec("S19", "s19-feature-realistic-drape", "feature", "Material texture and drape remain the proof", "material", "6:5", 9, "macro-orbit", "realism-compare", "plum", focus_x=0.68),
    VideoSpec("S20", "s20-feature-in-browser", "feature", "Try-on remains inside one browser frame", "devices", "6:5", 8, "desk-pan", "in-browser", "blue"),
    VideoSpec("S21", "s21-feature-brand-owned", "feature", "The merchant identity remains primary", "devices", "6:5", 7, "desk-push", "brand-owned", "paper"),
    VideoSpec("S22", "s22-feature-seven-day-launch", "feature", "A seven-day implementation timeline completes", "rail", "6:5", 8, "rail-push", "seven-days", "lime"),
    VideoSpec("S23", "s23-proof-structured-jacket", "proof", "Structured jacket fit proof", "structured", "16:9", 6, "portrait-left", "proof-jacket", "mint"),
    VideoSpec("S24", "s24-proof-fluid-dress", "proof", "Fluid dress fit proof", "fluid", "16:9", 6, "portrait-right", "proof-dress", "plum"),
    VideoSpec("S25", "s25-proof-knit-top", "proof", "Knit top fit proof", "knit", "16:9", 6, "portrait-rise", "proof-knit", "paper"),
    VideoSpec("S26", "s26-proof-trouser-fit", "proof", "Trouser proportion fit proof", "structured", "16:9", 6, "portrait-center", "proof-trouser", "blue"),
    VideoSpec("S27", "s27-proof-outerwear-layering", "proof", "Outerwear layering proof", "rail", "16:9", 6, "rail-dolly", "proof-outerwear", "lime", focus_x=0.75),
)

ACCENTS: Final = {
    "paper": PAPER,
    "lime": LIME,
    "mint": MINT,
    "blue": BLUE,
    "plum": PLUM,
}

_IMAGE_CACHE: dict[str, np.ndarray] = {}
_FONT_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(size: int, kind: str = "regular") -> ImageFont.FreeTypeFont:
    path = {"regular": FONT_REGULAR, "mono": FONT_MONO, "display": FONT_DISPLAY}[kind]
    key = (path, size)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = ImageFont.truetype(path, size)
    return _FONT_CACHE[key]


def load_plate(name: str) -> np.ndarray:
    if name not in _IMAGE_CACHE:
        path = PLATES[name]
        if not path.exists():
            raise FileNotFoundError(f"Missing plate '{name}': {path}")
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError(f"OpenCV could not read {path}")
        _IMAGE_CACHE[name] = image
    return _IMAGE_CACHE[name]


def ping_pong(phase: float) -> float:
    return 0.5 - 0.5 * math.cos(2 * math.pi * phase)


def smoothstep(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * (3 - 2 * value)


def pulse(phase: float, center: float, width: float = 0.22) -> float:
    distance = abs((phase - center + 0.5) % 1.0 - 0.5)
    return smoothstep(1 - min(1.0, distance / width))


def cover_crop(
    image: np.ndarray,
    size: tuple[int, int],
    phase: float,
    motion: str,
    focus_x: float,
    focus_y: float,
) -> np.ndarray:
    width, height = size
    source_h, source_w = image.shape[:2]
    breathe = ping_pong(phase)
    zoom = 1.035 + 0.045 * breathe
    if "push" in motion:
        zoom += 0.035 * breathe
    scale = max(width / source_w, height / source_h) * zoom
    resized_w = max(width, int(round(source_w * scale)))
    resized_h = max(height, int(round(source_h * scale)))
    resized = cv2.resize(image, (resized_w, resized_h), interpolation=cv2.INTER_LANCZOS4)

    travel_x = max(0, resized_w - width)
    travel_y = max(0, resized_h - height)
    cx = focus_x * travel_x
    cy = focus_y * travel_y
    wave_x = math.sin(2 * math.pi * phase)
    wave_y = math.sin(2 * math.pi * phase + math.pi / 2)
    if "slide" in motion or "dolly" in motion or "pan" in motion:
        cx += wave_x * min(travel_x * 0.36, width * 0.045)
    if "orbit" in motion:
        cx += wave_x * min(travel_x * 0.27, width * 0.04)
        cy += wave_y * min(travel_y * 0.22, height * 0.035)
    if "rise" in motion:
        cy += wave_x * min(travel_y * 0.35, height * 0.05)

    x0 = int(round(min(max(cx, 0), travel_x)))
    y0 = int(round(min(max(cy, 0), travel_y)))
    return resized[y0 : y0 + height, x0 : x0 + width].copy()


def portrait_composite(image: np.ndarray, spec: VideoSpec, phase: float) -> np.ndarray:
    width, height = spec.size
    background = cover_crop(image, spec.size, phase, "orbit", 0.5, 0.44)
    background = cv2.GaussianBlur(background, (0, 0), 34)
    wash = np.full_like(background, (224, 217, 207))
    background = cv2.addWeighted(background, 0.48, wash, 0.52, 0)

    source_h, source_w = image.shape[:2]
    scale = height * 1.025 / source_h
    foreground = cv2.resize(
        image,
        (int(round(source_w * scale)), int(round(source_h * scale))),
        interpolation=cv2.INTER_LANCZOS4,
    )
    drift = math.sin(2 * math.pi * phase)
    if "left" in spec.motion:
        center_x = width * 0.68
    elif "right" in spec.motion:
        center_x = width * 0.34
    else:
        center_x = width * 0.52
    x0 = int(round(center_x - foreground.shape[1] / 2 + drift * width * 0.012))
    y0 = int(round((height - foreground.shape[0]) / 2 + drift * height * 0.009))
    x1, y1 = x0 + foreground.shape[1], y0 + foreground.shape[0]
    sx0, sy0 = max(0, -x0), max(0, -y0)
    sx1 = foreground.shape[1] - max(0, x1 - width)
    sy1 = foreground.shape[0] - max(0, y1 - height)
    dx0, dy0 = max(0, x0), max(0, y0)
    dx1, dy1 = min(width, x1), min(height, y1)
    if dx1 > dx0 and dy1 > dy0:
        background[dy0:dy1, dx0:dx1] = foreground[sy0:sy1, sx0:sx1]
    return background


def source_frame(spec: VideoSpec, phase: float) -> np.ndarray:
    plate = load_plate(spec.plate)
    if spec.plate in {"structured", "fluid", "knit", "avatar"}:
        frame = portrait_composite(plate, spec, phase)
    else:
        frame = cover_crop(plate, spec.size, phase, spec.motion, spec.focus_x, spec.focus_y)

    if spec.secondary_plate:
        secondary = cover_crop(
            load_plate(spec.secondary_plate),
            spec.size,
            phase,
            "desk-pan",
            0.52,
            0.5,
        )
        blend = math.sin(math.pi * phase) ** 6
        frame = cv2.addWeighted(frame, 1 - blend, secondary, blend, 0)
    return frame


def rgba(frame: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")


def bgr(image: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2BGR)


def rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[float, float, float, float],
    fill: tuple[int, int, int, int],
    radius: int = 16,
    outline: tuple[int, int, int, int] | None = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(tuple(int(v) for v in box), radius=radius, fill=fill, outline=outline, width=width)


def label(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    value: str,
    size: int,
    fill: tuple[int, int, int, int] = INK,
    kind: str = "mono",
    anchor: str = "la",
) -> None:
    draw.text((int(xy[0]), int(xy[1])), value, font=font(size, kind), fill=fill, anchor=anchor)


def line(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[float, float]],
    fill: tuple[int, int, int, int],
    width: int = 2,
) -> None:
    draw.line([(int(x), int(y)) for x, y in points], fill=fill, width=width, joint="curve")


def dot(draw: ImageDraw.ImageDraw, x: float, y: float, r: float, fill: tuple[int, int, int, int]) -> None:
    draw.ellipse((int(x - r), int(y - r), int(x + r), int(y + r)), fill=fill)


def alpha_color(color: tuple[int, int, int, int], alpha: float) -> tuple[int, int, int, int]:
    return color[:3] + (int(min(255, max(0, color[3] * alpha))),)


def top_brand(draw: ImageDraw.ImageDraw, width: int, height: int, spec: VideoSpec) -> None:
    pad = int(width * 0.035)
    label(draw, (pad, pad), "M I R R A", max(13, int(width * 0.012)), WHITE)
    label(draw, (width - pad, pad), f"{spec.id} / {spec.family.upper()}", max(11, int(width * 0.009)), WHITE, anchor="ra")
    line(draw, [(pad, pad * 1.85), (width - pad, pad * 1.85)], (255, 255, 255, 86), 1)


def draw_rail_register(draw: ImageDraw.ImageDraw, w: int, h: int, p: float, accent: tuple[int, int, int, int]) -> None:
    y = h * 0.84
    left, right = w * 0.12, w * 0.88
    rect(draw, (left, y - h * 0.055, right, y + h * 0.055), (245, 242, 236, 232), int(h * 0.026))
    positions = np.linspace(left + w * 0.05, right - w * 0.05, 5)
    pointer = 0.5 - 0.5 * math.cos(2 * math.pi * p)
    active_x = positions[0] + pointer * (positions[-1] - positions[0])
    for index, x in enumerate(positions, 1):
        dot(draw, float(x), y, h * 0.009, (42, 42, 40, 80))
        label(draw, (float(x), y + h * 0.035), f"0{index}", max(9, int(w * 0.008)), GRAPHITE, anchor="ma")
    dot(draw, float(active_x), y, h * 0.014, accent)
    line(draw, [(active_x, h * 0.19), (active_x, y - h * 0.065)], alpha_color(accent, 0.72), max(2, int(w * 0.002)))
    rect(draw, (w * 0.41, h * 0.11, w * 0.59, h * 0.17), INK, int(h * 0.03))
    label(draw, (w * 0.5, h * 0.14), "CATALOGUE REGISTERED", max(10, int(w * 0.009)), WHITE, anchor="mm")


def draw_fit_map(draw: ImageDraw.ImageDraw, w: int, h: int, p: float, accent: tuple[int, int, int, int]) -> None:
    reveal = pulse(p, 0.48, 0.46)
    x = w * 0.68
    ys = [h * 0.25, h * 0.39, h * 0.54, h * 0.72]
    names = ["SHOULDER", "CHEST", "WAIST", "INSEAM"]
    for index, (y, name) in enumerate(zip(ys, names)):
        side = -1 if index % 2 == 0 else 1
        dot(draw, x + side * w * 0.075, y, h * 0.008, alpha_color(accent, reveal))
        line(draw, [(x + side * w * 0.075, y), (x + side * w * 0.16, y)], alpha_color(accent, reveal), 2)
        label(draw, (x + side * w * 0.17, y), name, max(10, int(w * 0.009)), alpha_color(WHITE, reveal), anchor="ra" if side < 0 else "la")
    rect(draw, (w * 0.055, h * 0.67, w * 0.28, h * 0.88), (24, 24, 23, 220), int(h * 0.025))
    label(draw, (w * 0.08, h * 0.72), "FIT PROFILE", max(11, int(w * 0.009)), accent)
    label(draw, (w * 0.08, h * 0.79), "Structured / regular", max(16, int(w * 0.015)), WHITE, "regular")
    label(draw, (w * 0.08, h * 0.845), "REPRESENTATION READY", max(10, int(w * 0.008)), (220, 220, 214, 230))


def draw_drape(draw: ImageDraw.ImageDraw, w: int, h: int, p: float, accent: tuple[int, int, int, int]) -> None:
    for index in range(5):
        offset = (index - 2) * h * 0.065
        points: list[tuple[float, float]] = []
        for step in range(80):
            x = w * (0.08 + 0.84 * step / 79)
            y = h * 0.5 + offset + math.sin(step / 8 + p * 2 * math.pi + index) * h * 0.025
            points.append((x, y))
        line(draw, points, alpha_color(accent, 0.33 + index * 0.08), max(1, int(w * 0.0015)))
    rect(draw, (w * 0.065, h * 0.1, w * 0.29, h * 0.19), (246, 244, 239, 226), int(h * 0.02))
    label(draw, (w * 0.09, h * 0.145), "DRAPE / MATERIAL TRUTH", max(11, int(w * 0.009)), INK, anchor="lm")


def draw_product_entry(draw: ImageDraw.ImageDraw, w: int, h: int, p: float, accent: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = w * 0.38, h * 0.2, w * 0.72, h * 0.76
    rect(draw, (x0, y0, x1, y1), (246, 244, 239, 242), int(h * 0.025))
    rect(draw, (x0 + w * 0.025, y0 + h * 0.04, x1 - w * 0.025, y0 + h * 0.09), (225, 221, 214, 255), int(h * 0.018))
    label(draw, (x0 + w * 0.04, y0 + h * 0.065), "PRODUCT / BLACK JACKET", max(9, int(w * 0.008)), GRAPHITE, anchor="lm")
    label(draw, (x0 + w * 0.035, y0 + h * 0.16), "Tailored blazer", max(19, int(w * 0.018)), INK, "regular")
    label(draw, (x0 + w * 0.035, y0 + h * 0.22), "Select a size", max(11, int(w * 0.009)), GRAPHITE)
    for index, value in enumerate(("S", "M", "L")):
        bx = x0 + w * (0.035 + index * 0.07)
        rect(draw, (bx, y0 + h * 0.25, bx + w * 0.055, y0 + h * 0.31), WHITE if index != 1 else accent, int(h * 0.012), (30, 30, 29, 45))
        label(draw, (bx + w * 0.0275, y0 + h * 0.28), value, max(11, int(w * 0.009)), INK, anchor="mm")
    glow = 0.72 + 0.28 * math.sin(2 * math.pi * p) ** 2
    rect(draw, (x0 + w * 0.035, y1 - h * 0.12, x1 - w * 0.035, y1 - h * 0.045), alpha_color(INK, glow), int(h * 0.035))
    label(draw, ((x0 + x1) / 2, y1 - h * 0.082), "TRY ON WITH MIRRA", max(12, int(w * 0.01)), WHITE, anchor="mm")


def draw_garment_resolve(draw: ImageDraw.ImageDraw, w: int, h: int, p: float, accent: tuple[int, int, int, int]) -> None:
    scan_y = h * (0.2 + 0.6 * ping_pong(p))
    line(draw, [(w * 0.16, scan_y), (w * 0.84, scan_y)], alpha_color(accent, 0.82), max(2, int(h * 0.004)))
    rect(draw, (w * 0.61, h * 0.68, w * 0.9, h * 0.87), (24, 24, 23, 220), int(h * 0.025))
    label(draw, (w * 0.64, h * 0.73), "FLUID DRESS / 02", max(11, int(w * 0.009)), accent)
    label(draw, (w * 0.64, h * 0.79), "Drape retained", max(17, int(w * 0.015)), WHITE, "regular")
    label(draw, (w * 0.64, h * 0.84), "DRAPE PRESERVED", max(10, int(w * 0.008)), (220, 220, 214, 230))


def draw_grid(draw: ImageDraw.ImageDraw, w: int, h: int, p: float, accent: tuple[int, int, int, int], title: str) -> None:
    alpha = 70
    for x in np.linspace(w * 0.08, w * 0.92, 7):
        line(draw, [(x, h * 0.12), (x, h * 0.88)], (255, 255, 255, alpha), 1)
    for y in np.linspace(h * 0.12, h * 0.88, 5):
        line(draw, [(w * 0.08, y), (w * 0.92, y)], (255, 255, 255, alpha), 1)
    active_x = w * (0.08 + 0.84 * ping_pong(p))
    line(draw, [(active_x, h * 0.12), (active_x, h * 0.88)], accent, 2)
    rect(draw, (w * 0.065, h * 0.79, w * 0.33, h * 0.87), (24, 24, 23, 220), int(h * 0.025))
    label(draw, (w * 0.09, h * 0.83), title, max(10, int(w * 0.009)), WHITE, anchor="lm")


def draw_avatar_view(draw: ImageDraw.ImageDraw, w: int, h: int, p: float, accent: tuple[int, int, int, int]) -> None:
    rect(draw, (w * 0.055, h * 0.22, w * 0.16, h * 0.76), (248, 247, 243, 230), int(h * 0.045))
    labels = ("PROFILE", "MEASURE", "GARMENT", "REVIEW")
    active = int(round(ping_pong(p) * 3))
    for index, value in enumerate(labels):
        y = h * (0.29 + index * 0.14)
        if index == active:
            dot(draw, w * 0.107, y - h * 0.025, h * 0.018, accent)
        else:
            draw.ellipse((w * 0.095, y - h * 0.037, w * 0.119, y - h * 0.013), outline=(32, 32, 31, 110), width=2)
        label(draw, (w * 0.107, y + h * 0.025), value, max(9, int(w * 0.008)), INK if index == active else GRAPHITE, anchor="ma")
    rect(draw, (w * 0.75, h * 0.11, w * 0.92, h * 0.18), (246, 244, 239, 230), int(h * 0.03))
    label(draw, (w * 0.835, h * 0.145), "BODY PROFILE / READY", max(10, int(w * 0.008)), INK, anchor="mm")


def draw_outerwear(draw: ImageDraw.ImageDraw, w: int, h: int, p: float, accent: tuple[int, int, int, int]) -> None:
    box = (w * 0.68, h * 0.16, w * 0.9, h * 0.78)
    draw.rounded_rectangle(tuple(int(x) for x in box), radius=int(h * 0.025), outline=accent, width=max(2, int(w * 0.002)))
    y = h * (0.25 + 0.44 * ping_pong(p))
    line(draw, [(w * 0.68, y), (w * 0.9, y)], accent, 2)
    rect(draw, (w * 0.055, h * 0.73, w * 0.31, h * 0.86), (24, 24, 23, 220), int(h * 0.025))
    label(draw, (w * 0.08, h * 0.775), "OUTERWEAR / LAYER 02", max(10, int(w * 0.008)), accent)
    label(draw, (w * 0.08, h * 0.825), "Volume preserved", max(16, int(w * 0.014)), WHITE, "regular")


def draw_size_choice(draw: ImageDraw.ImageDraw, w: int, h: int, p: float, accent: tuple[int, int, int, int]) -> None:
    x0, y0 = w * 0.06, h * 0.62
    label(draw, (x0, y0 - h * 0.06), "YOUR RECOMMENDED SIZE", max(10, int(w * 0.009)), WHITE)
    progress = ping_pong(p)
    for index, value in enumerate(("S", "M", "L")):
        x = x0 + index * w * 0.09
        selected = index == 1
        fill = accent if selected else (245, 243, 238, int(185 - progress * 75))
        rect(draw, (x, y0, x + w * 0.072, y0 + h * 0.095), fill, int(h * 0.02))
        label(draw, (x + w * 0.036, y0 + h * 0.0475), value, max(15, int(w * 0.013)), INK, anchor="mm")
    rect(draw, (x0, y0 + h * 0.13, x0 + w * 0.25, y0 + h * 0.195), (24, 24, 23, 220), int(h * 0.03))
    label(draw, (x0 + w * 0.125, y0 + h * 0.162), "REGULAR FIT SELECTED", max(10, int(w * 0.009)), WHITE, anchor="mm")


def draw_coordinates(draw: ImageDraw.ImageDraw, w: int, h: int, p: float, accent: tuple[int, int, int, int]) -> None:
    center_x = w * 0.52
    for index, y in enumerate((0.23, 0.36, 0.48, 0.62, 0.75)):
        radius = w * (0.045 + 0.012 * math.sin(2 * math.pi * p + index))
        draw.arc((center_x - radius, h * y - radius * 0.55, center_x + radius, h * y + radius * 0.55), 0, 360, fill=alpha_color(accent, 0.7), width=2)
    label(draw, (w * 0.06, h * 0.78), "BODY REPRESENTATION", max(11, int(w * 0.009)), WHITE)
    label(draw, (w * 0.06, h * 0.83), "01.000 / NEUTRAL BASE", max(17, int(w * 0.015)), WHITE, "regular")


def draw_seam_interface(draw: ImageDraw.ImageDraw, w: int, h: int, p: float, accent: tuple[int, int, int, int]) -> None:
    points = []
    for index in range(90):
        x = w * (0.08 + 0.84 * index / 89)
        y = h * (0.5 + 0.08 * math.sin(index / 10 + p * 2 * math.pi))
        points.append((x, y))
    line(draw, points, accent, max(2, int(w * 0.002)))
    cursor = int(ping_pong(p) * (len(points) - 1))
    dot(draw, points[cursor][0], points[cursor][1], h * 0.012, WHITE)
    rect(draw, (w * 0.69, h * 0.65, w * 0.92, h * 0.84), (246, 244, 239, 230), int(h * 0.025))
    label(draw, (w * 0.72, h * 0.705), "SEAM → INTERFACE", max(10, int(w * 0.008)), GRAPHITE)
    label(draw, (w * 0.72, h * 0.775), "One continuous fit", max(16, int(w * 0.014)), INK, "regular")


def draw_browser(draw: ImageDraw.ImageDraw, w: int, h: int, p: float, accent: tuple[int, int, int, int], owned: bool = False) -> None:
    x0, y0, x1, y1 = w * 0.31, h * 0.17, w * 0.75, h * 0.77
    rect(draw, (x0, y0, x1, y1), (247, 245, 240, 238), int(h * 0.026))
    rect(draw, (x0, y0, x1, y0 + h * 0.065), (28, 29, 28, 245), int(h * 0.026))
    for index in range(3):
        dot(draw, x0 + w * (0.025 + index * 0.018), y0 + h * 0.032, h * 0.006, (235, 232, 225, 140))
    label(draw, (x0 + w * 0.095, y0 + h * 0.032), "brand-store.com / products / jacket", max(9, int(w * 0.0075)), (235, 232, 225, 220), anchor="lm")
    label(draw, (x0 + w * 0.035, y0 + h * 0.14), "YOUR BRAND" if owned else "PRODUCT PAGE", max(10, int(w * 0.008)), GRAPHITE)
    label(draw, (x0 + w * 0.035, y0 + h * 0.21), "Tailored jacket", max(18, int(w * 0.016)), INK, "regular")
    y = y0 + h * (0.34 + 0.09 * math.sin(2 * math.pi * p))
    rect(draw, (x0 + w * 0.035, y, x1 - w * 0.035, y + h * 0.085), accent if not owned else INK, int(h * 0.04))
    label(draw, ((x0 + x1) / 2, y + h * 0.0425), "TRY ON WITH MIRRA", max(11, int(w * 0.009)), INK if not owned else WHITE, anchor="mm")
    if owned:
        label(draw, ((x0 + x1) / 2, y1 - h * 0.055), "POWERED QUIETLY / OWNED COMPLETELY", max(9, int(w * 0.0075)), GRAPHITE, anchor="mm")


def draw_parcel(draw: ImageDraw.ImageDraw, w: int, h: int, p: float, accent: tuple[int, int, int, int], mode: str) -> None:
    if mode == "one-size":
        label(draw, (w * 0.15, h * 0.23), "M", max(28, int(w * 0.03)), WHITE, "display", anchor="mm")
        label(draw, (w * 0.83, h * 0.23), "L", max(28, int(w * 0.03)), WHITE, "display", anchor="mm")
        alpha = 1 - ping_pong(p) * 0.78
        line(draw, [(w * 0.18, h * 0.29), (w * 0.44, h * 0.5)], alpha_color(WHITE, alpha), 2)
        line(draw, [(w * 0.82, h * 0.29), (w * 0.56, h * 0.5)], alpha_color(WHITE, alpha), 2)
        rect(draw, (w * 0.4, h * 0.43, w * 0.6, h * 0.57), accent, int(h * 0.05))
        label(draw, (w * 0.5, h * 0.5), "ONE INTENTIONAL SIZE", max(10, int(w * 0.008)), INK, anchor="mm")
    elif mode == "margin-retained":
        x0, y0 = w * 0.1, h * 0.75
        line(draw, [(x0, y0), (w * 0.9, y0)], (255, 255, 255, 120), 2)
        points = []
        for index in range(50):
            x = x0 + (w * 0.8) * index / 49
            y = y0 - h * (0.05 + 0.22 * index / 49 + 0.025 * math.sin(index / 5 + p * 2 * math.pi))
            points.append((x, y))
        line(draw, points, accent, max(3, int(w * 0.003)))
        dot(draw, points[-1][0], points[-1][1], h * 0.013, accent)
        rect(draw, (w * 0.63, h * 0.18, w * 0.9, h * 0.31), (24, 24, 23, 220), int(h * 0.03))
        label(draw, (w * 0.765, h * 0.225), "RETURN AVOIDED", max(10, int(w * 0.008)), accent, anchor="mm")
        label(draw, (w * 0.765, h * 0.275), "MARGIN RETAINED", max(17, int(w * 0.015)), WHITE, "regular", anchor="mm")
    else:
        rect(draw, (w * 0.36, h * 0.15, w * 0.64, h * 0.27), accent, int(h * 0.05))
        label(draw, (w * 0.5, h * 0.21), "ONE ORDER / CONFIRMED", max(11, int(w * 0.009)), INK, anchor="mm")
        progress = ping_pong(p)
        x = w * (0.23 + 0.54 * progress)
        line(draw, [(w * 0.23, h * 0.84), (w * 0.77, h * 0.84)], (255, 255, 255, 120), 2)
        dot(draw, x, h * 0.84, h * 0.014, accent)


def draw_catalogue(draw: ImageDraw.ImageDraw, w: int, h: int, p: float, accent: tuple[int, int, int, int]) -> None:
    left, top = w * 0.075, h * 0.68
    active = int(round(ping_pong(p) * 4))
    for index in range(5):
        x = left + index * w * 0.17
        selected = index == active
        rect(draw, (x, top, x + w * 0.14, top + h * 0.17), accent if selected else (246, 244, 239, 220), int(h * 0.018))
        label(draw, (x + w * 0.02, top + h * 0.05), f"SKU 0{index + 1}", max(9, int(w * 0.008)), INK)
        label(draw, (x + w * 0.02, top + h * 0.11), "READY" if selected else "SYNCED", max(11, int(w * 0.009)), INK, "regular")


def draw_realism(draw: ImageDraw.ImageDraw, w: int, h: int, p: float, accent: tuple[int, int, int, int]) -> None:
    split = w * (0.28 + 0.44 * ping_pong(p))
    line(draw, [(split, h * 0.13), (split, h * 0.87)], WHITE, max(2, int(w * 0.002)))
    rect(draw, (w * 0.07, h * 0.72, w * 0.31, h * 0.84), (24, 24, 23, 220), int(h * 0.025))
    label(draw, (w * 0.19, h * 0.765), "GARMENT IMAGE", max(9, int(w * 0.008)), accent, anchor="mm")
    label(draw, (w * 0.19, h * 0.81), "MATERIAL TRUTH", max(14, int(w * 0.013)), WHITE, "regular", anchor="mm")


def draw_timeline(draw: ImageDraw.ImageDraw, w: int, h: int, p: float, accent: tuple[int, int, int, int]) -> None:
    left, right, y = w * 0.09, w * 0.91, h * 0.79
    line(draw, [(left, y), (right, y)], (255, 255, 255, 120), 2)
    progress = ping_pong(p)
    for day in range(7):
        x = left + (right - left) * day / 6
        reached = day / 6 <= progress + 0.02
        dot(draw, x, y, h * (0.014 if reached else 0.009), accent if reached else (245, 243, 238, 170))
        label(draw, (x, y + h * 0.05), f"D{day + 1}", max(9, int(w * 0.008)), WHITE, anchor="ma")
    rect(draw, (w * 0.34, h * 0.13, w * 0.66, h * 0.25), (24, 24, 23, 220), int(h * 0.04))
    label(draw, (w * 0.5, h * 0.19), "STOREFRONT LIVE / DAY 07", max(11, int(w * 0.009)), WHITE, anchor="mm")


def draw_proof(draw: ImageDraw.ImageDraw, w: int, h: int, p: float, accent: tuple[int, int, int, int], title: str) -> None:
    x0 = w * 0.06
    rect(draw, (x0, h * 0.66, x0 + w * 0.27, h * 0.86), (24, 24, 23, 224), int(h * 0.025))
    label(draw, (x0 + w * 0.025, h * 0.71), "MIRRA FIT PROOF", max(10, int(w * 0.008)), accent)
    label(draw, (x0 + w * 0.025, h * 0.77), title, max(17, int(w * 0.015)), WHITE, "regular")
    label(draw, (x0 + w * 0.025, h * 0.825), "FORM / PROPORTION / DRAPE", max(9, int(w * 0.008)), (220, 220, 214, 230))
    x = w * (0.44 + 0.42 * ping_pong(p))
    line(draw, [(x, h * 0.18), (x, h * 0.82)], alpha_color(accent, 0.72), 2)


def overlay_frame(frame: np.ndarray, spec: VideoSpec, phase: float) -> np.ndarray:
    canvas = rgba(frame)
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    w, h = spec.size
    accent = ACCENTS[spec.accent]
    top_brand(draw, w, h, spec)

    overlay = spec.overlay
    if overlay in {"rail-register", "catalogue-sync"}:
        draw_rail_register(draw, w, h, phase, accent) if overlay == "rail-register" else draw_catalogue(draw, w, h, phase, accent)
    elif overlay in {"fit-map", "proof-jacket"}:
        draw_fit_map(draw, w, h, phase, accent) if overlay == "fit-map" else draw_proof(draw, w, h, phase, accent, "STRUCTURED JACKET")
    elif overlay == "drape-contour":
        draw_drape(draw, w, h, phase, accent)
    elif overlay in {"product-entry", "try-on-button"}:
        draw_product_entry(draw, w, h, phase, accent)
    elif overlay == "garment-resolve":
        draw_garment_resolve(draw, w, h, phase, accent)
    elif overlay == "knit-grid":
        draw_grid(draw, w, h, phase, accent, "KNIT / REGULAR DRAPE")
    elif overlay == "avatar-view":
        draw_avatar_view(draw, w, h, phase, accent)
    elif overlay in {"outerwear-focus", "proof-outerwear"}:
        draw_outerwear(draw, w, h, phase, accent) if overlay == "outerwear-focus" else draw_proof(draw, w, h, phase, accent, "OUTERWEAR LAYERING")
    elif overlay == "size-choice":
        draw_size_choice(draw, w, h, phase, accent)
    elif overlay == "body-coordinates":
        draw_coordinates(draw, w, h, phase, accent)
    elif overlay == "seam-interface":
        draw_seam_interface(draw, w, h, phase, accent)
    elif overlay in {"browser-continuity", "in-browser"}:
        draw_browser(draw, w, h, phase, accent)
    elif overlay == "brand-owned":
        draw_browser(draw, w, h, phase, accent, owned=True)
    elif overlay in {"parcel-confirmed", "one-size", "margin-retained"}:
        draw_parcel(draw, w, h, phase, accent, overlay)
    elif overlay == "decision-meter":
        draw_browser(draw, w, h, phase, accent)
        rect(draw, (w * 0.08, h * 0.73, w * 0.33, h * 0.86), (24, 24, 23, 224), int(h * 0.03))
        label(draw, (w * 0.105, h * 0.775), "FIT DECISION", max(10, int(w * 0.008)), accent)
        label(draw, (w * 0.105, h * 0.83), "FIT VIEW READY", max(15, int(w * 0.013)), WHITE, "regular")
    elif overlay == "realism-compare":
        draw_realism(draw, w, h, phase, accent)
    elif overlay == "seven-days":
        draw_timeline(draw, w, h, phase, accent)
    elif overlay == "proof-dress":
        draw_proof(draw, w, h, phase, accent, "FLUID DRESS")
    elif overlay == "proof-knit":
        draw_proof(draw, w, h, phase, accent, "KNIT TOP")
    elif overlay == "proof-trouser":
        draw_proof(draw, w, h, phase, accent, "TROUSER PROPORTION")
    else:
        raise ValueError(f"Unknown overlay: {overlay}")

    return bgr(Image.alpha_composite(canvas, layer))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atom_size(data: bytearray, start: int) -> tuple[int, int]:
    size = struct.unpack_from(">I", data, start)[0]
    if size == 1:
        return struct.unpack_from(">Q", data, start + 8)[0], 16
    if size == 0:
        return len(data) - start, 8
    return size, 8


def patch_chunk_offsets(moov: bytearray, delta: int) -> None:
    for marker, width in ((b"stco", 4), (b"co64", 8)):
        cursor = 0
        while True:
            marker_at = moov.find(marker, cursor)
            if marker_at < 0:
                break
            atom_start = marker_at - 4
            if atom_start < 0:
                break
            size = struct.unpack_from(">I", moov, atom_start)[0]
            if size >= 16 and atom_start + size <= len(moov):
                count = struct.unpack_from(">I", moov, marker_at + 8)[0]
                first = marker_at + 12
                if first + count * width <= atom_start + size:
                    fmt = ">I" if width == 4 else ">Q"
                    for index in range(count):
                        offset_at = first + index * width
                        value = struct.unpack_from(fmt, moov, offset_at)[0]
                        struct.pack_into(fmt, moov, offset_at, value + delta)
            cursor = marker_at + 4


def make_faststart(path: Path) -> None:
    data = bytearray(path.read_bytes())
    atoms: list[tuple[bytes, int, int]] = []
    cursor = 0
    while cursor + 8 <= len(data):
        size, _ = atom_size(data, cursor)
        if size < 8 or cursor + size > len(data):
            raise RuntimeError(f"Invalid MP4 atom at {cursor} in {path}")
        atoms.append((bytes(data[cursor + 4 : cursor + 8]), cursor, size))
        cursor += size
    moov_entry = next((entry for entry in atoms if entry[0] == b"moov"), None)
    mdat_entry = next((entry for entry in atoms if entry[0] == b"mdat"), None)
    if not moov_entry or not mdat_entry or moov_entry[1] < mdat_entry[1]:
        return
    _, moov_start, moov_size = moov_entry
    moov = bytearray(data[moov_start : moov_start + moov_size])
    patch_chunk_offsets(moov, moov_size)
    ftyp_entry = next((entry for entry in atoms if entry[0] == b"ftyp"), None)
    insertion = (ftyp_entry[1] + ftyp_entry[2]) if ftyp_entry else 0
    without_moov = data[:moov_start] + data[moov_start + moov_size :]
    optimized = without_moov[:insertion] + moov + without_moov[insertion:]
    temporary = path.with_suffix(".faststart.mp4")
    temporary.write_bytes(optimized)
    os.replace(temporary, path)


def render(spec: VideoSpec) -> dict[str, object]:
    VIDEO_ROOT.mkdir(parents=True, exist_ok=True)
    POSTER_ROOT.mkdir(parents=True, exist_ok=True)
    width, height = spec.size
    frames = int(round(spec.duration * FPS))
    video_path = VIDEO_ROOT / spec.video_name
    poster_path = POSTER_ROOT / spec.poster_name
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"avc1"),
        FPS,
        (width, height),
    )
    if not writer.isOpened():
        raise RuntimeError("OpenCV could not open the bundled libx264 MP4 writer")

    started = time.perf_counter()
    first_frame: np.ndarray | None = None
    for index in range(frames):
        phase = index / frames
        frame = overlay_frame(source_frame(spec, phase), spec, phase)
        if first_frame is None:
            first_frame = frame.copy()
        writer.write(frame)
    writer.release()
    make_faststart(video_path)

    if first_frame is None:
        raise RuntimeError(f"No frames rendered for {spec.id}")
    Image.fromarray(cv2.cvtColor(first_frame, cv2.COLOR_BGR2RGB)).save(
        poster_path,
        "WEBP",
        quality=88,
        method=6,
    )
    elapsed = time.perf_counter() - started

    capture = cv2.VideoCapture(str(video_path))
    fourcc_value = int(capture.get(cv2.CAP_PROP_FOURCC))
    fourcc = "".join(chr((fourcc_value >> (8 * index)) & 0xFF) for index in range(4))
    decoded_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    capture.release()
    if fourcc.lower() not in {"h264", "avc1"} or decoded_frames != frames:
        raise RuntimeError(f"Validation failed for {video_path}: {fourcc=}, {decoded_frames=}, expected={frames}")

    return {
        **asdict(spec),
        "width": width,
        "height": height,
        "fps": FPS,
        "frame_count": frames,
        "video": f"/mirra/video/{spec.video_name}",
        "poster": f"/mirra/posters/{spec.poster_name}",
        "codec": "H.264 / AVC (libx264 High Profile, yuv420p)",
        "silent": True,
        "faststart": True,
        "bytes": video_path.stat().st_size,
        "sha256": file_sha256(video_path),
        "poster_sha256": file_sha256(poster_path),
        "render_seconds": round(elapsed, 3),
    }


def contact_sheet(spec: VideoSpec, output: Path) -> None:
    video_path = VIDEO_ROOT / spec.video_name
    capture = cv2.VideoCapture(str(video_path))
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    samples: list[np.ndarray] = []
    for percentage in (0, 25, 50, 75):
        capture.set(cv2.CAP_PROP_POS_FRAMES, int(total * percentage / 100))
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"Could not read {percentage}% frame from {video_path}")
        thumb = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
        cv2.rectangle(thumb, (14, 14), (100, 48), (24, 24, 23), -1)
        cv2.putText(thumb, f"{percentage}%", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (245, 243, 238), 2, cv2.LINE_AA)
        samples.append(thumb)
    capture.release()
    sheet = np.vstack((np.hstack(samples[:2]), np.hstack(samples[2:])))
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])


def write_manifest(results: list[dict[str, object]]) -> None:
    planned = []
    by_id: dict[str, dict[str, object]] = {}
    if MANIFEST_PATH.exists():
        previous = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        by_id.update(
            {
                str(item["id"]): item
                for item in previous.get("videos", [])
                if item.get("rendered", True)
            }
        )
    by_id.update({str(item["id"]): item for item in results})
    for spec in SPECS:
        entry = by_id.get(spec.id)
        planned.append(entry if entry else {**asdict(spec), "rendered": False})
    payload = {
        "version": 1,
        "generator": "scripts/generate_mirra_videos.py",
        "creative_system": "Material Truth",
        "render_contract": {
            "fps": FPS,
            "audio": "none",
            "codec": "H.264 / AVC via OpenCV bundled FFmpeg/libx264",
            "pixel_format": "yuv420p",
            "looping": "sinusoidal or ping-pong; final-to-first transition is continuous",
            "poster": "first frame, WebP quality 88",
            "wide": {"width": WIDE[0], "height": WIDE[1], "aspect": "16:9"},
            "outcome": {"width": OUTCOME[0], "height": OUTCOME[1], "aspect": "16:9"},
            "card": {"width": CARD[0], "height": CARD[1], "aspect": "6:5"},
        },
        "source_plates": {name: str(path.relative_to(FRONTEND_ROOT)) for name, path in PLATES.items()},
        "videos": planned,
    }
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", action="append", default=[], metavar="ID", help="Render only an ID such as S01; repeatable")
    parser.add_argument("--contact-sheet", action="store_true", help="Write a four-frame review sheet under /private/tmp")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected_ids = {value.upper() for value in args.only}
    selected = [spec for spec in SPECS if not selected_ids or spec.id in selected_ids]
    unknown = selected_ids - {spec.id for spec in SPECS}
    if unknown:
        raise SystemExit(f"Unknown IDs: {', '.join(sorted(unknown))}")
    for path in PLATES.values():
        if not path.exists():
            raise FileNotFoundError(path)

    results: list[dict[str, object]] = []
    for spec in selected:
        result = render(spec)
        results.append(result)
        print(f"{spec.id} {spec.video_name}: {result['bytes']} bytes in {result['render_seconds']}s")
        if args.contact_sheet:
            sheet = Path("/private/tmp") / f"{spec.slug}-contact-sheet.jpg"
            contact_sheet(spec, sheet)
            print(f"contact-sheet: {sheet}")
    write_manifest(results)
    print(f"manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
