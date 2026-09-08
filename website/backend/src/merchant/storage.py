"""Capture-asset intake: real files, validated, hashed and stored.

The dashboard prototype recorded a capture by writing the constant filename
`front.jpg` and `accepted: true` — no bytes ever moved (audit P1-01). This
module is what actually receives them.

Layout mirrors the avatar/render stores so one upload root and one serving
guard cover everything:

    <dev_upload|live_upload>/captures/<tenant_id>/<garment_id>/<asset_id>.<ext>

and `CaptureAsset.stored_path` holds the path *relative* to that root, so a
document written on the worker machine still resolves on the API host.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..config import get_settings
from ..core.errors import ValidationFailed
from ..core.security import new_id
from .models import CaptureAsset

# Formats the segmentation stage can actually read. `run_segmentation` opens
# with PIL/cv2; HEIC (what an iPhone hands you by default) is not decodable
# without an extra plugin, so it is refused here with an actionable message
# rather than failing deep inside Step 2.
ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
CAD_CONTENT_TYPES = {
    "application/zip": ".zprj",
    "application/octet-stream": ".zprj",
    "model/gltf-binary": ".glb",
}

MAX_IMAGE_BYTES = 25 * 1024 * 1024      # 25 MB — a phone HDR frame fits
MAX_CAD_BYTES = 250 * 1024 * 1024       # 250 MB — a .zprj with textures

VALID_VIEWS = ("front", "back", "left", "right", "detail")

# Below this the segmentation quality metrics are meaningless and the texture
# projection produces a blurred atlas. Cheap to check, expensive to discover
# three pipeline stages later.
MIN_IMAGE_EDGE_PX = 640


@dataclass
class StoredFile:
    stored_path: str
    absolute_path: Path
    sha256: str
    bytes: int
    width: int | None
    height: int | None


def _captures_root() -> Path:
    return get_settings().avatars_upload_root / "captures"


def _probe_dimensions(path: Path) -> tuple[int | None, int | None]:
    """Image dimensions, or (None, None) when Pillow is unavailable.

    Pillow is a hard dependency of the pipeline but not of the API image, so
    a missing import downgrades the check rather than failing the upload.
    """
    try:
        from PIL import Image
    except ImportError:
        return None, None
    try:
        with Image.open(path) as img:
            return img.width, img.height
    except Exception:
        return None, None


def store_capture_file(
    *,
    tenant_id: str,
    garment_id: str,
    view: str,
    filename: str,
    content_type: str,
    data: bytes,
    sample_size: str,
    uploaded_by: str,
    is_cad: bool = False,
) -> CaptureAsset:
    """Validate and persist one uploaded file, returning the asset record.

    Everything recorded on the returned `CaptureAsset` is measured from the
    bytes that arrived — size, checksum, dimensions — so a capture set can be
    audited after the fact and a re-upload of the same file is detectable.
    """
    if not is_cad and view not in VALID_VIEWS:
        raise ValidationFailed(f"view must be one of {', '.join(VALID_VIEWS)}")

    allowed = CAD_CONTENT_TYPES if is_cad else ALLOWED_CONTENT_TYPES
    max_bytes = MAX_CAD_BYTES if is_cad else MAX_IMAGE_BYTES

    normalised = (content_type or "").split(";")[0].strip().lower()
    if normalised not in allowed:
        if not is_cad and normalised in ("image/heic", "image/heif"):
            raise ValidationFailed(
                "HEIC images cannot be processed. Set your phone camera to "
                "'Most Compatible' (JPEG), or export the photo as JPEG first."
            )
        raise ValidationFailed(
            f"{content_type or 'unknown'} is not an accepted format "
            f"({', '.join(sorted(allowed))})"
        )

    if not data:
        raise ValidationFailed("The uploaded file was empty")
    if len(data) > max_bytes:
        raise ValidationFailed(
            f"File is {len(data) / 1_048_576:.1f} MB; the limit is {max_bytes // 1_048_576} MB"
        )

    asset_id = new_id("cap")
    extension = allowed[normalised]
    target_dir = _captures_root() / tenant_id / garment_id
    target_dir.mkdir(parents=True, exist_ok=True)
    absolute = target_dir / f"{asset_id}{extension}"
    absolute.write_bytes(data)

    width, height = (None, None) if is_cad else _probe_dimensions(absolute)
    if not is_cad and width and height and min(width, height) < MIN_IMAGE_EDGE_PX:
        absolute.unlink(missing_ok=True)
        raise ValidationFailed(
            f"Image is {width}x{height}. Capture needs at least "
            f"{MIN_IMAGE_EDGE_PX}px on the short edge for segmentation to be reliable."
        )

    root = get_settings().avatars_upload_root
    return CaptureAsset(
        asset_id=asset_id,
        view="cad" if is_cad else view,
        filename=filename or absolute.name,
        content_type=normalised,
        bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        stored_path=str(absolute.relative_to(root).as_posix()),
        width=width,
        height=height,
        accepted=True,
        sample_size=sample_size,
        uploaded_by=uploaded_by,
        uploaded_at=datetime.now(timezone.utc),
    )


def resolve_capture_path(stored_path: str) -> Path:
    """Absolute path for a stored asset, with the traversal guard applied."""
    root = get_settings().avatars_upload_root.resolve()
    resolved = (root / stored_path).resolve()
    if root not in resolved.parents and resolved != root:
        raise ValidationFailed("Stored capture path is invalid")
    return resolved


def delete_capture_file(stored_path: str) -> None:
    try:
        resolve_capture_path(stored_path).unlink(missing_ok=True)
    except ValidationFailed:
        pass
