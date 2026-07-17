# Default Panels

Pre-built t-shirt pattern pieces for use while the panel generation pipeline
is being developed. When `use_default_panels=True` in the VTO pipeline, it
reads DXF files from this folder instead of running panel generation.

## How to populate

1. Open CLO 3D and create (or load) a standard t-shirt with four pattern pieces:
   - Front panel
   - Back panel
   - Left sleeve
   - Right sleeve

2. Export each piece as a separate DXF file:
   - File → Export → DXF
   - Units: **Millimetres**
   - One file per pattern piece

3. Name and place the files exactly as:
   ```
   clo_vto/default_panels/dxf/front_panel.dxf
   clo_vto/default_panels/dxf/back_panel.dxf
   clo_vto/default_panels/dxf/sleeve_left.dxf
   clo_vto/default_panels/dxf/sleeve_right.dxf
   ```

4. If your DXF panels use different edge ordering than the defaults, update
   `edge_manifest.json` to match. The default indices assume:

   **Front / Back (8 edges, 0-based):**
   0=hem, 1=right_side, 2=right_armhole, 3=right_shoulder,
   4=neckline, 5=left_shoulder, 6=left_armhole, 7=left_side

   **Sleeves (5 edges, 0-based):**
   0=cuff, 1=right_underarm, 2=cap_front, 3=cap_back, 4=left_underarm

## Reconnecting panel generation

When panel generation is production-ready, set `use_default_panels=False`
(or omit it) when calling `run_pipeline()`. No other code changes needed.
