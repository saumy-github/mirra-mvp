"""Step 2: Create a new CLO project."""

import time

from .helpers import print_result

# CLO keeps working internally after a command returns — wait_for_queue only
# proves the SDK call returned, not that the engine finished. Without a pause
# here, new-project runs while the previous run is still writing and silently
# fails to clear the scene, leaving the avatar imported by step 3 as the
# second one in the scene. Measured in step 1 (doc 11 Part 4): five
# back-to-back runs with no gap left 3,4,1,1,2 avatars; the same five with a
# gap left 3,1,1,1,1. Same constant as avatar_runtime's step_07.
CLO_SETTLE_SECONDS = 4.0


def run(ctx):
    print("\n[2] New project ...")

    # Let whatever ran before us finish before asking CLO to clear the scene.
    try:
        ctx.client.wait_for_queue(timeout=30)
    except Exception as exc:
        print(f"  [WARN] Pre-clear drain timed out ({exc}) — proceeding.")
    print(f"  Settling {CLO_SETTLE_SECONDS:.1f}s before new project ...")
    time.sleep(CLO_SETTLE_SECONDS)

    ok = print_result(ctx.client.new_project(), "new-project")

    try:
        ctx.client.wait_for_queue(timeout=30)
    except Exception as exc:
        print(f"  [WARN] new-project queue drain timed out ({exc}) — CLO may still be resetting.")
    # And let the clear itself complete before anything is imported.
    time.sleep(CLO_SETTLE_SECONDS)

    count = ctx.client.get_avatar_count()
    if count > 0:
        print(f"  [WARN] {count} avatar(s) still in the scene after new-project.")
        print("         step_03 will fail the run if this does not resolve to exactly 1 after import.")
    elif count == 0:
        print("  Scene is clear (0 avatars).")

    return ok  # gate only on whether the command was accepted, not on drain
