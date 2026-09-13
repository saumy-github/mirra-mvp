# 02 — Remaining build list, by pipeline step

Status: *compiled from source docs, verified against current code, nothing executed*
Compiled: *2026-08-30*
Last revised: *2026-08-30, after review — priorities set*
**Sources:** `.agent/saumy/01-previous-info.md`, `.agent/website-launch/`, `.agent/website-launch-2/`

Read from all three sources, then verified each claim against the current code — a lot of what those docs list as "remaining" has since landed. Below is only what is **actually still open**.

Priority column reflects the review on *2026-08-30*.

---

## Step 1 — Avatar generation

| # | Item | Priority | Source / state |
|---|---|---|---|
| 1.1 | **Replace the 4s guessed settle with a real completion signal.** `step_07` uses `CLO_SETTLE_SECONDS = 4.0`, a measured guess. Recommended approach: poll the output file for size stability. | **Later** — not high priority, long job | doc 11 §22 |
| 1.2 | **Delete `_pack_self_contained_glb` + `_is_binary_glb` fallback.** Still present (`step_12_export_glb.py:49,163`). | **Blocked** — VTO not tested yet; the garment-loaded run is the evidence this was waiting on | doc 11 §29 |
| 1.3 | **`ctx.write_json()` has zero callers.** Exists at `context.py:84`, nothing uses it. Every structured payload goes through `log_json()` into the text log — greppable, not machine-readable. | **Approved for removal** | doc 13 §42 |
| 1.4 | **CLI knobs unreachable from the worker.** `run_avatar_job` hardcodes base avatar, `apply_mode="avt_patch"`, no field filters, `measurement_file_input=None`. Only `user_id` varies, so a web run can't be reproduced from the CLI. | Debuggability gap, not blocking | doc 13 §41 |
| 1.5 | **Confirm the settle holds under sustained worker-driven load.** | **Later** — will test from the website once the pieces below are in place | doc 11 §23 |

---

## Step 2 — Product ingestion

| # | Item | Priority | State |
|---|---|---|---|
| 2.1 | **No logging at all.** 41 bare `print()` calls in `run_product_ingestion.py`, zero `getLogger`, no `run.log` written. | **Approved** — port Step 3's `RunLog` tee (not Step 1's logger; Step 2 needs third-party stdout captured) | verified open |
| 2.2 | **Cloth input folders.** `c_001`–`c_005` present, one image each. | **Done** — next is running them and improving output quality | verified 2026-08-30 |
| 2.3 | **Nested output layout not migrated.** `run_manifest.py` is rewritten for `<cloth>/<size>/<NNN>/`, but all 9 folders on disk are still flat `c_001-s_001-001`. `list_product_runs()` sees zero runs. | **Blocking** — `get_latest_product_run_dir()` fails for every pair, so website try-on cannot run | verified |
| 2.4 | **Segmentation gate before the bulk run.** A failed segmentation sets `image_status: "failed"` and carries on — the run still reports success. Ingest each cloth once, check `extraction_metadata.json`, then run the other 45. | Do before the 50 runs | doc 13 Phase 4 §5 |
| 2.5 | **`edge_manifest.json` fallback is silent.** Ingestion does generate the manifest, and paths line up. But a missing *or incomplete* manifest falls through to `DEFAULT_SEAMS` — 12 seams hardcoded for one 4-panel t-shirt — with no log line saying so. | Log which tier answered; set `allow_seam_fallback=False` on the worker after 2.4 | doc 14 §6 |

---

## Step 3 — Virtual try-on

| # | Item | Priority | State |
|---|---|---|---|
| 3.1 | **Render caching / reuse doesn't exist.** `request_render()` inserts and enqueues unconditionally — no lookup for an existing `ready` render on `(avatar_profile_id, cloth_id, size_id)`. Every repeat request is a fresh full CLO run. | **Open** — largest genuinely-open Step 3 item | verified open |
| 3.2 | **`default_panels/dxf/`** holds `front_panel`, `back_panel`, `sleeve_left`, `sleeve_right`. Names match `DEFAULT_SEAMS`. | **Done** — but panels are dated 2026-08-30 and `edge_manifest.json` is 2026-08-07; one CLI run needed to confirm edge indices still match | verified 2026-08-30 |
| 3.3 | **Texture step cannot fail.** `step_12_texture_glb.py` has eight `return` statements, all `return True`; three sit inside bare `except Exception`. A "successful" run carries no information about whether textures applied. | Needs a real run opened in a viewer, plus a deliberate break to prove failure is visible | docs 16 / A4 |
| 3.4 | **`use_default_panels` should become CLI-debug-only.** | **Agreed** — remove the backup entirely once panel generation is sorted | doc 13 Phase 6 §3 |
| 3.5 | **Strict knobs never set on the worker path.** `allow_seam_fallback`, `strict_seam_hash`, `strict_dxf_units` are exposed on the CLI but the worker passes none, so every shopper render takes the permissive path. | Flip `allow_seam_fallback`/`strict_dxf_units` after 2.4 | verified |
| 3.6 | **Test matrix never run:** 25 VTO runs. | **Last thing** — pass for now | doc 13 §49 |

