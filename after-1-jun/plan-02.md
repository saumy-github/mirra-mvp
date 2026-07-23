# Plan 002 — CLO Avatar Research Roadmap

**Status**: Research-only (no code changes)  
**Created**: 2026-07-03  
**Updated**: 2026-07-03 (clarified scope: reverse-engineering only, removed implementation/testing phases)  
**Objective**: Reverse-engineer CLO avatar system by analyzing available files to understand how CLO works  
**Scope**: Extract and document information from files in `research_files/` folder ONLY. Do NOT test routes, improve implementations, or run pipelines. Implementation/improvement work will be done later.

---

## Phase 1: Quick Wins & Baseline Data

**Goal**: Establish baseline understanding of avatars in research_files/ without external dependencies

### 1.1 Inventory All Avatars & Extract Baseline Feature Values
- **Task**: Systematically analyze all `.avt` files in `research_files/` folder
  - List all avatars (filename, type, gender if determinable)
  - Extract all 57 feature values from each `.dan` file
  - Determine avatar gender via: texture file names, feature patterns, metadata
  - Record avatar characteristics (apparent height, build, proportions)
- **Why Critical**: 
  - May reveal a female avatar already in research_files/ (accelerate Phase 2)
  - Provides baseline 57-value data for Phase 1.2 comparison
  - Establishes gender detection method for later use
- **How**: 
  1. Write Python script: extract all `.avt` → extract `.dan` → read 57 floats
  2. Analyze texture file names (female textures often contain "breast", "bust", etc.)
  3. Compare feature patterns (female bust/under-bust slots may differ)
- **Verification**: Produce table of all avatars with 57 feature values, gender classification
- **Output**: `results.md` entry: "Avatar Inventory & Baseline Feature Values"

### 1.2 Analyze Readable Strings in Binary Files
- **Task**: Extract and catalog all human-readable text from `.avs`, `.iks`, `.mea` files
- **Why Important**: May reveal feature slot purposes, naming patterns, or structural hints (supports Phase 3 reverse-engineering)
- **How**: 
  1. Hex dump binary files, extract ASCII/UTF-8 readable sections
  2. Identify patterns (e.g., "listFeatureValues", "BaseFeature", bone names, measurement markers)
  3. Document context and location
- **Verification**: Complete list of readable strings per file type
- **Output**: `results.md` entry: "Binary File Readable Strings Analysis"

### 1.3 CSV Format Analysis
- **Task**: Examine existing CSV files in `research_files/` to understand structure and format
- **Why Important**: Reverse-engineer CLO's expected measurement CSV format from available examples
- **How**: 
  1. Open `avatar_measurements__*.csv` files
  2. Analyze column names, formats, value ranges, patterns
  3. Document structure and any discoverable patterns
- **Verification**: Document format observations and structure
- **Output**: `results.md` entry: "CSV Format Analysis"

### 1.4 Weight Feature Investigation
- **Task**: Analyze existing avatars to identify which feature slot may control weight
- **Why Important**: Weight measurement has no known feature index; discover it by analyzing file data
- **How**: 
  1. If multiple avatars with known/different weights exist in research_files/, compare all 57 feature values
  2. Identify which slot differs most between them (likely weight candidate)
  3. Check feature slot 1 and nearby slots (likely location based on CLO structure patterns)
- **Verification**: Document hypothesis for weight slot with supporting evidence
- **Output**: `results.md` entry: "Weight Feature Index Hypothesis"

---

## Phase 2: Female Avatar Analysis

**Goal**: Analyze and compare female vs male avatars to identify gender-specific features

### 2.1 Obtain Female Avatar Template
- **Task**: Acquire a female `.avt` file from CLO SDK or vendor
- **Why Critical**: Female feature indices cannot be discovered without a female avatar to analyze
- **How to Verify**: Confirm it's a valid `.avt` (ZIP with `.dan` file inside), contains female textures
- **Owner**: (Requires vendor contact or SDK access)
- **Acceptance Criteria**: Have a female `.avt` file in `clo_avatar_generation/input/` that can be extracted and read

### 2.2 Discover Female Feature Indices
- **Task**: Compare 57 feature values from male and female avatars to identify gender-specific indices
- **Prerequisites**: Phase 1.1 (baseline feature extraction), Phase 2.1 (female template acquired)
- **Why Critical**: Bust and under-bust measurements cannot be applied without knowing which slots to write to
- **How**: 
  1. Use 57-value baseline from Phase 1.1 for `base-1.avt` (male)
  2. Extract 57 feature values from female `.avt` template (from Phase 2.1)
  3. Produce comparison table: which slots are identical (shared), which differ (female-specific)
  4. Identify which different slots likely correspond to bust/under-bust based on patterns
- **Verification**: Comparison table showing all 57 slots, male vs female values, gender-specific indices identified
- **Output**: Research file: `after-1-jun/female-feature-index-mapping.md`

