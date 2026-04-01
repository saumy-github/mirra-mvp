# CLO Avatar Research Plan

This file is a future research checklist for the CLO-native avatar lane.

It is organized around the two questions that matter most for Mirra:

1. How good is the CLO avatar for **Step 1: Personal Digital Twin**?
2. How good is the CLO avatar for **Step 3: Virtual Try-On Experience**?

The goal of this file is not to give answers yet. The goal is to list what we
still need to find, verify, collect, and compare.

## Step 1 Research: CLO Avatar As The Personal Digital Twin

This section is about how good the CLO avatar is at generating or representing
a person-specific avatar that can act as the body foundation for Mirra.

### 1. Avatar Source Options To Research

We need to identify all valid ways a CLO avatar can enter our system.

Research questions:

1. What kinds of avatar sources can CLO use for this lane?
2. Which of them are editable after loading?
3. Which of them preserve native CLO semantics best?
4. Which of them preserve arrangement slots best?
5. Which of them are easiest to automate?

Source types to investigate:

1. Default CLO avatars from the app/library
2. `.avt` avatars saved from the CLO app
3. CLO-converted avatars
4. Any size-editable CLO avatar type
5. Any non-size-editable CLO avatar type that still works well for VTO

### 2. Starting Mesh / Starting Avatar Selection

We need to decide how we will choose the base avatar before applying user
measurements.

Research questions:

1. What should be our default starting avatar for men?
2. What should be our default starting avatar for women?
3. Do we need more than one base avatar family?
4. Does the slot layout differ between different CLO base avatars?
5. Does the editable measurement set differ between different CLO base avatars?
6. Which starting avatar gives the cleanest garment placement for shirts,
   tops, and sleeves?
7. Which starting avatar is the best visual base if this avatar is shown to the
   user?

Selection criteria to capture:

1. Native slot availability
2. Measurement editability
3. Compatibility with measurement import
4. Visual neutrality
5. Good body proportions as a starting point
6. Stability across CLO versions
7. Ease of saving and reusing as `.avt`

### 3. Editable Dimensions And Body Controls

We need a full inventory of what parts of a CLO avatar can actually be changed.

Research questions:

1. Which body measurements can be directly edited on the chosen CLO avatar?
2. Which body measurements are visible but not editable?
3. Which body measurements exist only in detailed settings?
4. Which measurements are controlled by higher-level fields instead of direct
   fields?
5. Which measurements change independently and which ones trigger other body
   changes?
6. Can waist, hip, inseam, neck, arm, shoulder, bust, and height all be set in
   a controlled way?
7. Are there different editable fields for male and female avatars?
8. Are the editable fields identical for all CLO avatar families?

Data to collect:

1. A field-by-field list of editable measurements for each chosen base avatar
2. The exact field names shown by CLO
3. The units used by CLO
4. Whether each field is direct, linked, derived, or hidden
5. Whether the field survives save/load in `.avt`

### 4. Measurement Input Formats And Schemas

We need to discover the exact data format CLO expects when measurements are
passed through automation.

Research questions:

1. What is the exact schema for `ImportAvatarMeasurement(...)`?
2. What is the exact schema for `ImportMeasurement(...)`?
3. Does CLO expect a specific CSV structure for each avatar family?
4. Are `.avs` and `.mea` more suitable than CSV for some cases?
5. Does the same file format work for all templates, or is it template-specific?
6. Which fields are required and which are optional?
7. Are there ordering constraints in the file?
8. Are there version constraints in the file?

Schemas and file types to find:

1. Real CLO-exported measurement CSV samples
2. Real `.avs` files
3. Real `.mea` files
4. Any schema differences between avatar families
5. Any schema differences between CLO versions

For each format, we should capture:

1. Example file
2. Header names
3. Value rows
4. Required fields
5. Optional fields
6. Whether import succeeded
7. Which avatar template it worked with

### 5. Mirra Input Data To CLO Mapping

We need to understand what user/body data Mirra must produce so the CLO avatar
can be generated consistently.

Research questions:

1. Which user measurements are truly required by CLO for a usable avatar?
2. Which measurements can be estimated safely if the user does not provide
   them?
3. Which fields can come from our trained model?
4. Which fields may need clothing-standard defaults?
5. Which fields should remain first-class Mirra inputs even if CLO uses
   different names?

Data groups to define:

1. Required user-provided fields
2. Optional user-provided fields
3. Model-derived fields
4. Approximation/default fields
5. Identity and family-selection fields

Questions to answer for each field:

1. What is the Mirra name?
2. What is the CLO name?
3. Is the mapping direct or indirect?
4. Is the field mandatory?
5. What should happen if the field is missing?

### 6. How We Will Pass The Information

We need to define the exact operational method for sending body data into CLO.

Research questions:

1. Should we always load a base `.avt` first and then apply measurements?
2. Should we keep one saved template avatar per family?
3. Should the pipeline generate a temporary measurement file for each user?
4. Should the pipeline save the resized avatar after applying measurements?
5. Should the saved result become a user-specific `.avt` artifact?
6. At what point in the pipeline should measurement import happen?
7. Does measurement import require a fresh project every time?

Operational artifacts to define:

1. Base `.avt` template
2. Generated measurement file
3. Optional saved user-specific `.avt`
4. Report/debug file for the avatar-generation run

