# Properties Route Investigation — `avatar_properties` (live CLO editing)

**Status**: Closed. Confirmed non-viable for body measurements — not a bug to
keep chasing, a structural limitation of the API being used.
**Decision**: Proceed exclusively with the `avt_patch` route going forward.
This corresponds to Phase 3.2 of `plan-02.md`.

---

## What this route is

`avatar_properties` is the "live editing" route: instead of writing values
into the `.avt` file before CLO ever sees it (the `avt_patch` route), it asks
CLO's own SDK to change an already-loaded avatar's properties in place, via:

- `POST /avatar/set-properties` → plugin calls `UTILITY_API->SetAvatarProperties(avatarIndex, propertyMap)`
- `GET /avatar/property-debug` → plugin calls `UTILITY_API->GetAvatarProperties(avatarIndex)` to confirm

SDK signatures (from `UtilityAPIInterface.h`, CLO SDK v2025.2.368):
```cpp
void SetAvatarProperties(unsigned int avatarIndex, const std::map<std::string, std::string>& avatarPropertyMap);
std::map<std::string, std::string> GetAvatarProperties(unsigned int avatarIndex);
```

---

## Timeline of every test run against this route

### Early exploration (measurement-method-experiments.md, "Method 6")
Before this route was ever installed/tested live, the plugin code for it was
written and compiled locally. At that point the only known risk was already
flagged in advance: a live readback via `/avatars/state` showed
`GetAvatarProperties` exposing only generic properties —
`DivideMesh`, `KineticFriction`, `SkinOffsetMM`, `SoftBodySimulation`,
`StaticFriction` — never any body-measurement key. This turned out to
predict exactly what every subsequent live test confirmed.

### Runs `u_001-007`, `u_001-009`, `u_001-010` — full 6-field test, live CLO
All three runs sent the same request: all 6 mapped fields at once
(`Total Height`, `Chest`, `Waist`, `Low Hip`, `Inseam`,
`Across Shoulder (Curvilinear)`), unit `cm`. All three produced **identical**
results:

```json
"requested_property_count": 6,
"confirmed_changed_property_count": 0,
"changed_keys": [],
"missing_after_keys": [
  "Across Shoulder (Curvilinear)", "Chest", "Inseam",
  "Low Hip", "Total Height", "Waist"
],
"properties_after": {
  "DivideMesh": "...", "KineticFriction": "...", "SkinOffsetMM": "...",
  "SoftBodySimulation": "...", "StaticFriction": "..."
}
```

`SetAvatarProperties` returned without throwing (HTTP 200, `"success": true`
at every layer). But `GetAvatarProperties` immediately afterward shows:
- None of the 6 requested body-measurement keys are even present in the
  property map CLO returns — not "unchanged," **absent entirely**.
- The only keys CLO ever returns are the same 5 physics/simulation settings,
  regardless of what was requested.

The pipeline's own note at the time, written directly into `apply_result.json`:
> "SetAvatarProperties completed, but GetAvatarProperties did not confirm any
> requested key change. Visual validation in CLO is still required."

Because there was no binary-level verification yet at this point in the
project's history, these three runs were initially marked `"success": true`
and `"completed"` at the pipeline level — a **false positive**. The avatar
was never actually morphed. This was only caught in retrospect once
`avt_patch`'s binary readback (`verify_avatar_fields`) existed and could
prove the difference between "API said yes" and "the file actually changed."

### `plan-01.md` Phase 3 — the SEH wrapper's discovery (2026-07-03)
Unrelated to body measurements specifically, but relevant context: the same
`SetAvatarProperties`/`GetAvatarProperties` pair sit in the exact
`ProcessCommandQueue` code path later found to hang (see below) — confirming
this code path is fragile in more than one way, not just "silently wrong."

### `after-1-jun/scripts/manual_height_probe.py` — isolated single-field test (2026-07-03)
Given the earlier tests sent 6 properties together, this test isolated the
variable: send **only** `"Total Height": "130.00"` (base avatar is ~187.96
cm, chosen for an unmistakable visual delta), on an otherwise default,
unmodified base avatar.

Result:
- The request was accepted and queued normally.
- `GET /status` polling never saw `queue_processing` return to `false` —
  stuck `true` for 30+ seconds (the poll timeout), with `queue_size: 0` and
  `last_results: []`, meaning `ProcessCommandQueue()` picked up the command
  and never finished handling it.
- The user confirmed CLO's UI remained fully responsive throughout — not a
  full application freeze. Most likely explanation: the plugin's
  queue-draining code runs on a background thread (registered via
  `SetTimer`), separate from whatever thread renders/handles the interactive
  UI; something in `SetAvatarProperties` left that specific background
  thread stuck, without affecting the rest of the application.
- The avatar's height did not visibly change in the viewport (confirmed via
  screenshot — still default T-pose proportions).
- Full write-up: `after-1-jun/scripts/results.md`.

This is a **new and worse failure mode** than the earlier three runs: not
just "silently doesn't work," but capable of leaving the plugin's entire
command queue permanently stuck for the rest of that CLO session (every
command type shares one `g_queueProcessing` reset point in
`RestPlugin_windows.cpp`, so once one handler fails to return, nothing else
queued will ever run either — see `plan-01.md`'s discussion of this).

---

## Root cause (as far as it can be determined without CLO source access)

`SetAvatarProperties`/`GetAvatarProperties` operate on a **different property
namespace** than body shape. Every live readback, across every test, only
ever surfaces: `DivideMesh`, `KineticFriction`, `SkinOffsetMM`,
`SoftBodySimulation`, `StaticFriction` — physics/render/simulation settings.
Body-measurement keys (`Total Height`, `Chest`, `Waist`, `Low Hip`, `Inseam`,
`Across Shoulder (Curvilinear)`) never appear in `GetAvatarProperties`'
output, before or after a `SetAvatarProperties` call, regardless of how many
fields are requested at once or which single field is isolated. This is not
a matter of wrong value formatting, wrong units, or wrong key spelling (the
key names used match CLO's own Avatar Editor UI labels exactly, per
`avatar-editor-fields-observed.md`) — the API appears to simply not expose
body-shape control at all in this CLO SDK version (v2025.2.368).

This conclusion could only be overturned by finding a *different* SDK
interface that does control body sliders (only `ImportAPIInterface.h`,
`UtilityAPIInterface.h`, and `ExportAPIInterface.h` have been checked so
far) — not by continuing to test `SetAvatarProperties` itself.

---

## Verdict

| Test | Fields | Result |
|---|---|---|
| Runs 007, 009, 010 | All 6 body fields at once | Accepted, 0 confirmed changes, false-positive success |
| `manual_height_probe.py` | `Total Height` alone | Accepted, then plugin command queue stuck indefinitely, no visible change |

Two independent test designs (multi-field and single-field), across two
different points in the project's history, both conclude the same thing:
**`avatar_properties` does not, and structurally cannot as currently used,
control body measurements.** It is not being kept as a fallback route in the
pipeline's apply-mode selection going forward — `avt_patch` is the only
route in active use.

## What this means for `plan-02.md` Phase 3.2

This document satisfies that phase's task and verification criteria:
"either fix properties route OR confirm CLO only supports properties for
physics, not body shape" — confirmed the latter. No further time should be
spent on this route unless a different, not-yet-examined CLO SDK interface
is found that exposes body-shape controls directly.
