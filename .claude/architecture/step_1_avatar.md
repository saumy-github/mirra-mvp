# Step 1: Avatar Generation - Detailed Architecture

## Overview

**Step 1** creates a unique, reusable 3D digital twin for each user based on their body measurements. The avatar is personalized through a morphing algorithm that displaces vertices to match the user's real-world dimensions.

**Input**: User ID + body measurements (height, weight, chest, waist, hip, leg length, etc.)  
**Output**: Personalized .avt avatar file (stored and reused for all future sessions)  
**Execution**: ~30 seconds for a typical user  
**Entry Point**: `python clo_avatar_generation/run_avatar.py`

## 11-Step Pipeline

### **Step 1: Health Check**
- Verify CLO plugin is running and responding
- Check plugin capabilities (avatar import, measurement application)
- Fail fast if plugin not available
- **File**: `step_01_health.py`

### **Step 2: Run Setup**
- Create output directory: `output/<user_id>-<run_number>/`
- Initialize run manifest with metadata
- Prepare logging and artifact tracking
- **File**: `step_02_run_setup.py`

### **Step 3: Fetch Measurements**
- Query MongoDB "measurements" collection OR read local JSON input
- Validate measurement data exists and is complete
- Store original measurements in `mongo_snapshot.json`
- **File**: `step_03_fetch_measurements.py`
- **Data Source**: MongoDB or JSON file specified in config

### **Step 4: Resolve Base Avatar**
- Select gender-appropriate base avatar template
- Load template from file (`.avt` format)
- Verify template exists and is valid
- **File**: `step_04_resolve_base_avatar.py`
- **Templates**: Separate templates for male/female body shapes

### **Step 5: Normalize Targets**
- Validate measurement values are within expected ranges
- Apply any data transformations (e.g., unit conversions)
- Check for completeness (all required fields present)
- **File**: `step_05_normalize_targets.py`
- **Ranges**: See quick-reference.md for typical ranges

### **Step 6: Build Payloads**
- Create CLO-compatible payloads from measurements
- Generate 3 types: JSON bridge, CSV bridge, AVT patch
- Create measurement specification document
- **File**: `step_06_build_payloads.py`
- **Formats**:
  - CSV: Traditional measurement template format
  - JSON: Property-based specification
  - AVT: Binary patch for direct file modification

### **Step 7: Import Base Avatar**
- Send base avatar template to CLO plugin
- CLO loads avatar into active project
- Receive confirmation and initial state
- **File**: `step_07_import_base_avatar.py`
- **CLO Plugin Call**: `/import-avatar-avt`

### **Step 8: Apply Measurements**
- Send measurement payloads to CLO plugin
- CLO applies measurements via morphing algorithm
- Vertex displacement creates personalized shape
- **File**: `step_08_apply_measurements.py`
- **Methods**: CSV, properties, or AVT patch (configurable)
- **CLO Plugin Call**: `/import-avatar-measurements` or `/set-avatar-properties`

### **Step 9: Read Back**
- Query CLO for applied measurements
- Verify measurements were correctly applied
- Store applied measurements in output
- **File**: `step_09_readback.py`
- **Purpose**: Validation and diagnostic information

### **Step 10: Compute Error**
- Compare input measurements vs. applied measurements
- Calculate per-measurement error and overall accuracy
- Generate accuracy report with metrics
- **File**: `step_10_compute_error.py`
- **Output**: `error_report.json` with accuracy %

### **Step 11: Save Outputs**
- Export modified avatar as `.avt` file
- Save all artifacts (JSON, images, logs)
- Summarize run results in `output.json`
- **File**: `step_11_save_outputs.py`
- **Output Files**: Avatar + JSON artifacts

---

## Key Classes & Data Structures

### **Step1Context** (context.py)
Central mutable state container tracking pipeline progress.

**Key Attributes**:
- `user_id`: User identifier
- `run_dir`: Output directory path
- `measurements`: Input body measurements (dict)
- `base_avatar_path`: Path to template avatar file
- `clo_payloads`: Generated CLO-compatible payloads (dict)
- `import_result`: Avatar import response from CLO
- `apply_result`: Measurement application response from CLO
- `readback_measurements`: Measurements after applying
- `error_report`: Accuracy metrics

**Key Methods**:
- `write_json()`: Save state to JSON artifact
- `artifact_path(filename)`: Get full path for artifact file
- `require_run_dir()`: Ensure output directory exists

### **CLORestClient** (client.py)
Wrapper for REST API calls to CLO plugin.

**Key Methods**:
- `health_check()`: Test plugin connectivity
- `import_avatar_avt(avatar_path)`: Load avatar into CLO
- `import_avatar_measurements(payloads)`: Apply measurements
- `set_avatar_properties(properties)`: Alternative measurement method
- `wait_for_queue(operation_id)`: Poll for completion
- All methods handle timeouts and retries

