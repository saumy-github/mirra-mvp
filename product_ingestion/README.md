# Product Ingestion

Canonical Step 2 of the MVP now lives in `product_ingestion/`.

The main user-facing command is:

```powershell
.\.venv\Scripts\python.exe product_ingestion\run_product_ingestion.py
```

This runner is:
- cloth-folder driven via `product_ingestion/input/<cloth_id>/`
- MongoDB-only for size and cloth metadata via `size_id`
- aligned to the cleaned output contract under `product_ingestion/output/`

## Expected input

```plain
product_ingestion/input/
  c_001/
    image_1.jpg
    image_2.jpg
  c_002/
    image_1.jpg
```

## Canonical output

```plain
product_ingestion/output/
  c_001-s_001-001/
    image_info/
      base_garment.png
      colors.json
      extraction_metadata.json
      graphic_diffuse.png
    panels/
      dxf/
        front_panel.dxf
        back_panel.dxf
        sleeve_left.dxf
        sleeve_right.dxf
      svg/
        front_panel.svg
        back_panel.svg
        sleeve_left.svg
        sleeve_right.svg
      panel_metadata.json
    run_summary.json
```

## Notes

- Run folders use the locked naming format `<cloth_id>-<size_id>-<run_number>`.
- Run numbers increment per `cloth_id + size_id` pair.
- The canonical processing order is:
  1. view selection
  2. segmentation
  3. colour extraction
  4. design extraction
  5. panel generation
- `generate_patterns_clo3d.py` remains as a lower-level legacy helper during the transition.
- `generate_for_avatar.py` remains as a legacy overlap command during the transition.
