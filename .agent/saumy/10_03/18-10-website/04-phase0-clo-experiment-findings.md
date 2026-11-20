# 04 — Phase 0 CLO experiments: what CLO calculates itself, the role of weight, and the field mapping

*Status: experiments finished on 2026-10-20; findings only, no code or plan change made from them yet; waiting for your decision*
*Compiled: 2026-10-20*

All scripts, logs and result tables are in `phase0-clo-experiments/` next to this file (`scripts/`, `results/`; `work/` holds temporary files and is ignored by git). About 160 imports were run on your CLO 2026.1.224 through the REST plugin, plus the Avatar Editor driven with keys and clicks. CLO crashed once (after about 85 imports in one session) and was restarted.

## 1. What was tested

| Test | How | Bodies |
|---|---|---|
| Ground truth: import a CLO-shipped size file in full, then rebuild the same body from only some values and compare the two bodies vertex by vertex | plugin (command line) | female: 4 sizes (plus 5 in an earlier round); male: 5; teen girl: 2; girl 7-20: 2; boy 7-20: 2 |
| What does CLO recompute when only the six driven values are given? | plugin | same |
| CLO's weight model | Avatar Editor, Width driver set to Weight, weights typed (keys and clicks) | female 40 to 115 kg, male 50 to 130 kg |
| Typing the six values in the editor, with and without a weight first | Avatar Editor (keys and clicks) | female 3, teen 2, girl 1, boy 1 |
| Where CLO's measurements sit on the real mesh | plugin, GLB sliced at CLO's own measurement heights | female and male default |
| Definitions and how people measure | web (ISO 8559, CLO help, tailoring guides) | all fields |

"Mesh error" below is the mean distance in cm between the same vertex of two bodies. The truth is the body CLO makes from the full shipped `.avs` file.

## 2. Main findings

1. **CLO recomputes most of the body itself.** When an `.avs` that holds only our six values (and template defaults elsewhere) is imported, CLO changes 40 to 45 of the other 51 stored values. The same happens when the values are typed into the editor. This contradicts the earlier assumption in `06-avs-route-performance-and-changes.md` that CLO "uses the stored values". The 50-value regression we fitted for the male side is therefore mostly wasted: filling all 51 values and filling only the few CLO leaves alone give the identical body (checked on female, 5 sizes, mesh difference 0.00 cm).
2. **A few values are not recomputed and must be supplied.** They are the editor's other main input boxes (table in section 3). For adult female: Neck Base, Under Bust, High Hip, Thigh, Bicep, Arm length. For adult male: the same without Under Bust. Teen and kid avatars have a somewhat different set.
3. **Weight is stored in slot 1 and is ignored on import.** Importing an `.avs` with a different weight resets it to 50 (female) or 70 (male); a weight-only `.avs` leaves the body unchanged (0.00 cm). Weight only works through the Avatar Editor. There, with the Width driver on Weight, typing a weight rewrites about 45 values at once (neck, bust, under bust, waist, high hip, low hip, thigh, bicep and more), smoothly, while heights and lengths barely move. Example, female at 175 cm: 50 kg gives bust 81.4, waist 60.8, low hip 95.2; 70 kg gives 95.3, 76.3, 103.8; 100 kg gives 115.3, 99.0, 120.1. Male at 188 cm: 70 kg gives chest 96.5, waist 82.5, low hip 95.2.
4. **Our six values are applied exactly.** Whether imported in an `.avs` or typed in the editor, height, bust or chest, waist, low hip, inseam and shoulder come out at the requested number (within 0.1 cm in nearly all runs).
5. **Importing is as good as typing in the editor.** Typing the same six values gave the same recompute behaviour and similar mesh errors as the `.avs` import.
6. **CLO's circumferences are tape-style slices.** Slicing the mesh at CLO's own measurement heights and taking the tape-style perimeter reproduces CLO's numbers: waist, under bust, high hip and low hip within 1.5 cm (female and male). The bust slice could not be checked (the arms merge into the slice).
7. **CLO's Low Hip is the fullest part of the hips.** On the mesh the fullest hip section is within 1.3 cm in girth of CLO's Low Hip (female: 95.8 against 95.2; male: 96.5 against 95.2) and within 3 to 5 cm in height. High Hip sits 8 to 13 cm below the waist.
8. **The female mesh is taller than the stored height.** The female default mesh top is 2.7 cm above the stored 175.3 cm (hair); male default: 1.0 cm. The pipeline's body-height check uses 1.5 cm, so it would fail female bodies unless it is adjusted.

