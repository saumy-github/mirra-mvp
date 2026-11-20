# 49 - plugin_crash_trace.log analysis (lane BA)

*Status: complete. Data: `clo_workspace/logs/plugin_crash_trace.log`, read-only, streamed by `scripts/crash_trace_summary.py`. Raw output: `out/crash_trace_summary.txt`. Run: `python scripts/crash_trace_summary.py`.*

## Totals (file read at 293,052 lines; the log is still growing)
* BEGIN 907, END 898, difference 9. All 9 unmatched BEGINs match the list in findings/17 section 5.2:
  * 3x `clear-avatars`: lines 44724 (tid 25468), 45250 (tid 18732), 45294 (tid 23260).
  * 6x `import-avatar-avt`: lines 278065 (tid 15948), 278082 (7044), 278127 (9088), 278178 (9904), 281024 (24728), 287602 (21528).
* Command mix (BEGINs): import-avatar-avt 474, export 209, create-seam 100, import-pattern 46, set-fabric-color 36, set-fabric-texture 32, grading-avatar-size 5, clear-avatars 5.
* 68 CLO process sessions (new `g_cloMainWnd discovered`).
* "host CLO version differs" warning: 4 occurrences, lines 278158, 278180, 281008 (CLO 2026.1.310 host vs 224 SDK) and **291243** (CLO 2026.1.336 host vs 224 SDK, 14:55:04). "built against SDK folder" lines: 28 total, the last two being 291242 (224 SDK, host 336) and **291287** (336 SDK, host 336, 15:08:12).
* Note: the SDK/warning lines are logged just BEFORE the `discovered` line of the same start, so they belong to the session that follows them (the script handles this).

## Older sessions vs the 9 crashes
* Every unmatched BEGIN is followed by a new tid within the same line range, i.e. CLO died (or was killed) inside that command. Each of those sessions has 0 completed commands and ends at that BEGIN.
* The 278xxx cluster (CLO 310 host, 224 SDK) shows the version-differs warning on 3 starts, and 2 of the 6 import crashes (278178, tid 9904; 281024, tid 24728 occurs in the session started right after warning at 281008) sit in warned sessions. The crashes at 278065/278082/278127 occurred before the warning code existed in the plugin (no SDK lines yet). The one at 287602 occurred with host == SDK == 224 (no warning), so a version mismatch is not the only cause of an import-avatar-avt crash (that one imports a library avatar `FV...` from `CLO Assets`, not a patched .avt).
* Healthy comparison: with matched 224/224 (lines 281025 to 287041) there are 156+ completed commands in one session (tid 4236, ~16h34m wall span) and no crash; session tid 3268 (lines 287606-291246, host-224 SDK at start) completed 352 commands with 0 unmatched and 0 success=false.

## The 336 plugin (installed 2026-10-29 15:06)
* Session #66 (line 291246, 14:55:04, tid 18656): OLD 224 plugin on a 336 host. Version-differs warning present. 0 commands, no BEGIN at all, ended at 15:07:18 with `g_cloMainWnd is no longer a valid window` (CLO closed normally enough; the plugin was swapped).
* Session #67 (line 291290, 15:08:13, tid 3716) = first and only session of the 336 plugin: `built against SDK folder CLO_SDK_v2026.1.336_Win ... host CLO app is 2026.1.336`, **no version-differs warning**, no unmatched BEGINs. REST server thread started (`svr.listen(127.0.0.1, 50505)`), heartbeats continue every ~20 s with `serverRunning=true`, last tick 175801 at 01:04 (next day).
* **It ran zero commands.** 0 BEGIN, 0 END, 0 `ProcessCommandQueue returned normally` lines. The 9h56m wall span (15:08 to ~01:04) is idle heartbeat only.

## Verdict
The 336 plugin has loaded cleanly (no warning, no crash, process still alive and heartbeating at the end of the file) but has **not been exercised**: there is no evidence either way about whether `import-avatar-avt` / `clear-avatars` still crash under it. "No unmatched BEGINs" is trivially true because there are no BEGINs. The decisive test (an `import-avatar-avt` of a patched .avt, then `clear-avatars`) has not run in the log yet.

## What the data cannot tell
* No dates: lines carry only local `HH:MM:SS`. Day boundaries are only inferred from clock wrap (e.g. 00:03:50 at line 287603 after 23:36:46). The user-supplied 15:06 install time on 2026-10-29 and "last modified ~20:22" cannot be verified from the content; the file's tail is at 01:04, so it was apparently written after midnight (the file was observed larger than the ~291k lines cited in findings/17 (293,052 now)).
* Durations are wall-clock deltas BEGIN to END, 1 s resolution, modulo 24 h; session spans are first line to last line and include idle time.
* A missing END proves the process stopped writing, not why (crash vs kill vs user closing CLO mid-command).
* Whether CLO is still running now, and whether the REST server actually accepted any HTTP request (REST requests produce BEGIN only when queued to the CLO thread).
