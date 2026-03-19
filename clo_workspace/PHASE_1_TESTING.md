# Phase 1 Testing Guide

## Overview

This document provides step-by-step testing procedures for Phase 1 implementation of the CLO cloth placement automation fixes.

**Phase 1 Focus**: 
- Raw payload visibility for debugging Stage 6 diagnostics
- Hard-fail gates to prevent false-positive placement success
- Plugin observability features (version endpoint)

---

## Prerequisites

Before starting any tests:

1. ✅ RestPlugin.cpp has been **recompiled** and the new DLL is deployed in CLO
2. ✅ Python virtual environment is **active** in terminal
3. ✅ CLO is **running** and accessible on `localhost:50505`
4. ✅ Avatar and DXF patterns are ready to import

**Verify Setup**:
```powershell
# Check Python environment
python --version

# Check CLO connectivity (manual curl or from Python health check)
python -c "import requests; print(requests.get('http://localhost:50505/health').json())"
```

---

## Test 1: Plugin Version Endpoint & Stage 1 Health Output

### Objective
Verify that the new `/version` endpoint works and Stage 1 prints build identification info.

### Steps

```powershell
# Navigate to workspace root
cd C:\Users\Anant\mirra-mvp

# Ensure virtual environment is active
& .\.venv\Scripts\Activate.ps1

# Run the pipeline
python clo_workspace/plugins/clo_automation_client.py
```

### Expected Output

```
[1] Health check ...
✓ Connected to CLO REST server
  Plugin: CLO REST Automation
  Version: 1.0
  Build: Mar 19 2026 HH:MM:SS
```

### Success Criteria

- ✅ Build date and time appear in output (from RestPlugin.cpp compile time)
- ✅ No errors or exceptions in Stage 1
- ✅ `/version` endpoint successfully called by `client.get_version()`
- ✅ Output includes date, time, and version information

### Failure Diagnosis

| Issue | Cause | Solution |
|-------|-------|----------|
| `Build: <empty>` | RestPlugin.cpp not recompiled | Rebuild plugin and replace DLL in CLO |
| `503 Service Unavailable` | CLO not running or plugin not loaded | Ensure CLO is running and RestPlugin.dll is active |
| `AttributeError: 'NoneType'` | health_check response missing | Check `/health` endpoint in RestPlugin.cpp |

---

## Test 2: Raw Payload Dump (DEBUG_STAGE6_RAW=1)

### Objective

Verify that Stage 6 captures, prints, and saves raw CLO API response payloads when debug mode is enabled.

### Steps

```powershell
# Set debug environment variable
$env:DEBUG_STAGE6_RAW=1

# Run the pipeline
python clo_workspace/plugins/clo_automation_client.py
```

### Expected Output

```
[6] Reading pattern edge data ...
  Pattern 0: pattern_0  (? edges)
    [DEBUG] Raw payload for pattern 0:
    {
      "info": {
        "name": "front_panel",
        "line_count": 4
      },
      ...
    }
  Pattern 1: pattern_1  (? edges)
    [DEBUG] Raw payload for pattern 1:
    {...}
  Pattern 2: pattern_2  (? edges)
    [DEBUG] Raw payload for pattern 2:
    {...}
  Pattern 3: pattern_3  (? edges)
    [DEBUG] Raw payload for pattern 3:
    {...}

[6b] Querying CLO arrangement slots ...
    [DEBUG] Arrangement list payloads:
    attempt_0: {"slots": [...]}
    attempt_1: {"slots": [...]}
    attempt_2: {"slots": [...]}
    
    [DEBUG] Payloads saved to stage_6_payloads/stage6_payloads_20260319_143025.json
```

### Success Criteria

- ✅ Full JSON payload printed for each `/patterns/{index}` call
- ✅ All 3 arrangement list attempts logged
- ✅ Directory `stage_6_payloads/` created automatically
- ✅ JSON file with timestamp created in that directory
- ✅ File name format: `stage6_payloads_YYYYMMDD_HHMMSS.json`

### Payload File Inspection

```powershell
# View the saved payload file
$payload = Get-Content stage_6_payloads/stage6_payloads_*.json | ConvertFrom-Json

# Inspect pattern info structure
$payload.pattern_info | ConvertTo-Json -Depth 10

# Inspect arrangement list responses
$payload.arrangement_list | ConvertTo-Json -Depth 10

# Check the has_live_slots flag
$payload.has_live_slots
```

