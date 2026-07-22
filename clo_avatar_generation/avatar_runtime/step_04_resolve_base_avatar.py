"""Step 4: resolve and validate the fixed base avatar for the run."""

from __future__ import annotations

from pathlib import Path
import zipfile

from .context import Step1Context
from .field_contract import get_default_base_avatar


REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_candidate(base_avatar_path_input: str | None) -> Path:
    if base_avatar_path_input:
        return Path(base_avatar_path_input).expanduser().resolve()

    default_relative = get_default_base_avatar()
    if default_relative.is_absolute():
        return default_relative
    return (REPO_ROOT / default_relative).resolve()


def run(ctx: Step1Context) -> bool:
    candidate = _resolve_candidate(ctx.base_avatar_path_input)
    ctx.logger.info("Resolving base avatar: %s", candidate)
    if not candidate.exists():
        raise FileNotFoundError(f"Base avatar not found: {candidate}")
    if candidate.suffix.lower() != ".avt":
        raise ValueError(f"Base avatar must be a .avt file: {candidate}")
    if not zipfile.is_zipfile(candidate):
        raise ValueError(f"Base avatar is not a valid CLO avatar package: {candidate}")

    companion_files: dict[str, str] = {}
    for suffix in (".arr", ".iks", ".avs", ".mea"):
        companion = candidate.with_suffix(suffix)
        if companion.exists():
            companion_files[suffix.lstrip(".")] = str(companion)

    ctx.base_avatar_path = candidate
    ctx.base_avatar_metadata = {
        "path": str(candidate),
        "name": candidate.name,
        "size_bytes": candidate.stat().st_size,
        "companion_files": companion_files,
    }

    ctx.input_payload["base_avatar"] = ctx.base_avatar_metadata
    ctx.log_json("input", ctx.input_payload)
    ctx.logger.info("Base avatar resolved: %s (%d bytes)", candidate.name, candidate.stat().st_size)
    return True

