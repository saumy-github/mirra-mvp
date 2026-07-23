"""Step 2: Create a new CLO project."""

from .helpers import print_result


def run(ctx):
    print("\n[2] New project ...")
    # Queue the command and move on immediately — CLO wipes all existing state
    # when it processes new-project.  The drain is best-effort only; subsequent
    # steps do their own waits so this step must never gate on queue drain.
    ok = print_result(ctx.client.new_project(), "new-project")
    try:
        ctx.client.wait_for_queue(timeout=30)
    except Exception as exc:
        print(f"  [WARN] new-project queue drain timed out ({exc}) — CLO may still be resetting; proceeding.")
    return ok  # gate only on whether the command was accepted, not on drain
