Here’s your content cleaned, structured, and formatted so you can directly copy and use it (no content removed, just improved readability):

---

# **VTO Remaining Work \+ Slot Root-Cause Research**

**Date:** 2026-03-24

---

## **Objective**

Capture:

1. All current unresolved VTO problems  
2. What is still left from `VTO_SLOTS_AND_EDGE_DATA_DEEP_RESEARCH.md`  
3. In-depth root-cause analysis for empty slot responses even when avatar import succeeds  
4. Long-term, scalable (non-hardcoded) solution design

---

## **Current Unresolved Problems**

### **P0: Arrangement slots still return empty in runtime**

**Symptoms:**

* `GET /arrangement-list` returns `count=0, slots=[]`  
* `GET /pattern-arrangements` returns rows (for pattern indices), but generic entries only  
* Slot map remains unresolved (`front/back/sleeve_L/sleeve_R = -1`) unless degraded fallback is used

**Evidence:**

* `vto/clo_automation_steps/step_06_read_edges_and_slots.py`  
* `clo_workspace/plugins/RestPlugin.cpp` (`/arrangement-list`, `/pattern-arrangements`, `/arrangement/debug`)  
* `vto/output/*/pipeline_report.json` showing `slot_fallback_mode = pattern-arrangements-no-slots`

**Impact:**

* True semantic slot placement is unavailable  
* Pipeline relies on fallback offset-based placement

---

### **P0: True seam reliability remains blocked by edge semantics**

**Symptoms:**

* `line_count` often missing from `GetPatternInformation()` payload  
* Step 6 probes line lengths \+ DXF fallback (still inferred model)  
* Seam correctness depends on geometry hash compatibility

**Evidence:**

* `step_06_read_edges_and_slots.py`  
* `/patterns/{index}/line-lengths`  
* `step_09_create_seams.py`

**Impact:**

* High risk of seam mismatch when geometry changes

---

### **P1: Arrangement quality not validated post-placement**

**Symptoms:**

* Step 7 only checks existence of arrangement records  
* No overlap/spacing validation

**Impact:**

* Cloth pieces may intersect or be poorly spaced

---

### **P1: Scale gate still blocks diagnostics**

**Symptoms:**

* Scene mismatch is advisory  
* Metadata ratio still causes hard-fail

**Impact:**

* Debugging becomes harder due to early exits

---

### **P1: Slot matching is keyword-based and fragile**

**Symptoms:**

* Text matching (`front`, `back`, `left sleeve`, etc.)  
* Breaks with localization or payload changes

**Impact:**

* Poor semantic mapping across environments

---

### **P2: No avatar-readiness contract before slot query**

**Symptoms:**

* No explicit `avatar-ready-for-arrangement-slots` check  
* Slot queries assume readiness after queue drain

**Impact:**

* Slot calls may execute too early

---

## **What Is Left From Deep Research Document**

### **Implemented:**

* Plugin endpoints (bbox, line-length, debug info)  
* Distinct fallback offsets in Step 7  
* Scene-scale advisory (not hard-fail)

### **Pending:**

1. Capability contract refinement (runtime readiness flags)  
2. Full slot strategy chain  
3. Edge provider abstraction with confidence scoring  
4. Arrangement quality verification \+ retry system  
5. Step 5 split (hard vs advisory modes)  
6. Regression harness for slots, overlap, edge confidence

---

## **Root-Cause Research: Why Slots Are Empty**

### **Confirmed Observations**

1. Avatar import succeeds  
2. Pattern import succeeds  
3. `GetArrangementList()` returns empty  
4. `GetArrangementOfPattern(i)` returns generic data  
5. Direct offset-based arrangement works

---

## **Root-Cause Candidates**

### **A) Avatar Generation Output (High Confidence)**

**Findings:**

* STAR avatar exported as OBJ (static mesh)  
* No CLO-native semantic/rig metadata

**Why it matters:**

