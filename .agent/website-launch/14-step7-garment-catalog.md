# Step 7 - Garment catalog (premade clothes)

**Status:** planned, not yet executed — real gap found, not just missing fields
**Created:** 2026-08-04
**Part of:** [05-avatar-vto-live-pipeline-flow.md](05-avatar-vto-live-pipeline-flow.md) / [06-avatar-vto-implementation-status.md](06-avatar-vto-implementation-status.md)
**Independent of:** Steps 0-6 (can be worked in parallel — doesn't depend on the worker/queue)

## Goal

Give users a small set of real, visually distinct pre-made garments (2-3 t-shirt styles, multiple sizes each) to try on — generated once before launch, not on demand.

## Current state

- `sizes` collection + read-only catalog routes already exist (`catalog/service.py`, `catalog/routes.py`, `catalog/models.py`).
- `SizeDocument` already has `cloth_id`/`cloth_label`/`category`/`fit_type` grouping fields, plus the full seam-measurement field set (`half_chest_width_cm`, `garment_length_cm`, etc.).
- 10 demo sizes are already seeded (`website/backend/scripts/seed_sizes.py`) — pure measurement metadata, upserted by `size_id`.

**The real gap, found by reading `clo_vto`'s actual pipeline code, not assumed:** every catalog entry today, regardless of `cloth_id`, renders using the exact same single hardcoded pattern set at `clo_vto/default_panels/dxf/` (a manually-exported placeholder t-shirt — front/back/sleeve panels, per `clo_vto/default_panels/README.md`). Nothing in the pipeline currently reads `cloth_id` to select a different pattern. So today, "2-3 t-shirt styles" would just be 2-3 differently-labeled catalog rows that all physically render identically.

## Remaining work

Per this round's decision — the catalog is generated **before launch**, not on demand:

1. **Run `product_ingestion` (Step 2) once per real garment style/photo, ahead of launch.** Produces `product_ingestion/output/<cloth_id>-<size_id>-<run_number>/` as the pipeline already does — this part of Step 2 needs no code changes, just real runs against real garment photos.
2. **Pick the final run per (cloth_id, size_id)** and copy its pattern files + a product thumbnail into `live_upload/catalog/<cloth_id>/<size_id>/`, named properly (not raw run-numbered filenames) — per this round's explicit instruction: "keep them with proper name and in the live upload folder also."
3. **Add fields to `SizeDocument`:**
   ```python
   pattern_asset_path: str | None = None   # relative path under live_upload/catalog/<cloth_id>/<size_id>/
   thumbnail_url: str | None = None
   ```
4. **Update/replace the seed script** so what's actually seeded for launch is these real, pre-generated entries — not (only) the current placeholder measurement-only rows. Decide whether the existing 10 demo sizes stay as dev/test fixtures or get replaced outright.
5. **Change `clo_vto`'s pipeline to load patterns by catalog lookup**, not the `use_default_panels` flag: given a `cloth_id`, resolve `live_upload/catalog/<cloth_id>/<size_id>/` and import those DXF files instead of the hardcoded `default_panels/dxf/` folder. Per `default_panels/README.md`, this is exactly the "reconnecting panel generation" path it already anticipates (`use_default_panels=False`) — this step is that reconnection, just pointed at `live_upload/` instead of a re-run of `product_ingestion` at request time.
6. **If DXF panel edge ordering differs between garment styles**, each catalog item's folder needs its own `edge_manifest.json` (or an equivalent per-style config) — the current single `default_panels/edge_manifest.json` assumes one fixed panel layout; a second or third garment style may need its own.
7. **Frontend catalog browsing page:** pure Mongo read (`GET` routes already exist) + `thumbnail_url` image — no CLO involvement in browsing at all, only at try-on request time (Step 8/9).

## Files touched

- new: `live_upload/catalog/` tree (per-style pattern files + thumbnails)
- `website/backend/src/catalog/models.py` — new fields
- `website/backend/scripts/seed_sizes.py` (or its replacement) — real catalog data
- `clo_vto/native_vto/step_04_import_patterns.py` (and wherever `use_default_panels` is branched) — catalog-driven pattern lookup
- possibly new/duplicated `edge_manifest.json` per garment style

## Verification

- Selecting different `cloth_id`s in the catalog produces visibly different garment shapes in a test VTO run, not the same shape relabeled.
- Catalog browsing page loads with zero CLO/pipeline calls — confirm via logs.
- `pattern_asset_path` for each seeded size resolves to a real, populated folder before launch (no dangling references).

## Execution Log

Not started.
