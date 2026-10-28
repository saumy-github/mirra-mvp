"""Body-photo intake. Same upload root and traversal guard as merchant captures:

    <dev_upload|live_upload>/measurement_photos/<user_id>/<capture_id>/<view>.<ext>

These are photos of a person's body, so they live only until the worker has
measured them (worker/measure_tasks.py deletes them, success or failure).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from ..config import get_settings
from ..core.errors import ValidationFailed
from ..merchant.storage import ALLOWED_CONTENT_TYPES, MAX_IMAGE_BYTES, _probe_dimensions

# A full-body photo is legible well below the merchant capture minimum (640),
# but under this the silhouette edge is too coarse for cm-level girths.
MIN_EDGE_PX = 480


PHOTO_ROOT = "measurement_photos"


def _root(root: str = PHOTO_ROOT) -> Path:
    return get_settings().avatars_upload_root / root


def capture_dir(user_id: str, capture_id: str, root: str = PHOTO_ROOT) -> Path:
    return _root(root) / user_id / capture_id


def store_photo(
    user_id: str, capture_id: str, view: str, content_type: str, data: bytes, root: str = PHOTO_ROOT
) -> str:
    """Validate and write one photo; returns its path relative to the upload root.
    `root` is the folder under the upload root (face photos use their own)."""
    normalised = (content_type or "").split(";")[0].strip().lower()
    if normalised in ("image/heic", "image/heif"):
        raise ValidationFailed(
            "HEIC photos can't be processed. Set your phone camera to 'Most Compatible' "
            "(JPEG), or export the photo as JPEG first."
        )
    if normalised not in ALLOWED_CONTENT_TYPES:
        raise ValidationFailed(f"The {view} photo must be a JPEG, PNG or WebP image")
    if not data:
        raise ValidationFailed(f"The {view} photo was empty")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValidationFailed(
            f"The {view} photo is {len(data) / 1_048_576:.1f} MB; the limit is {MAX_IMAGE_BYTES // 1_048_576} MB"
        )

    target = capture_dir(user_id, capture_id, root)
    target.mkdir(parents=True, exist_ok=True)
    absolute = target / f"{view}{ALLOWED_CONTENT_TYPES[normalised]}"
    absolute.write_bytes(data)

    width, height = _probe_dimensions(absolute)
    if width and height and min(width, height) < MIN_EDGE_PX:
        absolute.unlink(missing_ok=True)
        raise ValidationFailed(
            f"The {view} photo is {width}x{height}; it needs at least {MIN_EDGE_PX}px on the short edge"
        )
    return absolute.relative_to(get_settings().avatars_upload_root).as_posix()


def resolve(relative: str) -> Path:
    root = get_settings().avatars_upload_root.resolve()
    resolved = (root / relative).resolve()
    if root not in resolved.parents:
        raise ValidationFailed("Stored photo path is invalid")
    return resolved


def delete_capture_files(user_id: str, capture_id: str, root: str = PHOTO_ROOT) -> None:
    shutil.rmtree(capture_dir(user_id, capture_id, root), ignore_errors=True)


def delete_user_files(user_id: str, root: str = PHOTO_ROOT) -> None:
    """Account-deletion cascade."""
    shutil.rmtree(_root(root) / user_id, ignore_errors=True)