## 3. Which values CLO calculates and which it does not

Slot numbers are the position in CLO's 57-value size block (same layout for male, female, teen and kids).

| Group | Slots and names | What happens |
|---|---|---|
| We set these (6) | 0 Total Height, 2 Chest (male) or Bust (female), 6 Waist, 8 Low Hip, 26 Inseam (height), 36 Across Shoulder (Curvilinear) | Applied exactly |
| Weight | 1 Weight | Ignored on import; works only in the editor |
| **Not recomputed: must be supplied (adult)** | 4 Neck Base, 5 Under Bust (female), 7 High Hip, 9 Thigh, 15 Bicep, 47 Arm length | Stay at the template default unless given. Largest effect. Error with only the six: Under Bust up to 25 cm, High Hip up to 22 cm, on Petite sizes |
| Not recomputed, teen girl | 4, 5, 7, 9, 31, 43, 47, 49, 50 | Larger set |
| Not recomputed, girl and boy (7-20) | 4, 9, 15, 40, 41, 48, 49 | Different set |
| Recomputed by CLO | 3 Mid Neck, 10 to 14 (mid thigh, knee, calf, ankle, armhole), 16 Elbow, 17 Wrist, 18 to 25 (HPS, shoulder, bust, under bust, waist, high hip, low hip heights, shoulder drop), 27 to 35 (thigh to ankle heights, across front, across back), 37 to 46 (neck and trunk lengths, waist to hip lengths, apex, halter), 48 to 56 (rises, vertical trunk and others) | Calculated by CLO from the values we set |

Note: the six "not recomputed" values are all things a person can measure (neck, under bust, high hip, thigh, upper arm, arm length), so they could be optional inputs in the form.

## 4. How well each way of filling the "not recomputed" values works

Mean mesh error against CLO's shipped size, in cm (average of the sizes tested; p95 and the worst vertex in brackets). Shipped sizes are not real people and the samples are small (2 to 5 sizes), so the numbers say which method is better, not how accurate the avatar is.

| Body | Six values only (CLO fills the rest) | Six + our regression on only the not-recomputed slots (leave-one-out) | Six + values copied from the nearest shipped size | Six + CLO weight model (weight chosen to fit bust, waist, hip) | Typed in the editor (six) | Typed in the editor (weight, then six) |
|---|---|---|---|---|---|---|
| Female (3 to 4 sizes) | 1.93 (4.8, 9.8) | **1.04** (1.4, 6.2) | 1.08 (1.5, 6.0) | 1.20 (3.0, 7.0) | 2.04 (4.0, 9.8) | 1.21 (3.1, 7.2) |
| Male (3 to 5 sizes) | 1.21 (3.4, 16.8) | **0.36** (1.0, 2.9) | 0.39 (1.4, 2.6) | 0.46 (1.4, 3.1) | not run | not run |
| Teen girl (2 sizes) | 1.05 (1.9, 5.2) | **0.53** (2.0, 2.9) | 0.61 (2.2, 3.2) | not run | 1.07 (1.9, 5.2) | 1.14 (1.9, 5.2) |
| Girl 7-20 (1 to 2 sizes) | 1.47 (3.4, 9.7) | **0.70** (1.2, 2.1) | 2.64 (3.3, 5.1) | not run | 0.17 (0.3, 0.8) | 0.44 (0.7, 1.4) |
| Boy 7-20 (1 to 2 sizes) | 2.48 (5.5, 8.6) | 1.47 (3.2, 5.0) | **1.21** (3.3, 4.3) | not run | 2.45 (3.5, 3.9) | 2.31 (3.1, 3.8) |

The repo's current male model (all derived values) gives 0.43 to 0.48 on the same male sizes (flattered, because some of those sizes were in its training data). Filling only the not-recomputed slots with a small regression (0.36) is at least as good and needs far fewer numbers.

Reading the table:
- Leaving the not-recomputed values at the template default (six only) is clearly worse, especially for sizes far from the default body.
- All three ways of supplying them (regression, nearest size, CLO weight model) land within about 0.1 to 0.3 cm of each other on shipped sizes. Shipped sizes are not built from weight, so this test cannot show whether the weight model is better for real people.
- Running the editor takes about 25 s per run without a mesh check and 40 to 45 s with one. The `.avs` import route takes about 40 s with a mesh check. The speed is mostly CLO's loading and exporting time, not the method.