### 2.3 Test Female Feature Indices via Manual CLO Morphing
- **Task**: Manually morph female avatar in CLO, record which measurements change
- **Why Critical**: Confirm feature index hypotheses from 1.2 with actual CLO behavior
- **How**:
  1. Load female avatar in CLO
  2. Manually adjust bust measurement in CLO UI
  3. Read the modified `.dan` file, identify which slots changed
  4. Repeat for under-bust, shoulder, waist (to verify male indices still apply)
- **Verification**: Slot changes match predictions from 1.2
- **Output**: Confirmed female feature index mapping

### 2.4 Document Female Measurement Ranges & Requirements
- **Task**: Research typical female body measurement ranges
- **Why Important**: Avoid rejecting valid measurements as out-of-range
- **How**:
  1. Collect anthropometric data for female body measurements
  2. Compare to current male ranges
  3. Determine if separate validation ranges needed for female
- **Verification**: Have documented ranges with sources
- **Output**: Updated validation ranges in field contract

---

## Phase 3: Binary Format Reverse-Engineering

**Goal**: Reverse-engineer and document proprietary CLO binary file formats

### 3.1 Reverse-Engineer .avs Serialization Format
- **Task**: Decode avatar state binary format
- **Why**: Could enable lightweight state snapshots without writing full `.avt` files
- **How**:
  1. Collect multiple `.avs` files with known feature values
  2. Compare binary differences to find patterns
  3. Identify field boundaries, value encoding
  4. Write partial decoder (at least feature block extraction)
- **Verification**: Can read feature values from `.avs` file matching `.dan` file
- **Output**: Binary format documentation + Python decoder stub

### 3.2 Map All Remaining Feature Slots (Analysis)
- **Task**: Document all 57 feature slots based on available files and discoverable patterns
- **Prerequisites**: Phase 1.2 (readable strings), Phase 1.4 (weight hypothesis)
- **Methods**:
  1. Analyze readable strings from Phase 0.2 to identify feature names/patterns
  2. Compare multiple avatars' 57 values to identify patterns (e.g., which slots vary with body characteristics)
  3. Use feature naming patterns, metadata, and documented CLO targets to label slots
  4. Document weight slot hypothesis from Phase 0.4
  5. Note which slots are identifiable vs. unknown from available files alone
- **Verification**: Complete list of all 57 slots with: identified name (if discoverable), purpose (if identifiable), or "unknown"
- **Output**: Complete feature slot reference table documenting what we can determine from files

### 3.3 Understand .iks Skeleton Format (Analysis)
- **Task**: Reverse-engineer IK bone mapping format from available `.iks` files
- **Why**: Understand skeleton/rigging structure without CLO SDK documentation
- **How**:
  1. Extract `.iks` files from research_files/
  2. Extract readable strings (bone names) already found in Phase 1.2
  3. Analyze binary structure by comparing patterns between different avatar files
  4. Map identifiable bone names to their positions in binary format
- **Output**: IK format documentation (structure, bone name mappings, encoding patterns)

### 3.4 Document .dan File Complete Structure (Analysis)
- **Task**: Map out the full `.dan` file structure beyond feature slots
- **Why**: Understand how CLO organizes avatar data in the binary format
- **How**:
  1. Analyze `.dan` file structure by examining binary patterns and readable markers
  2. Locate and identify: vertex position data (large binary blocks), texture UV coordinates, feature block, metadata
  3. Document offset locations and data types where discoverable
- **Output**: `.dan` file format specification (structure, known sections, offsets, data types)

---

## Phase 4: Secondary Measurement Discovery

**Goal**: Identify which feature slots correspond to secondary body measurements

### 4.1 Discover Secondary Measurement Slots (Analysis)
- **Task**: Identify which unmapped feature slots likely control secondary measurements (arm, neck, back, etc.)
- **Prerequisites**: Phase 3.2 (complete feature slot mapping from files)
- **How**: 
  1. Analyze feature slot names/purposes identified in Phase 3.2
  2. Use readable string patterns (bone names, measurement names) from Phase 1.2
  3. Compare avatar samples to identify which slots vary independently from core 6
  4. Hypothesize secondary measurement → slot mappings
- **Verification**: Document hypothesized mappings with supporting evidence from file analysis
- **Output**: Secondary measurement candidates with proposed feature slot indices

---

## Phase 5: Deep Dive Binary & Data Analysis

**Goal**: Investigate unclear aspects and verify assumptions from Phases 1-4

### 5.1 Compare .avs vs .dan Feature Values
- **Task**: Extract feature values from same avatar's .avs and .dan files, compare for equality
- **Why**: Determine if .avs is a complete state snapshot or a reference/derivative
- **How**:
  1. For each avatar with both .avs and .dan available
  2. Extract 57 features from .dan file
  3. Extract 57 features from corresponding .avs file
  4. Compare all 57 values for exact match or differences
  5. Document findings per avatar
- **Verification**: Complete value comparison table showing match/difference status
- **Output**: `results.md` entry: ".avs vs .dan Feature Value Comparison"