### Expected Payload Structure

```json
{
  "timestamp": "2026-03-19 14:30:25",
  "pattern_info": {
    "0": {
      "info": {
        "name": "front_panel",
        "line_count": 4
      },
      ...
    },
    "1": {...},
    "2": {...},
    "3": {...}
  },
  "arrangement_list": {
    "attempt_0": {
      "slots": [...]
    },
    "attempt_1": {
      "slots": [...]
    },
    "attempt_2": {
      "slots": [...]
    }
  },
  "has_live_slots": false
}
```

### Success Criteria Detailed

- ✅ Pattern info shows complete metadata structure CLO returned
- ✅ If `name` or `line_count` missing, parser gracefully used defaults
- ✅ Arrangement list attempts all captured (useful for seeing retry behavior)
- ✅ `has_live_slots` boolean matches final slot status

---

## Test 3: Hard-Fail Gate (No Slots Available)

### Objective

Verify that Stage 7 **fails the pipeline** when live arrangement slots are unavailable, preventing false-positive success runs.

### Prerequisites

- CLO is in a state where `/arrangement-list` returns **empty slots** (typical condition)
- No override flag is set

### Steps

```powershell
# Clear any previous override flags
Remove-Item Env:\ALLOW_DEGRADED_PLACEMENT -ErrorAction SilentlyContinue

# Clear debug flag (optional, but cleaner output)
Remove-Item Env:\DEBUG_STAGE6_RAW -ErrorAction SilentlyContinue

# Run the pipeline (will fail at Stage 7)
python clo_workspace/plugins/clo_automation_client.py
```

### Expected Behavior

Pipeline runs through Stages 1–6 successfully, then **STOPS at Stage 7** with clear error message:

```
[6] Reading pattern edge data ...
  Pattern 0: pattern_0  (? edges)
  Pattern 1: pattern_1  (? edges)
  Pattern 2: pattern_2  (? edges)
  Pattern 3: pattern_3  (? edges)

[6b] Querying CLO arrangement slots ...
  No slots returned - avatar may not be loaded yet or CLO version
  doesn't populate arrangement list until after first simulate.
  ! Using fallback slot strategy; stage 7 will apply stronger per-piece offsets.

[7] Arranging patterns in 3D around avatar ...
  ✗ PLACEMENT FAILURE: Live arrangement slots are unavailable in CLO.
     This typically means the avatar is not properly loaded or CLO's
     arrangement metadata is not yet available.
     Pipeline stopping to prevent silent false-positive placement.
     To force degraded-mode placement (not recommended), set:
     ALLOW_DEGRADED_PLACEMENT=1

[7] FAILED
Pipeline aborted at stage 7.
```

### Success Criteria

- ✅ Pipeline **stops before seams** (step 9) and simulation (step 8)
- ✅ Error message is **clear and actionable**
- ✅ Exit code indicates failure (non-zero)
- ✅ Instructions for override are provided (ALLOW_DEGRADED_PLACEMENT=1)
- ✅ `has_live_slots` flag is `false`

### Failure Diagnosis

| Issue | Cause | Solution |
|-------|-------|----------|
| Stage 7 doesn't fail; continues to seams | ALLOW_DEGRADED_PLACEMENT is set or flag check broken | Clear env: `Remove-Item Env:\ALLOW_DEGRADED_PLACEMENT`; verify step_07 code |
| Error message says "Live arrangement slots" but slots ARE returned | Logic inverted | Verify `ctx.has_live_slots` is correctly set in step_06 |
| Pipeline continues past stage 7 silently | Override flag active without being set | Check environment for any ALLOW_DEGRADED flags |

---

## Test 4: Override Gate with ALLOW_DEGRADED_PLACEMENT=1

### Objective

Verify that Stage 7 **can be explicitly overridden** to continue in degraded mode using the `ALLOW_DEGRADED_PLACEMENT=1` flag.

### Prerequisites

- Live arrangement slots are **unavailable** (same condition as Test 3)
- Override flag **will be set**

### Steps

```powershell
# Enable degraded placement override
$env:ALLOW_DEGRADED_PLACEMENT=1

# Optionally enable debug to see payloads
# $env:DEBUG_STAGE6_RAW=1

# Run the pipeline (will continue past Stage 7)
python clo_workspace/plugins/clo_automation_client.py
```

