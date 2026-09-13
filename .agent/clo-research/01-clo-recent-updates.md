# CLO3D Recent Updates — Research

Research conducted 2026-08-29. Findings below are as of this date; the CLO SDK changelog and download pages can change without notice, so treat version/date facts as a snapshot, not a guarantee of currency.

## What Mirra currently targets

- The custom REST automation plugin (`clo_workspace/`) is currently at plugin version **1.3.2**, built against **CLO_SDK_v2026.0.356_WIN (SDK v10.0.3)** — `clo_workspace/versions/v_1.3.2.json:33`.
- That same note records that the **CLO3D application** installed and driving the pipeline was upgraded to **2026.1.188 on 2026-08-15** — `clo_workspace/versions/v_1.3.2.json:33`. The plugin that had been built against the prior SDK generation (2025.2.368) hung CLO permanently on `NewProject()` after that app upgrade, which is why the plugin was rebuilt against SDK v10.0.3 — same citation.
- The v1.3.2 notes explicitly connect the rebuild to a Qt migration: "matching the Qt 6.10 migration the vendor changelog requires a rebuild for" — `clo_workspace/versions/v_1.3.2.json:33`.
- Plugin history (`clo_workspace/versions/v_1.3.1.json:14-19`) shows the export path was fixed in v1.3.1 to call the SDK's `ExportGLB()` function directly (previously it called `ExportGLTF(..., bGLBinary=true)`, which silently produced JSON glTF with embedded base64 buffers, not real binary GLB, despite reporting success). Export scale was also corrected from `1.0f` to `0.001f` to match the SDK's documented mm→m default for glTF/GLB.
- `clo_vto/native_vto/client.py` shows the plugin surface Mirra depends on: avatar import (`/import-avatar`, `/import-avatar-avt`, `/import-avatar-measurements`), pattern import (`/import-pattern` — DXF), project lifecycle (`/new-project`, `/save-project`), arrangement (`/arrange-pattern`, `/arrangement-list`, `/pattern-arrangements`), fabric (`/set-fabric*`), seaming (`/create-seam`), simulation (`/simulate`), export (`/export`, format `glb`/`gltf`), and status/health polling (`/status`, `/health`, `/avatars/state`, `/capabilities`). None of these are official CLO REST endpoints — they are Mirra's own plugin wrapping CLO SDK C++ calls.
- **Important mismatch to flag**: the plugin was rebuilt against SDK v10.0.3, whose corresponding CLO application build is **2026.0.356** per the official SDK download page (see table below) — not 2026.1.188, which is the application version actually running per Mirra's own note above. That means Mirra's currently-running CLO app (2026.1.x) is a minor version ahead of the SDK generation (2026.0.356 / v10.0.3) the plugin was actually built and linked against. See "Breaking changes and ABI risk" below.

## Release timeline

All version/date data below comes from the official CLO API changelog (`developer.clo3d.com/changelog.html`) and download page (`developer.clo3d.com/download.html`). The changelog only prints month/year, not exact day, for each entry — see Open Questions.

