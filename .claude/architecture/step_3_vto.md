# Step 3: Virtual Try-On - Detailed Architecture

## Overview

**Step 3** combines a personalized avatar with garment patterns to create a physics-simulated virtual try-on. The avatar is dressed, seams are created, and a realistic garment draping is simulated.

**Input**: Avatar (.avt from Step 1) + Patterns (DXF + edge_manifest.json from Step 2)  
**Output**: Physics-simulated virtual try-on with diagnostics  
**Execution**: ~5 minutes for a full VTO (depending on garment complexity)  
**Entry Point**: `python clo_avatar_generation/run_clo_vto.py`

**Key Characteristic**: Step 3 **requires** both Step 1 and Step 2 outputs.

---

## 11-Step Assembly Pipeline

### **Step 1: Health Check**
- Verify CLO plugin is running and responding
- Check plugin capabilities for VTO operations
- Fail fast if plugin not available
- **File**: `step_01_health.py`

### **Step 2: Create New Project**
- Initialize fresh CLO project workspace
- Get project ID for subsequent operations
- Set up project configuration
- **File**: `step_02_new_project.py`

### **Step 3: Import Avatar**
- Load .avt avatar file into CLO project
- Receive avatar geometry and state from CLO
- Optionally apply measurement CSV for avatar adjustment
- **File**: `step_03_import_avatar.py`
- **Input**: Avatar path from Step 1
- **CLO Plugin Call**: `/import-avatar-avt`

### **Step 4: Import Patterns**
- Load 4 DXF pattern files (front, back, left sleeve, right sleeve)
- CLO interprets DXF geometry and registers patterns
- Receive pattern IDs and state
- **File**: `step_04_import_patterns.py`
- **Input**: DXF files from Step 2
- **CLO Plugin Calls**: `/import-pattern` (called 4 times)

### **Step 5: Verify Patterns**
- Validate imported patterns have valid geometry
- Check bounding boxes and edge counts
- Compute pattern hashes for consistency tracking
- **File**: `step_05_verify_patterns.py`
- **Purpose**: Catch import errors early

### **Step 6: Read Edges & Slots**
- Query CLO for avatar slot metadata (predefined placement locations)
- Extract pattern edge information from imported patterns
- Build edge-to-index mapping (preliminary)
- **File**: `step_06_read_edges_and_slots.py`
- **Output**: Slots list, edge counts, candidate arrangements

### **Step 7: Arrange Patterns**
- Position patterns on avatar body (place in slots)
- Use auto-matching (keyword matching on slot names) OR manual specification
- Each pattern gets a slot assignment (e.g., front → "front", sleeve → "left_sleeve")
- **File**: `step_07_arrange_patterns.py`
- **CLO Plugin Call**: `/arrange-pattern`
- **Slot System**:
  - Avatar provides N predefined slots
  - Each slot has location, orientation, size
  - Pipeline auto-matches based on pattern type and keywords
  - Fallback to manual if auto-match fails

### **Step 8: Apply Fabric**
- Assign material properties to each pattern
- Apply colors (from Step 2 color extraction)
- Apply textures/images (from Step 2 design extraction)
- Set fabric parameters (stiffness, weight, etc.)
- **File**: `step_08_apply_fabric.py`
- **CLO Plugin Call**: `/set-pattern-properties`
- **Input**: Colors and design from Step 2 metadata

### **Step 9: Create Seams**
- Wire 10-seam system to sew patterns together
- Use edge_manifest.json from Step 2 to map edge names to CLO indices
- Seam configuration:
  - 2 shoulder seams (front-back connections)
  - 2 side seams (front-back connections)
  - 2 sleeve tube seams (self-seams on each sleeve)
  - 4 armhole seams (sleeves to front/back)
- **File**: `step_09_create_seams.py`
- **Seam Mapping**: See `seams.py` (10-seam T-shirt configuration)
- **CLO Plugin Call**: `/create-seam` (called 10 times)
- **CRITICAL**: Edge names from edge_manifest.json must exactly match seams.py expectations

### **Step 10: Simulate**
- Run 150-step physics simulation
- Gravity, fabric properties, boundary conditions applied
- Simulation converges toward equilibrium (realistic draping)
- Monitor for convergence and stability
- **File**: `step_10_simulate.py`
- **CLO Plugin Call**: `/simulate`
- **Steps**: 150 iterations (configurable)
- **Output**: Final garment state with draping, wrinkles, fit

### **Step 11: Export Note**
- Document final state in native_vto_report.json
- Export any available render/visualization data
- Summarize all 11 steps with success/failure status
- **File**: `step_11_export_note.py`
- **Output**: `native_vto_report.json` with complete diagnostics

---

## Key Classes & Data Structures

### **PipelineContext** (context.py)
Central mutable state container tracking VTO progress.

