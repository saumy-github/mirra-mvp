"""Step 10b: save the simulated scene as a .zprj.

Saved on every run by decision (doc 13, D5) — a failed try-on can then be
reopened in CLO. It also gives VTO the same avatar-count check step 1 uses,
by reading .avt members straight out of the archive.
"""

from __future__ import annotations

import time
import zipfile
from pathlib import Path

from .helpers import print_result

# CLO's internal mesh rebuild after simulation isn't tracked by our command
# queue, so save-project can race it. Same mitigation as avatar_runtime's
# step_11 (MESH_SETTLE_DELAY_SECONDS).
SAVE_SETTLE_SECONDS = 2.5


def count_project_avatars(zprj_path: Path) -> list[str]:
    """.avt members in the saved project. Exactly one is the healthy case."""
    if not zipfile.is_zipfile(zprj_path):
        return []
    with zipfile.ZipFile(zprj_path, "r") as archive:
        return [m for m in archive.namelist() if Path(m).suffix.lower() == ".avt"]


def run(ctx) -> bool:
    print("\n[10b] Saving project ...")

    zprj_path = ctx.output_dir / "simulation.zprj"
    print(f"  output_path : {zprj_path}")

    try:
        ctx.client.wait_for_queue(timeout=120)
    except Exception as exc:
        print(f"  [WARN] Pre-save drain timed out: {exc} — proceeding.")
    time.sleep(SAVE_SETTLE_SECONDS)

    ok = print_result(ctx.client.save_project(zprj_path), "save-project")
    if not ok:
        print("  [WARN] CLO rejected save-project — continuing without a project file.")
        return True

    try:
        ctx.client.wait_for_queue(timeout=120)
    except Exception as exc:
        print(f"  [WARN] Save drain timed out: {exc} — checking file anyway.")

    if not zprj_path.exists():
        print(f"  [WARN] Project not found at {zprj_path} after save.")
        return True

    ctx.zprj_path = zprj_path
    size_mb = zprj_path.stat().st_size / (1024 * 1024)
    print(f"  [OK] Project written — {size_mb:.1f} MB")

    avatars = count_project_avatars(zprj_path)
    ctx.project_avatars = avatars
    if len(avatars) == 1:
        print("  [OK] Project holds exactly 1 avatar.")
    elif not avatars:
        print("  [WARN] Project holds no .avt member — could not verify the avatar count.")
    else:
        print(f"  ! Project holds {len(avatars)} avatars: {avatars}")
        print("    The simulation may have draped onto the wrong body. Restart CLO and rerun.")
        return False

    return True
