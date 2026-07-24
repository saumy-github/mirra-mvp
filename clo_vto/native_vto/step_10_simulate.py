"""Step 10: Run physics simulation."""

from .helpers import ensure_avatar_visible_checked, print_result


def run(ctx):
    print("\n[10] Running physics simulation (150 steps) ...")
    if not ctx.avatar_loaded:
        print("  ! Skipping simulation - no avatar loaded (would crash CLO).")
        return True

    # Bug 2/3 fix: Simulate() is documented synchronous in the CLO SDK — if it
    # reports success but nothing visibly drapes, the leading hypothesis is
    # that the avatar was invisible (no collision body for the cloth solver
    # to settle onto), not that the call itself silently failed. Confirm
    # visibility right before simulating rather than assuming step_09's
    # reassertion held. See the debug-plan doc, Bugs 2 and 3.
    print("  Confirming avatar visibility before simulating ...")
    ensure_avatar_visible_checked(ctx, "before_simulate")

    ok = print_result(ctx.client.simulate(steps=150), "simulate")
    if not ok:
        print("  [FAIL] CLO rejected the simulate command.")
        return False

    print("     Waiting for simulation to complete (up to 5 min) ...")
    try:
        ctx.client.wait_for_queue(timeout=300)
        print("     Simulation complete.")
    except Exception as exc:
        print(f"  [WARN] Simulation drain timed out: {exc}")
        print("         Simulation may still be running inside CLO — check the CLO window.")
    return True
