# 014 Plan: Validate Queue Timer Reduction Before Cross-Platform Rollout

## Goal

Reduce the plugin queue-drain timer from `500ms` to `50ms` only after we have
evidence that it does not introduce regressions in the current CLO workflow.

This plan covers both:
- Windows plugin validation first
- macOS parity only after Windows passes

For today, the active working assumption remains:
- current plugin behavior stays at `500ms`
- current implementation and testing should use the existing built plugin

## Why This Needs Its Own Plan

Reducing the queue timer sounds small, but it changes how often the plugin
wakes up on CLO's main thread.

That means we need to validate that the change does **not** cause issues such
as:
- duplicate queue processing
- re-entry problems while commands are still running
- UI responsiveness problems inside CLO
- unexpected behavior in long or bursty command sequences
- differences between Windows and macOS plugin behavior

Because the new plugin has not been built and installed yet, today's work
should continue assuming the current `500ms` plugin only.

## Current Decision

The timer-reduction code change should not stay active in the repo while we are
still working against the current installed `500ms` plugin.

So the immediate decision is:

1. keep the repo aligned with the current `500ms` plugin behavior
2. do today's feature work using the existing plugin timing
3. treat `50ms` as a separate validation task
4. only roll it out cross-platform after Windows validation succeeds

## Scope

This plan is concerned with:
- `clo_workspace/`
- `clo_avatar_generation/`
- downstream verification paths that depend on the plugin queue behavior

This plan is not about changing avatar-dimension logic itself.

## Phase 1: Establish The `500ms` Baseline

Before trying `50ms`, we should document the current known-good behavior of the
existing `500ms` plugin.

Baseline checks should include:
- Step-1 avatar flow in `clo_avatar_generation/`
- command queue pickup behavior during normal use
- long-running command execution behavior
- native VTO flow behavior where plugin queueing is involved
- any visible lag, stuck queue, or repeated command symptoms

The purpose of this phase is to make sure later comparisons are based on the
same workflow and not on memory.

## Phase 2: Windows-Only `50ms` Experiment

After today's work is complete and we are ready to build a new plugin, we
should test the timer reduction on Windows only first.

Implementation direction:
- change the Windows queue-drain timer from `500ms` to `50ms`
- build and install the new Windows plugin
- keep all other flow assumptions unchanged during validation

Validation focus:
- queue still drains correctly
- commands are not executed twice
- commands are not skipped
- queue-processing guard still prevents overlap/re-entry
- CLO remains responsive while idle and during active command bursts
- HTTP endpoints still behave as expected when the queue is empty or busy

## Phase 3: End-To-End Workflow Validation On Windows

The `50ms` Windows plugin should be tested against the real workflow, not only
against isolated plugin endpoints.

Validation runs should include:
- current avatar-generation flow in `clo_avatar_generation/`
- repeated command submissions
- multi-step queued operations
- failure-path handling when a queued command errors
- save/export steps after queued work completes

If the current flow behaves exactly as before, with no regressions and better
pickup latency, the Windows side can be considered safe.

## Phase 4: Decide Whether Client Polling Also Needs Adjustment

The queue timer is only one part of observed responsiveness.

Even if plugin pickup becomes faster, end-to-end waits may still look slow if
the Python clients continue polling status on a slower interval.

So after Windows validation, we should separately decide:
- whether the timer change alone is enough
- whether client polling intervals should also be reduced
- whether those should be handled in this same rollout or in a follow-up task

This should remain a separate decision from the plugin timer change itself.

## Phase 5: macOS Parity Rollout

Only after the Windows `50ms` change is validated should we make the same
change in the macOS plugin.

macOS rollout rules:
- copy the behavior intentionally, not approximately
- keep the endpoint contract aligned with Windows
- verify that queue-drain semantics remain the same across platforms
- confirm that the macOS plugin does not introduce platform-specific timing
  regressions

The macOS change should be treated as a parity step, not as an unvalidated
parallel experiment.

## What We Need To Watch Closely

The main risks to monitor are:
- main-thread wakeups becoming too frequent
- busy-idle CPU cost increasing
- hidden race conditions appearing more often
- status endpoints reporting misleading queue state during fast drains
- flows that used to appear stable at `500ms` becoming flaky at `50ms`

If any of these appear, the rollout should pause and the timer should stay at
`500ms`.

## Success Criteria

This plan is successful when:

1. today's work is completed using the current `500ms` plugin
2. Windows `50ms` behavior is validated against the current real workflow
3. no queue correctness or stability regressions are found on Windows
4. the macOS plugin is updated only after Windows validation passes
5. both platforms end up with the same intended timer behavior
6. any related client-polling follow-up is tracked explicitly instead of being
   mixed into the timer change by accident

## Notes

- This plan intentionally separates validation from implementation.
- It is acceptable for the repo and the installed plugin to stay at `500ms`
  during today's work.
- The timer reduction should be treated as an optimization rollout, not as a
  prerequisite for the current avatar-dimension task.
