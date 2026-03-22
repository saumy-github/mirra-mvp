"""Step 2 of product_ingestion: view selection.

Classify images in a folder using CLIP zero-shot via the GarmentRouter helper.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, List

try:
    # garment_router is an internal helper using CLIP
    from garment_router import GarmentRouter
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


def run_view_selection(input_dir: str) -> List[ViewLabel]:
    """
    Classify images in *input_dir* using CLIP zero-shot.
    Returns list of ViewLabel for each image.
    """
    if not HAS_ROUTER:
        print("    ⚠️  garment_router.py not importable — skipping view selection")
        return []

    router = GarmentRouter()
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


def select_primary_image(input_dir: str | Path, skip_clip: bool = False) -> ViewSelectionOutput:
    """
    Select the primary cloth image.

    The canonical order is view selection first. If CLIP is skipped or unavailable,
    the first image is used.
    """
    images = list_cloth_images(input_dir)
    if not images:
        raise FileNotFoundError(f"No cloth images found in {input_dir}")

    if skip_clip:
        return ViewSelectionOutput(
            selected_image=images[0],
            selection_reason="skip_clip_fallback_first_image",
            views=[],
        )

    try:
        views = run_view_selection(str(input_dir))
    except Exception:
        views = []

    if not views:
        return ViewSelectionOutput(
            selected_image=images[0],
            selection_reason="clip_unavailable_fallback_first_image",
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
