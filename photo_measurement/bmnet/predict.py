"""Run the trained network on MediaPipe observations and fuse with the geometric pipeline."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from ..capture import Observation
from .data import TARGETS, canonical_view, scalar_features

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"

# learned BodyM target -> our measurement key(s)
LEARNED_KEYS = {
    "chest": ["chest"], "waist": ["waist"], "hip": ["hip"], "leg-length": ["inseam"],
    "shoulder-breadth": ["shoulder_width"], "arm-length": ["left_arm_length", "right_arm_length"],
    "bicep": ["left_bicep", "right_bicep"], "wrist": ["left_wrist", "right_wrist"],
    "thigh": ["left_thigh", "right_thigh"], "calf": ["left_calf", "right_calf"],
    "ankle": ["ankle"], "forearm": ["forearm"], "shoulder-to-crotch": ["shoulder_to_crotch"],
}
# measurements BodyM has no labels for: rescale the geometric value by how much the
# network corrected its nearest learned neighbour (same slice of the body)
ANCHORS = {"bust": "chest", "under_bust": "chest", "overarm": "chest", "abdomen": "waist"}


def available_models() -> list[Path]:
    return sorted(MODELS_DIR.glob("bmnet*.pt"))


def device() -> torch.device:
    return torch.device("mps" if torch.backends.mps.is_available()
                        else "cuda" if torch.cuda.is_available() else "cpu")


def load(path: Path, dev: torch.device | None = None):
    """Checkpoints are written by the training code in the R&D repo (for_measurements,
    mirra_avatar/bmnet/train.py): {"backbone": str, "state_dict": ...}."""
    from .model import BodyMeasureNet

    ck = torch.load(path, map_location="cpu", weights_only=False)
    model = BodyMeasureNet(ck["backbone"], pretrained=False)
    model.load_state_dict(ck["state_dict"])
    return model.to(dev or device()).eval()


@torch.no_grad()
def predict(front: Observation, side: Observation, height_cm: float, weight_kg: float | None,
            gender: str | None, model_paths: list[Path]) -> dict[str, float]:
    """Ensemble (all given models) x test-time mirror -> {BodyM target: cm}."""
    dev = device()
    x = torch.from_numpy(np.stack([canonical_view(front.mask), canonical_view(side.mask)]))[None].to(dev)
    s = torch.from_numpy(scalar_features(height_cm, weight_kg, gender))[None].to(dev)
    preds = []
    for p in model_paths:
        m = load(p, dev)
        preds += [m(x, s), m(torch.flip(x, dims=[3]), s)]
    out = torch.stack(preds).mean(0)[0].cpu().numpy()
    return {k: float(v) for k, v in zip(TARGETS, out)}


def fuse(result: dict, learned: dict[str, float]) -> dict:
    """Replace geometric values with learned ones where BodyM supervises them."""
    m = dict(result["measurements"])
    methods = dict(result["methods"])
    geometric = dict(m)
    for target, keys in LEARNED_KEYS.items():
        for k in keys:
            m[k] = round(learned[target], 1)
            methods[k] = "learned"
    for k, anchor in ANCHORS.items():
        if k in m and geometric.get(anchor):
            m[k] = round(m[k] * learned_value(learned, anchor) / geometric[anchor], 1)
            methods[k] = f"geometric, scaled by learned {anchor}"
    return {**result, "measurements": m, "methods": methods, "geometric_measurements": geometric}


def learned_value(learned: dict[str, float], key: str) -> float:
    target = next(t for t, keys in LEARNED_KEYS.items() if key in keys)
    return learned[target]
