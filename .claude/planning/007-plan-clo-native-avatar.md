# Plan 007: CLO-Native Avatar Path

## Overview

This plan explores the opposite approach from Plan 006.

Instead of teaching our own code to place garments around a STAR mesh, this path tries to move the avatar representation closer to a CLO-native or CLO-converted avatar so that CLO itself has better built-in understanding of the body for arrangement, fitting, and simulation.

The core idea is:

1. Drive a CLO avatar through CLO's own measurement and avatar system.
2. Load that avatar into the current automation flow through the SDK and plugin.
3. Measure whether CLO-native arrangement support is stronger than the STAR imported-mesh path.

This plan does not assume CLO has a public `betas`-style latent body model like STAR. Current evidence suggests the correct control space is editable avatar measurements and CLO avatar files, not a public low-dimensional shape vector.

## Implementation Boundary Rules

This plan must be implemented in a way that is easy to delete later if the CLO-native path is rejected.

The boundary rules are:

1. All main new code for this plan must live inside one new root folder:
   - `clo_avatar_generation/`
2. Do not change existing avatar-generation data logic in:
   - `avatar_generation/`
   - `mirra_measurements/`
   - `product_ingestion/`
   - current `vto/` runtime files
3. If this plan needs new schemas, contracts, import helpers, runners, or adapters, create them as new files rather than modifying existing business logic files.
4. The only existing integration area allowed to be extended is the CLO REST plugin layer.
5. In the plugin layer, preserve all current behavior and endpoint logic.
6. Any plugin support for this plan must be additive:
   - new command types
   - new helper files if needed
   - new endpoints
   - no deletion of old logic
   - no breaking changes to existing endpoints
7. If this plan needs a separate VTO-style entrypoint, create a new runner file for the CLO-native path instead of modifying the current `vto/run_vto.py`.
8. If this plan needs schema definitions, create new schema or contract files under the new folder rather than reusing or rewriting old schemas.
9. If this plan needs import wrappers or client adapters, create new files for the CLO-native path instead of rewriting the current default path.
10. Every change must be easy to remove later by deleting the new folder and any clearly isolated additive plugin files or plugin endpoint branches.

Design implication:

- this plan should behave like a removable experimental lane, not a rewrite of the current repo.

---

## Why This Plan Exists

The current STAR path gives us a user-specific body mesh, but CLO often treats it as a custom imported avatar with weak semantic slot support.

The CLO-native path matters because CLO already has:

1. its own avatar editor
2. native avatar files and size files
3. arrangement points and bounding volumes
4. fitting suit support
5. measurement-driven avatar controls
6. conversion tools that turn 3D bodies into CLO avatars

So the question behind this plan is:

"If we let CLO own the simulation avatar more directly, do we get better arrangement and placement behavior than we get from the imported STAR mesh?"

---

## What the Current Repo Already Supports

Relevant repo areas:

- `clo_workspace/plugins/RestPlugin.cpp`
- `vto/clo_automation_steps/client.py`
- `vto/clo_automation_steps/step_03_import_avatar.py`
- `vto/clo_automation_steps/step_06_read_edges_and_slots.py`

Current reality:

1. The current plugin supports OBJ avatar import through `/import-avatar`.
2. The current plugin does not expose endpoints for:
   - importing `.avt`
   - importing avatar measurement CSV
   - importing arrangement point `.arr`
   - importing bounding volume `.pan`
   - exporting `.avt`
3. The current VTO runner assumes the avatar handoff is an OBJ file plus `measurements.json`.

So even though the CLO SDK appears to support native avatar operations, the repo does not expose them yet.

---

## Research Findings About CLO Avatars

The following findings come from current public CLO support and developer documentation and are included here so the team does not need to re-search them later.

### 1. CLO avatar control is measurement-driven, not STAR-beta-driven

What we found:

1. CLO Avatar Editor is built around body measurements and shape controls.
2. CLO documentation says the editor is powered by large body-scan data and automatically adjusts unassigned measurements to realistic shapes.
3. I did not find public documentation for a STAR-like public low-dimensional body parameter vector such as `betas`.

Implication:

