# Known Issue — `set-fabric-graphic` silently drops `u`/`v`/`scale`

Status: **open, not fixed.** Found 2026-07-23 while reviewing
`plugin_contract.json`'s endpoint schemas against the actual Windows plugin
source. Pre-existing — introduced with the original fabric feature
(Anant, `patterns` branch), not caused by the recent merge.

---

## What the contract promises

`clo_workspace/plugin_contract.json`, `endpoint_schemas` →
`POST /set-fabric-graphic`:

```json
{
  "request":  {"pattern_index": "int", "graphic_path": "string", "u": "float[0-1]", "v": "float[0-1]", "scale": "float"},
  "response": {"success": "bool"}
}
```

`u`, `v`, and `scale` imply the graphic overlay can be positioned and scaled
on the pattern piece — distinct from a full texture replacement.

## What the code actually does

**The HTTP handler parses all three fields correctly**
(`RestPlugin_windows.cpp`, `POST /set-fabric-graphic`):

```cpp
cmd.param3      = j["pattern_index"].get<int>();
cmd.param1      = j["graphic_path"].get<std::string>();
cmd.floatParam4 = (float)j.value("u",     0.5);
cmd.floatParam5 = (float)j.value("v",     0.3);
cmd.floatParam6 = (float)j.value("scale", 1.0);
```

**But `ProcessCommandQueue`'s `"set-fabric-graphic"` branch never reads
`floatParam4/5/6` at all.** It calls:

```cpp
FabricDispatcher::dispatchTexture(fabric_idx, cmd.param1);
```

— the exact same function used for plain `set-fabric-texture`, which only
takes a fabric index and a file path. The handler's own comment says as
much: *"Dispatched identically to set-fabric-texture (base texture
replacement)."*

`FabricDispatcher` (namespace, ~line 383) only defines two functions:
`dispatchColor(fabric_idx, r, g, b)` and `dispatchTexture(fabric_idx, path)`.
**There is no `dispatchGraphic()` that accepts position/scale at all.**

## Impact

Any caller passing `u`/`v`/`scale` to `/set-fabric-graphic` gets a `200
{"success": true}` response — the request is accepted, queued, and
processed without error — but those three values are computed, stored in
the command struct, and then thrown away. The graphic always applies as a
full texture replacement identical to `/set-fabric-texture`, never as a
positioned/scaled overlay. There is currently no way to actually place a
graphic via this API, despite the contract and the request parser both
suggesting it's supported.

## Where

- Contract: `clo_workspace/plugin_contract.json`, lines 58–61.
- HTTP handler (parses u/v/scale, unused downstream): `RestPlugin_windows.cpp`,
  `svr.Post("/set-fabric-graphic", ...)`.
- Queue handler (drops u/v/scale): `RestPlugin_windows.cpp`,
  `else if (cmd.type == "set-fabric-graphic")` inside `ProcessCommandQueue`.
- Missing capability: `FabricDispatcher` namespace — no positioning-aware
  dispatch function exists for graphics.

