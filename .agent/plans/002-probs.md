# Problems: Plan 002

1. **Problem**: Seam Matching Failure in Blender Sewing

   Pattern piece names generated in Step 4 don't match names expected by Step 5, causing all 8 seam connections to fail. Step 4 generates seams.json referencing "Front" and "Back", but Step 5 creates Blender objects named "Front_Panel" and "Back_Panel". Result: garment pieces float separately, no sewing occurs, pipeline fails end-to-end.

   **Found in**: Phase 2, Step 1 (Blender sewing integration)

   **Evidence**: Console shows all seams skipped with "piece not found" errors. Root cause: naming mismatch between `pattern_generation.py` (seams.json) and `blender_sewing.py` (mesh object names). Fix options: update Step 4 seams.json naming, update Step 5 lookup logic, or establish consistent naming convention across both.

2. **Problem**: Missing Unified Asset Metadata

   Pipeline generates partial metadata in separate files but lacks unified asset JSON as specified in MVP-Step-2B. Step 4 creates `pattern_metadata.json` (measurements only), Step 3 creates `front_fabric_color.json` (color only), but no garment_id, has_design flag, or combined metadata exists.

   **Found in**: Phase 5, Step 2 (Asset package generation)

   **Evidence**: No file aggregates data from all pipeline steps. Required fields missing: garment_id, has_design, unified JSON with measurements + colors + fabric_type. Prevents proper asset tracking and Step 3 (VTO) integration. Fix: create metadata aggregation step combining all outputs into MVP-Step-2B schema.
