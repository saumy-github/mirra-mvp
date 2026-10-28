"""Pure 2D geometry on binary person masks. No ML dependencies, fully unit-testable."""
from __future__ import annotations

import math

import numpy as np


def runs_in_row(mask: np.ndarray, y: int) -> list[tuple[int, int]]:
    """Contiguous foreground runs in row y as (x_start, x_end_exclusive)."""
    row = mask[int(np.clip(y, 0, mask.shape[0] - 1))].astype(np.int8)
    edges = np.diff(np.concatenate(([0], row, [0])))
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)
    return list(zip(starts.tolist(), ends.tolist()))


def run_containing(mask: np.ndarray, y: int, x: float) -> tuple[int, int] | None:
    """The run in row y that contains x, else the nearest run (None if row empty)."""
    runs = runs_in_row(mask, y)
    if not runs:
        return None
    for s, e in runs:
        if s <= x < e:
            return s, e
    return min(runs, key=lambda r: min(abs(r[0] - x), abs(r[1] - 1 - x)))


def row_extent(mask: np.ndarray, y: int) -> tuple[int, int] | None:
    """Leftmost to rightmost foreground pixel in row y (includes arms)."""
    runs = runs_in_row(mask, y)
    if not runs:
        return None
    return runs[0][0], runs[-1][1]


def vertical_extent(mask: np.ndarray) -> tuple[int, int]:
    """(top_row, bottom_row_exclusive) of the foreground."""
    rows = np.flatnonzero(mask.any(axis=1))
    if rows.size == 0:
        raise ValueError("empty mask")
    return int(rows[0]), int(rows[-1]) + 1


def width_perpendicular(mask: np.ndarray, p0, p1, t: float, max_len: float | None = None,
                        free_side_only: bool = False) -> float:
    """Width of the mask across the segment p0->p1 at parameter t, measured
    perpendicular to the segment (for limbs that aren't axis aligned).

    free_side_only: limbs that touch the torso merge with it in the mask, so the walk
    towards the body runs on across the torso. Use twice the shorter half-width
    instead, but only when one half is clearly longer than the other (the landmark
    sits near the limb's centre line, so a free limb has two similar halves)."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    n = np.linalg.norm(d)
    if n == 0:
        return 0.0
    d /= n
    perp = np.array([-d[1], d[0]])
    c = p0 + t * (p1 - p0)
    max_len = max_len or n
    h, w = mask.shape

    def walk(sign: int) -> float:
        dist = 0.0
        step = 0.5
        while dist < max_len:
            q = c + sign * (dist + step) * perp
            x, y = int(round(q[0])), int(round(q[1]))
            if not (0 <= x < w and 0 <= y < h) or not mask[y, x]:
                break
            dist += step
        return dist

    cx, cy = int(round(c[0])), int(round(c[1]))
    if not (0 <= cx < w and 0 <= cy < h) or not mask[cy, cx]:
        return 0.0
    a, b = walk(+1), walk(-1)
    merged = max(a, b) > 3 * min(a, b)  # one side ran on into the torso (landmark jitter stays < 3x)
    return 2 * min(a, b) if free_side_only and merged else a + b


def ellipse_circumference(width: float, depth: float) -> float:
    """Ramanujan's second approximation for an ellipse with full axes width x depth."""
    a, b = width / 2.0, depth / 2.0
    if a + b == 0:
        return 0.0
    h = ((a - b) / (a + b)) ** 2
    return math.pi * (a + b) * (1 + 3 * h / (10 + math.sqrt(4 - 3 * h)))


def polyline_length(points) -> float:
    pts = np.asarray(points, float)
    return float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())