- If we train ML for a CLO-native path, the correct output target is most likely a CLO measurement profile, not hidden latent shape coefficients.

### 2. CLO avatar size is editable

What current docs confirm:

1. CLO avatars can be edited through Avatar Editor.
2. Size-editable converted avatars can also be edited.
3. Editable measures appear in black and non-editable measures appear in grey.
4. Hidden measures can be activated through `Set Details`.

Important implication:

- CLO avatar dimensions are not fixed or unchangeable.

### 3. Documented CLO measurement controls

Current official documentation confirms these control areas:

#### Overall size keys

- Width basis:
  - `Bust`
  - `Under Bust`
  - `Weight`
- Height basis:
  - `Total Height`
  - `HPS Height`
  - `Inseam`

#### Detailed measurement groups

- `Circumference`
- `Height`
- `Length`

#### Movable body-measure regions

- `Under Bust`
- `Waist`
- `High Hip`
- `Low Hip`
- `Thigh`

#### Other documented controls

- `Cup Size`
- `Hands & Head`
- `Crotch Gap`
- `Crotch Volume` for male avatars
- `Breast Shape`
- `Breast Space`
- `Breast Height`
- `Hip Dips`
- `Hip Volume`

Examples visible in the official guide screenshots include:

- `Neck Base`
- `Bust`
- `Bicep`
- `Waist`
- `High Hip`
- `Low Hip`
- `Thigh`
- `Across Shoulder (Curvilinear)`
- `Arm`

Important limitation:

- CLO does not publish one clean public text table listing every field for every avatar family.
- The exact field set depends on the avatar, version, and what is enabled in `Set Details`.

### 4. CLO-native avatar file ecosystem

Official CLO file-format documentation confirms:

- `.avt`
  - avatar file
  - contains model/mesh, sizing data, pose, motion, shoes, hair, glasses, bounding volumes, arrangement points, and related avatar data
- `.avs`
  - avatar size file
  - requires a compatible `.avt`
- `.arr`
  - arrangement points
- `.pan`
  - bounding volumes
- `.mea`
  - avatar body measurement file
- `.pos`
  - avatar pose file
- `.mtn`
  - motion file
- `.iks`
  - IK mapping file

Important implication:

- If we commit to the CLO-native path, the real handoff object is not "just an avatar mesh."
- It is a structured CLO avatar package built around `.avt` and related sidecar or companion data.

### 5. Custom imported avatars versus CLO-native avatars

Official docs also show a very important tradeoff.

Through `Automatic Rigging & Converter`, CLO offers multiple conversion outcomes:

1. `CLO Skin Style`
   - keeps the body shape of the original file
   - converts the appearance to a CLO avatar and adds joints
   - size editing is not possible
2. `Rigging only`
   - adds joints while maintaining original shape and appearance
3. `Convert to size editable avatar`
   - changes the body shape to a CLO avatar body that can be size-edited
   - tries to maintain the appearance of the original file

Implication:

- There is a real tradeoff between:
  - preserving the exact imported custom body shape
  - and getting full CLO-native size editability

This is one of the most important decision points in this whole topic.

### 6. CLO native arrangement and fitting advantages

Official docs confirm:

1. Arrangement points can be saved and loaded as `.arr`.
2. Bounding volumes can be saved and loaded as `.pan`.
3. CLO-native avatars include a fitting suit by default.
4. Custom avatars need a fitting suit added manually if re-drape behavior is needed.
5. Automated arrangement point creation exists for imported OBJ avatars in T-pose or A-pose.

Implication:

- CLO-native avatars are structurally better aligned to CLO's arrangement and draping tools than a plain imported mesh.

### 7. CLO SDK and API support relevant to this path

The public developer API currently documents these relevant import functions:

- `ImportAvatarMeasurement(csvPath, avtPath, opt)`
- `ImportMeasurement(csvPath)`
- `ImportAvatar(avtPath, opt)`
- `ImportFile(filePath, options)` for files including OBJ / FBX / AVT depending on type

Other relevant API functions visible in the public list:

- `ExportAVTW(filePath)`
- `GetAvatarNameList()`
- `GetAvatarGenderList()`
- `GetArrangementList()`