### Expected Behavior

Stage 7 **continues despite missing slots**, applying fallback offsets and proceeding through seams and simulation:

```
[7] Arranging patterns in 3D around avatar ...
  ! DEGRADED MODE: Live arrangement slots unavailable; applying fallback spread offsets.
  pattern 0 -> slot -1:
    [✓] ok
  pattern 1 -> slot -1:
    [✓] ok
  pattern 2 -> slot -1:
    [✓] ok
  pattern 3 -> slot -1:
    [✓] ok

  Arrangement verify:
    pattern 0: requested={'slot': -1, 'x': 10, 'y': 80, 'z': 80, 'orientation': 0, 'position_only': true} reported={...}
    pattern 1: requested={'slot': -1, 'x': 90, 'y': 80, 'z': 80, 'orientation': 180, 'position_only': true} reported={...}
    pattern 2: requested={'slot': -1, 'x': 15, 'y': 25, 'z': 70, 'orientation': 270, 'position_only': true} reported={...}
    pattern 3: requested={'slot': -1, 'x': 85, 'y': 25, 'z': 70, 'orientation': 90, 'position_only': true} reported={...}

[7] OK
Pipeline continuing ...

[8] Draping fabric on patterns ...
...
```

### Success Criteria

- ✅ Stage 7 **proceeds to arrangement commands** instead of failing
- ✅ Output includes **"DEGRADED MODE"** label
- ✅ Fallback offsets are applied (slot indices are -1, positions have spread values)
- ✅ Pipeline continues through stages 8, 9, 10, 11 (seams, simulation, export)
- ✅ Visual CLO result may show stacked or poorly-placed pieces (expected in degraded mode)

### Verification Steps

```powershell
# Verify the override worked by checking the CLO viewport:
# - If avatar was NOT properly loaded, pieces will be stacked
# - This is expected behavior and validates the degraded mode
# - In proper avatar-loaded state, pieces should spread per fallback offsets

# Optional: compare with Test 3 output to confirm only difference is override flag
```

---

## Test 5: Full Run with Debug Mode & Override

### Objective

Capture complete debug data for offline analysis and log validation.

### Steps

```powershell
# Enable both debug and degraded override
$env:DEBUG_STAGE6_RAW=1
$env:ALLOW_DEGRADED_PLACEMENT=1

# Run full pipeline and capture output to file
python clo_workspace/plugins/clo_automation_client.py 2>&1 | Tee-Object -FilePath "full_run_debug_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
```

### Expected Output

Full pipeline completion with:
- ✅ Stage 1: Plugin version and build date
- ✅ Stage 6: Raw payload dumps and file save confirmation
- ✅ Stage 7: Degraded mode execution with spread offsets
- ✅ Stages 8–11: Fabric, seams, simulation, export
- ✅ All output captured in timestamped log file

### Post-Run Analysis

```powershell
# View saved payloads
$payload = Get-Content stage_6_payloads/stage6_payloads_*.json | ConvertFrom-Json

# Analyze pattern info structure
Write-Host "=== PATTERN INFO STRUCTURE ==="
$payload.pattern_info | ConvertTo-Json -Depth 10

# Analyze arrangement list responses
Write-Host "=== ARRANGEMENT LIST RESPONSES ==="
$payload.arrangement_list | ConvertTo-Json -Depth 10

# Check slot availability flag
Write-Host "=== HAS_LIVE_SLOTS ==="
$payload.has_live_slots

# Search log for specific messages
Write-Host "=== STAGE RESULTS FROM LOG ==="
Get-Content full_run_debug_*.log | Select-String "\[.\]" | Select-Object -Last 20
```

### Success Criteria

- ✅ Full pipeline completes to export (stage 11)
- ✅ Timestamp in log file (useful for tracking multiple runs)
- ✅ Payloads saved to JSON and log file
- ✅ All 11 stages completed with "OK" status
- ✅ No exceptions or errors (only expected warnings about degraded mode)

---

## Test 6: Verify Parser Gracefully Handles Schema Variations

### Objective

Ensure Step 6 parser doesn't crash or fail silently on unexpected API responses; confirms fallback mechanisms work.

### Steps

Since direct mocking is complex without modifying the plugin, verify indirectly:

```powershell
# Run with debug mode enabled to see actual API responses
$env:DEBUG_STAGE6_RAW=1

python clo_workspace/plugins/clo_automation_client.py
```