### 5.2 Decode the 273-Byte Unknown Offset
- **Task**: Analyze the 273 bytes between "listFeatureValues" marker and first feature value
- **Why**: Could contain encoding info, metadata, or critical offsets
- **How**:
  1. Extract exact 273 bytes from multiple avatars
  2. Look for patterns: magic numbers, null bytes, repeated sequences
  3. Try to identify structure: header fields, checksums, version info
  4. Compare across male/female/kid avatars for consistency
- **Verification**: Identify byte patterns and document hypothesis
- **Output**: `results.md` entry: "273-Byte Offset Structure Analysis"

### 5.3 Search for CLO SDK/API/Documentation Files
- **Task**: Search entire CLO folder for Python files, documentation, API references
- **Why**: May contain feature slot mapping or avatar parameter documentation
- **How**:
  1. Search for .py, .txt, .md, .doc files in CLO folder
  2. Search for files with "feature", "avatar", "measurement", "api" in name
  3. Search for files with "parameter", "slot", "morph" in name
  4. Check Configuration and Plugins folders for reference files
  5. Extract readable content from any found files
- **Verification**: Document all found files and their content relevance
- **Output**: `results.md` entry: "CLO SDK/Documentation Search Results"

### 5.4 Investigate Avatar Size Differences
- **Task**: Analyze why different avatars have different file sizes
- **Why**: Could indicate different mesh resolutions, compression, or structure
- **How**:
  1. Compare file sizes: Kid (15.1 MB) vs Female (20.6 MB) vs Male (21.3 MB)
  2. Extract and compare .dan file sizes (mesh data section)
  3. Check if vertex/polygon counts differ
  4. Analyze file structure differences per avatar type
- **Verification**: Document size breakdown and theories
- **Output**: `results.md` entry: "Avatar Size & File Structure Analysis"

### 5.5 Check Male vs Female .avs Structure Differences
- **Task**: Compare male and female .avs files for structural differences beyond values
- **Why**: Could reveal gender-specific encoding or metadata
- **How**:
  1. Compare male (.avs) vs female (.avs) file sizes
  2. Compare marker positions and offsets
  3. Compare readable string content (identical or different?)
  4. Compare trailing data sections
  5. Document any structural differences
- **Verification**: Detailed structural comparison table
- **Output**: `results.md` entry: "Male vs Female .avs Structure Comparison"

### 5.6 Analyze Trailing Data Sections
- **Task**: Reverse-engineer the purpose of trailing data in .dan and .avs files
- **Why**: Could contain deformation blends, texture mapping, or other parameters
- **How**:
  1. Extract trailing 45 KB from .dan files
  2. Extract trailing 520 bytes from .avs files
  3. Look for patterns: null bytes, repeated sequences, float values, ASCII strings
  4. Compare trailing data across different avatars
  5. Try to identify data type and structure
- **Verification**: Document patterns found and hypotheses
- **Output**: `results.md` entry: "Trailing Data Structure Analysis"

---

## Research Output Checklist

### Research Findings to Document (in results.md)

**Phase 1** (Baseline & Analysis):
- [ ] Avatar Inventory & Baseline Feature Values (all 57 floats per avatar)
- [ ] Binary File Readable Strings Analysis (from .avs, .iks, .mea files)
- [ ] CSV Format Analysis (structure, columns, patterns)
- [ ] Weight Feature Index Hypothesis (if discoverable from existing avatars)

**Phase 2** (Female Avatar Understanding):
- [ ] Female vs Male Feature Indices comparison table (all 57 slots)
- [ ] Gender-specific indices identified (which slots differ)

**Phase 3** (Binary Format Reverse-Engineering):
- [ ] Complete feature slot reference table (all 57 slots, CLO names/purposes)
- [ ] AVS serialization format documentation (structure, encoding)
- [ ] IKS skeleton format documentation (joint mapping, structure)
- [ ] DAN file complete structure documentation (beyond feature slots)

**Phase 4** (Secondary Measurement Discovery):
- [ ] Secondary measurement candidates with proposed feature slot indices (from file analysis)

### Code/Scripts to Create

- **Phase 1**: Write 4 Python analysis scripts (extract avatars, read strings, analyze CSVs, test weight hypothesis)
- **Phases 2–4**: Research/documentation only (no code implementation)

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Female template unavailable in research_files/ | 🔴 High | User will provide female .avt separately; proceed with male avatar analysis first |
| Feature indices cannot be fully discovered from files alone | 🟠 Medium | Document what's discoverable; incomplete mapping is acceptable for research |
| Binary formats too complex to decode completely | 🟡 Low | Partial documentation is valuable; focus on readable markers and patterns |
| Insufficient avatar samples for weight index hypothesis | 🟡 Low | Hypothesis only; will be verified later |

---

## Success Criteria

**Phase 1**: Baseline data extracted from all research_files/ avatars, gender detection method established, 57-value tables produced  
**Phase 2**: Female vs male feature indices compared (assuming female .avt provided), gender-specific slots identified  
**Phase 3**: All 57 feature slots documented (names, purposes, or "unknown" if not discoverable), binary formats partially reverse-engineered  
**Phase 4**: Secondary measurement slots identified where patterns exist
