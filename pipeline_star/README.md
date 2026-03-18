# STAR Avatar Pipeline

This pipeline creates a digital twin (avatar) from input data using the STAR body model.

## Command for running the Pipeline

```bash
python pipeline_star/run_avatar_pipeline.py
```

Then enter user_id from the mongodb.

---

## Clearing generated outputs

```bash
python pipeline_star/clear_generated.py
```

---

## Folder Structure

```plain
pipeline_star/
├── run_avatar_pipeline.py          # CLI entry point
├── first.py                        # Pipeline execution and args
├── star_runner.py                  # Loads STAR model, generates A-pose mesh
├── fit_betas.py                    # Fits shape params to measurements
├── mapping_layer.py                # Maps MongoDB doc to pipeline inputs
├── mesh_measure.py                 # Extracts body measurements from mesh
├── mesh_postprocess.py             # Validates mesh before export
├── avatar_exporter.py              # Exports mesh to GLB
├── avatar_style.py                 # Mannequin appearance for GLB
├── pose_catalog.py                 # different poses definitions
├── artifact_schema.py              # JSON schemas for pipeline artifacts
├── artifact_io.py                  # Reads/writes artifact JSON files
├── run_manifest.py                 # Run identity and output file paths
├── clear_generated.py              # Wipes the generated/ folder
├── diagnose_shoulder.py            # Visualizes shoulder width on mesh
├── inspect_star_joints.py          # Inspects STAR joint indices
├── test_shoulder_landmarks.py      # Tests shoulder landmark measurement
├── generated/                      # Auto-generated JSON output artifacts
├──.gitignore                       
├── SETUP.md                         
└── README.md                       


