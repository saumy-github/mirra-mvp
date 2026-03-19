"""Step 3: Import avatar mesh."""

from .helpers import print_result


def run(ctx):
    print("\n[3] Importing avatar ...")
    if not ctx.avatar_path.exists():
        print(f"  ! Avatar not found: {ctx.avatar_path}")
        print("  ! Simulation will be SKIPPED - CLO crashes without a body mesh.")
        print("  ! Generate an avatar OBJ via pipeline_star/ first.")
        ctx.avatar_loaded = False
    else:
        queued_ok = print_result(ctx.client.import_avatar(str(ctx.avatar_path)), "import-avatar")
        ctx.avatar_loaded = queued_ok

    ctx.client.wait_for_queue(timeout=30)

    if ctx.avatar_loaded:
        status = ctx.client.get_status()
        last_results = status.get("last_results", []) if isinstance(status, dict) else []
        executed = next((r for r in last_results if r.get("type") == "import-avatar"), None)

        if executed is None:
            print("  ! Could not confirm avatar import execution from /status last_results.")
        elif not executed.get("success", False):
            print(f"  ! Avatar import failed during execution: {executed.get('message', 'Unknown error')}")
            ctx.avatar_loaded = False
            return False

    return True
