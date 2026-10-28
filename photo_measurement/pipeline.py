"""Front + side photo + height -> body measurements, the one entry point the worker
and the CLI share.

    MediaPipe (person mask + pose) -> geometric measurements -> BMnet correction
    -> backend profile fields (user_measurements names) + skin tone + body shape

The learned model is required: a missing checkpoint is an error, not a silent
fall-back to the much less accurate geometric numbers.
"""
from __future__ import annotations

from pathlib import Path

from .bmnet.predict import MODELS_DIR, available_models, fuse, predict
from .capture import observe
from .measure import extract
from .report import to_profile


class ModelMissing(RuntimeError):
    pass


def measure_photos(front_path: str | Path, side_path: str | Path, height_cm: float,
                   weight_kg: float | None = None, gender: str | None = None,
                   shoe_sole_cm: float = 0.0) -> dict:
    """Returns {measurements, methods, warnings, model, profile, unit}.

    `profile` holds exactly the user_measurements field names (height_cm,
    chest_circumference_cm, ..., body_shape_type, skin_tone_hex); `measurements`
    holds every measurement the pipeline produces, for display and debugging.
    Photos with a bad pose still return numbers; `warnings` says what to fix.
    """
    models = available_models()
    if not models:
        raise ModelMissing(f"No BMnet checkpoint (bmnet*.pt) in {MODELS_DIR}; see photo_measurement/README.md")

    front, side = observe(front_path), observe(side_path)
    result = extract(front, side, height_cm, shoe_sole_cm).as_dict()
    # the network sees the shod silhouette, so give it the shod height
    learned = predict(front, side, height_cm + shoe_sole_cm, weight_kg, gender, models)
    result = fuse(result, learned)
    result["model"] = [p.name for p in models]
    result["profile"] = to_profile(result, front, weight_kg)
    # the network's height is a by-product; the user's own height is the truth
    result["profile"]["height_cm"] = round(float(height_cm), 1)
    result.pop("geometric_measurements", None)
    return result