### 7. Validation For Step 1

We need a repeatable way to judge whether the CLO avatar is good enough as a
personal digital twin.

Research tasks:

1. Measure whether requested waist, hip, height, and other fields are actually
   reflected after import
2. Compare requested values with the avatar values visible inside CLO
3. Check whether resizing preserves slot availability
4. Check whether resizing preserves garment-placement quality
5. Check whether a saved resized avatar reloads correctly
6. Check whether different starting avatars give different final results for
   the same user measurements

Evidence to collect:

1. Before/after screenshots
2. Requested measurement values
3. Observed avatar measurement values
4. Import success/failure logs
5. Saved working templates and test files

## Step 3 Research: CLO Avatar For Virtual Try-On

This section is about how good the CLO avatar is for garment placement,
simulation, and final try-on quality.

### 1. Slot Availability And Slot Stability

We need to understand how reliably the CLO avatar provides slots for clothing
placement.

Research questions:

1. Which base avatars return arrangement slots reliably?
2. Do those slots appear immediately after import or only after later steps?
3. Do the slot names remain stable across saves and reloads?
4. Do the slot names remain stable after measurement changes?
5. Do different avatar families expose different slot sets?
6. Which slots are best for torso placement?
7. Which slots are best for sleeve placement?

Evidence to collect:

1. Slot count
2. Full slot payload
3. Slot names
4. Best matched front/back/sleeve slots
5. Behavior before and after resizing

### 2. Placement Quality

We need to test whether the CLO avatar improves actual garment placement.

Research questions:

1. Does the native CLO avatar place front and back panels better than the STAR
   avatar path?
2. Do sleeves start in better positions on the CLO avatar?
3. Are fewer manual offsets needed?
4. Does placement remain good after changing body measurements?
5. Do different garments require different preferred slots?

Comparison tasks:

1. Same garment on STAR path
2. Same garment on CLO-native path
3. Same garment on multiple CLO base avatars
4. Same garment before and after avatar resizing

Metrics to capture:

1. Slot match used
2. Arrangement offsets used
3. Initial panel overlap
4. Whether manual correction was needed
5. Whether placement was visually acceptable before simulation

### 3. Sewing And Simulation Quality

We need to understand how well the CLO avatar supports the actual try-on
physics flow.

Research questions:

1. Does the CLO avatar improve seam success or reduce seam issues?
2. Does the garment drape more cleanly on the CLO avatar?
3. Are collision and penetration issues reduced?
4. Do sleeves behave better during simulation?
5. Does resizing the avatar affect sewing stability?

Evidence to collect:

1. Seam success rate
2. Simulation completion status
3. Visible collision issues
4. Sleeve drape quality
5. Torso drape quality

### 4. Compatibility With Product Ingestion Output

We need to verify how well the CLO avatar works with the garments already being
generated in our clothing pipeline.

Research questions:

1. Does the current CLO avatar pipeline work consistently with the DXF output
   from `product_ingestion`?
2. Are certain garment shapes more compatible than others?
3. Do pattern counts, edge probing, and seam creation remain stable?
4. Does resizing the avatar change the garment import/arrangement flow?

Evidence to collect:

1. Garment category tested
2. Pattern import result
3. Pattern arrangement result
4. Seam creation result
5. Simulation result

### 5. Final Output Quality

We need to judge whether this avatar can support the final user-visible try-on.

Research questions:

1. Is the CLO avatar visually acceptable as a user-facing body base?
2. Is it acceptable only as a simulation proxy?
3. Does the final dressed result look believable enough for presentation?
4. Does the avatar look consistent across different garments?
5. Can the final result be exported in a usable way for web or app display?

Evidence to collect:

1. Dressed avatar renders
2. Export success
3. Visual quality notes
4. Garment fit clarity
5. User-facing presentation suitability

### 6. Runtime And Operational Cost

We need to understand the operational cost of relying on CLO avatars for try-on.

Research questions:

1. How long does the CLO-native pipeline take per run?
2. How much manual preparation is required per avatar family?
3. How many saved templates do we need to maintain?
4. Does this flow depend on version-specific behavior?
5. How much debugging effort is needed when imports fail?

Evidence to collect:

1. Runtime per step
2. Number of manual prep steps
3. Number of required template files
4. Version notes
5. Failure cases and recovery steps

## Shared Research Deliverables

No matter which step we are researching, the following artifacts should be
saved whenever possible.

1. Source link or document name
2. CLO version used
3. Avatar template used
4. Input file used
5. Output file produced
6. Exact command or UI steps used
7. Success or failure result
8. Screenshots when useful
9. A short final conclusion for that experiment

## Minimum Questions That Must Be Answered Before Final Decision

### For Step 1

1. Which base CLO avatar will we use as the starting point?
2. Which measurement file format will we use in production?
3. Which fields can we actually control reliably?
4. Which fields must come from user input, model output, or defaults?
5. Can we save and reuse a resized user-specific CLO avatar reliably?

### For Step 3

1. Which CLO avatar gives the most reliable slot return?
2. Which slots should be used for front, back, and sleeves?
3. Does the CLO avatar improve placement enough to justify using it?
4. Does it improve sewing and simulation quality enough to justify using it?
5. Is it suitable as the final visible avatar, or only as a simulation avatar?
