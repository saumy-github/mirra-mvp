# 54 - Live AVS targeting test stopped by modal dialog

*Status: blocked safely. Supervised live test stopped before the first avatar
import completed; no dialog was dismissed automatically.*
*Date: 2026-11-10*

## Test

Experiment: `experiments/e01_avs_single_avatar.py`

Inputs:

- Avatar A: `clo_avatar_generation/input/base-1.avt`
- Avatar B: `clo_avatar_generation/input/female_research/random-weight-female.avt`
- AVS: `clo_avatar_generation/input/CLO_Male_Default.avs`
- Import method: `import_avatar`

The test passed the initial health/capability/status checks and successfully
cleared the scene to zero avatars. The first `import-avatar-avt` then failed to
settle within the 90-second queue timeout.

Recorder output:

`experiments/out/e01_avs_single_avatar_20261110_225947.json`

## State after timeout

Read-only checks showed:

- `/health`: `status=ok`, `host_matches_sdk=true`, host and SDK 2026.1.336.
- `/status`: `queue_processing=true`, `queue_size=0`.
- `/avatars/state`: timed out because the CLO main thread was busy.
- Watchdog: CLO main window disabled; one visible owned Qt popup detected.
- The popup class was `Qt6103QWindow`; its title was the same as the main
  window. The watchdog cannot read Qt message-box body text.

No automatic close, Escape, or button click was attempted because the dialog
text and button semantics were not established. No further REST command was
queued.

Computer Use was unavailable in the unattended session, so the Qt dialog could
not be inspected visually. The watchdog cannot expose the dialog body text.

## Interpretation

Observed:

1. The 336 plugin and CLO process remain alive.
2. The first avatar import can enter a modal-blocked state with this fixture
   and import method.
3. The current queue watchdog correctly identifies the stuck main-thread state.

The user supplied a screenshot of the popup. Its message is:

`Failed to read the Avatar file. Unzip error.Unzip error., log=, free disk space=11 GB`

The dialog offers `OK` and `Cancel`. This identifies the immediate blocker as
an AVT unzip/read failure, with CLO also reporting only 11 GB free disk space;
it is not an avatar-category or `.avs` targeting prompt.

Unknown:

1. Whether the unzip failure is caused by the source AVT, the generated test
   archive, or the low-free-space condition.
2. Whether `import_file` would avoid the same prompt.
3. Whether the original source AVT is valid for this CLO build.

Required next action is manual inspection of the visible CLO popup and a
human-selected response. Until that is done, do not send another command to
the plugin or run another live experiment.

## Reproduction with re-packed AVT

After the user supplied the popup text, the original source AVT was re-packed
with the repository's stdlib-only AVT preparation path and copied to
`experiments/out/e02/baseA.avt`. A second `e01` run used this re-packed file
as avatar A. The import again timed out with the same Qt popup shape; the
watchdog again observed a disabled main window and a single `Qt6103QWindow`
popup. Closing the popup returned the queue to idle and `/status` reported:

`Failed to import native avatar template: rev-eng/experiments/out/e02/baseA.avt`

This rules out the original source path/layout as the only cause. The popup's
reported free space was approximately 11 GB in both attempts, so available
disk space or CLO's temporary extraction requirement is now the primary
environmental blocker. No third mutation was attempted.