### Inspection

```powershell
# After run, examine the raw payloads to understand CLO's actual schema
$payload = Get-Content stage_6_payloads/stage6_payloads_*.json | ConvertFrom-Json

# Check if any fields are missing or null
function Check-Schema {
    param([object]$obj, [string]$path = "root")
    
    foreach ($key in $obj.PSObject.Properties.Name) {
        $value = $obj.$key
        if ($null -eq $value) {
            Write-Host "⚠️ NULL at $path.$key"
        }
        elseif ($value -is [PSCustomObject]) {
            Check-Schema $value "$path.$key"
        }
    }
}

Check-Schema $payload.pattern_info[0]

# If any nulls found, verify parser used fallback:
# - Pattern name should be "pattern_0", "pattern_1", etc. (fallback)
# - Line count should show "?" (fallback)
```

### Success Criteria

- ✅ No exceptions during Stage 6 parsing
- ✅ All 4 patterns parsed without errors
- ✅ Missing fields handled gracefully with fallback values
- ✅ Parser output shows expected fallback patterns (name, line_count fallbacks in debug output)
- ✅ No "TypeError" or "KeyError" exceptions

### Expected Fallback Behavior

If CLO returns minimal schema:
```json
{
  "info": {}
}
```

Parser should produce:
```
Pattern 0: pattern_0  (? edges)
```

(Both name and line_count filled with fallbacks)

---

## Test 7: End-to-End Scenario with Proper Avatar Loading

### Objective (Optional, Advanced)

Test the full happy-path scenario where CLO **does** have proper avatar and arrangement slots available.

### Prerequisites

- Avatar is **properly loaded** in CLO
- `/arrangement-list` returns **valid slots** (not empty)

### Steps

```powershell
# Clear all override flags
Remove-Item Env:\DEBUG_STAGE6_RAW -ErrorAction SilentlyContinue
Remove-Item Env:\ALLOW_DEGRADED_PLACEMENT -ErrorAction SilentlyContinue

# Run pipeline normally (should complete without hard-fail)
python clo_workspace/plugins/clo_automation_client.py
```

### Expected Behavior

If avatar is loaded and slots are available:
- ✅ Stage 6 shows actual slot information (not empty)
- ✅ `has_live_slots` is `true`
- ✅ Stage 7 **does NOT fail** (continues with slot-based arrangement)
- ✅ Pipeline proceeds through seams and simulation
- ✅ Visual result shows pieces arranged around avatar (not stacked)

If slots are still unavailable:
- ✅ Stage 6 shows recovery attempt message
- ✅ Stage 7 **fails** with clear error (as expected)
- ✅ (This is a cue that avatar needs better setup)

---

## Test Summary Checklist

Use this checklist to track test completion:

- [ ] **Test 1**: Version endpoint prints build date/time in Stage 1
- [ ] **Test 2**: DEBUG_STAGE6_RAW captures and saves raw payloads to JSON file
- [ ] **Test 3**: Hard-fail gate blocks Stage 7 when slots unavailable (without override)
- [ ] **Test 4**: ALLOW_DEGRADED_PLACEMENT=1 override allows Stage 7 to continue
- [ ] **Test 5**: Full debug run completes with all output logged to file
- [ ] **Test 6**: Parser handles schema gracefully (no crashes, fallbacks work)
- [ ] **Test 7** (Optional): End-to-end with proper avatar loads payloads and arranges correctly

---

## Monitoring During Tests

### Key Files to Watch

| File/Location | Purpose |
|---|---|
| `stage_6_payloads/stage6_payloads_*.json` | Raw CLO API response payloads—inspect to understand response structure |
| `full_run_debug_*.log` | Complete pipeline output with all debug info; useful for comparing runs |
| CLO Viewport | Visual confirmation of placement (pieces around avatar vs stacked) |
| Terminal Output | Real-time status, error messages, version info, debug payloads |

### Command Reference

```powershell
# Set debug mode
$env:DEBUG_STAGE6_RAW=1

# Set degraded mode override
$env:ALLOW_DEGRADED_PLACEMENT=1

# Clear environment variables
Remove-Item Env:\DEBUG_STAGE6_RAW
Remove-Item Env:\ALLOW_DEGRADED_PLACEMENT

# Run pipeline
python clo_workspace/plugins/clo_automation_client.py

# Run and log
python clo_workspace/plugins/clo_automation_client.py 2>&1 | Tee-Object -FilePath "run_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

# View latest payload
$payload = Get-Content (Get-ChildItem stage_6_payloads -Name | Sort-Object -Descending | Select-Object -First 1) | ConvertFrom-Json

# Pretty-print JSON
$payload | ConvertTo-Json -Depth 10
```