---

## Security / launch-readiness

Google OAuth removed from this list — **added and tested working, *2026-08-30*.**

| # | Issue | State |
|---|---|---|
| S1 | **`/docs`, `/redoc`, `/openapi.json` are wide open.** `main.py:40` has no `docs_url`/`redoc_url`/`openapi_url` gating and no env check. Neither CORS nor `get_identity` protects them. All three must be disabled together | Not started |
| S2 | **No rate limiting anywhere.** Zero matches for `slowapi`/`rate_limit` in the backend. Applies to auth endpoints *and* to avatar/VTO generation, where one request costs ~90s of exclusive CLO time | Not started |
| S3 | **No brute-force protection** on login | Not started |
| S4 | **Production `ACCESS_TOKEN_SECRET`** — `config.py` now enforces `min_length=32` with no default, so a missing value fails startup. Remaining work is provisioning the real one | Partially closed |
| S5 | **`COOKIE_SECURE=true` and `CORS_ORIGINS`** locked to the real domain must be *verified* in the deployed environment, not just configured | Not started |
| S6 | **Refresh-cookie behaviour across the Vercel↔Render domain boundary is untested.** Different domains in production; if refresh fails cross-domain, `SameSite`/domain settings need revisiting | Not started |
| S7 | **No CSP or security headers** on the frontend | Not started |
| S8 | **No monitoring/logging for auth failures or API errors** | Not started |

---

## Architecture

| # | Issue | Impact | Effort |
|---|---|---|---|
| AR1 | **Worker talks to MongoDB Atlas directly.** Three touchpoints: 11 collection ops in `tasks.py`, a hidden `find_one`+`replace_one` inside `_materialize_profile()`, and the pipeline's own connection in `step_03`. Needs ~5 `/internal/*` endpoints — and a service-auth scheme the backend does not have | High | High |
| AR2 | **`/me` route sprawl.** Five things called "me" across three routers; `users` and `user-measurements` differ by one character. Two genuinely dead ops: `PATCH /users/me`, `GET /user-measurements/me` | Medium | Low |
| AR3 | **Measurement fields defined six times** across Python and TypeScript, with ranges disagreeing on every field. Agreed fix: contract JSON as single source, generated TS file, one drift test | High | Medium |
| AR4 | **Backend enforces no measurement ranges** — `gt=0` only. A direct `PUT` can store a 400cm height that fails ~90s later inside CLO | High | Low |

---

## Frontend / performance

| # | Issue | Cost | Effort |
|---|---|---|---|
| F1 | **GLB re-downloads ~66 MB on every mount.** The route sends `immutable` cache headers, but the authed blob fetch creates a new object URL each mount, defeating both the HTTP cache and `useGLTF`'s own cache. Fix: cookie-auth this one route | Very high on real networks | Medium |
| F2 | **`ProfileAvatar` chunk is 997 kB** (271 kB gzip) — `three` + `@react-three/fiber` + `@react-three/drei`. Verified: no `lazy()` or dynamic `import()` in `ProfileAvatar.tsx` | High for that route | Low |
| F3 | **Zero `loading="lazy"`** across 12 `<img>` sites. Studio's product rail renders one thumbnail per catalog item, all eager — scales directly with catalog size | Medium, grows with catalog | Very low |
| F4 | **Home's 7 sections are one eager chunk** (~99 kB JS + 39 kB CSS). GSAP, Lenis, and a WebGL liquid-metal shader in a badge all mount unconditionally. ~252 kB gzip cold | Medium, marketing only | Medium |
| F5 | **`rotate-ccw` shared icon chunk, 45.84 kB gzip** — larger than the entire Home chunk. Unresolved whether it's genuine Rollup chunking or a `lucide-react` barrel import defeating tree-shaking | Medium | Low to investigate |
| F6 | **3D viewer presentation pass** — environment/IBL lighting, a floor, richer studio treatment. Camera framing and lighting rig already done | Cosmetic | Medium |

---

## Operational

| # | Issue | Decision |
|---|---|---|
| O1 | **`output/` retention** — `scripts/prune_output.py` exists, never run. Policy: keep last 3 runs per key, never the newest, nothing under 7 days, tiered deletion (drop `.zprj`/`.avt`, keep `run.log`/`run_summary.json`/`.glb`). Applies to `clo_*/output/` only — **never** `dev_upload/` | **Keep, don't use.** Deletion stays manual during development; implement properly later |
| O2 | **Guest flow** — no guest→Google merge, no TTL, no cross-device continuity | **Later** |
| O3 | **No migration** for real-user data in the old `measurements` collection | **Later** |
| O4 | **No object storage bridge** — `dev_upload`/`live_upload` are local-disk only, unreachable from a Render-hosted backend | **Later** |
| O5 | **`mirra_measurements/`** — imported by `step_03_fetch_measurements.py:150` (Step 1 fetch), `run_product_ingestion.py:42` (Step 2 live path), `garment_measurements.py`, and holds `seed_cloths.py`, the only thing that seeds the `cloths` collection | **Cannot delete — load-bearing.** It's an AR3 consolidation question; revisit after AR1 removes the worker as a consumer |