* CLO slots depend on semantic avatar anchors  
* Imported mesh lacks these anchors

**Solution:**

* Add avatar capability handshake  
* Detect anchor availability  
* Switch to geometry-based mode if absent

---

### **B) SDK/API Behavior Variance (High Confidence)**

**Findings:**

* `GetArrangementList()` can legitimately return empty  
* Plugin only reports API availability, not readiness

**Solution:**  
Add readiness flags:

* `arrangement_list_populated`  
* `arrangement_slots_semantic`  
* `avatar_anchor_mode`

---

### **C) Pipeline Timing/State (Medium Confidence)**

**Findings:**

* No slot warmup phase  
* Queue drain ≠ full CLO state readiness

**Solution:**  
Add slot bootstrap:

1. Query slots  
2. If empty → warmup (simulate/refresh)  
3. Retry with backoff  
4. Persist diagnostics

---

### **D) Clothes Import Mode (Medium Confidence)**

**Findings:**

* DXF append mode used  
* No semantic linkage to avatar slots

**Solution:**

* Add diagnostics (bbox, area, line lengths)  
* Compare pre/post arrangement state

---

### **E) API Usage Model Mismatch (Medium Confidence)**

**Findings:**

* Pipeline assumes slots must exist  
* Direct positioning works without slots

**Solution:**  
Define dual modes:

* Semantic-slot placement  
* Geometry-anchor placement

---

## **Most Likely Explanation**

1. STAR OBJ avatar is usable for simulation  
2. But lacks semantic arrangement slots  
3. CLO returns empty slot list  
4. Pattern-level arrangement still works  
5. Therefore → issue \= semantic readiness, not import failure

---

## **Long-Term Scalable Architecture**

### **1\) Capability \+ Readiness Contract (Plugin)**

Add fields:

* `has_arrangement_list_api`  
* `arrangement_list_populated`  
* `arrangement_semantics_quality`  
* `avatar_semantic_mode`  
* `slot_query_stage`

---

### **2\) Arrangement Provider Chain**

Order:

1. SemanticSlotProvider  
2. FuzzySlotProvider  
3. GeometryAnchorProvider  
4. RetryProvider

Each returns:

* Placement intent  
* Confidence score

---

### **3\) Edge Provider Chain**

Order:

1. SDKLineProbeProvider  
2. SDKInputInfoProvider  
3. DXFEdgeProvider  
4. HybridValidator

Outputs:

* Edge index map  
* Confidence score  
* Diagnostics

---

### **4\) Hard vs Advisory Gate Split**

**Hard Fail:**

* Missing files  
* Import mismatch  
* Critical API failure

**Advisory:**

* Empty slots  
* Low edge confidence

---

### **5\) Observability Contract**

Persist:

* Slot payloads (all retries)  
* Selected provider \+ confidence  
* Arrangement quality metrics  
* Edge validation results

---

## **Concrete Implementation Backlog**

### **Phase A: Slot Instrumentation**

1. `/avatar/debug` endpoint  
2. Slot warmup \+ retries  
3. Log slot payload across stages

---

### **Phase B: Provider Abstractions**

1. `ArrangementProvider` interface  
2. `EdgeProvider` interface  
3. Replace keyword matching

---

### **Phase C: Quality \+ Retry**

1. Overlap/distance checks  
2. Retry with spread/orientation  
3. Store metrics in `pipeline_report.json`

---

### **Phase D: Seam Hardening**

1. Geometry-hash binding  
2. Confidence-based failure  
3. Regression fixtures

---

## **Non-Hardcoded Design Principles**

1. No CLO version branching  
2. No reliance on slot names  
3. No dependence on `info.name`  
4. Use runtime capability \+ confidence  
5. Treat fallback as first-class

---

## **Recommended Next Step**

Implement **Phase A (Slot Instrumentation)** first.

Reason:

* Converts guesswork → measurable runtime evidence  
* Enables correct provider selection  
* Fastest path to clarity

---

📌 Source:

