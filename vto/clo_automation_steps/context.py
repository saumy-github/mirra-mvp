"""Pipeline context object and initializer."""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

workspace_root = Path(__file__).resolve().parents[2]
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from avatar_generation.run_manifest import get_latest_avatar_obj_path
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


def create_context(seam_map=None, avatar_path: Optional[Union[Path, str]] = None, patterns_dir: Optional[Union[Path, str]] = None):
    """Build a pipeline context with default paths and seam map.

    Optional `avatar_path` and `patterns_dir` can be provided to force inputs
    from a previously-created `vto/input/<run>/input.json` selection.
    """
    output_dir = workspace_root / "clo_workspace/exports"
    output_dir.mkdir(exist_ok=True)
    project_dir = workspace_root / "clo_workspace/projects"
    project_dir.mkdir(exist_ok=True)

    using_default_seams = seam_map is None

    if avatar_path:
        avatar_path = Path(avatar_path)
    else:
        try:
            avatar_path = Path(get_latest_avatar_obj_path())
        except FileNotFoundError:
            avatar_path = workspace_root / "avatar_generation" / "output" / "u_001-001" / "avatar.obj"

    if patterns_dir:
        patterns_dir = Path(patterns_dir)
    else:
        patterns_dir = resolve_patterns_dir()

    return PipelineContext(
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
        seams=seam_map if seam_map else DEFAULT_SEAMS,
        using_default_seams=using_default_seams,
    )
