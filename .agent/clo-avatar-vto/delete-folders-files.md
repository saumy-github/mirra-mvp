# Files and Folders to Delete Later

These items are confirmed dead code or old artifact files. They are **not being touched during the movement phase**. They will be deleted in a separate cleanup step after the folder split is done and verified.

All items below are inside `clo_avatar_generation/`.

---

## 1. `clo_avatar_generation/avatar_setup/`

**What it is:** An older prototype for the Step 1 avatar import workflow. Was the approach used before `avatar_runtime/` was built.

**Why it is safe to delete:**
- Not imported by `run_avatar.py` (active Step 1 command)
- Not imported by `run_clo_vto.py` (active Step 3 command)
- Only imported by `research/legacy/run_clo_avatar.py` and `avatar_setup/run_avatar.py` — both of which are also dead code

**Contents:**
```
avatar_setup/__init__.py
avatar_setup/contracts.py
avatar_setup/import_bundle.py
avatar_setup/measurement_mapping.py
avatar_setup/run_avatar.py
avatar_setup/run_manifest.py
avatar_setup/template_registry.py
avatar_setup/__pycache__/
```

---

## 2. `clo_avatar_generation/reporting.py`

**What it is:** A generic JSON report writer with a single function `write_json_report()`.

**Why it is safe to delete:**
- Not imported by `run_avatar.py` (active Step 1 command)
- Not imported by `run_clo_vto.py` (active Step 3 command)
- Only imported by `research/evaluate_avatar_role.py` and `avatar_setup/run_avatar.py` — both dead code

---

## 3. `clo_avatar_generation/research/`

**What it is:** Planning-phase research code and documents from before the current pipelines were built.

**Why it is safe to delete:**
- Not imported by either active command
- The Python files inside import from `avatar_setup/` (dead code) and `reporting.py` (dead code)
- The markdown docs are planning artifacts, superseded by the `.agent/` docs

**Contents:**
```
research/__init__.py
research/avatar_input_schema.py
research/avatar_output_schema.py
research/avatar_role_decision.md
research/completed.md
research/decision_matrix.py
research/evaluate_avatar_role.py          ← imports reporting.py (dead)
research/mapping_decisions.md
research/measurement_inventory.py         ← imports avatar_setup.contracts (dead)
research/phase-1-template-strategy.md
research/phase-2-measurement-inventory.md
research/phase-3-mirra-to-clo-mapping.md
research/phase-4-runtime-scaffold.md
research/phase-5-plugin-extension.md
research/phase-6-native-comparison.md
research/phase-7-avatar-role-decision.md
research/research.md
research/legacy/
    __init__.py
    run_clo_avatar.py                     ← old entry point, imports avatar_setup (dead)
research/__pycache__/
```

---

## 5. `clo_avatar_generation/output/base-1__native_vto_report.json`

**What it is:** A VTO pipeline report that was written into the Step 1 output folder because `run_clo_vto.py` defaulted its output to `clo_avatar_generation/output/`. This is a misplaced artifact.

**Why it is safe to delete:**
- It is an old report file, not live data
- After the folder split, new VTO reports will go to `clo_vto/output/`

**Note:** Only this one file should be deleted from `output/`. The `u_001-*` subdirs and all `.avt` probe files in `output/` are active Step 1 artifacts and must be kept.

---

## Deletion Order (when ready)

Delete in this order to avoid broken imports at the time of deletion:

1. `research/` (imports avatar_setup and reporting — delete first)
2. `avatar_setup/` (no longer imported by anything after research/ is gone)
3. `reporting.py` (no longer imported by anything after avatar_setup/ and research/ are gone)
4. `research_files/` (no Python imports, safe to delete any time)
5. `output/base-1__native_vto_report.json` (single file, safe to delete any time)
