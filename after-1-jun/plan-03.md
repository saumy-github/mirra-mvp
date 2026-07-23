# Plan 003 — Route Separation, Structured run.log, Health Watchdog (separate phases)

Discussion-phase conclusions, written up for execution. Phases 1–3 are
implemented and verified (route separation, `run.log`, health watchdog).
Phases 4 onward are planned but not yet implemented.

---

## Phase 1 — Separate the 3 measurement routes, default to `avt_patch`

### Goal

Only build the payload artifacts for the route actually being used. Stop
generating `clo_payload.bridge.csv` / `clo_payload.properties.json` on every
run when only `avt_patch` is in active use. `csv` and `avatar_properties`
become opt-in legacy routes gated behind an explicit CLI flag.

### Step 1 — `clo_avatar_generation/schema/legacy_routes.md` (new file)

Consolidate the existing scattered evidence into one reference doc:

- From `after-1-jun/summary-26-06-30-1.md`'s run-history table: `csv` route,
  runs 001–006 and 011 — never worked, failed every attempt.
- From `after-1-jun/properties-route-investigation.md`: `avatar_properties`
  route, runs 007/009/010 (false-positive "success", 0 confirmed property
  changes) and `manual_height_probe.py` (isolated single-field test — hung
  the plugin's entire command queue indefinitely).
- Explicit statement: these two routes are **not maintained**, exist only
  for historical/experimental reference, and require `--enable-legacy-route`
  to invoke. `avt_patch` is the only supported route.

### Step 2 — `clo_avatar_generation/run_avatar.py`

- Add `--enable-legacy-route` (store_true) flag.
- In both interactive and non-interactive paths: if the resolved apply mode
  (explicit `--apply-mode` or default) is `csv` or `avatar_properties` and
  `--enable-legacy-route` was not passed, fail fast with a clear error
  pointing at `clo_avatar_generation/schema/legacy_routes.md`, before the
  pipeline starts.
- No interactive prompt is added for apply-mode selection — CLI-flag-only,
  per your call. Interactive mode keeps defaulting to `avt_patch` silently
  unless `--apply-mode`/`--enable-legacy-route` are passed on the command
  line.
- Default apply mode when nothing is specified becomes `avt_patch`
  explicitly (rather than deferring to `get_preferred_measurement_apply_mode()`
  / `auto`), since `avt_patch` is the only real route now. `auto` stays
  available as a valid explicit choice for anyone who wants the old
  fallback-chain behavior, but is no longer the silent default.

### Step 3 — `clo_avatar_generation/avatar_runtime/context.py`

- Add `ctx.resolved_measurement_apply_mode` resolution earlier than step 8.
  (Field already exists on `Step1Context`; today it's only ever set inside
  `step_08_apply_measurements.run()`.)

### Step 4 — `clo_avatar_generation/avatar_runtime/step_05_normalize_targets.py`

- After building `normalized_targets`, resolve and store
  `ctx.resolved_measurement_apply_mode` here, moving `_resolve_apply_mode`
  out of `step_08_apply_measurements.py` into a shared location (e.g.
  `field_contract.py` or a new small `apply_mode.py`) so both step 5 and
  step 8 call the same function instead of duplicating it.
- **Correction found while checking this against the current code:**
  `_resolve_apply_mode()` as it exists today computes
  `avt_patch_field_count` from `ctx.clo_payload_avt_patch_json` — a field
  that is only populated in step 6 (`_build_avt_patch_payload`), which runs
  *after* step 5. Moving the resolution call as-is into step 5 would read
  an empty dict and always evaluate `has_avt_patch_route = False`, forcing
  every run into the `csv` fallback regardless of `--apply-mode`. The move
  must also change how that check is computed: instead of reading
  `ctx.clo_payload_avt_patch_json`, recompute the count directly from
  `ctx.normalized_targets["flat_requested_fields"]` cross-referenced
  against `get_v1_avt_patch_fields_for_gender(gender)` (the same two
  inputs `_build_avt_patch_payload` itself already uses — step 5 has both
  available since `normalized_targets` is built earlier in that same step).
  `has_property_route` has no such issue — it only reads
  `ctx.capabilities`, which step 1 already populates before step 5 runs.
- This makes the resolved mode available to step 6 without moving any
  CLO-calling logic earlier than it currently runs.

### Step 5 — `clo_avatar_generation/avatar_runtime/step_06_build_payloads.py`

- Branch on `ctx.resolved_measurement_apply_mode`:
  - `avt_patch` → build only `clo_payload.avt_patch.json`.
  - `csv` → build only `clo_payload.bridge.csv` (+ template-seed logic as
    today).
  - `avatar_properties` → build only `clo_payload.properties.json`.
- `clo_payload.json` and `clo_payload_manifest.json` shrink to describing
  only the active route instead of all three every time.
- Step 8 (`_apply_via_*`) already branches per route and only reads the
  payload file for the resolved mode — no functional change needed there
  beyond removing the now-redundant apply-mode re-resolution (step 8 reuses
  `ctx.resolved_measurement_apply_mode` set in step 5 instead of
  recomputing it).

### Verification

- Run with default (no flags) → only `avt_patch`-related payload files
  appear in the run dir; no `clo_payload.bridge.csv` /
  `clo_payload.properties.json`.
- Run with `--apply-mode csv` and no `--enable-legacy-route` → pipeline
  refuses before step 1, with a message pointing at `legacy_routes.md`.
- Run with `--apply-mode csv --enable-legacy-route` → only the csv payload
  file is built; run completes (or fails) exactly as it does today for that
  route.

---

## Phase 2 — `run.log`, added (not yet replacing anything)

### Goal

One additive, human-readable log file per run,
`output/<user_id>-<run_number>/run.log`, using Python's standard `logging`
module. Console output and `run.log` carry **identical** content — same
lines, same level of detail — expanded to narrate the full run from initial
input through to final success/failure (not just the sparse
`print()`-based summary `run_avatar.py` has today).

### Step 1 — `clo_avatar_generation/avatar_runtime/logging_setup.py` (new file)

- One function, e.g. `configure_run_logger(run_dir: Path) -> logging.Logger`.
- Creates a logger (e.g. `"mirra.step1"`), attaches:
  - a `FileHandler` at `run_dir / "run.log"`.
  - a `StreamHandler` to stdout.
  - both with the **same formatter** and **same level** (INFO), so the two
    outputs stay identical as requested — no DEBUG-only content hidden from
    the console, no console-only content hidden from the file.
- Called once, from `step_02_run_setup.py`, right after `run_dir` is
  created (the earliest point a log file has somewhere to live).
- **Sequencing issue found while checking this against the current code:**
  `pipeline.py` runs `step_01_health` *before* `step_02_run_setup` — so
  `run_dir` (and therefore `run.log`) does not exist yet during step 1. A
  console-only logger (same formatter, no `FileHandler` yet) must be
  created at the very start of `run_pipeline()`/`run_avatar.py`, before step
  1 runs, so step 1's lines still print. To satisfy "run.log has the exact
  same logging, from input to success/failure" (i.e. step 1's lines must
  also land in the file, not just the console), attach a
  `logging.handlers.MemoryHandler` (or a simple manual list-buffer) at
  startup that captures step 1's records, then once step 2 creates
  `run_dir` and attaches the real `FileHandler`, flush the buffered records
  into it before continuing. This mirrors the existing
  `_bootstrap_failure_run_dir()` pattern in `pipeline.py`, which already
  handles the same "no run_dir yet" problem for the JSON artifacts when
  step 1 fails.

