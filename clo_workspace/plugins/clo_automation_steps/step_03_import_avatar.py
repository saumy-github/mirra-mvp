"""Step 3: Import avatar mesh."""

from .helpers import print_result


def run(ctx):
    print("\n[3] Importing avatar ...")
    if not ctx.avatar_path.exists():
        print(f"  ! Avatar not found: {ctx.avatar_path}")
        print("  ! Simulation will be SKIPPED - CLO crashes without a body mesh.")
        print("  ! Generate an avatar OBJ via avatar_generation/run_avatar.py first.")
        ctx.avatar_loaded = False
    else:
        print_result(ctx.client.import_avatar(str(ctx.avatar_path)), "import-avatar")
        ctx.avatar_loaded = True

    ctx.client.wait_for_queue(timeout=30)
    return True