---

## Troubleshooting Guide

### General Issues

| Issue | Likely Cause | Solution |
|-------|---|---|
| `[ERROR] Could not connect to CLO REST server` | CLO not running or plugin not loaded | Start CLO; verify RestPlugin.dll is active in plugin manager |
| `ModuleNotFoundError: No module named 'requests'` | Virtual environment not active | Run `& .\.venv\Scripts\Activate.ps1` |
| `FileNotFoundError: stage_6_payloads directory` | Directory not created due to permission | Manually create: `mkdir stage_6_payloads` |

### Plugin Issues

| Issue | Likely Cause | Solution |
|---|---|---|
| Build date shows generic/old date | RestPlugin.cpp not recompiled after changes | Rebuild plugin in Visual Studio; ensure DLL is copied to CLO folders |
| `/version` endpoint returns 404 | Plugin DLL is old build without new endpoint | Recompile and deploy new DLL |
| Version endpoint shows `"version": "1.0"` but no build date | Recompile was done but `__DATE__` macro not updated | Force rebuild: Clean → Rebuild Solution in VS |

### Test 3 Issues (Hard-Fail Gate)

| Issue | Likely Cause | Solution |
|---|---|---|
| Stage 7 doesn't fail; continues to seams | `ALLOW_DEGRADED_PLACEMENT=1` is set | Clear: `Remove-Item Env:\ALLOW_DEGRADED_PLACEMENT` |
| Stage 7 fails but error message is generic | step_07 code not updated | Verify step_07_arrange_patterns.py has the hard-fail gate logic |
| Error says "slots unavailable" but `/arrangement-list` has slots | `ctx.has_live_slots` is wrong | Check step_06 correctly sets this flag based on slots response |

### Test 2 Issues (Debug Output)

| Issue | Likely Cause | Solution |
|---|---|---|
| `[DEBUG]` lines don't appear | `DEBUG_STAGE6_RAW` not set or misspelled | Use exact spelling: `$env:DEBUG_STAGE6_RAW=1` |
| JSON payload is malformed in terminal | json library encoding issue | Try: `python -c "import json; print(json.dumps(payload))"` |
| `stage_6_payloads_*.json` file not created | File write failed (permission or PYTHONPATH) | Check workspace write permissions; try manual mkdir |

---

## Success Criteria Summary

✅ **Phase 1 testing is successful when:**

1. **Observability**: Raw CLO payloads are fully inspectable in terminal and saved to JSON files
2. **Gating**: Pipeline explicitly fails when placement context is invalid (no live slots)
3. **Override**: Degraded mode can be explicitly enabled for testing/fallback scenarios
4. **Visibility**: Every run prints plugin build identity (version, date, time)
5. **Robustness**: Parser gracefully handles missing or unexpected API response fields
6. **Clarity**: All output messages are clear and actionable

---

## Next Steps After Testing

After completing all tests:

1. **Archive Test Results**: Save `stage_6_payloads/` and `full_run_debug_*.log` files for each test scenario
2. **Analyze Payloads**: Examine actual CLO response structure to inform Phase 2 (bbox endpoint) planning
3. **Document Findings**: Note any unexpected schema variations for SDK/plugin team
4. **Proceed to Phase 2**: Once Phase 1 tests pass, begin Phase 2 (bbox endpoint + recovery routine)

---

## Version Control

**Branch**: `clothplacement`  
**Phase 1 Changes**: 
- `clo_workspace/plugins/clo_automation_steps/step_06_read_edges_and_slots.py`
- `clo_workspace/plugins/clo_automation_steps/step_07_arrange_patterns.py`
- `clo_workspace/plugins/clo_automation_steps/step_01_health.py`
- `clo_workspace/plugins/clo_automation_steps/client.py`
- `clo_workspace/plugins/RestPlugin.cpp`

Before committing, ensure RestPlugin.cpp rebuild is complete and DLL is current.

---

**Last Updated**: March 19, 2026  
**Phase**: Phase 1 Testing  
**Status**: Ready for Testing