Not checked yet: whether `RestPlugin_macOS.cpp`'s `set-fabric-graphic`
handler has the identical gap (it mirrors the Windows fabric feature
closely, so likely yes, but hasn't been verified line-by-line).

## Options going forward

1. **Implement it for real** — add a `dispatchGraphic(fabric_idx, path, u,
   v, scale)` to `FabricDispatcher` that actually positions/scales the
   overlay via the CLO fabric API, and call that instead of
   `dispatchTexture()` from the queue handler.
2. **Be honest about scope** — if per-pattern graphic placement isn't
   actually needed right now, drop `u`/`v`/`scale` from the contract's
   schema and stop parsing them in the HTTP handler, so the API doesn't
   advertise a capability that doesn't exist.

Either is fine; leaving the current mismatch (contract says one thing, code
does another) is the one option that isn't — it will cost someone real
debugging time the next time a graphic doesn't land where they told it to.

---

# Known Issue — First avatar-gen run after a CLO restart produces an undersized mesh

Status: **open, not fixed — needs more data before deciding on a fix.**
Found 2026-07-23 while reviewing Step 1 (avatar generation) test runs
`u_001-055`, `u_001-056`, `u_001-057`, `u_002-003` against the new v1.3.0
plugin build. Pre-existing race condition (documented since Phase 6,
`after-1-jun/plan-03.md`) — not introduced by the recent merge — but this
session gave the first concrete evidence for *when* it actually triggers.

## What happened

Of the 4 runs tested:

| Run | CLO session (`TraceLog` thread id) | Result |
|---|---|---|
| `u_001-055` | `tid=3956` — CLO launched 15:27:59, first request of that session | **Failed** |
| *(CLO's window went invalid at 15:31:36 — session ended/restarted)* | | |
| `u_001-056` | `tid=12056` — CLO launched 15:32:13, first request of that session | **Failed** |
| *(CLO's window went invalid at 15:34:27 — session ended/restarted again)* | | |
| `u_001-057` | `tid=23532` — CLO launched 15:35:47, first request of that session | Passed |
| `u_002-003` | same `tid=23532` session as `057`, no restart in between | Passed |

(Note: `u_001-054`, initially thought to be part of this test batch, is
actually a stale run from 2026-07-06 against the old v1.2.0 plugin —
unrelated, ignore it for this comparison.)

Both failures were the **first and only pipeline run of a freshly-launched
CLO session** (`EnsureWndProcSubclass: g_cloMainWnd is no longer a valid
window — clearing for rediscovery`, followed by a brand-new thread id and
window handle in the trace log — consistent with CLO having been fully
restarted, not just idle). Both passes happened once CLO had already
processed one avatar-gen run earlier in that same session.

## The known mitigation, and why it didn't fully help here

`step_11_save_outputs.py` (lines 23–31) already has a documented guard for
exactly this class of problem: *"CLO's internal mesh rebuild after an
avt_patch import isn't tracked by our command queue, so save-project can
race it and capture a structurally incomplete mesh even though every API
call reports success."* Mitigation: a 2.5s settle delay before each save
attempt, a structural size check (fail if >3% smaller than the base
avatar), and up to 3 retries.

Both failing runs exhausted all 3 retries — and notably, **the mesh-size
delta was identical across all 3 attempts within each run** (`055`: −9.18%
every time; `056`: −7.83% every time). If this were purely "CLO hasn't
finished rendering yet," a later attempt with more elapsed time should show
a smaller delta. It didn't move at all, which suggests the avatar had
already fully "settled" — just to a genuinely smaller/incomplete result —
by the first save attempt. That points toward CLO's rendering/mesh engine
needing its first request after a fresh launch to warm up (first shader
compilation, first mesh-rebuild cache population, etc.), rather than a pure
timing race that additional wait time would fix.

## Ruled out: this is not something the merge/rebuild broke

Checked the trace log for the actual `import-avatar-avt` calls in all 4
runs — every one shows exactly one clean `BEGIN`/`END` pair. The
double-call bug fixed during the merge (§3a in
`merge-followup-clo-workspace.md`) is confirmed gone and staying gone, in
both the failing and passing runs. The failure happens later, in the
Python-side save/verify step, which this session's plugin work never
touched.

## Where

- Mitigation code (settle delay / retry / tolerance check):
  `clo_avatar_generation/avatar_runtime/step_11_save_outputs.py:23-31`.
- Evidence: `clo_workspace/logs/plugin_crash_trace.log`, entries around
  15:27–15:38 on 2026-07-23 (thread-id changes + `EnsureWndProcSubclass`
  rediscovery lines mark each CLO restart).
- Original documentation of the race: `after-1-jun/plan-03.md`, Phase 6.

## Options going forward

1. Treat "first request after a CLO restart" specially — e.g. a longer
   initial settle delay, or more retries, only on the first pipeline run of
   a session.
2. Adopt a team norm: always run one throwaway avatar-gen after restarting
   CLO before trusting pipeline output for real work.
3. Gather more data first — 2 failures and 2 passes is a strong pattern but
   a small sample; worth confirming on a few more cold-launch runs before
   committing to a fix, since the identical-delta-across-retries detail is
   itself only from 2 data points.

No fix implemented yet — this is written up for decision, not applied.

---

# Known Issue — Step 2 segmentation completely broken: `transformers`/`rembg` never updated after the RMBG→SAM2 rewrite

Status: **fixed in `requirements.txt` (2026-07-23) — needs `pip install -r
requirements.txt` re-run + a real test to confirm.** Found while comparing
product-ingestion runs `c_001-s_001-003` (old, working) against `-004`/`-005`
(new, broken).

## What happened

`c_001-s_001-003` (2026-05-17, old `segmentation.py`): segmentation
succeeded via `"method": "rmbg-1.4"`, `area_percent: 90.81`; colour
extraction found a 5-color palette; design extraction found a graphic
(68.6% coverage). All 3 output files (`base_garment.png`, `colors.json`,
`graphic_diffuse.png`) generated.

`c_001-s_001-004` and `-005` (2026-07-23, same input image, rewritten
`segmentation.py`): **identical failure in both** —
`"method": "none"`, `"message": "All segmentation methods failed for this
image."`, colour/design/all 3 files `null`. Colour and design extraction
both depend on a valid segmentation mask, so one failure cascades into
three. Panel/DXF/SVG generation is unaffected (independent of segmentation,
confirmed by comparing `panel_metadata.json` between `003` and `005` — only
a negligible numeric difference, `sleeve_cap_cm`/`ease_cm` off by ~0.003,
unrelated to this issue).

## Root cause, confirmed directly

`product_ingestion/segmentation.py` was rewritten — RMBG-1.4 removed
entirely, replaced by a SAM2 → U²-Net fallback chain (`segment()`, ~line
317). Both methods are gated behind `try/except` import guards (`HAS_SAM2`,
`HAS_U2NET`, ~lines 42–54) that silently swallow import failures. Ran both
imports directly against the repo's actual `.venv`:

```
>>> from transformers import Sam2Processor, Sam2Model
ImportError: cannot import name 'Sam2Processor' from 'transformers'

>>> import rembg
ModuleNotFoundError: No module named 'rembg'
```

`requirements.txt` still pinned `transformers==4.39.3` (March 2024) —
released well over a year before Hugging Face added SAM2 support.
Confirmed via `transformers`' own GitHub release notes: **v4.56.0** (Aug 29,
2025) changelog explicitly lists *"Add Segment Anything 2 (SAM2) ... in
#32317"*; v4.55.0's changelog has no mention of it. So 4.56.0 is the
earliest release with `Sam2Model`/`Sam2Processor` at all. Separately,
`rembg` (needed for the U²-Net fallback) was never added to
`requirements.txt` in the first place, and isn't installed.

With both `HAS_SAM2` and `HAS_U2NET` false, `segment()` never attempts
either method — it falls straight through to `"none"`. **Not specific to
this image or these two runs** — it will fail on every image until the
environment is fixed. This is an environment/dependency gap, not a bug in
the new segmentation logic itself (untested whether the new logic actually
works correctly, since it's never been able to run at all).

## One more gap worth knowing (not fixed, just noted)

When both methods fail, `segment()`'s intermediate diagnostics (`print(f"⚠
SAM2 invalid ({result.message})...")`) only go to console — never captured
in `extraction_metadata.json`. From the saved run artifacts alone there's no
way to tell "dependencies missing" apart from "both models ran and
genuinely failed on this image." The only reason this got root-caused
today is that the imports were tested directly against the venv, outside
the pipeline. Worth having `SegmentationResult`/the final `"none"` case
capture the per-method failure reasons in the persisted metadata, so this
doesn't require a manual venv test again next time.

## Fix applied

`requirements.txt`:
- `transformers==4.39.3` → `transformers==4.56.0` (first version with SAM2;
  requires `torch>=2.2`, satisfied by the existing `torch==2.4.1` pin — no
  torch/torchvision bump needed).
- Added `rembg==2.0.77` (latest stable, for the U²-Net fallback).

**Not yet done:** `pip install -r requirements.txt` needs to actually be run
into the repo's `.venv/` to pick up these changes, and a real
product-ingestion run against the same input image needs to confirm
segmentation now succeeds (and ideally produces a comparable
`area_percent`/palette/design result to the old RMBG-1.4 baseline from
`003`, as a sanity check that the new SAM2/U²-Net path itself works
correctly once it can actually run).

## Where

- Fixed: `requirements.txt`.
- Broken code (silently swallows missing deps): `product_ingestion/segmentation.py:42-54` (`HAS_SAM2`/`HAS_U2NET` guards), `:317-337` (`segment()` orchestrator).
- Evidence: `product_ingestion/output/c_001-s_001-003/image_info/extraction_metadata.json` (working baseline) vs. `c_001-s_001-004` and `-005` (broken), plus direct `.venv` import tests.

---

# Known Issue — `requirements.txt` torch/torchvision pins don't match what's actually installed (CUDA vs. plain)

Status: **decision made (plain CPU torch, for now) — not yet fully applied
to the `.venv`.** Surfaced 2026-07-23 while trying to `pip install -r
requirements.txt` after the fix above.

## What happened

Running `pip install -r requirements.txt` failed:

```
ERROR: Cannot install torch==2.4.1 and torchvision==0.19.1+cu121 because
these package versions have conflicting dependencies.
The conflict is caused by:
    The user requested torch==2.4.1
    torchvision 0.19.1+cu121 depends on torch==2.4.1+cu121
```

Checked the actual `.venv`:

```
.venv/Lib/site-packages/torch-2.4.1+cu121.dist-info
.venv/Lib/site-packages/torchvision-0.19.1+cu121.dist-info
```

This machine has the **CUDA (NVIDIA GPU)** builds installed, but
`requirements.txt` has always pinned the plain, non-CUDA version strings
(`torch==2.4.1`, `torchvision==0.19.1`, no `+cu121`). Under Python's version
matching rules a bare `==2.4.1` does not match an installed `2.4.1+cu121` —
they're different exact versions to the resolver. This mismatch was already
latent in the file; it had never been triggered before because a plain
`pip install -r requirements.txt` run previously had nothing new to
resolve, so pip never re-examined torch/torchvision at all. Adding
`rembg`/bumping `transformers` (see the segmentation entry above) forced a
real dependency resolution for the first time, which is what exposed it —
not something either of those changes caused directly.

## Why this can't be "just fix the version string" cleanly

CUDA only exists for NVIDIA GPUs. A `+cu121` wheel cannot be installed on a
Mac (Apple Silicon has no CUDA) — `segmentation.py` itself already expects
this (`# Device priority: MPS → CUDA → CPU`). So there was never going to be
one pinned version string that installs identically, with full GPU
acceleration, on every collaborator's machine. The two real options:

1. Pin to `+cu121` explicitly + add `--extra-index-url
   https://download.pytorch.org/whl/cu121` (PyPI's default index doesn't
   host `+cu121` wheels) — keeps GPU speed on this machine, but Mac
   collaborators would need to install torch/torchvision separately first
   (from the default index, no suffix) before running this file.
2. Drop back to plain torch/torchvision — one command works identically on
   every OS, but loses GPU acceleration for SAM2 (and anything else using
   `torch`) on machines that do have an NVIDIA GPU, like this one.

## Decision

**Went with option 2 (plain) for now** — `requirements.txt` already had the
plain pins (no edit needed there); CUDA support is deferred to a later
decision, not abandoned. Chosen for a single, universal install command
over GPU speed on this machine, for the moment.

## Not yet done

The `.venv` still physically has the `+cu121` builds installed. Running
`pip install -r requirements.txt` again should cause pip to replace both
`torch` and `torchvision` with their plain CPU wheels automatically (since
both pins are now consistently plain, they're mutually satisfiable without
needing the old `+cu121` builds at all) — but this hasn't actually been run
and confirmed yet. If pip still complains, the fallback is manually
uninstalling first: `pip uninstall torch torchvision -y`, then re-running
`pip install -r requirements.txt`.

## Where

- `requirements.txt`: `torch==2.4.1`, `torchvision==0.19.1` (unchanged,
  already plain).
- Reference for the CUDA option, if revisited later: PyTorch's CUDA wheels
  are hosted at `https://download.pytorch.org/whl/cu121`, not on PyPI's
  default index.

---

# Known Issue — `rembg==2.0.77` requires numpy 2.x, conflicting with the project's `numpy==1.26.4` pin

Status: **fixed in `requirements.txt` (2026-07-23) — needs a real install +
test to confirm.** Surfaced immediately after fixing the torch/torchvision
conflict above — same `pip install -r requirements.txt` attempt, next error
in the chain.

## What happened

```
ERROR: Cannot install ... and numpy==1.26.4 because these package versions
have conflicting dependencies.
The conflict is caused by:
    The user requested numpy==1.26.4
    ...
    rembg 2.0.77 depends on numpy<3.0.0 and >=2.3.0
```

`rembg==2.0.77` (the version originally pinned for the U²-Net fallback, see
the segmentation entry above) requires `numpy>=2.3.0`. `numpy==1.26.4` is
pinned project-wide and depended on by `opencv-python`, `scikit-learn`,
`torch`, `torchvision`, and `transformers`. Bumping numpy to a 2.x major
version to satisfy one fallback dependency would be a much bigger, riskier
change than picking a different `rembg` version — a numpy major-version
bump can ripple across the entire numeric/ML stack.

## Root cause, and the fix

Checked rembg's actual release metadata on PyPI directly, release by
release, to find exactly where the numpy constraint was introduced:

| Version | Release date | numpy constraint |
|---|---|---|
| 2.0.65 | 2025-03-17 | none (`"numpy"`, unconstrained) |
| 2.0.67 | 2025-07-05 | none (`"numpy"`, unconstrained) |
| 2.0.70 | 2026-01-03 | `numpy<3.0.0,>=2.3.0` |
| 2.0.75 | 2026-04-08 | `numpy<3.0.0,>=2.3.0` |
| 2.0.77 | 2026-07-18 | `numpy<3.0.0,>=2.3.0` (originally pinned) |

**Fix:** repinned to `rembg==2.0.67` — the most recent release with no
numpy constraint at all, avoiding the conflict entirely without touching
`numpy` or anything that depends on it. The public API used by
`segmentation.py` (`new_session`, `remove`) is a long-standing, stable part
of rembg's interface and not expected to differ between 2.0.67 and 2.0.77.

## Not yet done

Not yet re-run `pip install -r requirements.txt` to confirm this resolves
cleanly end-to-end (this was the second conflict found in sequence — there
could plausibly be a third if something else in the graph also assumed a
newer package). Confirm the full install succeeds, then run product
ingestion again per the segmentation entry above.

## Where

- `requirements.txt`: `rembg==2.0.77` → `rembg==2.0.67`.

---

# Known Issue — `transformers==4.56.0` bump silently breaks CLIP-based view selection (torch>=2.6 required for non-safetensors checkpoints)

Status: **open, NOT fixed** — reproduced and root-caused, but per instruction
we're only testing/reporting right now, not patching. Found while checking
whether product-ingestion run `c_001-s_001-007` was fully clean.

## What happened

`007`'s `run_summary.json` shows `"selection_reason":
"clip_unavailable_fallback_first_image"` — every prior run showed
`"best_front_view"` with real CLIP confidence scores. Segmentation itself
succeeded in `007` (the fix from the segmentation entry above worked), but
the CLIP-based view-selection step silently stopped working and fell back
to "just use the first image in the folder."

This particular run only had 1 image in `c_001`, so the fallback picked the
same image CLIP would have anyway — no visible difference in `007`'s
output. **This would matter a lot on any cloth folder with multiple images**,
since the fallback doesn't classify anything — it just grabs whichever file
sorts first (see the image-count question below).

## Root cause, confirmed by reproducing it directly

`view_selection.py:105-108` wraps the CLIP call in a bare
`except Exception: views = []` with no logging at all — so the real error
never reaches `run_summary.json`, `extraction_metadata.json`, or console.
Ran it manually against the actual `.venv` to surface the real exception:

```
ValueError: Due to a serious vulnerability issue in `torch.load`, even with
`weights_only=True`, we now require users to upgrade torch to at least v2.6
in order to use the function. This version restriction does not apply when
loading files with safetensors.
See the vulnerability report here https://nvd.nist.gov/vuln/detail/CVE-2025-32434
```

Raised from `garment_router.py:98`, `CLIPModel.from_pretrained(self.model_name)`.
`transformers==4.56.0` (bumped for SAM2, see the segmentation entry above)
added a hard guard: it refuses to load a checkpoint via `torch.load` unless
`torch>=2.6`, unless the checkpoint is in safetensors format. This repo's
`torch==2.4.1` doesn't meet that. So the `transformers` bump that fixed Step
2's segmentation broke Step 2's view selection at the same time.

**Verified a fix exists, but did not apply it** (testing-only mode):
`CLIPModel.from_pretrained(self.model_name, use_safetensors=True)` loads
successfully — `openai/clip-vit-base-patch32` ships both checkpoint formats,
so forcing safetensors sidesteps the torch-version guard entirely without
touching `torch` itself. Confirmed this loads and that
`view_selection.run_view_selection(...)` would need this one-line change at
`garment_router.py:98` to work again. **Not applied — reverted back to the
original code**, per instruction to report only, not fix, right now.

## Same silent-failure pattern as the segmentation issue

Second time today a bare `except Exception` has hidden the real cause of a
`transformers` version-related failure from every persisted artifact,
requiring a manual reproduction outside the pipeline to find. Worth fixing
both call sites' error handling at some point (log the actual exception,
even if the fallback behavior stays the same) — not just this one instance.

## Where

- Broken: `garment_router.py:98`, `CLIPModel.from_pretrained(self.model_name)` — needs `use_safetensors=True` (verified working, not applied).
- Silent failure: `view_selection.py:105-108`, bare `except Exception: views = []`.
- Caused by: `requirements.txt`'s `transformers==4.56.0` bump (segmentation entry above) — same root change, second regression from it found today.
- CVE reference: https://nvd.nist.gov/vuln/detail/CVE-2025-32434

---

# Known Issue — Step 3 (VTO) has a stale-scene safety check after `new-project`; Step 1 (avatar generation) does not

Status: **open, not fixed — testing/reporting only.** Found while checking
two consecutive `clo_vto` runs today: `base-1__native_vto_report.json`'s
second run failed at `step_05_verify_patterns` with `"loaded_patterns": 8`
(expected 4) — leftover patterns from the previous run were still in CLO's
scene when this run's `new-project` fired. That prompted checking whether
Step 1 has the same exposure.

## Both pipelines share the same underlying race

`new-project` is queued and its own drain is "best-effort" — the plugin's
command queue reporting empty doesn't guarantee CLO's *internal* scene
teardown has actually finished. `clo_vto/native_vto/step_02_new_project.py`
says this outright in its own comment:

```python
# Queue the command and move on immediately — CLO wipes all existing state
# when it processes new-project.  The drain is best-effort only; subsequent
# steps do their own waits so this step must never gate on queue drain.
ok = print_result(ctx.client.new_project(), "new-project")
try:
    ctx.client.wait_for_queue(timeout=30)
except Exception as exc:
    print(f"  [WARN] new-project queue drain timed out ({exc}) — CLO may still be resetting; proceeding.")
```

`clo_avatar_generation/avatar_runtime/step_07_import_base_avatar.py` calls
`new_project()` then `wait_for_queue(timeout=30)` the exact same way — same
race, same lack of a guarantee that the scene actually cleared before the
next step imports into it.

## Where they diverge: only Step 3 checks afterward

`clo_vto/native_vto/step_05_verify_patterns.py`:
```python
ctx.loaded_patterns = status.get("patterns_loaded", 0)
if ctx.loaded_patterns != len(ctx.pattern_files):
    print("  Pattern count mismatch - expected all 4 pieces. Aborting.")
    return False
```
This is exactly what caught today's stale-scene run — loud failure, pipeline
stopped before arrangement/fabric/seams ever ran.

`clo_avatar_generation/avatar_runtime/step_07_import_base_avatar.py` has no
equivalent. After the import call, it only checks whether *that specific
call* reported success:
```python
success = bool(avatar_result.get("success")) and bool(
    native_debug.get("native_avatar_import", {}).get("success")
)
```
There's no check on how many avatars/objects actually exist in the scene
afterward — and there structurally can't easily be one right now, since
`GET /avatars/state` (`GetAvatarCount`) is the endpoint disabled on Windows
due to the SEH crash documented in `POST_MORTEM_v1.1.1.md`. So if a previous
session's leftovers were still present when Step 1's `new-project` fired,
nothing in the pipeline would currently notice or abort — it would most
likely proceed silently.

## Confidence level

This is a **code-comparison finding, not a reproduced failure** — unlike the
Step 3 case (which failed live, today, with a captured report), Step 1
hasn't actually been observed hitting this. It's a real, structural gap
(same race present, no safety net present) rather than a confirmed live bug.

Separately, this is **not** the same issue as the earlier "first avatar-gen
run after a CLO restart produces an undersized mesh" entry above — that one
only happens on a *freshly launched* CLO session (nothing to leave residue
from). This one would only matter mid-session, between two pipeline runs
sharing the same still-open CLO instance.

## Where

- Shared race, Step 3: `clo_vto/native_vto/step_02_new_project.py`.
- Shared race, Step 1: `clo_avatar_generation/avatar_runtime/step_07_import_base_avatar.py`.
- Step 3's safety net (present): `clo_vto/native_vto/step_05_verify_patterns.py`.
- Step 1's missing equivalent: no file — this is an absence, not a broken function.
- Why Step 1 can't easily add the same check: `GET /avatars/state` disabled on Windows (`.claude/research/step-1/POST_MORTEM_v1.1.1.md`).
- Evidence of the underlying race actually firing: `clo_vto/output/base-1__native_vto_report.json`, run at `2026-07-23T11:29:18Z`, `"loaded_patterns": 8` vs expected 4.
