"""Per-measurement linear correction fitted against tape-measured ground truth.

Raw silhouette girths carry systematic bias (ellipse vs real cross-section,
clothing, posture). Collect 30-50 people, tape-measure them, run `mirra calibrate`,
and every later prediction is corrected as  value' = a * value + b.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np


def fit(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    """rows: dicts with keys `measurement`, `predicted_cm`, `actual_cm`."""
    by_name: dict[str, list[tuple[float, float]]] = {}
    for r in rows:
        by_name.setdefault(r["measurement"], []).append((float(r["predicted_cm"]), float(r["actual_cm"])))

    coeffs = {}
    for name, pairs in by_name.items():
        x, y = np.array(pairs).T
        if len(pairs) >= 8 and np.ptp(x) > 0:
            a, b = np.polyfit(x, y, 1)
        else:  # too little data for a slope: correct the mean offset only
            a, b = 1.0, float(np.mean(y - x))
        pred = a * x + b
        coeffs[name] = {
            "a": float(a), "b": float(b), "n": len(pairs),
            "mae_before_cm": float(np.mean(np.abs(x - y))),
            "mae_after_cm": float(np.mean(np.abs(pred - y))),
        }
    return coeffs


def fit_csv(csv_path: str | Path) -> dict:
    with open(csv_path, newline="") as f:
        return fit(list(csv.DictReader(f)))


def apply(measurements: dict[str, float], coeffs: dict) -> dict[str, float]:
    out = {}
    for k, v in measurements.items():
        c = coeffs.get(k)
        out[k] = round(c["a"] * v + c["b"], 1) if c else v
    return out


def load(path: str | Path | None) -> dict:
    if not path or not Path(path).exists():
        return {}
    return json.loads(Path(path).read_text())
