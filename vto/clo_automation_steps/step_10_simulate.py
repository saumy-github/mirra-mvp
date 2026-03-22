"""Step 10: Run physics simulation."""

from .helpers import print_result


def run(ctx):
    print("\n[10] Running physics simulation (150 steps) ...")
    if not ctx.avatar_loaded:
        print("  ! Skipping simulation - no avatar loaded (would crash CLO).")
        return True

    print_result(ctx.client.simulate(steps=150), "simulate")
    print("     Waiting for simulation to complete ...")
    ctx.client.wait_for_queue(timeout=300)
    return True