**Key Attributes**:
- `avatar_path`: Path to .avt avatar from Step 1
- `patterns_dir`: Directory containing DXF files from Step 2
- `project_dir`: CLO project output directory
- `loaded_patterns`: Count and metadata of imported patterns
- `slots`: Avatar slot information (locations, names, capabilities)
- `seams`: 10-seam configuration and wiring
- `arrangement_results`: Pattern-to-slot assignments
- `final_state`: Simulation results and render data

**Key Methods**:
- `write_json()`: Save state to JSON artifact
- `artifact_path(filename)`: Get full path for artifact file

### **CLORestClient** (client.py)
Wrapper for REST API calls to CLO plugin.

**Key Methods**:
- `health_check()`: Test plugin connectivity
- `new_project()`: Create fresh CLO project
- `import_avatar_avt(avatar_path)`: Load avatar
- `import_pattern(dxf_path, pattern_id)`: Load pattern
- `get_slots()`: Query avatar slots
- `arrange_pattern(pattern_id, slot_id)`: Position pattern
- `create_seam(seam_spec)`: Wire seam between edges
- `simulate(num_steps)`: Run physics simulation
- `wait_for_queue(operation_id)`: Poll for completion

### **Seam Mapping** (seams.py)
Defines 10-seam system for T-shirt assembly.

**10-Seam Configuration**:
1. Shoulder Left: front-left-shoulder ↔ back-left-shoulder
2. Shoulder Right: front-right-shoulder ↔ back-right-shoulder
3. Side Left: front-left-side ↔ back-left-side
4. Side Right: front-right-side ↔ back-right-side
5. Sleeve Tube Left: sleeve-left-self-seam (underarm)
6. Sleeve Tube Right: sleeve-right-self-seam (underarm)
7. Armhole Front-Left: front-left-armhole ↔ sleeve-left-armhole
8. Armhole Front-Right: front-right-armhole ↔ sleeve-right-armhole
9. Armhole Back-Left: back-left-armhole ↔ sleeve-left-armhole
10. Armhole Back-Right: back-right-armhole ↔ sleeve-right-armhole

**Edge Names**: Must exactly match names in edge_manifest.json from Step 2.

### **Helpers** (helpers.py)
Utility functions for common VTO operations.

**Key Functions**:
- `resolve_patterns_dir(avatar_path)`: Find latest DXF output from Step 2
- `find_slot(pattern_type, available_slots)`: Auto-select slot by keyword matching
- `score_slots(keyword, slot_names)`: Rank slots by similarity to keyword
- `print_result(step_name, result)`: Format and display step results

---

## Input Data

### **Avatar File**
- **Format**: .avt binary file (from Step 1)
- **Path**: Specified in command-line arguments or config
- **Content**: 3D mesh, vertex positions, material properties

### **Pattern Files**
- **Format**: DXF files (CAD format)
- **Files**: `front_panel.dxf`, `back_panel.dxf`, `sleeve_left.dxf`, `sleeve_right.dxf`
- **Path**: `output/<cloth_id>-<size_id>-<run_number>/panels/dxf/` (from Step 2)
- **Content**: 2D panel geometry with vertices and edges

### **Edge Manifest**
- **File**: `edge_manifest.json` (from Step 2)
- **Content**: Mapping of edge names to CLO geometry indices
- **Example**:
  ```json
  {
    "front_neck": 0,
    "front_left_shoulder": 1,
    "front_right_shoulder": 2,
    "front_left_armhole": 3,
    ...
  }
  ```

### **Optional: Measurement CSV**
- For avatar adjustment before VTO
- Applied in Step 3 (step_03_import_avatar.py)
- Format: CSV with measurement names and values

---

## Output Data

### **VTO Report**
- **File**: `native_vto_report.json`
- **Content**:
  - Each step's results (success/failure, timing)
  - Loaded patterns count and hashes
  - Slot information and arrangement success
  - Edge count and source verification
  - Seam results and wiring success
  - Final status and diagnostics
- **Purpose**: Complete diagnostic record of VTO generation

### **CLO Project**
- Native CLO project file with avatar + patterns + seams + simulation state
- Can be opened in CLO 3D for manual inspection/refinement
- Location: `output/` (path in native_vto_report.json)

### **Render Outputs** (if supported)
- Images, videos, or 3D data suitable for user visualization
- Format depends on CLO plugin capabilities
- Location: `output/` (path in native_vto_report.json)

---

## Slot System Explanation

### **What Are Slots?**
Avatar provides predefined placement locations ("slots") where patterns can be arranged.

**Example Slots for T-Shirt**:
- `front`: Front of torso
- `back`: Back of torso
- `sleeve_left`: Left arm
- `sleeve_right`: Right arm

### **Auto-Slot Matching**
Pipeline tries to match patterns to slots automatically:
1. Pattern type detected (front/back/sleeve)
2. Keywords extracted (e.g., "front" from front_panel.dxf)
3. Available slots scored by similarity to keyword
4. Best-matching slot selected

### **Manual Specification**
If auto-match fails:
- User can manually specify pattern-to-slot mapping
- Passed as configuration parameter
- Guarantees correct placement

