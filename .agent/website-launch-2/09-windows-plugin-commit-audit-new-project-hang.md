# 09 — Windows plugin commit audit: what changed, and what it means for the `new-project` hang

**Status**: investigation complete, no code changed. Written 2026-08-20.
**Question asked**: is the `new-project` hang caused by a change we made to the Windows plugin, rather than the CLO SDK/app version skew?
**Short answer**: **no — but the audit turned up something important for when you rebuild.**

Scope: Windows plugin only (`clo_workspace/windows/`). Mac changes deliberately excluded.

---

## 1. The decisive fact: the running DLL predates every recent change

| Artifact | Date |
|---|---|
| `RestPlugin_v1.3.1.dll` (the DLL CLO is actually loading) | **2026-08-03 00:23** |
| Most recent commit touching `clo_workspace/windows/` (`5682a1d`) | **2026-08-04 10:21** |

**The installed plugin binary was built *before* the last plugin commit.** Whatever `5682a1d` changed is **not** in the DLL that hung today.

That has a direct consequence for the question asked:

- **2026-08-09** — avatar generation **succeeded**, with this exact DLL.
- **2026-08-20** — three consecutive hangs on first `new-project`, with **the same exact DLL** (unchanged mtime, never rebuilt).

**The plugin binary is byte-identical between the working run and the failing runs.** A component that did not change cannot explain a behaviour that did. Plugin *source* changes are irrelevant here for the same reason — none of them were ever compiled in.

**What did change in that window:** CLO was updated to **2026.1.188 on 2026-08-15 16:04** (`CLO_Standalone_OnlineAuth_x64.exe`), while the plugin still builds against `CLO_SDK_v2025.2.368`. See §4.

---

## 2. Full commit history for the Windows plugin

```
5682a1d  2026-08-04  Saumy         intermediate work of website launch
16fc690  2026-07-23  Saumy         merger complete
96d9be2  2026-07-17  Anant Mathur  Add unit tests for garment segmentation...
f122ea9  2026-07-03  Saumy         try except block added, problem in readback and save outputs
7e52927  2026-07-01  Saumy         Port sync-read architecture to Windows plugin
8403065  2026-05-17  Saumy         claude setup and avatar generation half done
ce26e21  2026-04-01  Saumy         clo-based avatar, slots issue solved
```

Everything from `16fc690` (2026-07-23) and earlier **is** in the running DLL. Only `5682a1d` is not.

---

## 3. What `5682a1d` (2026-08-04) actually changed — 93 insertions, 57 deletions, one file

Two distinct changes. **Neither is in the running DLL**, so neither caused today's hang — but both land the moment you rebuild, so both need reviewing first.

### 3a. GLB export rerouted through `ExportGLTF`

```cpp
- bool asGLB = (cmd.param2 == "glb");
- options.scale          = 1.0f;
- options.bExportGarment = true;
- options.bEmbedded      = asGLB;
- EXPORT_API->ExportGLTF(cmd.param1, options, asGLB);
+ options.scale          = 0.001f;                      // CLO is mm, glTF expects m
+ options.bExportGarment = (g_patternsLoaded.load() > 0);
+ EXPORT_API->ExportGLTF(cmd.param1, options, false);
```

Sensible on its face: a real unit-scale fix (mm → m), and garment export only when patterns are loaded.

**But note the commit message's own reasoning** — it attributes `ExportGLB` returning empty to *"this CLO version simply not implementing it yet"*, based on the SDK header's body being a bare stub. **`01-how-ai-should-work.md` records that reasoning as a misreading**: every export method in that header is an empty stub, including `ExportGLTF`, which works on every run. The abstract-interface pattern means an empty declared body proves nothing.

The change itself is fine. The *conclusion written into the comment* is not, and it should be corrected rather than propagated — especially now that §4 makes vtable skew the leading explanation for both symptoms.

### 3b. `DoFunctionAfterLoadingCLOFile` — auto-start the REST server. **Review this before rebuilding.**

`DoFunction`'s startup logic was extracted into `EnsureServerStarted(bool showMessageBox)`, and a new CLO callback was wired up:

```cpp
CLO_PLUGIN_SPECIFIER void DoFunctionAfterLoadingCLOFile(const char* fileExtension)
{
    try { EnsureServerStarted(/*showMessageBox=*/false); }
    catch (...) {}
}
```

The intent is good — no more manual Plugins-menu click each session — and the author already reasoned about one hazard, documenting why the message box must be suppressed on the automatic path:

> *"a modal DisplayMessageBox would block CLO's main thread waiting for a click nobody is there to make, which would look identical to the queue hangs seen elsewhere in this plugin — never show it unattended."*

**The hazard that does not appear to have been considered: this callback fires on *every* file load, and `NewProject()` may well be one.**

The concern, concretely. The `new-project` handler runs on the main thread inside `ProcessCommandQueue()`, with the RAII reentrancy guard holding `g_queueProcessing = true`:

```cpp
else if (cmd.type == "new-project") {
    UTILITY_API->NewProject();     // "Clear the current garment and begin a new garment"
    ...
```

If `NewProject()` causes CLO to load its blank default project, CLO would call `DoFunctionAfterLoadingCLOFile` **synchronously, on the same main thread, while the queue drain is still in progress**. `EnsureServerStarted` returns immediately when `g_serverRunning` is true, so the common path is probably harmless — but this is exactly the shape of a reentrancy deadlock, in exactly the call whose hang we are chasing.

**This is a hypothesis, not a finding.** It cannot be the cause of today's hang (not in the DLL). It is flagged because rebuilding introduces it, and the symptom it could produce is indistinguishable from the bug being fixed. Establish first whether `NewProject()` triggers the file-load callback — a `TraceLog` line at the top of `DoFunctionAfterLoadingCLOFile` answers it in one run.

---

## 4. What actually changed between working and failing

```
Plugin DLL   : v1.3.1, built 2026-08-03      — unchanged throughout
Plugin SDK   : CLO_SDK_v2025.2.368           — unchanged throughout
CLO app      : 2026.0.374  →  2026.1.188     — CHANGED 2026-08-15 16:04
```

| Date | Event | Outcome |
|---|---|---|
| 2026-08-03 | Plugin DLL built | — |
| 2026-08-08/09 | Guest avatar generated, app 2026.0.374 | **worked** |
| **2026-08-15** | **CLO updated to 2026.1.188** | — |
| 2026-08-20 | Three runs, three hangs on first `new-project` | **all failed** |

The skew widened from **one** major line (2026.0 vs 2025.2 — worked) to **two** (2026.1 vs 2025.2 — hangs).

This is the **vtable/ABI skew** hypothesis already recorded in `01-how-ai-should-work.md` for `ExportGLB`, written down 2026-08-15 as untested. Calls through an abstract C++ interface dispatch by **vtable slot index**, not by name. If CLO inserted or reordered virtuals between SDK lines, `NewProject()` no longer lands on `NewProject()` — it lands on whatever occupies that slot now, and blocks forever. A hang is a wholly plausible outcome of calling the wrong function with the wrong arguments.

Also relevant: `03-clo-2026.1-upgrade-assessment.md` recommended **not** taking this upgrade, and flagged that rollback is the real risk because CLO offers no version archive.

**Still a hypothesis.** It fits every data point, but "the only thing that changed" is circumstantial until a plugin rebuilt against a matching SDK is tested.

---

## 5. Recommended order of work

1. **Establish whether a 2026.1-line Windows SDK is downloadable from the CLO account.** This single answer decides everything below. `clo_workspace/mac_plugin_setup.md` records that `CLO_SDK_v2026.0.262_Mac` was already obtainable, so newer SDKs do get published.
2. **If yes — rebuild against it.** This is the real fix, and it would likely also resolve `ExportGLB`, making §3a's workaround unnecessary.
3. **If no — reinstall CLO 2026.0.374**, restoring the known-good pairing. Requires an installer you already hold.
4. **Before any rebuild, review §3b.** A rebuild ships the auto-start callback for the first time. Add the `TraceLog` line first so a reentrancy hang is instantly distinguishable from the SDK-skew hang.
5. **Correct §3a's comment** while the file is open — do not let the "CLO doesn't implement ExportGLB" misreading harden into accepted fact.
6. **Retest `ExportGLB` directly after the rebuild.** If vtable skew is the cause, it may simply start working, and the Python-side packing workaround becomes removable.

## 6. What not to do

- **Stop retrying through the website.** Three restarts, three identical hangs, one on a six-minute-old instance. Each attempt costs a CLO restart and leaves an orphaned `queued` job.
- **Do not "fix" the pipeline.** Steps 01-06 pass every time, including A1's `mongodb:user_measurements` lookup. There is nothing wrong on the Python side.
- **Do not rebuild the plugin as a first move** without settling the SDK question — rebuilding against the *same* 2025.2 SDK changes nothing about the skew, while introducing §3b's untested callback.