## 5. The role of weight

- In CLO, weight is a width driver (it appears in the Width dropdown next to Bust or Under Bust). Changing it re-shapes all circumferences together and keeps the body proportioned.
- Through our `.avs` route it has no effect at all. Today's field contract lists `weight_kg` as applied by the CSV bridge, which CLO rejects, so weight has never changed the avatar.
- Options (decision for you):
  1. Keep weight as user data only (as decided earlier).
  2. Use CLO's weight model to supply the not-recomputed values: sample the model once in the editor (as done here: female and male weight tables exist in `results/weight_sweep_*.json`), then interpolate by the user's weight and height when building the `.avs`. The user's real weight then shapes neck, thigh, bicep, under bust and high hip. Not yet validated with real people.
  3. Drive the editor with keys and clicks at generation time. It works, but it is slow and fragile (pop-ups, a stale dropdown after a new project, an open editor window needed), so it is not recommended for the website.

## 6. Mapping: database field to CLO

| Database field | Frontend key (label) | CLO slot and name | Status | How CLO defines it | How people measure it | Recommendation |
|---|---|---|---|---|---|---|
| `height_cm` | `height` (Height) | 0 Total Height | We set it | Ground to top of head. CLO's help says Total Height is its least accurate height input and recommends HPS Height or Inseam | Standing height (stature), ISO: vertical distance from the highest head point to the ground | Keep. Only the mesh is 1 to 3 cm taller than the stored value (hair), so the height check needs an allowance, more for female |
| `weight_kg` | `weight` (Weight) | 1 Weight | Not applied (ignored on import) | Width driver in the editor; rewrites about 45 circumference values | Body weight | See section 5 |
| `chest_circumference_cm` (male) | `chest` (Chest) | 2 Chest | We set it | Circumference at chest level | Around the fullest part of the chest, under the armpits | Keep for male |
| `bust_circumference_cm` (female) | none yet | 2 Bust (same slot as Chest) | We set it, once female is supported | ISO: girth at the bust point level (the most forward point of the bust) | Around the fullest part of the bust | Female form should ask Bust, not Chest |
| `under_bust_circumference_cm` (female) | none yet | 5 Under Bust | **Not recomputed: set it from the user's value** | ISO: girth directly below the breast | The band size under the bust | Make it a required or strongly encouraged female field; it removes the largest error |
| `waist_circumference_cm` | `waist` (Waist) | 6 Waist | We set it | Natural waist (mesh slice matches CLO's number). ISO: midway between the lowest rib and the top of the hip bone | Narrowest part, just above the navel. Men often give their trouser size, which sits lower and is larger | Keep. Add helper text: "natural waist, narrowest part, not your trouser size" |
| `hip_circumference_cm` | `hips` (Hips) | 8 Low Hip | We set it | The fullest part of the hips and seat (matches ISO hip girth within about 1 cm) | Fullest part of the hips and buttocks, about 20 cm below the waist | **Mapping is correct, no change.** Do not switch to High Hip |
| not stored | none | 7 High Hip | **Not recomputed** | About 8 to 13 cm below the waist (hip-bone level) | About 4 inches below the waist; few people know it | Leave to the model or weight table; optional |
| `leg_length_cm` | `inseam` (Inseam) | 26 Inseam (height) | We set it | Vertical height from the ground to the crotch (ISO inside-leg height) | Crotch to ankle or floor, inside leg | Mapping is right, but the database name `leg_length_cm` invites the wrong number (leg length is often the outside leg, hip bone to floor, about 100 cm). Rename it `inseam_cm` and say "crotch to floor" in the form |
| `shoulder_width_cm` | `shoulderWidth` (Shoulder width) | 36 Across Shoulder (Curvilinear) | We set it | Distance between the two shoulder points following the surface over the back (ISO "back shoulder width"). CLO values: female default 37.7, male default 44.1 | Most people think of the straight distance between the shoulder bones (ISO biacromial breadth), which is shorter, or a tape across the back | Biggest definition mismatch. A straight-line value fed into the curved slot makes the shoulders too narrow. Change the label and help text to "across the back, shoulder tip to shoulder tip, tape following the body", or add a small conversion after testing real people |
| not stored | none | 4 Neck Base, 9 Thigh, 15 Bicep, 47 Arm | **Not recomputed** | Circumferences and arm length | Neck, thigh, upper arm, arm length | Optional form fields, or taken from the model or weight table |
| `body_shape_type` | none | none | Unused | | | Remove (decided) |
| `skin_tone_hex` | none | none | Not applied | | | Keep for the later skin-colour task |
| `accuracy` | `accuracy` | none | For our own use | | | Keep |
| `units_preference` (metric or imperial) | form units option | none | Not used (only metric stored) | | | Inches removed from the form for now (decided) |

Notes on the table:
- The "How CLO defines it" column is from the mesh checks in section 2 and CLO's own help excerpts. I could not open CLO's help pages (access refused), so the definitions of Across Shoulder (Curvilinear) and of High Hip and Low Hip come from the measured heights on the mesh plus ISO and tailoring sources, not from CLO text.
- Tailors commonly put the high hip about 4 inches and the low (full) hip about 8 inches below the natural waist. On CLO's default avatars the high hip is 8 to 13 cm below the waist and the low hip 18 to 26 cm below, so they are consistent with that convention.

## 7. Teens, kids and babies

- Female teen avatar `FV2.1_Luna_Teenager` uses template `FemaleTemplate_10`, with its own size files (default and four girls' sizes). It behaves like the adult case, with a somewhat larger set of not-recomputed values (section 3). The editor route worked on it.
- Kid avatars `KV1.1B_Oliver` (boy) and `KV1.1G_Melody` (girl), 7 to 20 years, have size files for 7, 8, 10, 12, 14, 16, 18 and 20. Same behaviour; the not-recomputed set differs and shows no Under Bust. Only one or two sizes each were tested, so these numbers are rough.
- **Not testable with the files we have:** babies (no avatar and no size files in the assets folder, only accessories and poses), the kid 2 to 6 avatar (a size file exists for it but no avatar), a male teen (only size files exist, no male teen avatar), and the male avatars Leo and Luka (different templates, no matching size files). To test them I would need those avatars and size files from CLO.

## 8. Limits of these results

- The tests use CLO's shipped sizes (51 female, 11 male adult sizes and a few teen and kid sizes), not real people, and only 2 to 5 sizes per group were tested because each costs about 3 minutes.
- Leave-one-out was used for the regression and the nearest-size copy, so those numbers do not include the test size.
- The weight table was sampled at the default height only (175 cm female, 188 cm male); arm length was scaled with height.
- The mesh error compares body shape only; it does not say how close a body is to a particular real person.
- The male and female weight sweeps and the editor tests rely on keys and clicks and the pixel positions of one screen layout.

## 9. Decisions for you

1. **Replace the 51-value regression** with filling only the not-recomputed values (about 5 to 6 per body type), as the next change to the pipeline (Phase 2 and the pipeline files). Yes or no.
2. **Source of those values:** (a) a small regression on shipped sizes, (b) the nearest shipped size, (c) CLO's weight model sampled once into a table, or (d) optional user inputs where people know them (under bust, neck, thigh, upper arm, arm length) with (a), (b) or (c) as the fallback. My view from these tests: use user-provided values when present, and (a) or (b) otherwise; use (c) only if weight should shape the avatar.
3. **Weight:** keep as user data only, or use it through the weight table (section 5).
4. **Mapping changes:** rename `leg_length_cm` to `inseam_cm` with clearer form text; fix the shoulder label and help text (and decide whether to convert); add helper text for the natural waist; ask Bust and Under Bust for female. Hips stay mapped to Low Hip.
5. **More tests if wanted:** the avatars and size files for babies, the 2 to 6 kid, a male teen, Leo and Luka; more sizes per group; a check of how real people's straight shoulder width compares with CLO's curvilinear value.

## 10. Sources

- CLO Help Center, Adjust Avatar Size (width and height drivers, link buttons, editable and non-editable measures; Total Height not recommended): https://support.clo3d.com/hc/en-us/articles/33854094900633-Adjust-Avatar-Size (the page itself would not open from here; the points were read from search excerpts)
- IBV digital measuring tape metrics catalogue, which quotes ISO 8559-1:2017 and ISO 7250-1:2017 definitions of height, waist, hip, bust, under bust, inside-leg height, back shoulder width and biacromial breadth: https://services.ibv.org/3dmodel/doc/DigitalMeasuringTape_3dModel.html
- Nathan Tailors, how to measure hip (high hip about 4 in and low or full hip about 8 in below the waist): https://www.nathantailors.com/guides/how-to-measure-hip
- Dress pattern making, Across Shoulder: https://dresspatternmaking.com/blog/across-shoulder-gotcha