### **Field Contract** (field_contract.py)
Defines measurement field names, types, and validation rules.

**Includes**:
- Male/female measurement field definitions
- Valid ranges for each measurement
- Unit specifications (cm, kg)
- Required vs. optional fields

---

## Input Data

### **From MongoDB**
- Collection: `measurements`
- Document format: Contains user measurements and metadata
- Query: By user_id

### **From JSON File**
- Format: Flat JSON object with measurement fields
- Example:
  ```json
  {
    "user_id": "u_001",
    "gender": "male",
    "height": 175,
    "weight": 75,
    "chest_circumference": 100,
    "waist_circumference": 85,
    ...
  }
  ```

### **Required Fields (Varies by Gender)**
**Male**:
- Height, weight
- Shoulder width, chest circumference, waist circumference, hip circumference
- Leg length, optional: arm length, back length

**Female**:
- Height, weight
- Shoulder width, bust circumference, under-bust circumference, waist circumference, hip circumference
- Leg length, optional: arm length, back length

---

## Output Data

### **Primary Output**
- **`<user_id>.avt`** - Modified avatar file ready for use in Step 3

### **Artifacts** (for debugging and auditing)
- **`input.json`** - Input payload specification
- **`mongo_snapshot.json`** - Original measurement document from MongoDB
- **`clo_payload.json`** - Human-readable measurement specification
- **`import_result.json`** - Avatar import response from CLO
- **`apply_result.json`** - Measurement application response from CLO
- **`error_report.json`** - Accuracy metrics (per-field errors, overall %)
- **`output.json`** - Complete run summary with artifact paths and status

---

## Avatar Morphing & Accuracy

### **How It Works**
- Base avatar has N vertices distributed across the mesh
- Measurement values define target dimensions
- Morphing algorithm displaces vertices to match targets
- Result: Avatar shape changes while maintaining structure

### **Accuracy Metrics**
- Per-measurement error: |target - applied| / target × 100%
- Overall accuracy: Mean of all per-measurement errors
- Target: <5% error for 95% of population

### **Factors Affecting Accuracy**
- Base avatar template appropriateness for body shape
- Measurement quality (accurate tape measurements)
- Extreme body shapes (very tall, very short, very wide)
- Number of morphing iterations (algorithm convergence)

---

## Measurement Convention

**Body Measurements** for Step 1:
- **Height**: Total body height in cm (e.g., 175 cm)
- **Weight**: Body weight in kg (e.g., 75 kg)
- **Shoulder Width**: Shoulder tip to shoulder tip in cm
- **Chest/Bust Circumference**: Widest part of chest/bust in cm
- **Waist Circumference**: Narrowest part in cm
- **Hip Circumference**: Widest part in cm
- **Leg Length**: Waist to ankle in cm

All measurements are **absolute** (not half-girth).

---

## Dependencies

### **Required**
- CLO plugin must be running (clo_workspace/)
- Base avatar template files must exist
- MongoDB access OR JSON input file
- Python dependencies in requirements.txt

### **Data Dependencies**
- Step 1 has no dependencies on Step 2 or 3
- Completely independent

---

## Error Handling & Debugging

### **Common Issues**

**CLO Plugin Not Responding**:
- Check CLO application is running
- Verify plugin build is current
- Check network/API connectivity
- See troubleshooting.md

**Measurements Out of Range**:
- Verify input data is correct
- Check measurement field names match field_contract.py
- Review mongo_snapshot.json for data source

**Low Accuracy Metrics**:
- Check error_report.json for which measurements have high error
- Verify base avatar is appropriate for body shape
- Try with fresh avatar template

### **Debugging Tips**
- All step results are in output/ folder in JSON format
- Check error_report.json first (tells you what didn't match)
- Add print() statements in specific step files
- Run single step in isolation with added logging

---

## CLO Plugin API Calls

**Health Check**:
```
GET /health
GET /capabilities
```

**Avatar Import**:
```
POST /import-avatar-avt
Body: { avt_file_path, project_id }
```

**Measurement Application**:
```
POST /import-avatar-measurements
Body: { measurements_csv, avatar_id }
OR
POST /set-avatar-properties
Body: { property_specifications }
```

**Status Polling**:
```
GET /queue/<operation_id>
```

See `clo_workspace/plugin_contract.json` for complete endpoint definitions.

---

## Related Documentation

- **High-level**: `.claude/architecture/architecture.md`
- **Quick reference**: `.claude/quick-reference.md` → Step 1 section
- **FAQ**: `.claude/faq.md` → Step 1 section
- **Troubleshooting**: `.claude/troubleshooting.md` → Step 1 section
- **How to start**: `.claude/commands/start-work.md` → Step 1 section

---

*Last updated: 2026-05-16*