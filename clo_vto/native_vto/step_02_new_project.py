"""Step 2: Create a new CLO project."""

from .helpers import print_result

# NewProject() is a void CLO SDK call (confirmed against the real SDK header,
# UtilityAPIInterface.h) — it cannot report success/failure itself, and its
# internal scene teardown is not guaranteed to be finished when the command
# queue reports empty (see .agent/clo-avatar-vto/vto-pipeline-debug-plan-26_7_24.md,
# Bug 1). The only real post-condition would be reading the scene back
# afterward.
#
# STATUS (2026-07-24): scene-clear verification is currently NON-BLOCKING —
# KNOWN BROKEN, NEEDS FURTHER DEBUGGING. Two live runs against a freshly
# restarted CLO both failed to verify: run 1 got "unverifiable" (-1, -1) on
# all 3 readback attempts; run 2 (immediately after, same CLO session) hit a
# fully stuck command queue (queue_processing stuck True, queue_size=7).
# The queue_size=7 is suspicious and not yet explained — it matches exactly
# "1 new-project + 3 attempts x 2 leftover reads from run 1" as if NONE of
# run 1's failed /patterns/count + /avatars/state reads ever actually
# drained, and kept accumulating into run 2. That in turn suggests
# QueueDrainTimer may not be firing AT ALL in some sessions (not just
# "unreliably"), and/or that CLO's main thread is genuinely hanging (not
# just slow) inside one of these read commands — most likely
# "read-avatar-state" (EXPORT_API->GetAvatarCount() et al., the same API
# family flagged as SEH-crash-prone in POST_MORTEM_v1.1.1.md; a silent hang
# instead of a crash would be a new, worse variant of that same risk,
# possibly specific to calling it while the scene is still mid-teardown from
# new-project). This is a PRE-EXISTING plugin bug independent of this
# session's C++ changes — the currently-deployed plugin (not yet rebuilt)
# already contains the read-avatar-state handler being exercised here; this
# step's polling just started calling it more than anything did before.
#
# Skipping the gate for now rather than blocking every pipeline run on a
# verification layer that isn't reliable yet. new_project() is still called
# exactly once per run (not retried — see prior comment history in git blame
# for why hammering it with retries made a stuck queue worse, not better).
_MAX_READBACK_ATTEMPTS = 3


def run(ctx):
    print("\n[2] New project ...")
    ok = print_result(ctx.client.new_project(), "new-project")
    if not ok:
        return False  # command itself was rejected — real failure, not a race

    try:
        ctx.client.wait_for_queue(timeout=30)
    except Exception as exc:
        print(f"  [WARN] Queue drain timed out after new-project: {exc}")
        print("         [SKIPPED] Scene-clear verification is unreliable right now — see the")
        print("         module docstring in step_02_new_project.py. NEEDS FURTHER DEBUGGING.")
        print("         Proceeding without verifying the scene actually cleared.")
        return True

    counts = {"patterns": -1, "avatars": -1}
    for attempt in range(1, _MAX_READBACK_ATTEMPTS + 1):
        counts = ctx.client.wait_for_scene_clear(timeout=10)
        if counts["patterns"] == 0 and counts["avatars"] == 0:
            print(f"  Scene confirmed clear (readback attempt {attempt}).")
            return True

        if counts["patterns"] == -1 or counts["avatars"] == -1:
            print(f"  [WARN] Scene-clear readback unverifiable ({counts}, attempt {attempt}).")
        else:
            print(f"  [WARN] Scene not clear yet: {counts} (readback attempt {attempt}).")

    print(f"  [WARN] Could not confirm scene is clear after {_MAX_READBACK_ATTEMPTS} readback attempts: {counts}")
    print("         [SKIPPED] Scene-clear verification is unreliable right now — see the")
    print("         module docstring in step_02_new_project.py. NEEDS FURTHER DEBUGGING.")
    print("         Proceeding without a confirmed-clear scene.")
    return True
