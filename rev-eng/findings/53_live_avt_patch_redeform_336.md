# 53 - Live AVT patch/redeform test on SDK 336

*Status: complete. Supervised live test; one male avatar, five AVT variants.*
*Date: 2026-11-10*

## Test

Experiment: `experiments/e02_avt_patch_redeform.py`

Source avatar:

- `clo_avatar_generation/input/base-1.avt`

Variants:

- baseline
- `enLastUpdateMode = 1`
- `enLastUpdateMode = 2`
- `bHeightLinked = false`
- both edits together

Each variant was processed in isolation:

1. Clear avatars.
2. Import the variant through `/import-avatar-avt`.
3. Read avatar state.
4. Export a GLB.

The run used the installed CLO 2026.1.336 host and matching SDK 336 plugin.
All commands completed within the queue timeout. No modal dialog appeared and
CLO remained responsive.

## Observed results

| Variant | Import | Avatar count | GLB buffer SHA-256 prefix | Vertices reported | Triangles |
|---|---:|---:|---|---:|---:|
| baseline | true | 1 | `ef5ab2c9aa1fcee3` | 606,659* | 179,080 |
| mode1 | true | 1 | `ef5ab2c9aa1fcee3` | 606,659* | 179,080 |
| mode2 | true | 1 | `ef5ab2c9aa1fcee3` | 606,659* | 179,080 |
| unlinked | true | 1 | `ef5ab2c9aa1fcee3` | 606,659* | 179,080 |
| mode1_unlinked | true | 1 | `ef5ab2c9aa1fcee3` | 606,659* | 179,080 |

`*` The experiment's primitive-summed vertex display retains the known
counting artefact; the distinct POSITION accessor total is 200,134 as recorded
in finding 25.

The complete recorder output is:

`experiments/out/e02_avt_patch_redeform_20261110_225738.json`

## Conclusion

For this source avatar and these five same-size `.avt` edits, the exported
geometry buffer is byte-identical across variants. This live result confirms
the existing static conclusion: changing these `.avt` resizing fields does
not cause CLO to re-deform the mesh during `.avt` import.

This does not establish behavior for every possible `.avt` field or for
`.avs` measurement import. The `.avs` route remains the correct live path for
testing measurement-driven deformation.
