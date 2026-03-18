"""Pipeline context object and initializer."""

from dataclasses import dataclass, field
from pathlib import Path

from .client import CLORestClient
from .helpers import resolve_patterns_dir
from .seams import DEFAULT_SEAMS


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


def create_context(seam_map=None):
    """Build a pipeline context with default paths and seam map."""
    workspace_root = Path(__file__).resolve().parents[3]
    output_dir = workspace_root / "clo_workspace/exports"
    output_dir.mkdir(exist_ok=True)
    project_dir = workspace_root / "clo_workspace/projects"
    project_dir.mkdir(exist_ok=True)

    using_default_seams = seam_map is None

    return PipelineContext(
        client=CLORestClient(),
        workspace_root=workspace_root,
        avatar_path=workspace_root / "pipeline_star/generated/clo_avatars/user_m_001_001_avatar.obj",
        patterns_dir=resolve_patterns_dir(),
        output_dir=output_dir,
        project_dir=project_dir,
        pattern_files=[
            "front_panel.dxf",
            "back_panel.dxf",
            "sleeve_left.dxf",
            "sleeve_right.dxf",
        ],
        seams=seam_map if seam_map else DEFAULT_SEAMS,
        using_default_seams=using_default_seams,
    )
