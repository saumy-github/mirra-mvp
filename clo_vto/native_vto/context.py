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
from .seams import DEFAULT_SEAMS, SeamManifestError, load_seams_from_manifest


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
    # Bug 2 fix diagnostics: before/after IsShowAvatar readbacks recorded at
    # each ensure_avatar_visible() call site, keyed by call-site label (e.g.
    # "after_seams", "before_simulate"). See
    # .agent/clo-avatar-vto/vto-pipeline-debug-plan-26_7_24.md, Bug 2.
    avatar_visibility_debug: dict = field(default_factory=dict)
    import_scale_debug: dict = field(default_factory=dict)
    slot_diagnostics: list[dict] = field(default_factory=list)
    seam_results: list[dict] = field(default_factory=list)
    step_results: list[dict] = field(default_factory=list)
    # Edge manifest loaded from panels_dir/../edge_manifest.json
    edge_manifest: dict = field(default_factory=dict)
    # P07: When True, step_09 requires a non-empty geometry hash baseline and
    # aborts if missing.  False = warn-only (default for backward compat).
    strict_seam_hash: bool = False
    # P10: When True, step_04 aborts if DXF units cannot be determined.
    # False = fall back to scale 1.0 with a warning (default for backward compat).
    strict_dxf_units: bool = False
    # Texture pipeline paths (resolved from ingestion output).
    # step_08 falls back to deriving these from patterns_dir if not set.
    colors_json_path: Optional[Path] = None
    textures_dir: Optional[Path] = None
    graphic_diffuse_path: Optional[Path] = None
    # Default panels mode — decouples VTO from panel generation.
    # When True, patterns_dir points at clo_vto/default_panels/dxf/ and
    # texture paths are resolved from ingestion_output_dir instead.
    use_default_panels: bool = False
    default_panels_dir: Optional[Path] = None
    ingestion_output_dir: Optional[Path] = None
    # Phase 2: GLB post-processing paths.
    # glb_path is set by step_11 after CLO exports; step_12 reads it.
    # textured_glb_path is set by step_12 after texture injection.
    # skip_glb_postprocess=True disables step_12 entirely.
    glb_path: Optional[Path] = None
    textured_glb_path: Optional[Path] = None
    skip_glb_postprocess: bool = False
    # Bug 3/4 fix: minimum mesh count step_11 requires in the exported GLB
    # before trusting it contains a real avatar + garment result, not just
    # the 4 garment panels with no avatar. Calibrated against real evidence:
    # clo_vto/output/simulation.glb, a confirmed Bug-4 failure (4 floating
    # unsewn panels, 0 avatar meshes), has exactly 4 meshes — one per
    # pattern_files entry. step_11 defaults this to len(pattern_files) + 1
    # (at least one avatar mesh beyond the panels) if left at 0 here; set
    # explicitly to override.
    expected_min_export_meshes: int = 0


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


_DEFAULT_PANELS_DIR = Path(__file__).resolve().parents[1] / "default_panels"


def create_context(
    seam_map=None,
    avatar_path: Optional[Path | str] = None,
    patterns_dir: Optional[Path | str] = None,
    allow_seam_fallback: bool = True,
    strict_seam_hash: bool = False,
    strict_dxf_units: bool = False,
    use_default_panels: bool = False,
    ingestion_output_dir: Optional[Path | str] = None,
):
    """Build a pipeline context with default paths and seam map.

    Seam resolution order:
    1. Explicit seam_map argument (highest priority).
    2. edge_manifest.json found alongside the DXF patterns (auto-generated).
    3. DEFAULT_SEAMS fallback (only if allow_seam_fallback=True; P08).

    Parameters
    ----------
    allow_seam_fallback : bool
        If False, raise SeamManifestError instead of silently falling back to
        DEFAULT_SEAMS when the manifest is missing or incomplete (P08).
    strict_seam_hash : bool
        If True, step_09 requires a non-empty geometry hash baseline (P07).
    strict_dxf_units : bool
        If True, step_04 aborts when DXF units cannot be determined (P10).
    use_default_panels : bool
        If True, patterns_dir is overridden to clo_vto/default_panels/dxf/.
        Texture artifact paths are derived from ingestion_output_dir instead
        of from patterns_dir. Decouples VTO from panel generation.
    ingestion_output_dir : Path | str | None
        Root directory of the product ingestion run output (contains
        image_info/ and panels/). Only used when use_default_panels=True.
    """
    output_dir = package_root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    project_dir = output_dir / "projects"
    project_dir.mkdir(parents=True, exist_ok=True)

    if avatar_path:
        avatar_path = Path(avatar_path).resolve()
    else:
        avatar_path = _discover_default_native_avatar().resolve()

    if use_default_panels:
        patterns_dir = (_DEFAULT_PANELS_DIR / "dxf").resolve()
        print(f"  [DEFAULT PANELS MODE] patterns_dir → {patterns_dir}")
    elif patterns_dir:
        patterns_dir = Path(patterns_dir).resolve()
    else:
        patterns_dir = Path(resolve_patterns_dir()).resolve()

    if ingestion_output_dir:
        ingestion_output_dir = Path(ingestion_output_dir).resolve()

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
                # P08: manifest present but incomplete — fallback only if allowed.
                if not allow_seam_fallback:
                    raise SeamManifestError(
                        "Edge manifest found but incomplete and allow_seam_fallback=False. "
                        "Regenerate panels to produce a valid edge_manifest.json."
                    )
                resolved_seams = DEFAULT_SEAMS
                print("  WARNING: Edge manifest found but incomplete — using DEFAULT_SEAMS.")
        else:
            # P08: no manifest at all — fallback only if allowed.
            if not allow_seam_fallback:
                raise SeamManifestError(
                    "No edge_manifest.json found and allow_seam_fallback=False. "
                    f"Expected at: {patterns_dir.parent / 'edge_manifest.json'}"
                )
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
        strict_seam_hash=strict_seam_hash,
        strict_dxf_units=strict_dxf_units,
        use_default_panels=use_default_panels,
        default_panels_dir=_DEFAULT_PANELS_DIR if use_default_panels else None,
        ingestion_output_dir=ingestion_output_dir,
    )
    return ctx
