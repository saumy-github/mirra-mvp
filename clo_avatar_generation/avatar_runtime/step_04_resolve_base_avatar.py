"""Step 4: resolve and validate the base avatar for the run (per gender, see the
contract's `base_avatars`; an explicit --base-avatar always wins)."""

from __future__ import annotations

from pathlib import Path
import zipfile

from .context import Step1Context
from .field_contract import get_base_avatar_for_gender


REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_candidate(base_avatar_path_input: str | None, gender: str) -> Path:
    if base_avatar_path_input:
        return Path(base_avatar_path_input).expanduser().resolve()

    default_relative = get_base_avatar_for_gender(gender)
    if default_relative.is_absolute():
        return default_relative
    return (REPO_ROOT / default_relative).resolve()


def run(ctx: Step1Context) -> bool:
    gender = str((ctx.mongo_doc or {}).get("gender", "")).strip().lower()
    candidate = _resolve_candidate(ctx.base_avatar_path_input, gender)
    ctx.logger.info("Resolving base avatar for gender=%s: %s", gender or "?", candidate)
    if not candidate.exists():
        if gender == "female" and not ctx.base_avatar_path_input:
            raise FileNotFoundError(
                f"Female base avatar not installed at {candidate}. Copy CLO's stock Female V2 avatar "
                "(e.g. <CLO assets>/Avatar/Female_V2/FV2_Feifei.avt) there — see the contract's female_note."
            )
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

