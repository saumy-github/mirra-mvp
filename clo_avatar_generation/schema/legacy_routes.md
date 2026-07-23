# Legacy Measurement Apply Routes — `csv` and `avatar_properties`

**Status**: Not maintained. Kept only for historical/experimental reference.
`avt_patch` is the only supported measurement apply route.

Both routes below require passing `--enable-legacy-route` alongside
`--apply-mode csv` or `--apply-mode avatar_properties` in
`run_avatar.py`. Without that flag the pipeline refuses to start. There is
no interactive prompt for either route — they are reachable via CLI flags
only.

---

## `csv` — never worked

Uses CLO's `/import-avatar-measurements` API with a 2-row CSV bridge file
(header + values), seeded from
`schema/measurement_template_unconfirmed.csv`.

**Runs that used it**: 001–006 (implicit/early), 011 (explicit).

**What happened**: failed every time. Runs 001–006 collapsed before step 8
even ran. Run 011 reached step 8 and the route explicitly returned
`success: false` — the CSV template's column names didn't match what CLO
expected internally.

**Verdict**: broken from the start, never produced a morphed avatar in any
run.

---

## `avatar_properties` — misleadingly "successful", proven non-functional

Uses CLO's live-editing API: `POST /avatar/set-properties`
(`UTILITY_API->SetAvatarProperties`) to change an already-loaded avatar's
properties in place, confirmed via `GET /avatar/property-debug`
(`UTILITY_API->GetAvatarProperties`).

**Runs that used it**: 007, 009, 010 (full 6-field test), plus an isolated
single-field test via `after-1-jun/scripts/manual_height_probe.py`.

**What happened**:

- Runs 007/009/010 all returned `"success": true` at every layer (HTTP 200,
  no thrown errors), but `GetAvatarProperties` immediately afterward showed
  `confirmed_changed_property_count: 0` and `changed_keys: []` — none of the
  6 requested body-measurement keys (`Total Height`, `Chest`, `Waist`,
  `Low Hip`, `Inseam`, `Across Shoulder (Curvilinear)`) even appeared in the
  property map CLO returned. Only physics/simulation properties
  (`DivideMesh`, `KineticFriction`, `SkinOffsetMM`, `SoftBodySimulation`,
  `StaticFriction`) were ever present. This was a **false positive** — the
  pipeline marked these runs `"completed"` before binary verification
  existed to catch the discrepancy. The avatar was never actually morphed.
- `manual_height_probe.py` isolated a single field (`"Total Height":
  "130.00"` on an otherwise default base avatar) to rule out a multi-field
  interaction. Result: the request was accepted and queued, but
  `GET /status` polling never saw `queue_processing` return to `false` —
  stuck for 30+ seconds. The plugin's queue-draining background thread got
  stuck handling this command, though CLO's UI itself remained responsive.
  The avatar's height did not visibly change. This is a **worse** failure
  mode than the earlier three runs: it can leave the plugin's entire
  command queue permanently stuck for the rest of that CLO session, since
  every command type shares one `g_queueProcessing` reset point.

**Root cause**: `SetAvatarProperties`/`GetAvatarProperties` operate on a
different property namespace than body shape. Every live readback across
every test only ever surfaces physics/render/simulation settings — body
measurement keys never appear, regardless of field count or which field is
isolated. This looks like a structural limitation of this CLO SDK version
(v2025.2.368), not a formatting/key-naming bug on our side (key names match
CLO's own Avatar Editor UI labels exactly).

**Verdict**: does not, and structurally cannot as currently used, control
body measurements. Additionally has a demonstrated ability to hang the
plugin's command queue. Not safe to use outside of deliberate, isolated
research into a different CLO SDK interface.

Full detail: `after-1-jun/properties-route-investigation.md` and
`after-1-jun/scripts/results.md`.