Important limitation:

- I found the public API function names, but I did not find a public exact CSV schema for `ImportAvatarMeasurement`.
- That means the SDK supports the operation, but we still need a reference CSV or SDK sample to lock the format.

---

## What This Means in STAR-vs-CLO Terms

### STAR path

Strengths:

- exact control of the body model we generate
- clear mesh topology
- known `betas`
- independent of CLO internals

Weaknesses:

- CLO sees it mainly as an imported mesh avatar
- semantic arrangement support is weak or inconsistent

### CLO-native path

Strengths:

- measurement-driven avatar control already exists
- arrangement, bounding volumes, fitting suit, and avatar tooling are built in
- better chance of native placement support

Weaknesses:

- no public `betas` equivalent found
- some exact shape fidelity may be lost when converting to size-editable avatars
- field inventory and CSV schema are not cleanly documented in one place

---

## Goal of This Plan

Build a second avatar path that allows us to:

1. create or load a CLO-native / CLO-converted avatar
2. drive it from a controlled measurement profile
3. import it through the existing automation infrastructure
4. compare its arrangement and try-on performance with the STAR path

---

## Proposed New Root Folder

When implementation begins, create a new root folder:

```plain
clo_avatar_generation/
```

This folder should own the CLO-native avatar path, separate from `avatar_generation/`, so both approaches can coexist and be evaluated fairly.

### Proposed structure

```plain
clo_avatar_generation/
  README.md
  run_clo_avatar.py
  run_clo_vto.py
  contracts.py
  template_registry.py
  measurement_mapping.py
  csv_builder.py
  import_bundle.py
  schema/
    avatar_input_schema.py
    avatar_output_schema.py
    measurement_csv_schema.md
  adapters/
    clo_native_client.py
    clo_native_importer.py
  avt_templates/
  reference_docs/
  output/
```

Purpose of this separation:

1. do not pollute the STAR pipeline with CLO-native assumptions
2. allow both paths to stay runnable
3. make the evaluation cleaner later
4. make later deletion easy if this path is abandoned

### Folder responsibility rule

Everything that is specific to the CLO-native experiment should be created inside this new folder unless it is impossible to do so because the code must cross the live CLO plugin boundary.

That means this folder should own:

- the runner
- the measurement mapping
- CSV generation
- template selection
- contracts
- schema documentation
- import-bundle assembly
- native-avatar-specific client wrappers
- comparison outputs for this path

Existing folders should remain the baseline system and should not be reshaped around this experiment.

---

## New Plugin / Method Work Needed

### Recommendation

Prefer extending the existing `RestPlugin.cpp` rather than building a completely separate plugin first.

Reason:

1. the repo already has one stable queue-driven main-thread-safe plugin bridge
2. the current Python VTO orchestration already targets it
3. extending one plugin is lower-risk than running two parallel CLO automation bridges

Important constraint for implementation:

- even here, prefer additive helper files and additive endpoint wiring
- do not remove or rewrite existing endpoint behavior
- do not break the current OBJ-based flow

### Endpoints or methods likely needed

The current plugin already supports `/import-avatar` for OBJ.

For this plan, likely additions are:

#### 1. Native avatar import

Endpoint idea:

- `POST /import-avatar-avt`

Purpose:

- load a native CLO avatar file directly

Likely SDK call:

- `ImportAvatar(avtPath, opt)`

#### 2. Measurement CSV import

Endpoint ideas:

- `POST /import-avatar-measurements`
- or `POST /import-avatar-measurement-csv`

Purpose:

- load measurement values into a compatible CLO avatar

Likely SDK calls:

- `ImportAvatarMeasurement(csvPath, avtPath, opt)`
- or `ImportMeasurement(csvPath)` if the avatar is already loaded

#### 3. Arrangement point import

Endpoint idea:

- `POST /import-avatar-arrangement-points`

Purpose:

- load `.arr` files if needed

Why:

- this lets us preserve arrangement-point contracts rather than hoping they always auto-generate perfectly

#### 4. Bounding volume import

Endpoint idea:

- `POST /import-avatar-bounding-volumes`

Purpose:

- load `.pan` files if needed

#### 5. Native avatar debug endpoint

Endpoint idea:

- `GET /avatar/native-debug`

Purpose:

- report avatar name
- avatar gender
- whether native avatar was loaded
- whether arrangement list is populated
- whether measurement CSV import succeeded

#### 6. Optional AVT export endpoint

Endpoint idea:

- `POST /export-avatar-avt`

Purpose:

- save the resulting avatar state for reproducibility and debugging

Likely SDK call:

- `ExportAVTW(filePath)`

---

## How CLO Values Should Be Controlled in This Plan

This is the most important conceptual shift.

### Do not think in STAR-betas terms

For this path, do not search for a CLO equivalent of:

- `betas`
- direct vertex weights
- a public statistical latent body vector

Current evidence does not support that as the main usable control mechanism.

### Think in measurement-profile terms

Instead, the CLO-native path should be driven by a structured measurement profile such as:

- total height
- inseam
- chest / bust
- under bust where relevant
- waist
- hip
- shoulder / neck / arm-related length fields where available
- any other editable details we confirm from the actual template

The model output for this path should therefore become:

- a CLO measurement vector
- or a generated measurement CSV
- or later an `.avs` size state tied to a locked `.avt`

### What the future ML model would predict

If we go down this path, a future ML model should likely predict:

1. direct CLO-editable measurements from user inputs
2. plus derived approximations for fields the user cannot provide

It should not try to predict hidden CLO internals unless we later discover an official supported parameter space.

---

## Phase Plan

## Phase 1: Lock the CLO Avatar Template Strategy

**Goal**: decide exactly which CLO avatar family and conversion mode we will test.

**Steps**:

1. Lock the CLO version used for evaluation.
2. Choose the first avatar families to test:
   - male
   - female
3. Decide whether the first candidate is:
   - a default CLO avatar
   - a converted size-editable avatar
   - a converted custom-shape avatar
4. Save one reference `.avt` per chosen avatar family.
5. Record version, gender, and template name in the plan and later in code config.

**Why this is necessary**:

- avatar size files and related data are compatibility-sensitive
- we need a stable template target before writing code

## Phase 2: Collect the Actual Measurement Inventory and CSV Schema

**Goal**: replace assumptions with a concrete field map for the chosen CLO avatar template.

**Steps**:

1. Open the chosen avatar in CLO Avatar Editor.
2. Enable detailed measurements through `Set Details`.
3. Save or export whatever reference files are needed to reveal the actual supported measurement set.
4. Capture the exact field names and units into repo docs.
5. Obtain a real reference CSV format for `ImportAvatarMeasurement`.
6. Classify every field into:
   - directly user-supplied
   - derived from user measurements
   - approximated from standards or priors
   - unavailable

**Deliverable**:

- locked field inventory for the chosen template
- locked CSV schema reference

**Important note**:

This is the biggest current unknown in the public docs. The public API confirms the import functions exist, but not the exact CSV structure.

## Phase 3: Define Mirra-to-CLO Measurement Mapping

**Goal**: create the translation layer from current Mirra measurements into CLO measurement space.

**Steps**:

1. List current Mirra measurement fields from `mirra_measurements/README.md`.
2. Map each field to a CLO target when possible.
3. Mark unsupported direct mappings explicitly.
4. Define how missing fields are derived.
5. Keep the mapping versioned so training data and runtime code stay aligned.

**Example mapping categories**:

- direct:
  - `height_cm` -> `Total Height`
  - `waist_circumference_cm` -> `Waist`
  - `hip_circumference_cm` -> `Hip`
- approximate / derived:
  - `shoulder_width_cm` -> likely shoulder-related CLO length or width field, once verified
  - neck and arm lengths from priors or training data
- conditional:
  - female bust / under bust / cup related fields

## Phase 4: Build the New `clo_avatar_generation/` Folder

**Goal**: create the code path that prepares a CLO-native avatar input bundle.

**Proposed responsibilities**:

### `measurement_mapping.py`

- map Mirra fields to CLO measurement fields
- classify direct vs derived values

### `csv_builder.py`

- write the exact measurement CSV format required by CLO

### `template_registry.py`

- choose the correct `.avt` template by version / gender / avatar family

### `run_clo_avatar.py`

- create one run folder
- write input contract
- write generated measurement CSV
- point to chosen `.avt`
- later trigger plugin import

### `run_clo_vto.py`

- act as the isolated runner for the CLO-native test path
- avoid modifying the current `vto/run_vto.py`
- call the new native-avatar adapters or plugin endpoints
- write outputs only for this experimental lane

### `contracts.py`

- define JSON contracts for:
  - source Mirra measurements
  - chosen avatar template
- generated CLO measurement profile
- run summary

### `import_bundle.py`

- assemble the exact files needed for one CLO-native run
- keep path and handoff logic local to this folder

### `adapters/clo_native_client.py`

- wrap only the new additive plugin endpoints for the CLO-native path
- leave the existing default client untouched

### `adapters/clo_native_importer.py`

- define the isolated import sequence for:
  - avatar template
  - measurement CSV
  - optional arrangement points
  - optional bounding volumes

## Phase 5: Extend the Plugin and Python Client

**Goal**: make the current automation stack capable of loading CLO-native avatars and their measurement data.

**Likely repo areas**:

- `clo_workspace/plugins/RestPlugin.cpp`

Important boundary rule:

- do not modify the current default VTO client if that can be avoided
- prefer a new native-avatar adapter client under `clo_avatar_generation/adapters/`
- only the plugin itself is allowed to be extended in the existing codebase

**Steps**:

1. Add new queued command types in the plugin for AVT import and measurement import.
2. Add REST endpoints for those operations.
3. If plugin implementation gets large, split new helper code into new plugin-side files rather than overloading existing logic blocks.
4. Add a new CLO-native-specific Python client in the new folder.
5. Keep the old OBJ path intact so both paths remain comparable.
6. Do not replace the current runtime path selector inside the existing VTO code.
7. Keep all new debugging and native-avatar status output additive.

## Phase 6: Test Arrangement and Placement Behavior on the CLO-Native Avatar

**Goal**: verify whether the native path actually fixes the problem we care about.

**Steps**:

1. Import the chosen `.avt` through the new plugin path.
2. Import measurement CSV and confirm avatar loads correctly.
3. Query arrangement list and pattern arrangements after import.
4. Compare slot availability with the current STAR OBJ path.
5. Run panel arrangement, sewing, and simulation on the same garment and user case as the STAR path.

**Success signal**:

- arrangement list is populated more reliably
- initial placement needs less manual fallback
- simulation starts from cleaner positions

## Phase 7: Decide Whether CLO-Native Avatar Is the Final Simulation Avatar or Only a Proxy

**Goal**: resolve the business tradeoff if CLO-native placement is better but body fidelity is weaker.

Possible outcomes:

1. CLO-native avatar becomes both simulation avatar and user-visible avatar.
2. CLO-native avatar becomes only the simulation proxy, while STAR or another avatar remains the user-visible twin.
3. CLO-native path is rejected if arrangement gains do not justify body-fidelity loss.

## Phase 8: Evaluate This Plan Against Plan 006

**Goal**: make the final architecture choice based on evidence, not preference.

**Evaluation criteria**:

1. measurement fidelity to the intended user body
2. arrangement-list availability
3. placement quality before simulation
4. seam success rate
5. simulation cleanliness
6. engineering effort
7. maintainability
8. dependency on CLO-specific tooling
9. future extensibility for motion

---

## What We Need to Capture Once and Store in the Repo

This is the minimum CLO-native research package we should preserve locally once implementation starts:

1. chosen CLO version
2. chosen avatar templates
3. reference `.avt` files or template registry metadata
4. exact measurement CSV schema
5. actual editable field inventory for each chosen avatar family
6. mapping from Mirra measurements to CLO fields
7. conversion-mode tradeoff notes:
   - custom shape preserved
   - size editable
   - rigging only
8. arrangement-point and bounding-volume handling notes

This material should live in the new folder and not remain only in chat history.

---

## Main Risks

1. The exact CLO measurement CSV schema is not clearly documented publicly.
2. CLO-native editable shape may not match the exact user body as closely as STAR.
3. Converted size-editable avatars may shift toward CLO's body prior.
4. The plugin expansion may be straightforward at the SDK level but still tricky to stabilize in REST form.
5. We may discover that arrangement support improves, but not enough to justify losing STAR fidelity.

---

## Why This Plan Is Still Worth Testing

Even with the above risks, this path is worth testing because it is the clearest way to answer whether CLO-native semantics solve the exact placement problem we are facing today.

If it works well:

- we get stronger native placement behavior
- we reduce the need for custom fallback logic
- we can train future models directly into CLO measurement space

If it does not work well:

- we will know early that the STAR semantic-sidecar path is the better long-term foundation

---

## Recommended First Slice

If we execute this plan, the first slice should be:

1. choose one CLO avatar template
2. lock one reference `.avt`
3. obtain the real measurement CSV schema
4. extend the plugin with AVT import and measurement import
5. run one direct comparison against the same user and same shirt used in the STAR path

That is the smallest proof point that can tell us whether the CLO-native path is genuinely better.

---

## Repo Files Most Relevant to This Plan

- `clo_workspace/plugins/RestPlugin.cpp`
- `clo_workspace/plugins/BUILD_GUIDE.md`
- `vto/clo_automation_steps/client.py`
- `vto/clo_automation_steps/context.py`
- `vto/clo_automation_steps/step_03_import_avatar.py`
- `vto/clo_automation_steps/step_06_read_edges_and_slots.py`
- `vto/clo_automation_steps/step_07_arrange_patterns.py`
- `avatar_generation/first.py`
- `avatar_generation/avatar_exporter_clo.py`
- `mirra_measurements/README.md`

## Coding Readiness Rule

This plan is ready for coding only if implementation follows these constraints:

1. new CLO-native logic goes into `clo_avatar_generation/`
2. existing business logic stays untouched
3. plugin work is additive only
4. any experimental runner, schema, import bundle, or adapter is created as a new file
5. rollback remains easy:
   - delete `clo_avatar_generation/`
   - remove additive plugin extensions if the experiment is abandoned

---

## Source Links Used for the Findings Above

- CLO Avatar Editor Guide:
  https://support.clo3d.com/hc/en-us/articles/360052611653-CLO-Avatar-Editor-Guide
- Avatar Editor PDF:
  https://support.clo3d.com/hc/en-us/article_attachments/41879234609945
- Adjust Avatar Size:
  https://support.clo3d.com/hc/en-us/articles/33854094900633-Adjust-Avatar-Size
- Older Adjust Avatar Size reference:
  https://support.clo3d.com/hc/en-us/articles/360013257553-Adjust-Avatar-Size-ver5-0-0-and-Above-
- Convert to Avatar:
  https://support.clo3d.com/hc/en-us/articles/360013161274-Convert-to-Avatar
- Automatic Rigging & Converter:
  https://support.clo3d.com/hc/en-us/articles/360055227373-Automatic-Rigging-Converter
- Automated Arrangement Point Creation:
  https://support.clo3d.com/hc/en-us/articles/360001749467-Automated-Arrangement-Point-Creation
- Create an Avatar Fitting Suit:
  https://support.clo3d.com/hc/en-us/articles/24451580024601-Create-an-Avatar-Fitting-Suit-ver-7-3
- Open/Save Arrangement Point:
  https://support.clo3d.com/hc/en-us/articles/115002622467-Open-Save-Arrangement-Point
- Open/Save Tape Measure:
  https://support.clo3d.com/hc/en-us/articles/115000393468
- CLO File Format:
  https://support.clo3d.com/hc/en-us/articles/115000470688-CLO-File-Format
- CLO API list:
  https://developer.clo3d.com/list.html

## Public-Docs Gaps We Still Need to Resolve

I found enough to plan this path, but these exact items were still not fully available in the public docs:

1. the exact `ImportAvatarMeasurement` CSV schema
2. a single full text table of every editable measurement field for a chosen avatar family
3. a public STAR-like latent body parameter model for CLO avatars

Those are the main research gaps that Phase 2 of this plan must close.
