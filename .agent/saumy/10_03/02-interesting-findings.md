# 02 — Interesting findings worth preserving

*Status: current*
*Compiled: 2026-10-04*

A running log of notable Q&A from working sessions — not planning docs, not instructions, just things worth not losing. New sections get appended here as they come up, each one a question that was asked and the answer that was given at the time.

---

## 1. How do industry-scale companies actually use avatars for virtual try-on?

**Q:** How do other companies which are of industry scale use this avatar, like those working in this field?

**A:**

Three distinct patterns show up at real industry scale, and none of them look quite like what this repo is building.

**Pattern A — size recommendation, no visual avatar at all (True Fit, Fit Analytics).** These are the companies actually embedded at scale in big retailers' checkout flows. Neither renders a 3D body to the shopper. True Fit outputs a score ("T-Score") and pre-selects a size; Fit Analytics matches your measurements against millions of past purchase/return records to recommend a size label. The "avatar" — if it exists internally at all — never gets shown. This is the cheapest possible version of the problem: skip rendering, skip physics, skip CLO3D-equivalent entirely, just answer "will this fit, yes/no/how." It's also the pattern most large retailers actually picked.

**Pattern B — CLO3D/Browzwear at real industrial scale is a B2B sample-reduction tool, not a consumer feature.** This is the sharpest finding. Brands do use CLO3D-class software at genuine scale — but for internal design and sampling, plugged into their PLM (product lifecycle management) systems, to cut the number of physical sample garments they have to sew and ship during development (Browzwear reports 50-70% fewer physical samples, 4-8 week shorter dev cycles). Two things matter here specifically:

1. The avatar used is not a personalized shopper body — it's one of a handful of standard fit-model mannequins the brand already uses for physical sample fitting. Nobody's running CLO3D once per customer.
2. The 3D garment is not reconstructed from a product photo — a real patternmaker builds it directly from the brand's actual manufacturing pattern (the tech pack), which already exists digitally. That's categorically more accurate than Step 2's approach of inferring a pattern by looking at a photo of the finished garment, and it sidesteps the exact failure modes this repo's own build-list documents (complex prints failing segmentation, threshold tuning per garment type).

In other words: the one place CLO3D-class engines genuinely dominate at industrial scale is explicitly a backend design tool fed by real pattern data — not a real-time per-shopper consumer feature. Mirra is pointing a sample-reduction tool at a problem (live consumer try-on) it wasn't built to solve at that volume, which is also why this repo needs a concurrency=1 worker queue and a desktop app running in the background — that constraint isn't a bug to engineer around, it's the tell that this tool category wasn't designed for this usage pattern.

**Pattern C — accurate measurements without asking anyone to type numbers in (3DLook and similar).** The industry already solved the "get real measurements from a shopper" problem differently than Step 1 does here. 3DLook takes two phone photos (front + side) and extracts 80+ measurements via computer vision — and claims that beats dedicated 3D scanning hardware on accuracy (self-reported, worth treating skeptically, but directionally telling). Mirra's Step 1 still asks the shopper to manually type in tape-measure numbers, which is exactly the kind of friction step that real funnels see the highest abandonment on — nobody at scale is relying on self-reported tape-measure entry as the primary input anymore.

**Put together:** the two patterns that actually scaled to real consumer traffic (A and C) both deliberately route around the expensive thing this repo is building — full 3D reconstruction + CLO3D physics simulation, rendered per shopper. The one place that expensive thing genuinely earns its keep at scale (B) is a backend tool brands use on themselves during design, fed by data this repo doesn't have access to (the real manufacturing pattern), not something aimed at a shopper in real time.

Sources: True Fit (textileworld.com), Browzwear/DeSL PLM partnership (textileworld.com), 3DLook (3dlook.ai).

---

## 2. Per-user avatar storage cost — how do we compact it?

**Q:** The avatar which we are reusing and making a separate avatar for each user has high storage cost, what can we do to compact it?

**A:**

Checked a real file instead of guessing, and the numbers are worse than expected, which points straight at the fix.

**What's actually happening today:** `clo_avatar_generation/avatar_runtime/step_12_export_glb.py` packs the avatar into a single `.glb` by embedding every mesh buffer and texture image as a base64 text string (`ImageFormat.DATAURI`). A real sample: the raw export is 80KB, the packed version is **30.5MB**. This matches the earlier-known F1 issue (66MB GLB re-downloaded per avatar on every page mount) — this isn't a one-off, it's how every avatar gets built.

Three concrete, ranked levers:

**1. Stop using base64 for images — free, no quality loss, smallest change.** `pygltflib` has `ImageFormat.BUFFERVIEW` as an alternative to `ImageFormat.DATAURI` — it stores images as raw binary inside the `.glb`'s binary chunk instead of as base64 text. Base64 inflates size by ~33% for zero benefit once already packing into one binary file. One-line change in `step_12_export_glb.py` and the equivalent `clo_vto/native_vto/step_12_texture_glb.py`, and it's pure win — do this first regardless of what else gets decided.

