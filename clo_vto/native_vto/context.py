"""Pipeline context object and initializer."""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

workspace_root = Path(__file__).resolve().parents[2]
package_root = Path(__file__).resolve().parents[1]
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from .client import CLORestClient
from .helpers import resolve_patterns_dir
from .seams import DEFAULT_SEAMS, load_seams_from_manifest


@dataclass
class PipelineContext:
    """Mutable context shared by all step modules."""

    client: CLORestClient
    workspace_root: Path
    avatar_path: Path
    patterns_dir: Path
    output_dir: Path
    project_dir: Path
    pattern_files: list[str]
    seams: list[dict]
    using_default_seams: bool = True
    avatar_loaded: bool = False
    loaded_patterns: int = 0
    slots: list[dict] = field(default_factory=list)
    slot_map: dict[str, int] = field(default_factory=dict)
    imported_files: list[str] = field(default_factory=list)
    imported_pattern_names: list[str] = field(default_factory=list)
    edge_ok: bool = False
    slot_ok: bool = False
    arrangement_ok: bool = False
    ready_for_sewing: bool = False
    expected_pattern_count: int = 4
    imported_pieces: list[str] = field(default_factory=list)
    piece_to_index: dict[str, int] = field(default_factory=dict)
    index_to_piece: dict[int, str] = field(default_factory=dict)
    pattern_import_scale: float = 1.0
    pattern_import_scales: dict[str, float] = field(default_factory=dict)
    pattern_hashes: dict[str, str] = field(default_factory=dict)
    pattern_geometry_hash: str = ""
    scale_metrics: dict = field(default_factory=dict)
    slot_candidates: dict[str, list[dict]] = field(default_factory=dict)
    slot_fallback_mode: str = ""
    edge_counts: dict[str, int] = field(default_factory=dict)
    edge_sources: dict[str, str] = field(default_factory=dict)
    sdk_capabilities: dict = field(default_factory=dict)
    avatar_debug: dict = field(default_factory=dict)
    import_scale_debug: dict = field(default_factory=dict)
    slot_diagnostics: list[dict] = field(default_factory=list)
    seam_results: list[dict] = field(default_factory=list)
    step_results: list[dict] = field(default_factory=list)
    # Edge manifest loaded from panels_dir/../edge_manifest.json
    edge_manifest: dict = field(default_factory=dict)


def _load_manifest(patterns_dir: Path) -> dict:
    """Try to load edge_manifest.json from the panels directory.

    patterns_dir is typically …/panels/dxf; the manifest lives one level up
    at …/panels/edge_manifest.json.
    """
    manifest_path = patterns_dir.parent / "edge_manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _discover_default_native_avatar() -> Path:
    output_root = package_root / "output"
    preferred = output_root / "clo_test.avt"
    if preferred.exists():
        return preferred

    output_candidates = sorted(output_root.glob("*.avt"))
    if len(output_candidates) == 1:
        return output_candidates[0]

    template_root = package_root / "avt_templates"
    template_candidates = sorted(template_root.glob("*.avt"))
    if len(template_candidates) == 1:
        return template_candidates[0]

    default_input_avatar = workspace_root / "clo_avatar_generation" / "input" / "base-1.avt"
    if default_input_avatar.exists():
        return default_input_avatar

    if output_candidates:
        return output_candidates[0]
    if template_candidates:
        return template_candidates[0]

    return output_root / "clo_test.avt"


def create_context(seam_map=None, avatar_path: Optional[Path | str] = None, patterns_dir: Optional[Path | str] = None):
    """Build a pipeline context with default paths and seam map.

    Seam resolution order:
    1. Explicit seam_map argument (highest priority).
    2. edge_manifest.json found alongside the DXF patterns (auto-generated).
    3. DEFAULT_SEAMS fallback (hardcoded 10-seam map).
    """
    output_dir = package_root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    project_dir = output_dir / "projects"
    project_dir.mkdir(parents=True, exist_ok=True)

    if avatar_path:
        avatar_path = Path(avatar_path)
    else:
        avatar_path = _discover_default_native_avatar()

    if patterns_dir:
        patterns_dir = Path(patterns_dir)
    else:
        patterns_dir = resolve_patterns_dir()

    # Determine seams and whether they come from the manifest
    using_default_seams = True
    edge_manifest: dict = {}

    if seam_map is not None:
        resolved_seams = seam_map
        using_default_seams = False
    else:
        edge_manifest = _load_manifest(patterns_dir)
        if edge_manifest:
            manifest_path = patterns_dir.parent / "edge_manifest.json"
            manifest_seams = load_seams_from_manifest(manifest_path)
            if manifest_seams:
                resolved_seams = manifest_seams
                using_default_seams = False
                print(f"  Loaded {len(manifest_seams)} seams from edge manifest.")
            else:
                resolved_seams = DEFAULT_SEAMS
                print("  Edge manifest found but incomplete — using DEFAULT_SEAMS.")
        else:
            resolved_seams = DEFAULT_SEAMS

    ctx = PipelineContext(
        client=CLORestClient(),
        workspace_root=workspace_root,
        avatar_path=avatar_path,
        patterns_dir=patterns_dir,
        output_dir=output_dir,
        project_dir=project_dir,
        pattern_files=[
            "front_panel.dxf",
            "back_panel.dxf",
            "sleeve_left.dxf",
            "sleeve_right.dxf",
        ],
        seams=resolved_seams,
        using_default_seams=using_default_seams,
        edge_manifest=edge_manifest,
    )
    return ctx
