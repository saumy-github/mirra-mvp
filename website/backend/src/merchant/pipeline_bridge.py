"""Turning a dashboard garment into something the CLO pipeline can run.

This module is the join between the merchant surface and Steps 2 and 3. It is
the piece that did not exist: the dashboard modelled garments, the pipeline
consumed `input/c_XXX/` folders plus `cloths`/`sizes` documents, and nothing
translated one into the other.

The mapping
-----------
    MerchantGarment              →  one `cloths` document
      .pipeline.cloth_id            c_<garment suffix>
      .sizing.rows[]             →  one `sizes` document each
      .pipeline.size_ids            s_<garment suffix>_<size slug>
      .capture.assets[]          →  product_ingestion/input/<cloth_id>/image_N.jpg

Then, per size:

    run_product_ingestion(cloth_id, size_id)   → panels + textures  (Step 2)
    run_clo_vto(avatar, panels)                → simulation GLB     (Step 3)

Why ids are derived, not sequential
-----------------------------------
`c_001` style counters are fine for a single operator running the CLI. With
several tenants ingesting concurrently, a counter is a race. These ids are
derived from the garment id, so they are unique by construction, stable across
re-runs, and reversible — given a run directory you can find the garment.
They keep the `c_`/`s_` prefixes because `product_ingestion/run_manifest.py`
matches on them (`_CLOTH_RE = ^c_[^-]+$`), and because a dash inside the id
would be read as a run-folder separator.

Capability gate
---------------
Step 2 is a T-shirt block. `panel_generation_clo` drafts a crew-neck set-in
sleeve tee and nothing else; `view_selection` picks one front image. A dress
or a pair of trousers submitted here would produce a t-shirt and claim
success. `check_pipeline_capability()` refuses those up front with a reason
the merchant can read — audit P0-03, which asked for exactly this gate.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..config import REPO_ROOT, get_settings
from ..db import cloths_col, sizes_col
from .models import MerchantGarmentDocument, SizeRow

# product_ingestion reads its input from here; the runner's --input-root
# default is product_ingestion/input.
INGESTION_INPUT_ROOT = REPO_ROOT / "product_ingestion" / "input"

# Categories Step 2 can actually draft. Everything else is refused rather
# than silently returned as a t-shirt.
SUPPORTED_CATEGORIES = ("top",)

# The four measurement fields with no sane default. A size missing any of
# these cannot be drafted at all.
REQUIRED_MEASUREMENTS = (
    "half_chest_width_cm",
    "garment_length_cm",
    "shoulder_width_cm",
    "armhole_depth_cm",
)

# Kept byte-identical to product_ingestion/panel_generation_clo.py and
# mirra_measurements/size_model.py so a derived value here and the adapter's
# own fallback agree exactly.
HEM_TO_CHEST_RATIO = 269.9999 / 290.0975
WRIST_TO_BICEP_RATIO = 384.3506 / 490.2734

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _slug(value: str) -> str:
    """A dash-free, lowercase token. Dashes are stripped, not replaced: the
    run-folder id is `<cloth>-<size>-<run>`, so a dash inside either id makes
    `parse_product_run_dir` ambiguous."""
    return _SLUG_RE.sub("", value.strip().lower()) or "x"


# ------------------------------------------------------------------- ids


def cloth_id_for(garment_id: str) -> str:
    """`m_g_abc123` → `c_mgabc123`. Deterministic and dash-free."""
    return f"c_{_slug(garment_id)}"


def size_id_for(garment_id: str, size_label: str) -> str:
    """`m_g_abc123` + `M` → `s_mgabc123m`."""
    return f"s_{_slug(garment_id)}{_slug(size_label)}"


# ------------------------------------------------------------- capability


@dataclass
class CapabilityVerdict:
    ok: bool
    reasons: list[str]

    @property
    def reason(self) -> str:
        return "; ".join(self.reasons)


def check_pipeline_capability(garment: MerchantGarmentDocument) -> CapabilityVerdict:
    """Can Step 2 actually produce panels for this garment?

    Answered before anything is queued, so a merchant is told "this pipeline
    only drafts tops today" instead of receiving a t-shirt where they asked
    for a dress.
    """
    reasons: list[str] = []

    if garment.category not in SUPPORTED_CATEGORIES:
        reasons.append(
            f"The panel generator drafts a crew-neck t-shirt block only, so "
            f"'{garment.category}' cannot be digitised yet (supported: "
            f"{', '.join(SUPPORTED_CATEGORIES)})"
        )

    if garment.capture.method == "cad":
        if garment.capture.cad_asset is None:
            reasons.append("Capture method is CAD but no 3D asset has been attached")
    else:
        accepted = [a for a in garment.capture.assets if a.accepted]
        if not accepted:
            reasons.append("No accepted capture images — Step 2 needs at least a front view")
        elif not any(a.view == "front" for a in accepted):
            reasons.append(
                "No accepted front view — view selection picks the front image to segment"
            )

    if not garment.sizing.rows:
        reasons.append("No sizes recorded — every size becomes its own ingestion run")
    else:
        for row in garment.sizing.rows:
            missing = [f for f in REQUIRED_MEASUREMENTS if getattr(row, f, None) in (None, 0)]
            if missing:
                reasons.append(f"Size {row.size} is missing {', '.join(missing)}")

    return CapabilityVerdict(ok=not reasons, reasons=reasons)


# ------------------------------------------------------- measurement docs


def size_row_to_size_doc(row: SizeRow, size_id: str, fit_type: str) -> dict:
    """One graded size → one `sizes` collection document.

    Field names and units pass straight through: `SizeRow` was defined in the
    pipeline's own vocabulary precisely so nothing has to be translated here,
    and a translation layer is where half-girth conventions get inverted.

    `hem_width_cm`/`wrist_width_cm` are derived at the CLO reference taper
    when the merchant has not measured them, matching
    `size_model.derive_*` exactly.
    """
    half_chest = float(row.half_chest_width_cm or 0)
    bicep = float(row.bicep_width_cm or 0)

    hem = row.hem_width_cm
    if hem is None and half_chest:
        hem = round(half_chest * HEM_TO_CHEST_RATIO, 2)
    wrist = row.wrist_width_cm
    if wrist is None and bicep:
        wrist = round(bicep * 2.0 * WRIST_TO_BICEP_RATIO, 2)

    now = _now()
    doc = {
        "size_id": size_id,
        "fit_type": fit_type,
        "half_chest_width_cm": half_chest,
        "garment_length_cm": float(row.garment_length_cm or 0),
        "shoulder_width_cm": float(row.shoulder_width_cm or 0),
        "neck_width_cm": float(row.neck_width_cm or 0),
        "neck_depth_front_cm": float(row.neck_depth_front_cm or 0),
        "neck_depth_back_cm": float(row.neck_depth_back_cm or 0),
        "sleeve_length_cm": float(row.sleeve_length_cm or 0),
        "bicep_width_cm": bicep,
        "armhole_depth_cm": float(row.armhole_depth_cm or 0),
        "seam_allowance_cm": float(row.seam_allowance_cm or 1.0),
        "created_at": now,
        "updated_at": now,
    }
    if hem is not None:
        doc["hem_width_cm"] = float(hem)
    if wrist is not None:
        doc["wrist_width_cm"] = float(wrist)
    return doc


async def publish_measurements(garment: MerchantGarmentDocument) -> tuple[str, list[str]]:
    """Write this garment's `cloths` + `sizes` documents. Returns (cloth_id, size_ids).

    Upserts rather than inserts: re-submitting a garment after fixing a
    measurement has to update the size the pipeline reads, not create a
    second one the pipeline will never look at.
    """
    cloth_id = garment.pipeline.cloth_id or cloth_id_for(garment.id)
    size_ids: list[str] = []

    for row in garment.sizing.rows:
        size_id = size_id_for(garment.id, row.size)
        doc = size_row_to_size_doc(row, size_id, garment.sizing.fit_type)
        doc["cloth_id"] = cloth_id
        doc["cloth_label"] = garment.canonical_title
        doc["category"] = garment.category
        # created_at must survive a re-submission; only updated_at moves.
        created_at = doc.pop("created_at")
        await sizes_col().update_one(
            {"size_id": size_id},
            {"$set": doc, "$setOnInsert": {"created_at": created_at}},
            upsert=True,
        )
        size_ids.append(size_id)

    now = _now()
    cloth_doc = {
        "cloth_id": cloth_id,
        "label": garment.merchant_title or garment.canonical_title,
        "category": garment.category,
        "size_ids": size_ids,
        "brand_id": garment.tenant_id,
        "updated_at": now,
    }
    await cloths_col().update_one(
        {"cloth_id": cloth_id},
        {"$set": cloth_doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return cloth_id, size_ids


# ------------------------------------------------------------ input files


@dataclass
class StagedInput:
    cloth_id: str
    input_dir: Path
    image_count: int
    copied: list[str]


def stage_capture_input(garment: MerchantGarmentDocument, cloth_id: str) -> StagedInput:
    """Copy accepted capture assets into `product_ingestion/input/<cloth_id>/`.

    Named `image_1.jpg`, `image_2.jpg`, … because that is the layout
    `list_cloth_images` expects, with the front view first so that
    `--skip-clip` (and CLIP's own ordering tie-breaks) still land on the
    right frame.

    The directory is emptied first: a re-run after replacing a bad photo must
    not leave the old one behind for view selection to pick.
    """
    upload_root = get_settings().avatars_upload_root
    input_dir = INGESTION_INPUT_ROOT / cloth_id
    if input_dir.exists():
        for existing in input_dir.iterdir():
            if existing.is_file():
                existing.unlink()
    input_dir.mkdir(parents=True, exist_ok=True)

    # Front first, then the other principal views, then details.
    order = {"front": 0, "back": 1, "left": 2, "right": 3}
    accepted = sorted(
        (a for a in garment.capture.assets if a.accepted),
        key=lambda a: (order.get(a.view, 9), a.uploaded_at),
    )

    copied: list[str] = []
    for index, asset in enumerate(accepted, start=1):
        source = (upload_root / asset.stored_path).resolve()
        # Server-written paths, but never trusted blindly — same guard as the
        # avatar and render serving routes.
        if upload_root.resolve() not in source.parents:
            continue
        if not source.is_file():
            continue
        suffix = Path(asset.filename).suffix.lower() or ".jpg"
        target = input_dir / f"image_{index}{suffix}"
        shutil.copyfile(source, target)
        copied.append(target.name)

    return StagedInput(
        cloth_id=cloth_id, input_dir=input_dir, image_count=len(copied), copied=copied
    )
