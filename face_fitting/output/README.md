# Face-fitting run output

Every face job writes a run directory here: `<user_id>-face-<NNN>/`, holding the faced
`.avt` (~31 MB), any GLB exported from it, `output.json`, and the debug overlays that make
a bad hair or iris sample diagnosable after the fact.

**Nothing in here is committed.** `.gitignore` excludes the whole tree, because a run is
reproducible from its photo and the pipeline is deterministic — keeping the artifacts would
add tens of megabytes per run for no information.

## `baseline/` is the exception

`baseline/` is tracked, and holds the small, measured artifacts the docs quote and that a
later change gets compared against:

| Path | What it is |
|---|---|
| `familiarity/familiarity.png`, `.json` | The familiarity scores: stock 51%, faced 59%, colour +38 / shape +10 / proportions −2 |
| `familiarity/render_stock.png` | The template avatar with no face job — the control that proved the proportion failures are the skull, not our warp |
| `familiarity/render_test2.png`, `render_alpha.png` | The same subject faced, and faced with hair thinned to 0.50 — the pair that measured 10.7% less hair |
| `familiarity/render_comp_front.png`, `_back.png` | Hair render compensation at 1.0, for calibrating `--hair-render-compensation` |
| `evidence/clo_texture_verification.json` | Proof CLO loads the textures we patch: 0.00 from ours against 17–21 from stock |
| `evidence/glb_export.json`, `glb_optimize.json` | GLB size results — 36.4 MB raw → 16.2 MB delivered |
| `evidence/u_phase1_*_output.json` | The runs those numbers came from |

Add to `baseline/` deliberately, by copying a file in and committing it. If an artifact is
not worth explaining in the table above, it belongs in a run directory instead.

See `.agent/clo-avatar-vto/master-plan-26_11_10.md` for what the numbers mean.