### Step 2 — `clo_avatar_generation/avatar_runtime/context.py`

- Add `ctx.logger: logging.Logger | None = None`, set by step 2 once the
  file/stream handlers are configured. Every later step pulls its logger
  from `ctx.logger` instead of importing `logging.getLogger` ad hoc, so the
  handler configuration is only ever done once per run.

### Step 3 — Every step file (`step_01` through `step_11`) + `pipeline.py`

- Replace/add `ctx.logger.info(...)` calls narrating what the step is doing,
  written to read like the current console summary but covering the whole
  pipeline: run identity + input echoed at start, each step's start/finish
  and pass/fail, resolved apply mode, key file paths written, and the final
  status line — taking the existing `run_avatar.py` print statements
  (header, run folder, completion/failure message, failure detail) as the
  tone/style baseline, not the ceiling.
- `run_avatar.py`'s existing `print()` calls are removed once the logger
  produces the same lines on stdout via the `StreamHandler` — no duplicate
  output.

### Verification

- Run the pipeline normally → `run.log` exists in the run dir, console and
  file contents match line-for-line, and narrate the full run.

---

## Phase 3 — Health watchdog (background thread, pipeline-scoped only for now)

Depends on Phase 2 (`ctx.logger` must exist for the watchdog to log
anything). Split into its own phase so it can be built, tested, and
confirmed independently of the logging work itself — this is also the
phase that answers the "can two threads actually work here" question
before anything more ambitious (a standalone watcher) is considered.