**2. Question whether ~25 textures should exist at all.** The packed file is almost certainly textures, not geometry (a body mesh is a few MB at most; 30MB minus a small mesh is overwhelmingly image data). But the MVP scope (`.claude/project-context.md`) says this avatar is supposed to be "silhouette-focused... black matte style" — not photorealistic, no skin tones, no detail. If that's true, why is CLO exporting ~25 separate texture images per avatar? That smells like CLO's default scene/material export (base color, normal, roughness, AO, etc. per body part) rather than anything the matte-style avatar actually needs visually. Worth checking what those 25 textures actually contain before compressing them — deleting textures nobody renders beats compressing textures nobody renders.

**3. For whatever textures genuinely need to stay — compress and downscale them.** Three sub-levers, in order of effort:
   - Re-encode as JPEG instead of PNG where there's no transparency need (typically 5-10x smaller for photo-like content).
   - Downscale resolution — a matte, non-closeup body avatar almost certainly doesn't need 2K/4K textures; 512px or 1024px is probably visually identical at the distance/zoom this gets viewed at.
   - KTX2/Basis Universal compressed textures — the real "industry" answer for this exact problem (GPU-native compressed format, both smaller on disk and faster to decode in the browser). More tooling to add (needs `gltf-transform` or similar in the export pipeline) — treat as the next step after 1 and 2, not the first move.

**One thing worth flagging separately from file size:** even a perfectly compacted avatar doesn't solve total storage growth, because nothing currently prunes `dev_upload/`/`live_upload/` at all — `utils/prune_output.py` explicitly never touches those folders, since they're "the product." The real long-term question isn't just "how big is one file" but "do we keep every avatar a user ever generated forever, or only the latest." That's a policy decision, not a compression one — worth tracking separately.

---

## 3. Is the avatar accuracy actually being validated? ("<5% error" — is that real?)

**Q:** The error report is not correct because we are not able to validate our measurements from the CLO app? Or is there any other method by which we are validating it? *(Follow-up: checked whether a manual/offline validation method is documented anywhere in the repo before writing this up.)*

**A:**

Two separate mechanisms exist, and they answer two different questions — confusing them is exactly how the stale "<5% error" claim likely survived this long.

**`error_report.json` (`clo_avatar_generation/avatar_runtime/step_10_compute_error.py`) is a permanent stub.** It always writes `"available": false` and `"status": "not_read_back"` for every field. Its own `reason` string says why: CLO's plugin "does not expose resulting body measurements field-by-field," so there's nothing to compare against. This file has never contained a real computed error number.

**`measurement_verification.json` (`verify_avatar_fields()` in `avt_patch.py`, called from `step_11_save_outputs.py`) is real, active, and currently gates the pipeline** — a failure here flips `final_success = False` for the whole run. But it checks something narrower than dimensional accuracy: it opens the `.avt` file CLO actually saved, reads the raw float bytes at known offsets (`Total Height` = feature index 0, `Chest` = 2, `Waist` = 6, `Low Hip` = 8, `Inseam` = 26, `Across Shoulder` = 36 — reverse-engineered in `.claude/research/step-1/measurement-method-experiments.md`), and checks it matches the requested value within tolerance `0.05` — essentially float-equality. **This confirms CLO stored the number requested. It does not confirm the resulting 3D mesh is geometrically that size.** Nothing in this repo independently re-measures the mesh itself; CLO's named sliders ("Chest", "Waist") are trusted to do what their names say internally.

**No manual or offline validation method is documented anywhere in `.agent/` or `.claude/`.** Searched both folders specifically for this — no record of anyone tape-measuring a rendered avatar and comparing it to the request, no visual sign-off process, nothing. The "<5% error between measured and morphed dimensions" claim in `.claude/project-context.md` and `.claude/current-roadmap.md` has no supporting validation anywhere in the repo, automated or manual. It reads as an unverified target, not a measured result.

**Related finding, same investigation:** a real recent run's output folder (`u_015-005`) shows the ~25 exported textures per avatar aren't generic placeholders — they're CLO's default fully-detailed human character: `MV2_Jinho_01_face/_eye/_tooth/_leg/_arm/_body` (each with base color + normal + roughness maps), `hair_main`/`hair_cap`, and even `Male_Sneaker_01`. Confirms the Section 2 suspicion: a "silhouette-focused, matte" MVP avatar is currently shipping a full photorealistic character's skin/hair/eye/tooth/shoe texture set, unused and uncompressed.

---

## 4. How does CLO3D know when to process a request, and how does the Python script know when to send the next one?

**Q:** In this third point [of "running a pipeline step"], how does CLO3D know when to process the next request and how does our script know when to make which request? There are 2 things — python script sends the request to clo3d, clo3d executes that request. So now how does python know when to send the next request and how does clo3d know when to execute it? We have faced a lot of issues during development like too many requests sent, loading time too low or too long, then we decided to process the request at different speeds — 200ms, 500ms, etc. What can be the solution for this?

**A:**

Two separate clocks, neither one pushing to the other.