### **Arrangement Failure**
- If no suitable slot found, arrangement fails
- VTO cannot proceed without pattern placement
- Must re-try with different avatar or manual specification

---

## 10-Seam System in Detail

### **Why 10 Seams?**
- Minimum seams needed to assemble 4-piece T-shirt
- Each seam connects two edges from different patterns
- Covers shoulders, sides, sleeves, armholes

### **Seam Wiring Process**
1. Get edge names from edge_manifest.json (e.g., "front-left-shoulder")
2. Look up corresponding edges in both patterns
3. Send `/create-seam` command with edge indices
4. CLO validates edge compatibility and creates seam
5. Repeat for all 10 seams

### **Edge Name Matching (CRITICAL)**
- Edge names in edge_manifest.json must exactly match seams.py expectations
- If mismatch: "front_left_shoulder" vs "front-left-shoulder" → seam creation fails
- If edge missing: Entire VTO fails
- See troubleshooting.md for edge mismatch issues

### **Sleeve Tube Seams**
- Self-seams closing each sleeve tube (underarm)
- Keeps sleeve hollow (not solid)
- Allows garment to fit over arm

---

## Physics Simulation Details

### **What It Simulates**
- Gravity: Pulls fabric downward
- Fabric properties: Weight, stiffness, stretch
- Constraints: Seams prevent separation, anchor points prevent movement
- Collision: Patterns don't pass through body

### **150-Step Iteration**
- Each step: Physics calculations → vertex displacement
- Steps continue until convergence (equilibrium reached)
- 150 is typical; can be reduced for speed or increased for accuracy

### **Convergence Detection**
- Monitor energy changes between steps
- If energy stabilizes (low change), simulation converged
- Early termination possible if converged before 150 steps

### **Visual Output**
- Draping folds and wrinkles
- Fabric weight distribution
- Fit on specific body shape
- Realistic appearance matching real garment

---

## Error Handling & Debugging

### **Common Issues**

**Pattern Import Fails**:
- Check DXF files exist and are valid
- Verify file paths are correct
- See troubleshooting.md → "Pattern Import Fails"

**Slot Matching Fails**:
- Auto-matching keywords don't match avatar slots
- Solution: Manually specify pattern-to-slot mapping
- See troubleshooting.md → "Slot Matching Fails"

**Seam Creation Fails**:
- Edge names in edge_manifest.json don't match seams.py expectations
- Solution: Verify edge names exactly match
- See troubleshooting.md → "Seam Creation Fails"

**Simulation Hangs/Timeout**:
- Very complex geometry or strict physics parameters
- Solution: Reduce garment complexity or step count
- See troubleshooting.md → "Physics Simulation Hangs"

### **Debugging Tips**
- Check native_vto_report.json for which step failed
- Verify avatar and patterns are valid (from successful Step 1 & 2)
- Run Step 3 in isolation with added logging
- Inspect edge_manifest.json manually
- Compare edge names against seams.py expectations

---

## Performance Considerations

### **Bottlenecks**
- **Pattern Import**: O(# patterns) - typically fast
- **Seam Creation**: O(# seams) - typically fast
- **Physics Simulation**: O(150 steps × mesh_complexity) - main time consumer

### **Optimization Strategies**
- Reduce pattern mesh complexity
- Reduce physics step count (if fast convergence)
- Early termination on convergence
- Pre-compute avatar slot layout

### **Time Targets**
- Full VTO: <5 minutes
- Typical breakdown: Import 10s, seams 20s, simulation 4m, export 10s

---

## Integration with Step 1 & Step 2

### **Avatar Integration (Step 1 → Step 3)**
- Step 3 imports .avt file from Step 1
- Avatar represents specific user's body (personalized)
- Same avatar can be used for multiple try-ons

### **Pattern Integration (Step 2 → Step 3)**
- Step 3 imports DXF files from Step 2
- Edge manifest critical for seam creation
- **Half-girth convention** in Step 2 must align with Step 3 expectations
- Same patterns can be used for multiple avatars

### **Data Flow Example**
```
User A measurements → Step 1 → Avatar_A.avt
Product Image_1 → Step 2 → Patterns_1.dxf

Avatar_A.avt + Patterns_1.dxf → Step 3 → VTO_A1
Avatar_A.avt + Patterns_2.dxf → Step 3 → VTO_A2

User B measurements → Step 1 → Avatar_B.avt
Avatar_B.avt + Patterns_1.dxf → Step 3 → VTO_B1
```

---

## Related Documentation

- **High-level**: `.claude/architecture/architecture.md`
- **Step 1 details**: `.claude/architecture/step_1_avatar.md` (for reference)
- **Step 2 details**: `.claude/architecture/step_2_ingestion.md` (for reference)
- **Quick reference**: `.claude/quick-reference.md` → Step 3 section
- **FAQ**: `.claude/faq.md` → Step 3 section
- **Troubleshooting**: `.claude/troubleshooting.md` → Step 3 section
- **How to start**: `.claude/commands/start-work.md` → Step 3 section

---

*Last updated: 2026-05-16*
