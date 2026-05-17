# Step-1 Digital Twin Summary Since Last Commit

This summary is only about the recent Step-1 digital twin work.
It does not cover VTO, Mac, or `product_ingestion`.

## What changed in simple language

Before these changes, the pipeline could:

- load the base avatar
- try a few measurement routes
- say a run completed

But we did not have proof that the saved avatar had actually changed.

Now the pipeline can:

- load `base-1.avt`
- apply the verified body measurement changes
- save the result
- check the saved `.avt` file itself to confirm the values really changed

That is the main improvement.

## Main changes made

### 1. The Step-1 runtime now supports JSON-first measurement input

We made the runtime easier to test by allowing it to read measurements directly from:

- `clo_avatar_generation/input/u_001.measurements.json`

This helped us move faster without depending only on MongoDB.

Files involved:

- `clo_avatar_generation/run_avatar.py`
- `clo_avatar_generation/avatar_runtime/step_02_run_setup.py`
- `clo_avatar_generation/avatar_runtime/step_03_fetch_measurements.py`

### 2. We added more control over how measurements are applied

The runtime now supports different apply modes:

- `csv`
- `avatar_properties`
- `avt_patch`
- `auto`

`auto` now prefers the working AVT patch route.

Files involved:

- `clo_avatar_generation/run_avatar.py`
- `clo_avatar_generation/avatar_runtime/step_08_apply_measurements.py`

### 3. We kept the old CSV route, but proved it is not reliable

We did not delete the CSV path.
We kept it for comparison and debugging.

But testing showed that:

- multi-field CSV failed
- single-field CSV failed
- even the repo CSV template failed unchanged

So the CSV bridge is still not trusted.

Files involved:

- `clo_avatar_generation/avatar_runtime/step_06_build_payloads.py`
- `clo_avatar_generation/research-2/measurement-method-experiments.md`

### 4. We added an experimental plugin route for avatar properties

On the Windows plugin side, we added support for:

- reading avatar property debug info
- setting avatar properties with JSON
- exporting the current avatar directly as `.avt`

This was useful for investigation, even though the property route did not end up being the real solution for body measurement changes.

Files involved:

- `clo_workspace/windows/RestPlugin_windows.cpp`
- `clo_workspace/plugin_contract.json`
- `clo_workspace/versions/v_1.1.0.json`
- `clo_avatar_generation/avatar_runtime/client.py`

### 5. We added the real working route: AVT patching

This was the biggest change.

We found that certain body measurements are stored inside the avatar `.avt` file.
So we added a new runtime helper that:

- opens the base `.avt`
- patches the verified measurement positions inside it
- imports that patched avatar into CLO
- saves it back out
- verifies the saved avatar still contains the requested values

This is the route that finally worked.

Files involved:

- `clo_avatar_generation/avatar_runtime/avt_patch.py`
- `clo_avatar_generation/avatar_runtime/field_contract.py`
- `clo_avatar_generation/schema/step1_field_contract.json`
- `clo_avatar_generation/avatar_runtime/step_06_build_payloads.py`
- `clo_avatar_generation/avatar_runtime/step_08_apply_measurements.py`
- `clo_avatar_generation/avatar_runtime/step_11_save_outputs.py`

### 6. We added real verification instead of trusting weak success messages

Earlier, a run could look successful even when the avatar had not really changed.

Now the pipeline verifies the saved avatar file itself.
That means a run is only considered successful when the saved `.avt` actually differs from the base avatar for the mapped measurements.

Files involved:

- `clo_avatar_generation/avatar_runtime/step_11_save_outputs.py`
- `clo_avatar_generation/avatar_runtime/pipeline.py`

### 7. We documented the experiments and the observed CLO fields

We wrote down:

- which methods failed
- which method finally worked
- which visible CLO field names were observed in the UI

Files involved:

- `clo_avatar_generation/research-2/measurement-method-experiments.md`
- `clo_avatar_generation/research-2/avatar-editor-fields-observed.md`

## What is now working

For Step-1, these body measurements are now verified as stored in the saved avatar:

- `Total Height`
- `Across Shoulder (Curvilinear)`
- `Chest`
- `Waist`
- `Low Hip`
- `Inseam`

In simple words:

- the avatar changes are now really being saved
- reopening the saved `.avt` in CLO shows the changed values
- the pipeline can prove this from the saved file

## What is not solved yet

- `Weight` is still not verified on the working AVT patch route
- the old CSV import route is still failing
- the Avatar Editor preset dropdown in CLO can reset the avatar back to default if the user manually reapplies the default preset

## About the `build-local` folder

The contents of `clo_workspace/windows/build-local/` do **not** need to be committed.

Reason:

- it is a generated local build folder
- it is only used to compile-check or produce a local DLL
- it can be recreated any time from source

So in normal source control terms:

- commit the source code changes
- do not commit `build-local`

The only time to keep something from that folder is if you personally want the built DLL as a local artifact, but that should usually not go into git.
