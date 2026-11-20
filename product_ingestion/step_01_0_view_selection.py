"""Step 1 of product_ingestion: view selection.

Classify images in a folder via the GarmentRouter helper.

P16 (CV project): `method="trained"` (default) uses the trained view model in multi_view.py (works on
torch 2.4.1); `method="v0"` keeps the old CLIP ViT-B/32 zero-shot path.  `select_views(dir)` returns the
full multi-photo assignment (front, back, sides, details, outliers) as a multi_view.ViewAssignment.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, List

try:
    # step_01_1_garment_router is an internal helper using CLIP
    from step_01_1_garment_router import GarmentRouter
    HAS_ROUTER = True
except Exception:
    HAS_ROUTER = False

SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}


@dataclass
class ViewLabel:
    """View classification for one image."""
    filename: str
    filepath: str
    label: str       # front_view | back_view | side_view | irrelevant
    confidence: float
    scores: dict


def run_view_selection(input_dir: str, method: str = "trained") -> List[ViewLabel]:
    """
    Classify images in *input_dir* (method "trained" = P16 view model, "v0" = CLIP zero-shot).
    Returns list of ViewLabel for each image.
    """
    if not HAS_ROUTER:
        print("    ⚠️  step_01_1_garment_router.py not importable — skipping view selection")
        return []

    router = GarmentRouter(method=method)
    routing = router.route_images(input_dir)

    views: List[ViewLabel] = []
    for score in routing.all_scores:
        views.append(ViewLabel(
            filename=score.filename,
            filepath=score.filepath,
            label=f"{score.assigned_view}_view" if score.assigned_view != "irrelevant" else "irrelevant",
            confidence=score.confidence,
            scores={
                "front_view": score.front,
                "back_view": score.back,
                "side_view": score.side,
                "irrelevant": score.irrelevant,
            },
        ))
    return views


@dataclass
class ViewSelectionOutput:
    """Selected image and supporting CLIP routing metadata."""

    selected_image: Path
    selection_reason: str
    views: List[ViewLabel]

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_image": str(self.selected_image),
            "selection_reason": self.selection_reason,
            "views": [asdict(view) for view in self.views],
        }


def list_cloth_images(input_dir: str | Path) -> list[Path]:
    """List supported input images for a cloth folder."""
    base = Path(input_dir)
    return sorted(
        path
        for path in base.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_EXTS
    )


def select_views(input_dir: str | Path, **kwargs):
    """P16: assign front / back / side / detail / other to every photo in the folder.

    Returns a multi_view.ViewAssignment (see multi_view.assign_views); `.front` is the primary image and
    `.back` the back photo or None.  With one photo it is returned as the front.
    """
    from multi_view import assign_views
    images = list_cloth_images(input_dir)
    if not images:
        raise FileNotFoundError(f"No cloth images found in {input_dir}")
    return assign_views([str(p) for p in images], **kwargs)


def select_primary_image(input_dir: str | Path, skip_clip: bool = False, method: str = "trained") -> ViewSelectionOutput:
    """
    Select the primary cloth image.

    The canonical order is view selection first. If view selection is skipped or unavailable,
    the first image is used.  A single photo is returned as is (no model is loaded), as before.
    `method="v0"` runs the old CLIP zero-shot routing; "trained" (default) runs the P16 view model.
    """
    images = list_cloth_images(input_dir)
    if not images:
        raise FileNotFoundError(f"No cloth images found in {input_dir}")
    if len(images) == 1 and not skip_clip and method == "trained":
        return ViewSelectionOutput(
            selected_image=images[0],
            selection_reason="single_photo",
            views=[],
        )

    if skip_clip:
        return ViewSelectionOutput(
            selected_image=images[0],
            selection_reason="skip_clip_fallback_first_image",
            views=[],
        )

    if method == "trained":
        try:
            va = select_views(input_dir)
            if not va.method.startswith("fallback"):
                labels = [ViewLabel(
                    filename=Path(ph.path).name, filepath=ph.path,
                    label={"front": "front_view", "extra_front": "front_view", "back": "back_view",
                           "extra_back": "back_view", "side": "side_view"}.get(ph.role, "irrelevant"),
                    confidence=float(ph.view_probs.get(ph.view, ph.other_prob)),
                    scores={"front_view": ph.view_probs.get("front", 0.0), "back_view": ph.view_probs.get("back", 0.0),
                            "side_view": ph.view_probs.get("side", 0.0),
                            "irrelevant": max(ph.view_probs.get("additional", 0.0), ph.other_prob)})
                    for ph in va.photos]
                return ViewSelectionOutput(selected_image=Path(va.front), selection_reason="trained_joint_front_view",
                                           views=labels)
        except Exception:  # noqa: BLE001
            pass
        return ViewSelectionOutput(selected_image=images[0],
                                   selection_reason="view_model_unavailable_fallback_first_image", views=[])
    try:
        views = run_view_selection(str(input_dir), method=method)
    except Exception:
        views = []

    if not views:
        return ViewSelectionOutput(
            selected_image=images[0],
            selection_reason="clip_unavailable_fallback_first_image" if method == "v0" else "view_model_unavailable_fallback_first_image",
            views=[],
        )

    front_views = [view for view in views if view.label == "front_view"]
    if front_views:
        best_front = max(front_views, key=lambda view: view.confidence)
        return ViewSelectionOutput(
            selected_image=Path(best_front.filepath),
            selection_reason="best_front_view",
            views=views,
        )

    best_candidate = max(views, key=lambda view: view.scores.get("front_view", 0.0))
    return ViewSelectionOutput(
        selected_image=Path(best_candidate.filepath),
        selection_reason="best_available_front_candidate",
        views=views,
    )
