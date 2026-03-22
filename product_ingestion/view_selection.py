"""Step 1 of product_ingestion: view selection."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, List

from tshirt_extractor import ViewLabel, run_view_selection

SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}


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