**How CLO3D knows when to process a request:** a fixed internal timer (`QueueDrainTimer`, inside the plugin's C++ code) fires every 200ms, always, independent of Python. Each tick, it checks whether anything is sitting in `g_commandQueue`; if so, it drains the whole batch right then, on CLO's single main thread (the only thread allowed to call CLO's real API functions). CLO never gets told "process now" by Python — it just checks its own queue on a fixed cycle, forever.

**How the Python script knows when to send the next request:** it doesn't get a push notification back — it polls. `wait_for_queue()` in `clo_avatar_generation/avatar_runtime/client.py`:

```python
while time.time() < deadline:
    status = self.get_status()
    if status.get("queue_size") == 0 and not status.get("queue_processing"):
        return status
    time.sleep(poll_interval)   # default 0.3s
```

It repeatedly calls `GET /status`, sleeps `poll_interval` seconds, asks again — until CLO reports the queue is empty and not mid-processing. Only then does the pipeline move to the next step. Ordering is enforced client-side, by refusing to proceed until completion is confirmed — not by CLO signaling back.

**Where the "too many requests" / timing problems came from — two different knobs:**
1. **CLO's 200ms timer** — fixed in the C++ plugin, not tunable from Python without rebuilding the plugin DLL.
2. **Python's `poll_interval`** — how often the script asks "done yet." Poll faster than CLO's own 200ms cadence and you're hammering `/status` for information that can't have changed yet. Poll slower and you add dead latency onto every step.

A third related knob: `timeout` (the give-up ceiling — default 30s in `wait_for_queue`, but tuned per call site: `timeout=120` for GLB export, 20min/25min job timeouts at the worker's RQ enqueue sites for full avatar/VTO runs). "Loading time too low" = timeout firing before a genuinely slow operation (like a 150-step simulation) finished — a false failure. "Too long" = a truly frozen CLO sitting silent for ages before the failure surfaces. The real fix was always matching each operation's timeout/poll pair to how long *that specific kind* of CLO call realistically takes, not sharing one number across a health check and a full simulation.

**What can be the solution:**

1. **Quick, low-risk fix: floor `poll_interval` at CLO's own cadence (~200-250ms).** Since CLO can't possibly report new information faster than its own 200ms timer, polling faster than that is pure waste with zero benefit. This alone removes the "too many requests" problem without touching anything else.
2. **Better fix: adaptive/exponential backoff instead of one fixed interval.** Poll fast (near 200ms) right after sending a command — most quick operations (health check, import) finish fast, so you want to notice immediately. The longer the wait drags on, back the interval off (e.g. 200ms → 400ms → 800ms → cap around 2-3s) — a long-running simulation doesn't need checking 5x a second once it's clearly going to take a while. This is a standard, well-established pattern (same idea behind most SDKs' retry/poll logic), low-risk to adopt, and fixes both the "too many requests" waste and the "fixed timeout mismatch per operation type" problem in one change, without needing to hand-tune a different constant per call site.
3. **Real fix, bigger effort: let CLO push a completion signal instead of being polled at all.** The root cause of having to guess intervals is that the plugin only exposes pull-based state (`/status`) — it never tells the caller "I just finished X." If the C++ plugin called back out (a webhook-style HTTP POST, or similar) when `ProcessCommandQueue()` finishes a batch, Python wouldn't need to poll or guess timeouts for normal completion at all — it would just be told. A frozen/crashed CLO would still need a timeout as a backstop, but that backstop would only matter for the actually-broken case, not the common case. Worth noting: this is the same direction already flagged elsewhere in the repo's own open-issues list for a different sub-step (`.agent/saumy/02-remaining-build-list.md` item 1.1 — replacing a guessed 4s settle delay with a real completion signal by polling the output file for size stability) — so this isn't a new idea, it's the same fix the team already recognized was needed in one place, generalized to the request/response layer too.

Recommended order: do #1 immediately (free, no risk), move to #2 when there's time to actually test polling behavior properly, treat #3 as the real long-term fix if request/response latency ever becomes a bottleneck worth the plugin-side engineering effort.

---

## 5. Checking the SDK/docs for a better fix — one dead end, one real find, one wrong assumption corrected

**Q:** Search Google and look into the SDK downloaded locally to check if there's a better fix, and the CLO3D developer blog site. Also: the latest plugin build is against the newest SDK only, as far as I remember — confirm that. Also looked at the in-app Python Editor (no autocomplete, no API list, just run a `.py` file or write a script in the text field) — is it possible to run our script there for some improvement?

**A:**

**Dead end — no better built-in fix for the polling problem exists, even in the newest SDK.** Checked CLO's official "Event Plugin" system directly, both in the local SDK header (`Samples/CloEventPlugin/CloEventPlugin.h`) and the live docs (`developer.clo3d.com/eventplugin.html`). It supports exactly two events, both UI-only:
```cpp
virtual bool MouseDropEventOn2DView(...)
virtual bool MouseDropEventOn3DView(...)
```
Nothing for simulation-complete, export-complete, import-complete, or queue-drained — in the 2026.1.224 SDK either. The polling workaround this repo built isn't a missed feature; CLO genuinely has no completion-callback API. Section 4's adaptive-backoff recommendation stands as the real fix for that specific problem.

**Real find — a newer SDK adds the measurement-readback function Section 3 said didn't exist.** `CLO_SDK_v2026.1.224_Win` (sitting in Downloads, matching the CLO app version shown in the screenshot — "Version: 2026.1.224") adds:
```cpp
virtual std::vector<Marvelous::CloApiAvatarMeasurement> GetAvatarMeasurements(int _avatarIndex)
```
returning, per field: `measurementName`, `measurementType` ("Tape"/"Circumference"/"Height"/"Linear"/"Default"), `value`, `basicLength` (convex-fit), `surfaceLength` (surface-fit — the real tape-measure-around-the-body value), `unit`. This is exactly what `step_10_compute_error.py`'s own code comment says doesn't exist ("the current plugin... does not expose resulting body measurements field-by-field"). **That was true against the older SDK the plugin references. It may no longer be true.** Wiring this into a new endpoint would give Step 1 genuine geometry-based accuracy validation for the first time — not the write-fidelity check `measurement_verification.json` already does, but an actual "does the generated mesh measure what was requested" answer.

**Standing note worth keeping: always check the newest downloaded SDK version before concluding CLO doesn't support something.** The plugin's own codebase has already been burned by stale-SDK assumptions before (the 2025.2.368 → 2026.1.188 hang below) — treat "the SDK doesn't expose X" as true only as of whatever SDK version was last checked, not as a permanent fact.

**Correction (superseding an earlier wrong claim in this same section):** the deployed plugin IS built against the newest SDK. `v_1.3.2.json`'s notes field says *"Built against CLO_SDK_v2026.0.356_WIN"* — that's stale documentation, not what actually happened. The real evidence is the build log and the deployed binary, not the notes field, and they agree with each other: `clo_workspace/logs/build_plugin_windows_20260912T142745Z.log` (timestamp matches the deployed DLL exactly — 14:27:45 UTC = 19:57:45 IST, same as `C:\D-drive-data\plugins\mirra-vault\RestPlugin_v1.3.2.dll`'s mtime) states directly: *"Synced windows plugin sources to: `C:\Users\Saumy\Downloads\CLO_SDK_v2026.1.224_Win\Samples\RestPlugin`"* and *"Built plugin artifact: `...CLO_SDK_v2026.1.224_Win\Samples\RestPlugin\build\Release\RestPlugin.dll`"* — the SDK zip was downloaded and extracted ~30 minutes before that same build. So there is no version mismatch and no hang risk right now; that part of the original finding was wrong, and the fix is the lesson, not the specific claim: check the build log and binary timestamps, not a version file's notes field, when the two can drift apart.

**What doesn't change: `GetAvatarMeasurements()` is real, available in the SDK the plugin was actually built against — and still unused.** Checked directly: it does not appear anywhere in `clo_workspace/windows/RestPlugin_windows.cpp`. So no SDK upgrade or rebuild is needed to get it — the function is already sitting in the build environment. The only remaining work is adding a new endpoint/queue-command (same Type-1-or-2 pattern as every other mutating/read call, see Section 4) that actually calls it. This is a smaller, more precise fix than originally stated: not "rebuild against a newer SDK," just "wire up a function that's already there."

---

## 6. CLO's in-app Python Editor — could it replace or improve the automation path?

**Q:** User shared a screenshot of CLO's built-in Python Editor (`Edit → Python Script`): a bare text field with a "Source:" file-load dropdown and a play button — no autocomplete, no visible API list. Is it possible to run a script from here for some improvement over the current REST-plugin approach?

**A:** Plausible, but genuinely unconfirmed — here's the actual research trail, not just the conclusion, since it's worth knowing what was and wasn't checked.

**What was checked:**
- The local SDK (`CLO_SDK_v2026.1.224_Win`) has no `.pyi` file or any Python binding module to inspect offline — the only Python-related sample is `Samples/PythonPluginAutoRegister/`, which is about registering a `.py` file as a clickable menu action, not a Python API reference.
- `developer.clo3d.com/python.html` was fetched directly. It documents *how to open and run* the Python Editor (`Edit → Python Script`, or drag a `.py` file into the 3D window) but not *what's callable from it* — no class/function reference rendered.
- `CloApiData.h` in the SDK tags several struct fields (including `CloApiAvatarMeasurement` from Section 5) with an `EXPORT_PYTHON` macro — real evidence *some* of CLO's internal data is exposed to its embedded Python environment, not just to the C++ plugin.
- The `PythonPluginAutoRegister` sample's own README states directly: *"CLO does not auto-execute Python files at startup."* A script registered through that mechanism still needs a human to click the menu item — it isn't a background/headless trigger.

**What that leaves unconfirmed:**
1. **Whether the embedded Python environment exposes the full automation surface** — import, measurement, simulate, export — or only UI/scene-editing conveniences. The `EXPORT_PYTHON` tags are suggestive, not proof. Cheapest way to resolve this: open that same editor and try something trivial, like printing what's available in scope — a two-minute test, not more searching.
2. **Whether it can be triggered headlessly** — launched by the worker with no human present — rather than only by someone opening the editor and clicking play. The one piece of evidence found so far (the auto-register README quote above) points *against* this for that specific mechanism. It doesn't rule out some other command-line/batch launch path, which hasn't been checked yet.

**Why it would matter if both turn out true:** a script running *inside* CLO's own process could call the same API functions directly and get a real blocking return — no HTTP layer, no 200ms timer, no polling at all, for anything triggered this way. That would be a genuinely simpler architecture than today's REST-plugin design, and it would sidestep Section 4's polling problem entirely rather than just mitigating it.

**Where this stands:** if (1) is true and (2) is false, this is a good tool for manually testing/debugging the measurement pipeline by hand, not a replacement for worker-driven automation. If both are true, it's worth a serious architecture conversation. Neither is confirmed yet — this is a flagged follow-up, not a recommendation to act on.

---

## 7. The three ways to run Step 1 — and the problems with that structure

**Q:** What all are the ways of calling the avatar generation pipeline, how is each triggered, where does their output get stored, and what's different for each (output files, worker or not, purpose)? Then: think like a senior developer critiquing this setup — what are the problems? And: why is the CLI reading measurements from a JSON file when I've never made one — does it read from MongoDB and just log a JSON file in the run output? What improvements should we make?

**A:**

**Confirmed directly in code:** the CLI (`run_avatar.py`) falls back to MongoDB automatically when no `--measurement-file` is given and no `clo_avatar_generation/input/<user_id>.measurements.json` exists — `user_measurements` first, then the legacy `measurements` collection (`step_03_fetch_measurements.py`). Whatever gets fetched is written out as `mongo_snapshot.json` inside that run's own output folder as a record, not supplied by the user as an input. If MongoDB itself is unreachable, it can fall further back to the *previous run's* saved `mongo_snapshot.json` as a last resort. So: four possible measurement sources in priority order — explicit file → default per-user JSON in `input/` → MongoDB `user_measurements` → MongoDB legacy `measurements` → stale local snapshot cache.

Yes: when run_avatar.py is run without --measurement-file, and there's no clo_avatar_generation/input/<user_id>.measurements.json sitting around, step_03_fetch_measurements.py falls through to MongoDB automatically — user_measurements first, then the legacy measurements collection. You've never had to hand-author a JSON file for a real user to work.

And yes — a JSON file does get created, but not by you, and not as an input. Whatever gets fetched (from wherever it came from) gets written out as mongo_snapshot.json inside that run's own output folder (ctx.log_json("mongo_snapshot", ...)), purely as a record of what was used. That's also why Section 4's _load_latest_local_snapshot() exists — if MongoDB itself is unreachable, the pipeline can fall back to the previous run's saved mongo_snapshot.json as a last resort. So "JSON file" here means "automatic output artifact," not "something you prepare."

One thing worth flagging right inside that same function, since it's relevant to what follows: there are actually four possible measurement sources, in priority order — explicit --measurement-file → default per-user JSON in input/ → MongoDB user_measurements → MongoDB legacy measurements → a stale local snapshot from some previous run, if MongoDB fails entirely. That's a lot of silent fallback stacked on one function, and it's the first thing worth critiquing below.

### Three ways to run the pipeline, all calling the same `run_pipeline()` underneath

| | CLI (`run_avatar.py`) | Worker (`run_avatar_job`) | `repeat_run_check.py` |
|---|---|---|---|
| Who triggers it | A person, by hand | A shopper, via the website → Redis queue | A person, by hand |
| Measurements from | A JSON file (or the Mongo fallback chain above) | MongoDB `user_measurements` | A JSON file |
| Base avatar / apply mode | Configurable via flags | Hardcoded | Configurable |
| Writes `clo_avatar_generation/output/` | Yes | Yes | Yes (×N) |
| Writes `dev_upload`/`live_upload` | No | Yes, via `save_avatar_version()` | No |
| Writes MongoDB (`avatar_jobs`, `avatar_profiles`) | No | Yes | No |
| Purpose | Manual dev/debug | Real production path | Reliability/QA measurement (runs N times, compares output file size to catch a race-condition save corrupting the mesh) |

### The critique

1. **Context construction is duplicated three times, by hand, with no shared source of truth.** Each of the three callers independently builds a `Step1Context`. No factory function any of them share. This is structurally why build-list item 1.4 exists ("CLI knobs unreachable from the worker") — three independent implementations will drift by default, not by accident.
2. **A production job can't be reproduced locally.** The worker hardcodes its inputs with zero pass-through from the actual job document — no way to take a specific failed shopper job and replay its exact inputs through the CLI. For a pipeline this expensive per attempt (CLO3D, concurrency=1, ~90s+), that's a real operational gap.
3. **The fallback chain is resilience that can silently produce a wrong result.** The last tier — falling back to a stale snapshot from a previous run when MongoDB is briefly unreachable — means a transient DB hiccup can silently regenerate an avatar from outdated measurements, with nothing louder than a log line marking it happened. Quietly serving wrong body measurements is arguably worse than failing the job outright.
4. **The CLI's implicit test-file convention is a footgun for real users.** A stale test JSON for a real `user_id` sitting in `input/` gets silently preferred over fresh MongoDB data, with no visible warning — just an easy-to-miss INFO log line.
5. **Nothing guards the two live code paths from drifting apart in behavior.** No test asserts that equivalent inputs through the CLI and the worker produce equivalent results.

### Proposed improvements, in order

1. **One shared context-building function** (e.g. `build_step1_context(...)`, parameterized by caller type) that all three callers become thin wrappers around. Fixes #1 and #5.
2. **Make failed worker jobs replayable** — persist what was actually resolved for a job (base avatar, apply mode, and the exact `mongo_snapshot.json` used) so a developer can hand it straight to the CLI for a deterministic repro. Highest-value fix for debugging time.
3. **Make non-primary measurement sources loud**, and reconsider whether the worker/production path should use the stale-snapshot fallback at all — failing the job outright on a DB outage is probably safer than silently serving stale data to a real shopper. Connects to architecture issue AR1 (the worker talking to MongoDB directly instead of through the backend) — fixing that properly would let the backend hand the worker a locked-in snapshot explicitly, removing the ambiguity rather than patching around it.
4. **A visible warning when the CLI picks up a test JSON file for what looks like a real user_id.**
5. **One regression test** asserting the CLI and worker paths build equivalent contexts for equivalent inputs, once #1 makes that testable.

**Decision:** a lot of surface area here — flagged for a dedicated, detailed discussion later rather than acted on immediately.

---

## 8. Step timing, the avt_patch flow confirmed, file-to-step map, parallelism, and a testing critique

**Q:** (1) Approx time per step from the last 5 complete runs of `u_001` (ignore failures). (2) `avt_patch` is the one in use now, right? (3) In simple language: avt_patch means copying the binary `.avt`, changing dimensions directly in the binary (`clo_payload.patched`), opening that in CLO3D, saving as `.zprj` from CLO, then making the `.glb` in CLO for Chrome — correct? (4) How is `result_avatar_from_project.avt` created, and which step made each output file? (5) Are we wasting time running all 3 apply paths/methods? (6) Is `normalize_targets` actually needed, or should the DB just save field names properly? (7) Can we parallelize / open a new project sooner? (8) What's the difference between readback and compute error? Plus: critique the pipeline's individual unit testing and the overall testing across worker, website, and CLI.

**A:**

**1. Timing (last 5 genuinely completed `u_001` runs: 072, 073, 075, 078, 081 — each confirmed ending "pipeline completed," not a failure):**

| Step | Avg | What it's doing |
|---|---|---|
| `step_01_health` | 4.2s | HTTP round-trip to confirm CLO's reachable |
| `step_02`–`step_06` | ~0s each | pure Python — fetch/normalize/build, no CLO involved |
| `step_07_import_base_avatar` | 14.8s | new project + the hardcoded 4s settle delay |
| `step_08_apply_measurements` | 20.4s | patch + import + `wait_for_queue` poll |
| `step_09_readback` | 6.2s | debug-state HTTP calls |
| `step_10_compute_error` | 0.0s | the permanent stub — does nothing CLO-side |
| `step_11_save_outputs` | 12.8s | project save + settle delay + verification |
| `step_12_export_glb` | 13.0s | CLO's export call |
| **Total** | **~71s** | |

~96% of total runtime is the five steps that actually talk to CLO (7, 8, 9, 11, 12). Steps 2-6 and 10 are free.

**2. Confirmed:** `avt_patch` is the one in use — both the CLI's default and the worker's hardcoded value. The other two (`csv`, `avatar_properties`) only run if someone explicitly passes `--enable-legacy-route`.

**3. Mental model confirmed, with one precise correction:** right about the binary patch → import → CLO makes the `.glb`. The correction: the `.zprj` save isn't incidental — **step 11 specifically triggers it**, then **re-opens that `.zprj` as a zip and extracts the `.avt` back out of it** for verification, rather than doing a fresh independent export. Full sequence: step 8 patches and imports the `.avt` → steps 9/10 attempt readback (mostly inert) → step 11 saves `result_project.zprj`, extracts the `.avt` from inside it, runs `verify_avatar_fields()` on the extracted copy → step 12 exports the `.glb` from the current scene, a separate later CLO call.

**4. `result_avatar_from_project.avt`** — created in step 11, by extracting the `.avt` member from inside the just-saved `.zprj` zip (`EXTRACTABLE_SUFFIXES` in `step_11_save_outputs.py`), not a direct export. Full file-to-step map:

| File | Created in |
|---|---|
| `run.log`, `mongo_snapshot.json` | step 2 / step 3 |
| `clo_payload.patched.avt` | step 8 |
| `result_project.zprj` | step 11 (the save) |
| `result_avatar_from_project.avt` | step 11 (extracted from the zprj) |
| `measurement_verification.json` | step 11 (verification against the extracted avt) |
| `error_report.json` | step 10 (always the stub) |
| `result_avatar.glb` / `result_avatar_packed.glb` | step 12 |

**5. Not wasting runtime — but some wasted prep exists.** `step_08`'s `run()` branches on `apply_mode` and calls exactly one of the three `_apply_via_*` functions, never all three; the timing data confirms no hidden cost from unused routes. However, `step_06_build_payloads.py`'s own docstring says it builds "payload artifacts for both apply routes," and its imports pull in CSV-bridge and property-field helpers regardless of which mode will run — cheap enough to round to 0.0s, but it is unnecessary code-complexity/maintenance surface.

**6. `normalize_targets` is necessary — it's doing real work, not just renaming.** `step_05` maps `mongo_field` (DB's name) to `clo_target` (CLO's name) — genuinely different vocabularies — applies decimal rounding, and tags `unit`/`apply_routes`. Storing CLO's own field names directly in the database instead would be worse: it would couple the schema to a third-party vendor's internal naming, which can change across SDK versions (as Section 5 already showed happens). Keep the translation layer; audit `field_contract.py`'s mapping table periodically instead.

**7. Parallelism — not meaningfully available, for two different reasons.** Within one run: steps 2-6 are already ~0s combined, so overlapping them with step 7 saves a fraction of a second at best, for real risk (firing "new project" before measurements are confirmed valid). Steps 7/8/11/12 are inherently serial — each depends on CLO's scene state left by the previous one. Across different runs/users: blocked by design — CLO3D is concurrency=1 (one main thread, one `QueueDrainTimer`). Real throughput gains would require multiple separate CLO3D instances on separate machines, each with its own worker — an infrastructure cost, not a code change.

**8. Readback vs. compute error — the timing makes the distinction concrete.** `step_09_readback` (6.2s) makes real HTTP calls, collecting whatever generic debug state CLO's plugin exposes. `step_10_compute_error` (0.0s) does nothing CLO-side at all — a stub precisely because readback never had real per-field measurement data to hand it. Readback = "collect what's available." Compute error = "try to grade it" — and currently can't, for exactly the reason readback couldn't supply what it needed.

### Testing critique

Checked directly: **zero test files exist anywhere for `clo_avatar_generation`, `avatar_runtime`, or `worker`.**

This isn't a small gap — the pipeline's own code comments describe real bugs that were only found by running it against real CLO3D and noticing something was wrong afterward: the `CLO_SETTLE_SECONDS` race (Part 15), the mesh-size-tolerance retry logic in `step_11` (CLO's internal mesh rebuild can race save-project and silently capture an incomplete mesh even though every API call reports success), and the avatar-leak bug that needed a whole new `/clear-avatars` endpoint. `repeat_run_check.py` exists specifically because there was no other way to detect this class of bug systematically.

What's missing, layered cheapest-first:
1. **Pure-Python unit tests for steps 2-6 and 10** — free, zero CLO dependency, currently entirely untested. `step_05` is a perfect example: deterministic transformation (rename/round/tag), fully testable with a fake Mongo doc, no CLO3D needed.
2. **`avt_patch.py`'s binary read/write/verify logic** — also free to test. A fixture with a known base `.avt` and expected patched bytes would catch a feature-index regression immediately (exactly the kind of thing that broke across the CSV/property/avt_patch experiments in Section 4) instead of discovering it 70 seconds into a real CLO run.
3. **No integration test connects worker → website → CLI as one system.** `scripts/smoke_e2e.py` explicitly skips anything CLO-dependent, so the one automated suite that exists deliberately excludes this entire pipeline.
4. **The CLO-dependent steps (7, 8, 11, 12) are the hardest to test and the only ones actually exercised — by hand, repeatedly, by a human watching the output.** A thin mock of `CLORestClient` returning canned responses would let `pipeline.py`'s orchestration logic (step ordering, failure handling, early-exit on a failed step) get tested without real CLO, leaving only the actual CLO integration as something verified by hand.

Bottom line: correctness currently rests entirely on "a human ran it and it looked right," for a process with at least three documented races/bugs already found exactly that way. Highest-value starting point: #1 and #2, since both cost nothing (no CLO needed) and catch the kind of silent data bug that's hardest to notice by eyeballing a rendered avatar.

---

## 9. GPU usage in CLO — simulation mode, and separately, the V-Ray render engine

**Q:** There was an option to use GPU for CLO3D — have we been using GPU? Search how we can speed up processes that take 10-15 sec. Follow-up: I've seen CLO used for rendering with GPU, like normal people do when showing off clothes — search about GPU usage in CLO itself, not our plugin directly.

**A:**

**Simulation-mode GPU — confirmed not used, and it wouldn't help the slow steps anyway.** CLO's SDK exposes `SetSimulationQuality(quality, simulationMode)` — `simulationMode`: 0 = CPU, 1 = FAST(GPU). Checked directly: **never called anywhere** in `RestPlugin_windows.cpp`, so CLO runs at its installed app's own default (CPU/Normal, per the SDK's own comment). More importantly: GPU simulation mode only affects the cloth-physics `Simulate()` call — and **Step 1 (avatar generation) never calls `Simulate()` at all.** The measured 10-20s steps (Section 8: `step_07` import, `step_08` apply, `step_11` save, `step_12` export) are I/O- and settle-delay-bound, not physics-computation-bound — GPU has nothing to accelerate there. `Simulate()` is only called in `clo_vto/native_vto/step_10_simulate.py` (Step 3, 150 steps, 5-minute timeout). CLO's own support community is explicit that GPU/FAST mode trades away real fabric accuracy and is meant for interactive building, not final output — not a free win even where it would apply, especially given Section 3's unresolved accuracy-validation gap.

What Google surfaced that's actually relevant to Step 1's real costs: CLO's own docs flag textures above 4000×4000px as a documented slowness cause in export/rendering — connecting back to Section 2/3's ~25 default character textures finding. Stripping/downscaling those may be a speed fix, not just a storage fix. But the real cause of the 10-20s costs is the hardcoded settle delays (`CLO_SETTLE_SECONDS`, `MESH_SETTLE_DELAY_SECONDS`) already found in Section 5 — a hardware/GPU change can't make a `time.sleep(4.0)` finish sooner; the fix is the real-completion-signal item already flagged (build-list 1.1).

**Separately — CLO's V-Ray render engine is real GPU-accelerated rendering, and it's a third, distinct thing Mirra doesn't use at all.** CLO has a built-in V-Ray (Chaos) render engine, reached through the **Render** menu, for producing a photorealistic **still image or video** of a garment (catalog/lookbook-style output) — not the same thing as the simulation-mode toggle above. Nvidia GPU (CUDA) rendering there is **2-6x faster** than CPU rendering per CLO's own docs; Apple Silicon (Metal) GPU rendering was added in CLO v2025.0.

This is not relevant to Mirra's current pipeline, and precisely why: every export step traced today (`step_12_export_glb.py`, `clo_vto`'s export steps) produces a `.glb` — raw geometry and textures — never a rendered image. The actual visual display happens **in the shopper's own browser**, via `three.js`/WebGL (`website/frontend/package.json`'s `@react-three/fiber`/`@react-three/drei`/`three`) — the shopper's device renders it live; CLO's job stops at exporting the asset. CLO's V-Ray render engine would only become relevant if the product needed CLO itself to generate a photorealistic photo/video of a try-on result, rather than handing the shopper's browser a live 3D model — a product decision, not a gap in the current pipeline.

---

## 10. Pattern shape is a fixed template — the photo never influences garment style, only its scale

**Q:** For which part of the pipeline are the researched training datasets (Sewformer/SewFactory, GarmentCodeData, etc.) actually good?

**A:**

Mapping them precisely required checking `product_ingestion/curve_config.py` directly, and it surfaced a real, previously-unnoticed gap.

**Confirmed: pattern *style* is a fixed template, never derived from the photo.** `curve_config.py`'s `ArmholeConfig` (and the other curve-shape dataclasses alongside it) hold values like `hollow_position_frac: float = 0.40`, `hollow_depth_frac: float = 0.18`, `shoulder_flare_frac: float = 0.05` — fixed defaults, only clamped to safe bounds in `__post_init__`, never set differently per garment based on what the segmented photo actually shows. Stage 5 (pattern generation) genuinely splits into two different things that happen to live in one stage:
- **Dimensions** — how big each panel is. Correctly, deterministically driven by the size chart. Already verified millimeter-exact (Section 2 of `03-step2-product-ingestion.md`). Should stay this way — not a target for any model.
- **Style/shape** — how deep the neckline curves, how the armhole is shaped, overall silhouette. **Currently a fixed template, every time.** Mirra cannot today tell a v-neck from a crew-neck tee from the photo — it always generates the same curve shape, just scaled to size.

**This is exactly where Sewformer/GarmentCodeData map, and exactly where the texture/draping datasets don't.** Mapped precisely to pipeline stages:

| Dataset group | Pipeline stage | What it would actually fix |
|---|---|---|
| DeepFashion2 / Fashionpedia / ModaNet / logo sets | Stage 2 (segmentation), Stage 4 (design extraction) | Better garment cutout, better logo/print detection |
| Sewformer / GarmentCodeData | Stage 5 — **style only, not dimensions** | Garments could vary in neckline/sleeve/silhouette instead of one fixed shape |
| CLOTH3D / DeepIron / Pattern-Coordinate Diffusion / synthetic CLO3D pairs | Stage 7 (texture projection) | The actual decided course-project contribution: fold-aware texture projection |
| VITON-HD / DressCode | None | Wrong task entirely — end-to-end image generation, not geometric reconstruction |

---