| SDK version | Corresponding CLO app version | Release date (month precision only) | Relevance to Mirra | One-line summary |
|---|---|---|---|---|
| v9.1.0 | (2025.2.x series) | December 2025 | Low | Normal blending method, TopStitch APIs, library tab customization. |
| v9.1.1 | (2025.2.x series) | March 2026 | Low | Print layout nesting, improved avatar import, render property controls. |
| v10.0.0 | 2026.0.238 | May 2026 | Medium | New graphic-style/UV-tile APIs; removed `GetFabricSize` from Fabric API. |
| v10.0.1 | 2026.0.262 | May 2026 | Low | Crash fixes only (Library Window on macOS, smooth curve tool, Alembic export, Windows launch crash). |
| v10.0.2 | 2026.0.312 | June 2026 | Medium | Completed Qt 6 migration (Qt 6.10.x); fixed graphic placement export in headless mode; `SetColor`-by-name fix. |
| **v10.0.3** (Mirra's current target) | **2026.0.356** | July 2026 | — (baseline) | GLB export z-offset / missing "source" texture field fixes; **removed** `ImportPatternCPX`, `ExportPatternCPX`, `ConvertPatternJSONToCPX`, `ReDrape3DArrangement`; fixed headless `.zmod` persistence and an authentication registry-path error. |
| v11.0.0 | 2026.1.224 | August 2026 | **High** | New geometric-data/grading/pattern-utility/material-property APIs; **re-introduced** Pattern CPX APIs and `ReDrape3DArrangement` (removed one cycle earlier in v10.0.3); removed `GetNestingBufferSpacing`; explicit warning about `LibraryWindowInterface` startup crashes **on CLO 2026.1+**; sample projects updated to Qt 6.10.3. |

Since Mirra's plugin (v1.3.2 / SDK v10.0.3, mapped to app 2026.0.356), one further SDK generation has shipped: **v11.0.0**, mapped to app **2026.1.224** — which is the release line matching the 2026.1.188 application Mirra is actually running against a plugin still built for 2026.0.356.

## Changes that affect us

### SDK/API changes
- v10.0.0 removed `GetFabricSize` from the Fabric API. Mirra's client does not call this directly (no reference in `client.py`), so likely no impact, but worth a grep of the C++ plugin source if fabric sizing is read anywhere.
- v11.0.0 adds new "pattern utility APIs" and "geometric data structures" per the changelog summary — described only at a high level by the source (no exact function names surfaced by the fetch). This could plausibly replace hand-rolled bbox/line-length pattern introspection Mirra currently does via `/patterns/{index}/bbox` and `/patterns/{index}/line-lengths` in `client.py:259-266`, but the exact API names were not confirmed (see Open Questions).
- Source: https://developer.clo3d.com/changelog.html (official)

### Plugin ABI / build-toolchain changes
- v10.0.2 (June 2026) "completed Qt 6 migration" of the CLO SDK to Qt 6.10.x.
- v11.0.0 (August 2026) further raised the *sample* project's minimum Qt version to 6.10.3 and updated the sample CMake project version to 2026.1.224.
- This lines up with Mirra's own note that a Qt 6.10 migration forced the v1.3.2 plugin rebuild (`clo_workspace/versions/v_1.3.2.json:33`) — i.e., Mirra's account of *why* it had to rebuild is corroborated by the official changelog's Qt migration entries.
- Source: https://developer.clo3d.com/changelog.html (official)

### Avatar format / avatar API changes
- No avatar file-format (`.avt`) changes were surfaced in the fetched changelog entries for v10.0.0–v11.0.0. v9.1.1 (March 2026, one generation before Mirra's baseline) mentions "improved avatar import" but no specifics were returned by the fetch.
- Source: https://developer.clo3d.com/changelog.html (official) — not independently verified beyond the summarized fetch.

### glTF/GLB export changes
- v10.0.3 (Mirra's current baseline) fixed a GLB export "graphic z-offset issue" and a "missing 'source' field in textures" bug, plus a colorway flag being ignored by `ExportRenderingImage`. **These post-date the export bugs Mirra itself already found and worked around in plugin v1.3.1** (`clo_workspace/versions/v_1.3.1.json:14-19` — the `ExportGLTF` vs `ExportGLB` confusion and the 1.0/0.001 scale bug). Since Mirra's plugin is built against SDK v10.0.3, these particular v10.0.3 fixes should already be present in the SDK Mirra links against — but this was not independently verified against actual SDK header/changelog diff text, only the plugin's own version notes plus the vendor changelog summary.
- No further GLB/glTF changes were reported for v11.0.0.
- Source: https://developer.clo3d.com/changelog.html (official)

### DXF import changes
- No DXF-specific changelog entries were found in v10.0.0 through v11.0.0. Mirra's `/import-pattern` DXF path (`client.py:69-71`) does not appear to be affected by anything in the researched window, but this is an absence of evidence, not confirmed absence of change — the changelog fetch was a summarized pass, not a full-text audit.

### Simulation engine changes
- Nothing simulation-specific was surfaced in v10.0.0–v11.0.0 changelog entries. Not independently confirmed either way.

### Headless / automation / batch operation
- v10.0.2 fixed a "graphic placement export type in headless mode" bug.
- v10.0.3 fixed "headless `.zmod` persistence" and an "authentication registry path error" — both headless-mode issues, and both **directly relevant** to Mirra's unattended pipeline model, though the exact failure mode wasn't detailed in the summarized fetch.
- No dedicated new "official automation API" (e.g., a documented REST/automation layer replacing custom plugins) was found. Mirra's own REST plugin remains a bespoke solution; nothing in the researched changelog suggests CLO now ships an equivalent out of the box.
- Source: https://developer.clo3d.com/changelog.html (official)

## Breaking changes and ABI risk

**Loudest finding: version skew between Mirra's plugin build target and the app it now runs against.** Mirra's plugin v1.3.2 is built against SDK v10.0.3, which the official download page maps to CLO application build **2026.0.356**. But Mirra's own version notes say the actual CLO application in use was upgraded to **2026.1.188** on 2026-08-15 (`clo_workspace/versions/v_1.3.2.json:33`). 2026.1.188 sits in the *next* minor line, whose matching SDK is **v11.0.0 → CLO 2026.1.224**, not v10.0.3. This is exactly the class of skew that has already caused a crash for this project once (the 2025.2.368-built plugin hanging CLO permanently after the app moved to 2026.1.188, per the same note). Building against v10.0.3 got the plugin working again, but it is still one SDK generation behind the running application line — the same shape of mismatch that caused the prior incident, just smaller in magnitude. This should be verified/closed out, not assumed safe merely because it currently works.

**Named API removals to check against Mirra's plugin source:**
- v10.0.3 removed `ImportPatternCPX`, `ExportPatternCPX`, `ConvertPatternJSONToCPX`, and `ReDrape3DArrangement`. If any of these are referenced in the C++ plugin source under `clo_workspace/`, they would fail to compile/link against SDK v10.0.3 (which Mirra already targets) — worth a direct grep of the plugin source for these symbol names as a follow-up (not done here; this task was scoped to web research only, and the instructions here also barred touching plugin/build files).
- v11.0.0 re-introduces Pattern CPX APIs and `ReDrape3DArrangement` — if Mirra ever moves to SDK v11.0.0, these symbols reappear, but with what is described only as "re-introduced" (no confirmation the signatures are identical to the pre-v10.0.3 versions).
- v10.0.0 removed `GetFabricSize`; v11.0.0 removed `GetNestingBufferSpacing`. Neither name appears in `clo_vto/native_vto/client.py`, but that file only shows the Python-side REST wrapper, not the C++ plugin's internal SDK calls — absence here does not confirm absence in the plugin source.
- v11.0.0 explicitly calls out a `LibraryWindowInterface` startup crash risk "on CLO 2026.1+" — i.e., precisely the app line (2026.1.188) Mirra is running. This was flagged as a known platform issue by the vendor for that exact app generation.

## Open questions / could not verify

- **Exact release dates**: the official changelog page prints only month/year for each SDK version (e.g., "July 2026" for v10.0.3), not a specific day. I could not obtain day-level precision from the fetched content.
- **Whether Mirra's plugin C++ source actually calls any of the removed APIs** (`ImportPatternCPX`, `ExportPatternCPX`, `ConvertPatternJSONToCPX`, `ReDrape3DArrangement`, `GetFabricSize`, `GetNestingBufferSpacing`). This requires grepping `clo_workspace/` plugin source, which was out of scope for this web-research task (no source changes were made and no exhaustive symbol search of the C++ tree was performed).
- **Exact new API function names/signatures added in v11.0.0** ("geometric data structures," "grading APIs," "pattern utility APIs," "material property management tools") — the fetched changelog summary named categories, not concrete function names. Could not confirm whether any of these would let Mirra retire hand-built logic (e.g., its own bbox/line-length pattern introspection).
- **Avatar (.avt) format changes** — the v9.1.1 entry mentions "improved avatar import" but no specifics were retrievable from the summarized fetch; could not confirm whether the .avt format itself changed in any version researched.
- **Licensing/activation policy for automated or server-side use** — I found no official CLO3D documentation (developer portal, support articles, or forum) addressing license or activation requirements specific to unattended/automated/server-driven plugin operation. This is a real gap: Mirra runs CLO headlessly and driven by a REST plugin, and I could not confirm or rule out any licensing constraint on that usage pattern from official sources. Do not assume no constraint exists — this is unverified, not cleared.
- **Whether the v10.0.3 GLB export fixes (z-offset, texture "source" field, colorway flag) actually resolve or overlap with the export bugs Mirra fixed by hand in plugin v1.3.1** — plausible given the timing and subject matter, but not confirmed against actual SDK release notes or header diffs; only inferred from two independent summaries (Mirra's own plugin notes and the vendor changelog).
- **Whether the CLO application currently installed is still exactly 2026.1.188**, or has since been auto-updated — this task did not touch the CLO installation or worker environment (out of scope per instructions), so the only source for the running app version is the repo's own dated note from 2026-08-15.
- All web content above was retrieved via WebFetch, which summarizes pages through a secondary model rather than returning raw HTML/text. I made a follow-up pass asking for verbatim quotes to reduce paraphrase risk, but I cannot rule out fetch-summarization error entirely. Treat exact wording (not just facts) as approximate.

## Sources

- https://developer.clo3d.com/changelog.html — **Official** (CLO API documentation site). Primary source for SDK version history, changes, and removed/added APIs.
- https://developer.clo3d.com/download.html — **Official**. Source for SDK-version-to-CLO-app-version mapping (e.g., SDK v10.0.3 ↔ CLO 2026.0.356; SDK v11.0.0 ↔ CLO 2026.1.224).
- https://developer.clo3d.com/ — **Official**. CLO API documentation landing page, confirms the developer portal's existence and scope.
- https://developer.clo3d.com/python.html — **Official**. Confirms a Python scripting API exists within CLO (not further explored in depth for this report).
- https://support.clo3d.com/hc/en-us/articles/360017616633-CLO-API-SDK-Guide — **Official** (CLO support center). Not fetched in full; surfaced by search only, as a lead.
- https://style.clo-set.com/docs/closetapi — **Official** (CLO-SET). CLO-SET's own API for asset/file management (ZPRJ/ZPAC/AVT upload/conversion). Not fetched in depth; noted as a lead for potential relevance to Mirra's asset pipeline, not confirmed relevant.
- https://www.clo3d.com/en/resources/notices/1375 — **Official** (CLO3D site notice). "CLO 2026.0 New Features Webinar" — surfaced by search only; not fetched, so its content is unconfirmed. Lead only.
- https://www.cgchannel.com/2026/04/clo-virtual-fashion-releases-marvelous-designer-2026-0/ — **Unverified** (third-party trade press, CG Channel). Surfaced by search; not fetched or relied on for any fact in this report. Marvelous Designer is a related but separate CLO Virtual Fashion product — do not conflate with CLO3D itself.
- https://www.vntana.com/resource/vntana-clo-plugin/ — **Unverified** (third-party vendor page). Surfaced by search only; not used for any fact in this report.
- https://aescripts.com/floating-license-server/ — **Unverified** (third-party marketplace, unrelated to CLO specifically). Surfaced during the licensing search; not relevant, not used.
- https://s3.amazonaws.com/Outside_Work/CLO_API/4_1_2/CLO+API_SDK_GUIDE_20230406.pdf and the Aliyun-hosted equivalent — **Official-hosted but stale** (2021/2023-dated SDK guide PDFs, several SDK generations behind Mirra's current target). Surfaced by search only; not fetched, given their age.