### Goal

Detect CLO crashing or becoming unresponsive *while a pipeline run is in
progress*, and pin down which step was running at the moment it happened —
instead of only seeing a generic downstream step failure after the fact.

### Step 1 — `clo_avatar_generation/avatar_runtime/health_watchdog.py` (new file)

- A daemon `threading.Thread` started once `ctx.logger` has its real
  `FileHandler` attached (i.e. after step 2 creates `run_dir` — see the
  sequencing note in Phase 2 Step 1; step 1 already completed successfully
  by this point anyway, since step 2 wouldn't run otherwise), polling
  `GET /health` every 2 seconds for the duration of the run.
- **Detection condition, corrected against the actual client code:**
  `CLORestClient._get()` never raises on a connection failure — it catches
  `requests.exceptions.RequestException` internally and returns
  `{"success": False, "error": ...}`. A normal healthy `/health` response
  has no `"success"` key at all (it's `{"status": "ok", "plugin": ...}`,
  per `step_01_health.py`'s own check of `status == "ok"`). So "CLO
  crashed" must be detected as `response.get("success") is False` (the
  client's own failure marker) **or** `response.get("status") != "ok"` —
  not by catching an exception, since the watchdog will never see one from
  this client.
- On a detected failure, logs one `logger.critical(...)` line to `run.log`
  + console: `"CLO appears to have crashed or stopped responding"`, with a
  timestamp and whichever step name was last recorded as in-progress (read
  from `ctx.step_results` / a small `ctx.current_step` marker updated at
  each step's start) — so the log directly shows what was running when CLO
  died, instead of only showing the generic downstream step failure.
- Thread is stopped (via a `threading.Event`) when `run_pipeline()` returns,
  success or failure.
- Scope for this phase: runs only inside `run_pipeline()`/`run_avatar.py`.
  Not a standalone always-on watcher yet — that's explicitly out of scope
  until this pipeline-scoped version is confirmed working, per your
  "first we need to make sure 2 threads can actually work" call. Two
  threads here should not be architecturally risky: the watchdog thread
  only does blocking HTTP GETs (releases the GIL during I/O) and never
  touches `g_commandQueue`/CLO state directly — it talks to the same REST
  plugin over the same loopback HTTP interface every other client call
  already uses.

### Verification

- Kill the CLO process partway through a run (manual test) → within ~2s a
  `CRITICAL` line appears in both console and `run.log`, naming the step
  that was in progress.
- Run the pipeline to completion normally → the watchdog thread starts,
  polls quietly, and stops cleanly with no leftover thread and no impact on
  run duration or step behavior (confirms two threads coexist safely before
  anything further is built on top of this).

---

## Phase 4 — Consolidate JSON artifacts into `run.log`

All of Phases 1–3 are implemented and verified (route separation, `run.log`,
health watchdog — confirmed against a real successful CLO run and a real
step-1-failure bootstrap case). This phase makes `run.log` the single
source of truth for everything currently spread across per-run JSON files,
leaving only the files CLO itself actually needs to exist on disk.

### Goal

Every JSON artifact that exists purely for our own inspection (not
something CLO reads back, not something a future Step 3 consumes) gets
logged as a full JSON block into `run.log` instead of written as a
separate file. What's left in `<run_dir>` after this phase: `run.log`,
`result_project.zprj`, `result_avatar_from_project.avt` (+ sibling
extracted artifacts), and `clo_payload.patched.avt` (the actual binary fed
to CLO's import call — this one stays, since it's a real input CLO
consumed, not just a record of our own reasoning).

### Step 1 — `clo_avatar_generation/avatar_runtime/context.py`

Add a `log_json(label: str, payload: dict) -> None` method next to the
existing `write_json`:

```python
def log_json(self, label: str, payload: dict[str, Any]) -> None:
    self.logger.info("%s:\n%s", label, json.dumps(payload, indent=2))
```

This becomes the replacement for every `ctx.write_json(...)` call whose
file is being folded into `run.log` below. `write_json` itself is **not**
removed — it's still used for the files that stay on disk
(`clo_payload.patched.avt` is written directly via `avt_patch.py`, not
through `write_json`, so in practice after this phase `write_json` is only
called for that one binary path's bookkeeping, if at all; verify at
implementation time whether `write_json` ends up unused entirely and should
be deleted).

### Step 2 — Convert each `ctx.write_json(...)` call, file by file

| File being removed | Written by | Replace with |
|---|---|---|
| `input.json` | steps 02, 03, 04 (progressively) | `ctx.log_json("input", ctx.input_payload)` — call once, at the point step 4 finishes building it (last writer), not three times |
| `mongo_snapshot.json` | step 03 | `ctx.log_json("mongo_snapshot", ctx.mongo_snapshot)` |
| `target_measurements.json` | step 05 | `ctx.log_json("target_measurements", ctx.normalized_targets)` |
| `clo_payload.json` | step 06 | `ctx.log_json("clo_payload", ctx.clo_payload_json)` |
| `clo_payload_manifest.json` | step 06 | `ctx.log_json("clo_payload_manifest", manifest_payload)` |
| `clo_payload.avt_patch.json` | step 06 | `ctx.log_json("clo_payload.avt_patch", avt_patch_payload)` (the derived `clo_payload.patched.avt` binary still gets written to disk in step 8 — this JSON was only ever the recipe for building it) |
| `clo_payload.properties.json` / `clo_payload.bridge.csv` | step 06 (legacy routes only) | same treatment if a legacy route is ever exercised via `--enable-legacy-route`; low priority since these routes are unmaintained |
| `import_result.json` | step 07 | `ctx.log_json("import_result", ctx.import_result)` |
| `apply_result.json` | step 08 | `ctx.log_json("apply_result", ctx.apply_result)` |
| `readback_measurements.json` | step 09 | `ctx.log_json("readback_measurements", ctx.readback_measurements)` |
| `error_report.json` | step 10 | `ctx.log_json("error_report", ctx.error_report)` |
| `save_outputs.json` | step 11 | `ctx.log_json("save_outputs", payload)` |
| `measurement_verification.json` | step 11 | `ctx.log_json("measurement_verification", measurement_verification)` — folded in too; this is a final decision, not the "tentative" open question from the original placeholder text. Its pass/fail is still driven off the same in-memory dict, so `final_success` logic in step 11 is unaffected — only the separate file disappears. |
| `run_summary.json` | `pipeline.py`, incrementally after every step | stop writing incrementally; log the full payload once at the very end via `ctx.log_json("run_summary", _run_summary_payload(ctx))`. The per-step "Step X: passed/failed" lines already give live status in `run.log` as the run progresses — the incremental file's only unique value was letting something else tail live status, and nothing in this repo does that today. |
| `output.json` | `pipeline.py`, once at the end | `ctx.log_json("output", ctx.output_payload)`. Still no live reader in this repo (confirmed: no `run_clo_vto.py`/`native_vto/` exist), so nothing breaks. |
| `health.json` | `pipeline._bootstrap_failure_run_dir` | `ctx.log_json("health", {...})` — only ever written on the step-1-failure bootstrap path today; same treatment. |

### Step 3 — Clean up now-dead fallback code

`step_08_apply_measurements.py`'s `_load_json_artifact()` helper reads
`clo_payload.avt_patch.json` / `clo_payload.properties.json` from disk as a
fallback when `ctx.clo_payload_avt_patch_json` / `ctx.clo_payload_property_json`
are empty. Since those files no longer exist after this phase, and the
in-memory dict is always populated in the same run (step 6 always runs
before step 8 in the same process), this fallback becomes genuinely
unreachable. Remove `_load_json_artifact` and the `or _load_json_artifact(...)`
fallback expressions in `_apply_via_avatar_properties` and
`_apply_via_avt_patch` — keep the plain `ctx.clo_payload_avt_patch_json`
reference.

### Verification

- Run the pipeline end to end → `<run_dir>` contains only `run.log`,
  `result_project.zprj`, `result_avatar_from_project.avt` (+ extracted
  siblings), and `clo_payload.patched.avt`. No other `.json`/`.csv` files.
- `run.log` contains a full, readable JSON block for every artifact listed
  above, in the same order the pipeline produces them.
- Re-run the Phase 1/3 verification scenarios (legacy-route gating, health
  watchdog crash detection) to confirm nothing that depended on a since-removed
  file silently broke.

---

## Phase 5 — Measurements from MongoDB by `user_id` (real-user data path)

Must land **before** Phase 6 (mesh-corruption fix) — real MongoDB fetch
latency changes the timing pattern between avatar import and save compared
to today's instant local-JSON reads, and Phase 6 needs to reproduce/fix the
race under the same conditions the real pipeline will actually run under.

### Context confirmed before writing this phase

The MongoDB path is not something to build from scratch — it already works:

- `mirra_measurements/db.py` is a real, working `pymongo` wrapper. Reads
  `MONGODB_URI` from `mirra_measurements/.env` (already populated), connects
  to db `mirratest`, collection `measurements`.
- `step_03_fetch_measurements.py` already imports and calls
  `get_measurements_collection()` — today only as the *fallback* path, after
  a local JSON file check.
- Field names match exactly: `mirra_measurements/avatar_model.py`'s document
  shape (`height_cm`, `weight_kg`, `chest_circumference_cm`, etc.) lines up
  field-for-field with `step1_field_contract.json`'s `mongo_field` names —
  no mapping/renaming work needed.
- `python -m mirra_measurements.seed_measurements` already seeds 10 golden
  test users (`u_001`–`u_010`) into the real collection, usable for local
  verification without a real website submission.

### Decisions made for this phase (flagged for your review)

1. **`--measurement-file` CLI flag**: kept as a manual/QA override, but no
   longer auto-detected. Today `run_avatar.py`'s
   `_resolve_default_measurement_file(user_id)` silently guesses
   `input/<user_id>.measurements.json` if it exists, even when the flag
   isn't passed. That auto-detection is removed — the flag now only takes
   effect if explicitly passed on the command line.
2. **Local-snapshot fallback removed.** Today, if a live Mongo fetch fails,
   `step_03_fetch_measurements.py` falls back to loading a previous run's
   saved `mongo_snapshot.json` from `output/`. This silently serves stale
   data on a genuine Mongo outage instead of surfacing the failure. Since
   this phase's `mongo_snapshot.json` file no longer exists anyway (folded
   into `run.log` in Phase 4), and real-user correctness matters more than
   dev-environment convenience now, this fallback is removed — a Mongo
   fetch failure becomes a hard pipeline failure with a clear error message.
3. **Interactive "Measurement JSON path" prompt removed.** Since Mongo-by-
   `user_id` is now the default flow, the interactive prompt in
   `run_avatar.py` for a measurement JSON path is dropped entirely.
   `--measurement-file` remains CLI-only, matching the existing
   `--enable-legacy-route` pattern (no interactive equivalent).

If any of these three should go the other way, flag it before implementation.

### Step 1 — `clo_avatar_generation/avatar_runtime/step_03_fetch_measurements.py`

- Reorder `run()`: if `ctx.measurement_file_input` is explicitly set (CLI
  override), use it as today. Otherwise, go straight to
  `get_measurements_collection().find_one({"user_id": ctx.user_id})` — no
  more auto-detected local file check first.
- Remove the `_load_latest_local_snapshot()` fallback entirely (both call
  sites: the "MongoDB fetch failed" branch and the "no live document found"
  branch) — replace both with a direct `raise RuntimeError(...)` /
  `raise ValueError(...)` naming the user_id and the real cause.
- Keep `_sanitize_doc()` / gender+range validation unchanged — those apply
  equally to a Mongo-sourced or JSON-sourced document.
- Update `ctx.logger` lines accordingly (drop the "falling back to local
  snapshot" warnings; log the real Mongo error instead).

### Step 2 — `clo_avatar_generation/run_avatar.py`

- Remove `_resolve_default_measurement_file()` and its call sites in both
  the interactive and non-interactive branches.
- Remove the interactive "Measurement JSON path" prompt block entirely.
- `--measurement-file` argparse flag stays, passed straight through to
  `Step1Context.measurement_file_input` as today — just no longer defaulted
  or prompted for.

### Step 3 — Manual verification (no code change)

- Confirm golden users are present: `python -m mirra_measurements.seed_measurements`.
- Run `python clo_avatar_generation/run_avatar.py --non-interactive --user-id u_001`
  with **no** `--measurement-file` → `run.log` shows
  `Measurement source: mongodb` and the pipeline completes using the Mongo
  document's values.
- Run with a `user_id` that has no Mongo document and no `--measurement-file`
  → pipeline fails clearly at step 3 with a real "no measurements found"
  error, not a silent stale-snapshot substitution.
- Run with `--measurement-file <path>` explicitly → confirm the override
  still works, for the cases where it's genuinely needed (QA, isolated
  field experiments).

### Step 4 — Manual cleanup (deferred to you, not automated)

Once you've verified the above works end to end against real data, delete
`clo_avatar_generation/input/u_001.measurements.json` (and any sibling
`*.measurements.json` files) yourself. Not something this plan automates —
per your own instruction, this is a manual step after manual verification.

---

## Phase 6 — Fix: saved mesh can be silently incomplete

Must come **after** Phase 5, since Mongo fetch latency changes the timing
profile between avatar import and save — reproducing/fixing this under
today's instant-local-JSON timing could produce a fix that stops working
once Phase 5 changes that timing.

### Known issue (found 2026-07-06, still open)

While comparing two back-to-back real CLO runs (`u_001-035` and
`u_001-036`) right after Phase 1 landed: same user, same measurements, same
base avatar, same `avt_patch` route, run about 90 seconds apart. Run 035's
`result_project.zprj` opened in CLO shows a visibly broken avatar mesh —
spiky/exploded geometry, not a clean T-pose. Run 036 opened clean.

**Every API-level artifact the pipeline captures was identical between the
two runs** — `import_result.json`, `apply_result.json`, and
`measurement_verification.json` (both `verification_pass: true`,
`delta_from_requested: 0.0` on all 6 fields). By every check the pipeline
performs, both runs were indistinguishable successes.

**But the actual saved data differed.** The embedded avatar mesh
(`result_project_0.avt` inside the `.zprj` zip) was ~8% (~2.8 MB) smaller
in the broken run (31,502,115 vs 34,304,185 bytes) despite identical
inputs and identical API responses — CLO genuinely wrote a structurally
different, smaller mesh into the project file. `measurement_verification.json`
can't catch this: it only reads raw float bytes at fixed offsets, not mesh
topology.

**Working theory:** `avt_patch` writes measurement floats directly into
the binary `.avt` before CLO ever imports it, bypassing CLO's own morph
pipeline. When CLO imports that pre-patched file, it still does its own
internal work afterward — rebuilding the body mesh/subdivision to match
the new feature values. `client.wait_for_queue()` only confirms **our own
command queue** drained, not that CLO's internal mesh rebuild finished
(that rebuild isn't a command we queued). If `save-project` fires while
that rebuild is still in progress, the save can capture a structurally
incomplete mesh. Not confirmed — no CLO-side "rebuild finished" signal has
been found yet. The health watchdog (Phase 3) won't catch this on its own:
CLO doesn't crash or become unresponsive in this failure mode, so `/health`
reports fine throughout.

### Step 1 — Characterize the failure rate before attempting a fix

`clo_avatar_generation/scripts/repeat_run_check.py` (new file): runs
`run_pipeline()` N times back-to-back for the same user (default N=10,
configurable via CLI arg), and after each run:
- Unzips the resulting `.zprj`, reads the embedded `result_project_0.avt`
  size.
- Compares it against the base avatar's own file size (same topology, just
  morphed — so a healthy save should land within some tolerance band of the
  base size, not an arbitrary fixed number pulled from one prior good run).
- Prints a summary table: run_id, embedded size, % delta from base, and a
  flagged/not-flagged verdict per run.

This exists purely to turn "one bad run, one good run" into an actual
failure rate and a concrete size-deviation threshold to alarm on, before
touching any pipeline code. Run it once before any fix, and again after,
to have a real before/after comparison instead of anecdote.

### Step 2 — Mitigation, informed by Step 1's characterization

Two complementary changes to `step_11_save_outputs.py` (exact
thresholds/delay tuned from Step 1's data, not guessed up front):

1. **Settle delay before save.** After step 8's measurement-apply queue
   drain and before step 11 calls `save_project`, add a short deliberate
   delay (starting point ~2–3 seconds, adjustable) to give CLO's internal
   mesh rebuild more wall-clock time to finish before the save fires.
2. **Post-save structural check + bounded retry.** After `save_project`
   succeeds and the `.zprj` is extracted, compare the embedded
   `result_project_0.avt` size against the base avatar's size using the
   same tolerance band Step 1 characterized. If it looks anomalously small:
   log an error (this is new — today nothing checks mesh size at all),
   re-issue `save_project` up to a small bounded number of retries (e.g. 2),
   and only mark the run failed if retries are exhausted. This directly
   closes the gap in today's `measurement_verification.json`, which only
   checks binary float offsets and would happily mark a structurally broken
   save `verification_pass: true`.

A deeper CLO-SDK-level "is CLO still busy rebuilding" signal may not exist
in this SDK version — not something to go looking for before trying the
above, since it could be an open-ended investigation with no guaranteed
answer.

### Verification

- Re-run `repeat_run_check.py` after the mitigation lands, compare failure
  rate against the Step 1 baseline.
- Manually shorten the settle delay in a test run to deliberately provoke
  the race, and confirm the post-save structural check catches it and
  retries instead of silently passing.

---

## Phase 7 — Step 9 (`/avatars/state` readback) and Step 11 (`ExportAVT` direct export)

Starts only after Phases 4–6 are done and confirmed, per your ordering.
Both steps have plugin-side C++ changes already made (`plan-01.md` Phases 1
and 3) that were hoped to unblock them, but never manually verified against
a live pipeline run. With `run.log`, the health watchdog, and the Phase 6
mesh-corruption detection all in place by this point, there's now enough
visibility to test these safely instead of debugging blind.

### Step 1 — `clo_avatar_generation/avatar_runtime/step_09_readback.py`

- Replace the hardcoded `avatar_state = {"success": False, "error":
  "skipped: unsafe CLO API call from HTTP thread on Windows"}` with a real
  `ctx.client.get_avatar_state()` call — the Windows plugin's
  `/avatars/state` endpoint has routed through `dispatchSyncRead` on the
  main thread since `plan-01.md` Phase 1, so the SEH-crash risk that
  justified skipping it should no longer apply.
- Run the pipeline multiple times (reuse `repeat_run_check.py` from Phase 6
  as a repeat-run harness) watching `run.log` + the health watchdog for any
  crash/hang signal during this specific call. If stable, remove the
  "skipped" notes text and keep it enabled permanently.
- **Important expectation to set correctly:** `/avatars/state` returns
  `GetAvatarCount`/`GetAvatarNameList`/`GetAvatarGenderList` data — avatar
  count, names, and genders, **not per-field body measurement values**. Re-
  enabling this does **not** unlock real measurement-error computation in
  step 10. Step 10 remains a stub after this change; don't expect otherwise.

### Step 2 — `clo_avatar_generation/avatar_runtime/step_11_save_outputs.py`

- Replace the hardcoded `direct_export_available = False` with a check
  against `ctx.capabilities.get("has_avatar_avt_export")` (populated
  dynamically by the plugin per `plan-01.md` Phase 3 — `true` only after a
  real `/export-avatar-avt` call has succeeded once, `false` otherwise,
  since the plugin no longer auto-probes this at startup after the Phase 3
  live-incident fix).
- When true, call `ctx.client.export_avatar_avt(direct_avatar_path)` (routed
  through the plugin's `ExportAVT_SEHSafe` wrapper) as today's code already
  does when `direct_export_available` is true — no new call logic needed,
  just flip the gate from hardcoded to capability-driven.
- Keep the existing `.zprj`-extraction path as the fallback when direct
  export isn't available or fails for a given run, rather than making
  direct export a hard requirement — this preserves today's working path
  as a safety net while direct export is still unproven at scale.
- Run repeatedly (same harness), watching for stability. If stable across
  multiple runs, this becomes the preferred path; if it ever destabilizes
  CLO, revert to the extraction-only path and document the failure the same
  way the Phase 3 live incident in `plan-01.md` was documented.

### Verification

- N repeated runs (`repeat_run_check.py`) with both changes active, no CLO
  crashes or hangs reported by the health watchdog across any run.
- `run.log` shows real avatar-state data (count/names/genders) instead of
  the "skipped" placeholder, and shows a real direct-export result instead
  of `direct_avatar_export_available: false`, for every run in the batch.
- Confirm step 10's `error_report.json`-equivalent log block is unchanged in
  shape/capability (still a stub) — this phase does not attempt to fix step
  10 itself, only unblock steps 9 and 11.

---

## Explicitly deferred (not scheduled in this plan)

- **Standalone always-on health watchdog** (independent of a pipeline run,
  useful during manual CLO testing) — deferred until there's a specific
  need for it; the pipeline-scoped version from Phase 3 is what's proven to
  work so far.
- **A different, not-yet-examined CLO SDK interface for live body-shape
  editing** — would be the only thing that could revive the
  `avatar_properties` route (see `clo_avatar_generation/schema/legacy_routes.md`).
  Not something to go looking for as part of this plan.

Found 2026-07-06 while comparing two back-to-back real CLO runs
(`u_001-035` and `u_001-036`) after Phase 1 landed. Same user, same
measurements, same base avatar, same `avt_patch` route, run about 90
seconds apart. Run 035's `result_project.zprj` opened in CLO shows a
visibly broken avatar mesh — spiky/exploded geometry, not a clean T-pose.
Run 036 opened clean.

**Every API-level artifact the pipeline captures is identical between the
two runs** — `import_result.json` (byte-for-byte identical besides nothing,
literally no diff), `apply_result.json` (identical besides run-specific
file paths), and `measurement_verification.json` (identical per-field
values, both `verification_pass: true`, `delta_from_requested: 0.0` on all
6 fields in both runs). By every check this pipeline currently performs,
both runs are indistinguishable successes.

**But the actual saved data differs.** Unzipping both `.zprj` files and
comparing the embedded avatar mesh (`result_project_0.avt` inside the zip)
by size:

| Run | Embedded `result_project_0.avt` size |
|---|---|
| 035 (visibly broken) | 31,502,115 bytes |
| 036 (clean) | 34,304,185 bytes |

An ~8% (~2.8 MB) difference in the actual saved mesh, despite identical
inputs and identical API responses. This means CLO genuinely wrote a
structurally different, smaller mesh into the project file for run 035 —
this is not a viewport rendering glitch, and not something
`measurement_verification.json` can catch, since that check only reads raw
float bytes at fixed offsets in the extracted `.avt` and says nothing about
mesh topology.

**Working theory:** the `avt_patch` route writes measurement floats
directly into the binary `.avt` before CLO ever imports it, bypassing
CLO's own morph pipeline entirely. When CLO imports that pre-patched file,
it still has to do its own internal work afterward — rebuilding the body
mesh/subdivision to match the new feature values. `client.wait_for_queue()`
(used after both the import-avt call in step 8 and before save in step 11)
only confirms **our own command queue** (`g_commandQueue`/
`g_queueProcessing`) has drained — it says nothing about whether CLO's
internal mesh rebuild has finished on its own timeline, since that rebuild
isn't a command we queued. If `save-project` fires while that internal
rebuild is still in progress, the save could capture a structurally
incomplete mesh — matching both symptoms seen here (smaller file size,
spiky/broken geometry). This is a hypothesis, not confirmed — no CLO-side
signal has been found yet that would let the pipeline detect "mesh rebuild
finished" directly.

**Why this isn't a Phase 1 regression:** the two runs' pipeline-visible
data (API calls, responses, patch payloads) are identical up to the point
of saving. Nothing in the route-separation work touches timing between
import and save. This looks like a pre-existing CLO-side race that Phase
1's tighter file output simply made easier to notice by isolating exactly
what data is/isn't identical between runs.

**Why the Phase 3 health watchdog won't catch this on its own:** CLO
doesn't crash or become unresponsive in this failure mode — `/health`
would report fine throughout. The watchdog is built to catch "CLO died",
not "CLO saved something structurally incomplete while still alive." A fix
here needs either a CLO-side readiness signal to poll for before calling
`save-project`, a deliberate settle/retry delay, or a post-save structural
check (e.g. comparing embedded `.avt` size or some other geometry-derived
signal against an expected range) that can fail the run instead of
silently marking it `verification_pass: true`. Not designed yet — deferred
to Phase 4 or later, after the logging/watchdog work lands and there's
richer run-by-run visibility to work with when reproducing this
deliberately.

---

## Explicitly deferred (not in this plan)

- **Step 9 (`/avatars/state` readback) and Step 11 (`ExportAVT` direct
  export)** — both have plugin-side changes already made (per `plan-01.md`
  Phases 1 and 3 of `plan-01.md`) that were hoped to unblock them, but those
  changes have not been manually verified yet. Per your instruction, the
  logging/route work in this plan comes first specifically so that when
  step 9/11 are revisited, `run.log` + the health watchdog make it possible
  to see exactly what happens (and whether CLO survives) instead of
  debugging blind. Do not start on step 9/11 fixes until this plan's
  Phases 1–3 are done and confirmed.
- **Standalone always-on health watchdog** (independent of a pipeline run,
  useful during manual CLO testing) — explicitly deferred until the
  pipeline-scoped version is proven to work correctly with two threads.
