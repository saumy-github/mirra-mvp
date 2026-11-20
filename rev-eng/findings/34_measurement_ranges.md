# 34 - Measurement ranges from the CLO resize training data (lane AE)

*Status: complete, 2026-10-29. Scripts: `scripts/ae_ranges.py` (loader), `scripts/ae_analyze.py` (stats), `scripts/ae_maletable.py` (table formatter). Raw derived output: `raw/ae_out.txt` (per-profile 58-row percentile tables, correlations, regressions). Only derived statistics are recorded; no Preset content is copied.*

Tags: [V] verified from file bytes/arithmetic, [I] inferred.

## 1. File formats

### 1.1 FeatureData.bd  [V]
- Binary, little-endian: `int32 M (=58)`, `int32 N (subjects)`, then `M*N` float32, **row-major `[M][N]`** (row r = measurement r for all N subjects). File size = 8 + 4*58*N exactly for all five profiles.
- Layout check: row 0 read as N contiguous floats spans 142.8-211.3 (a height distribution); the alternative `[N][M]` reading gives a narrow nonsensical range. [V]
- **Rows 1-17 are stored as sqrt(value)**, not cm. Evidence: raw Male means for rows 1-17 are 4.3-9.1; squared they give physiological values (wrist 4.31^2 = 18.6 cm, ankle 5.06^2 = 25.6, thigh 7.65^2 = 58.5, bust 10.22^2 = 104.4, ...), and row 1 squared spans 46-181 with mean 83 = body weight in kg (the default avatar's idx 1 is 70.0). Rows 0 and 18-57 are plain cm. All stats below apply the square to rows 1-17. [V arithmetic; I that this is the format's intent]
- Subjects per profile (header N): Male 1882, Female 2161, Boy 470, Girl 485, PreSchool 397.

### 1.2 range_list.rlist is NOT a measurement range file  [V]
- It is whitespace-separated text with **one small integer per mesh vertex** (Male 48345 tokens = BaseMesh.obj vertex count; Female 47650 = its obj; Boy/Girl/PreSchool 24121 = their obj). Values 0-6 (Female also 7). Male histogram: 5:12606, 6:9042, 4:6436, 3:5743, 2:5721, 1:4403, 0:4394. It is a per-vertex body-region id. Sibling `detail_range_list.rlist` has values -1..11 (-1 = no detail region); `static_vertex_list.slist` holds 0/1 flags; same per-vertex shape.
- Therefore **there is no per-measurement clamp in range_list.rlist**. The only hard clamp found in the code is `SetFeatureValue`: **0.1 .. 300 cm** (findings/15 section 3; ratio-type features 0..100). [V]
- Consequence: CLO does not reject out-of-training-range inputs; it clamps at 0.1-300 cm and lets the optimiser extrapolate (lane W loader strings: "Optimization by Joint", "Early termination", "fail to generate avatar"). So the sane operating range is the training hull below, not a CLO limit. [I]

## 2. Row -> index mapping (FeatureData row vs the 67-float listFeatureValues)  [V/I]
Compared the 58 rows with `_feature_index_map` / `listFeatureValues` of the default male avatar in raw/avs_tree.json (187.96, 70.0, 96.52, 37.55, 40.96, 89.39, 82.55, ...). **Mapping is identity: FeatureData row r = listFeatureValues index r for r = 0..57**, with the sqrt storage for r = 1..17. Confidence about 95%: (a) every row's training mean sits in the neighbourhood of the default avatar's value with the same physical meaning (rows 18-31 are descending landmark heights; row 26 Inseam mean 79.5 vs default 86.4; row 36 across-shoulder 43.8 vs 44.13); (b) the findings/15 section 2.3 names fit the distributions (neck < bust < hip; thigh > mid thigh > knee > calf > ankle; heights monotone down the body); (c) the six lane-15 indices (0, 2, 6, 8, 26, 36) agree with the defaults. Indices 58-66 (hand, head, ...) are not in the 58-row table. Weakest: rows 32, 33, 48, 52-54 (unnamed in findings/15; matched by magnitude only).
Note idx 1 is **body weight (kg)**, a training feature the CSV importer cannot set (derived/optimiser-driven). [I]

## 3. Training-set ranges, Male profile (n = 1882; cm, weight in kg)
Marginal percentiles. Use p1-p99 for soft limits, min-max for hard limits.

| idx | name | min | p1 | p50 | p99 | max | mean | std |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | Total Height | 142.82 | 161.25 | 177.22 | 194.98 | 211.25 | 177.49 | 7.31 |
| 1 | Weight (kg) [I] | 45.80 | 54.85 | 80.50 | 139.81 | 181.41 | 83.14 | 16.90 |
| 2 | Bust/Chest Circumference | 77.70 | 83.88 | 103.39 | 135.40 | 146.46 | 104.60 | 10.38 |
| 3 | Mid Neck Circumference | 29.61 | 33.63 | 39.41 | 48.89 | 54.04 | 39.87 | 3.19 |
| 4 | Neck Base Circumference | 31.48 | 35.73 | 42.17 | 52.72 | 59.42 | 42.64 | 3.47 |
| 5 | Under Bust Circumference | 73.08 | 79.35 | 99.19 | 133.64 | 145.04 | 100.43 | 10.99 |
| 6 | Waist Circumference | 65.51 | 71.10 | 91.71 | 131.11 | 145.70 | 93.16 | 12.69 |
| 7 | High Hip Circumference | 73.86 | 80.56 | 96.23 | 135.08 | 154.96 | 97.86 | 10.19 |
| 8 | Low Hip Circumference | 79.19 | 86.50 | 102.14 | 130.28 | 150.99 | 103.10 | 8.54 |
| 9 | Thigh Circumference | 43.58 | 48.28 | 58.07 | 73.54 | 89.87 | 58.60 | 4.95 |
| 10 | Mid Thigh Circumference | 38.55 | 43.08 | 52.29 | 66.52 | 80.36 | 52.81 | 4.63 |
| 11 | Knee Circumference | 29.44 | 32.81 | 38.25 | 45.82 | 51.82 | 38.50 | 2.60 |
| 12 | Calf Circumference | 29.33 | 31.41 | 37.78 | 46.32 | 51.07 | 37.95 | 2.95 |
| 13 | Ankle Circumference | 20.95 | 22.51 | 25.55 | 29.33 | 31.70 | 25.61 | 1.37 |
| 14 | Armhole Circumference | 35.36 | 39.95 | 49.41 | 68.07 | 74.66 | 50.22 | 5.63 |
| 15 | Bicep Circumference (approx) | 16.15 | 25.40 | 32.92 | 42.59 | 49.80 | 33.16 | 3.61 |
| 16 | Elbow Circumference | 21.12 | 23.42 | 27.23 | 32.44 | 35.52 | 27.35 | 1.95 |
| 17 | Wrist Circumference | 16.05 | 16.57 | 18.56 | 21.41 | 23.54 | 18.62 | 1.00 |
| 18 | HPS Height | 120.42 | 137.01 | 152.07 | 169.29 | 186.22 | 152.29 | 6.94 |
| 19 | Shoulder Height | 115.75 | 131.46 | 146.53 | 163.65 | 179.62 | 146.69 | 6.85 |
| 20 | Shoulder Drop | 2.91 | 4.05 | 5.60 | 7.01 | 7.82 | 5.59 | 0.64 |
| 21 | Bust Height | 101.44 | 116.04 | 129.48 | 144.50 | 158.83 | 129.63 | 6.13 |
| 22 | Under Bust Height | 99.55 | 113.52 | 126.40 | 141.53 | 155.09 | 126.65 | 6.03 |
| 23 | Waist Height | 85.15 | 96.89 | 108.90 | 123.35 | 136.67 | 109.19 | 5.68 |
| 24 | High Hip Height | 79.80 | 88.66 | 99.45 | 112.42 | 125.22 | 99.81 | 5.10 |
| 25 | Low Hip Height | 73.95 | 80.56 | 90.19 | 102.16 | 112.85 | 90.47 | 4.65 |
| 26 | Inseam Height | 64.36 | 69.69 | 79.22 | 89.95 | 99.68 | 79.48 | 4.24 |
| 27 | Thigh Height | 62.30 | 67.83 | 76.42 | 86.22 | 95.54 | 76.66 | 3.93 |
| 28 | Mid Thigh Height | 55.37 | 60.92 | 67.83 | 76.25 | 84.20 | 68.05 | 3.30 |
| 29 | Knee Height | 40.34 | 44.60 | 49.73 | 56.10 | 62.06 | 49.91 | 2.47 |
| 30 | Calf Height | 29.61 | 31.52 | 35.54 | 40.22 | 44.72 | 35.58 | 1.83 |
| 31 | Ankle Height | 7.97 | 8.39 | 8.91 | 9.54 | 11.02 | 8.92 | 0.22 |
| 32 | ? (30.8) (unnamed) | 24.44 | 27.73 | 33.71 | 43.71 | 49.82 | 34.01 | 3.24 |
| 33 | ? (20.1) (unnamed) | 13.86 | 17.02 | 23.33 | 33.73 | 36.49 | 23.74 | 3.52 |
| 34 | Across Front | 31.60 | 34.97 | 39.07 | 44.99 | 47.18 | 39.23 | 2.05 |
| 35 | Across Back | 29.23 | 33.36 | 38.44 | 45.41 | 48.25 | 38.60 | 2.46 |
| 36 | Across Shoulder (Curvilinear) | 33.28 | 37.44 | 43.59 | 51.49 | 54.43 | 43.78 | 2.86 |
| 37 | Across Shoulder (CB Neck) | 16.62 | 19.03 | 21.57 | 24.73 | 40.49 | 21.65 | 1.34 |
| 38 | CF Neck to Across Front | 5.76 | 6.78 | 9.14 | 11.77 | 13.65 | 9.18 | 1.06 |
| 39 | CB Neck to Across Back | 11.44 | 12.85 | 15.33 | 18.45 | 39.99 | 15.41 | 1.40 |
| 40 | CF Neck to Waist | 32.05 | 35.16 | 40.94 | 47.15 | 53.05 | 41.00 | 2.55 |
| 41 | CB Neck to Waist | 36.93 | 40.80 | 46.75 | 52.15 | 58.26 | 46.68 | 2.40 |
| 42 | Waist to High Hip | 5.35 | 7.15 | 9.25 | 12.74 | 14.93 | 9.38 | 1.14 |
| 43 | Waist to Low Hip | 11.21 | 14.67 | 18.51 | 24.80 | 29.15 | 18.72 | 2.10 |
| 44 | Apex to Apex | 13.91 | 15.15 | 18.42 | 23.66 | 26.90 | 18.64 | 1.77 |
| 45 | HPS to Apex | 22.78 | 23.63 | 27.60 | 31.89 | 34.23 | 27.62 | 1.70 |
| 46 | Halter | 58.48 | 62.41 | 73.35 | 87.60 | 92.52 | 73.52 | 5.15 |
| 47 | Arm Length | 49.16 | 55.21 | 61.82 | 68.65 | 75.16 | 61.85 | 2.90 |
| 48 | ? (86.7) (unnamed) | 66.51 | 74.67 | 83.38 | 92.67 | 107.73 | 83.50 | 3.80 |
| 49 | Total Rise | 56.77 | 65.03 | 75.86 | 103.53 | 113.74 | 77.46 | 7.51 |
| 50 | Front Rise | 25.28 | 28.97 | 33.83 | 49.86 | 56.66 | 34.86 | 4.19 |
| 51 | Back Rise | 31.49 | 35.32 | 41.88 | 55.38 | 62.91 | 42.60 | 4.03 |
| 52 | ? (29.0) (unnamed) | 20.80 | 25.07 | 29.11 | 39.52 | 43.79 | 29.70 | 2.85 |
| 53 | ? (23.0) (unnamed) | 18.98 | 20.45 | 25.65 | 38.09 | 43.39 | 26.08 | 3.26 |
| 54 | ? (13.7) (unnamed) | 4.63 | 7.55 | 11.56 | 14.20 | 15.53 | 11.43 | 1.32 |
| 55 | Front Vertical Trunk | 65.33 | 72.34 | 82.97 | 100.25 | 110.41 | 83.70 | 5.50 |
| 56 | Back Vertical Trunk | 70.86 | 79.87 | 91.24 | 106.39 | 113.38 | 91.60 | 5.44 |
| 57 | Vertical Trunk | 136.19 | 153.58 | 174.53 | 203.86 | 216.28 | 175.30 | 10.16 |

### 3.1 Key measurements across profiles (min / p1 / p99 / max; mean +- std)  [V]
Full 58-row tables for all profiles: `raw/ae_out.txt` (`## <Profile>` sections; columns idx|name|min|p1|p5|p50|p95|p99|max|mean|std).

| Measurement | Male | Female | Boy | Girl | PreSchool |
|---|---|---|---|---|---|
| Height | 142.8 / 161.3 / 195.0 / 211.3; 177.5+-7.3 | 140.4 / 150.0 / 181.3 / 192.1; 164.0+-6.6 | 114.5 / 117.4 / 178.5 / 185.8; 149.9+-16.6 | 104.6 / 113.6 / 167.0 / 170.2; 145.3+-14.1 | 104.6 / 113.2 / 160.8 / 182.1; 133.5+-10.8 |
| Weight kg | 45.8 / 54.9 / 139.8 / 181.4; 83.1+-16.9 | 37.9 / 44.4 / 122.5 / 156.5; 67.9+-16.4 | 20.0 / 21.5 / 88.5 / 95.0; 46.4+-15.8 | 16.7 / 20.9 / 68.8 / 89.0; 41.8+-11.8 | 16.7 / 20.3 / 68.4 / 77.5; 33.4+-9.5 |
| Bust/Chest circ | 77.7 / 83.9 / 135.4 / 146.5; 104.6+-10.4 | 76.7 / 80.2 / 135.9 / 159.5; 98.1+-11.7 | 58.9 / 59.9 / 106.7 / 109.6; 79.0+-10.9 | 54.4 / 58.1 / 95.3 / 103.9; 75.5+-9.1 | 55.1 / 57.5 / 97.3 / 106.5; 70.1+-8.3 |
| Under bust | 73.1 / 79.4 / 133.6 / 145.0; 100.4+-11.0 | 65.5 / 68.4 / 125.2 / 145.1; 84.5+-11.9 | 54.2 / 55.2 / 100.0 / 103.6 | 50.6 / 53.5 / 86.2 / 96.0 | 50.6 / 53.4 / 90.1 / 101.1 |
| Waist circ | 65.5 / 71.1 / 131.1 / 145.7; 93.2+-12.7 | 58.7 / 61.7 / 122.4 / 140.3; 80.1+-13.1 | 49.0 / 51.7 / 93.1 / 99.1; 67.4+-9.6 | 47.4 / 49.8 / 82.3 / 89.4; 63.7+-7.1 | 47.7 / 49.8 / 86.6 / 98.5; 62.5+-8.1 |
| High hip | 73.9 / 80.6 / 135.1 / 155.0; 97.9+-10.2 | 74.7 / 77.8 / 139.8 / 163.7; 97.2+-13.0 | 53.8 / 54.4 / 97.7 / 104.3 | 50.1 / 54.1 / 90.2 / 100.2 | 52.5 / 56.3 / 90.7 / 99.4 |
| Low hip | 79.2 / 86.5 / 130.3 / 151.0; 103.1+-8.5 | 81.1 / 87.3 / 140.3 / 163.7; 104.2+-10.6 | 57.9 / 60.0 / 104.9 / 110.7 | 55.1 / 60.0 / 97.7 / 110.2 | 54.8 / 59.2 / 95.3 / 100.9 |
| Inseam height | 64.4 / 69.7 / 90.0 / 99.7; 79.5+-4.2 | 62.8 / 68.1 / 87.0 / 93.4; 76.9+-4.1 | 49.2 / 50.8 / 83.1 / 86.8 | 43.9 / 49.4 / 77.2 / 80.6 | 43.9 / 49.0 / 73.3 / 80.6 |
| Across shoulder (curvilinear) | 33.3 / 37.4 / 51.5 / 54.4; 43.8+-2.9 | 32.0 / 34.1 / 45.9 / 50.0; 38.8+-2.5 | 26.5 / 27.8 / 44.7 / 47.6 | 25.8 / 26.8 / 40.8 / 42.2 | 25.8 / 26.7 / 40.1 / 45.0 |
| Arm length | 49.2 / 55.2 / 68.7 / 75.2; 61.9+-2.9 | 47.4 / 50.1 / 62.5 / 73.9; 55.9+-2.6 | 37.1 / 38.4 / 60.5 / 74.1 | 34.3 / 37.3 / 56.8 / 69.7 | 34.1 / 37.0 / 52.7 / 60.1 |

Notes: the adult sets are heavy-skewed (male mean BMI about 26, p99 41). Step 3 is male only. Boy/Girl/PreSchool weight minima are round (20.00), so those sets look partly synthetic or binned [I].

## 4. Male joint structure
Pearson r, six measurements, n = 1882 [V]:

| | Height | Bust | Waist | LowHip | Inseam | AcrShoulder |
|---|---:|---:|---:|---:|---:|---:|
| Height | 1.00 | 0.27 | 0.25 | 0.41 | 0.88 | 0.56 |
| Bust | 0.27 | 1.00 | 0.92 | 0.86 | 0.03 | 0.81 |
| Waist | 0.25 | 0.92 | 1.00 | 0.88 | -0.01 | 0.75 |
| LowHip | 0.41 | 0.86 | 0.88 | 1.00 | 0.15 | 0.78 |
| Inseam | 0.88 | 0.03 | -0.01 | 0.15 | 1.00 | 0.33 |
| AcrShoulder | 0.56 | 0.81 | 0.75 | 0.78 | 0.33 | 1.00 |

Weight correlates 0.88 with bust, 0.89 waist, 0.92 low hip, 0.81 shoulder, 0.46 height, 0.20 inseam.

Reading: two near-independent factors, **girth** (bust, waist, hip, shoulder, weight) and **stature** (height, inseam). Height + bust span both factors, so they are a sensible driver pair.

### 4.1 Conditional spread given the two Mirra drivers (Height + Bust)  [V]
OLS on the male subjects (cm):

| Target | Fit | Residual std | R^2 | Marginal std |
|---|---|---:|---:|---:|
| Waist | -23.8 - 0.007*H + 1.130*Bust | **4.87** | 0.853 | 12.69 |
| Low hip | -5.4 + 0.220*H + 0.664*Bust | **4.10** | 0.770 | 8.54 |
| High hip | -16.7 + 0.148*H + 0.843*Bust | 4.58 | 0.799 | 10.19 |
| Inseam | -8.1 + 0.550*H - 0.095*Bust | **1.73** | 0.834 | 4.24 |
| Across shoulder | -1.9 + 0.142*H + 0.196*Bust | **1.36** | 0.776 | 2.86 |

Adding weight as a third predictor lowers residual std to waist 4.34, hip 3.31, inseam 1.71, shoulder 1.35 (weight helps girth only). Waist residual p1/p99 = -12.7/+10.7; hip residual p1/p99 = -8.2/+11.9; waist and hip residuals correlate 0.46.

So after fixing height and bust, the four free Mirra measurements keep roughly: waist +-5 cm (1 sd), hip +-4, inseam +-1.7, shoulder +-1.4. Inseam and shoulder are nearly determined; waist and hip carry real freedom. [I: the CLO solver is probably most accurate near the training regression plane and extrapolates away from it]

### 4.2 Plausibility ratios and differences (male training set)  [V]

| Quantity | min | p1 | p50 | p99 | max |
|---|---:|---:|---:|---:|---:|
| waist - bust (cm) | -29.8 | -23.8 | -11.3 | -0.2 | **+5.3** |
| low hip - bust (cm) | -20.4 | -14.3 | -1.3 | +10.1 | +19.8 |
| low hip - waist (cm) | -11.8 | -7.4 | +10.5 | +22.3 | +26.3 |
| waist / bust | 0.707 | 0.775 | 0.890 | 0.998 | 1.039 |
| low hip / bust | 0.837 | 0.881 | 0.987 | 1.108 | 1.207 |
| inseam / height | 0.375 | 0.415 | 0.448 | 0.473 | 0.487 |
| across shoulder / height | 0.208 | 0.216 | 0.246 | 0.280 | 0.299 |
| bust / height | 0.445 | 0.477 | 0.585 | 0.742 | 0.824 |
| BMI (weight row / height) | 15.7 | 18.4 | 25.6 | 41.1 | 54.9 |

6-variable Mahalanobis distance (H, Bust, Waist, LowHip, Inseam, AcrShoulder) of the training subjects: median 2.20, p95 3.75, p99 5.06, max 7.27. Examples: CLO default avatar 2.28; typical male (177, 102, 93, 101, 79, 44) 0.97; waist 110 with bust 90 (H 175) 7.77; waist 70 with hip 115 7.86; height 150 with bust 120 6.58. Above about 5.1 is outside 99% of training subjects. [V computation, I interpretation]

## 5. Recommended validation rules for step_03 (male)

Current repo ranges (`clo_avatar_generation/avatar_runtime/step_03_fetch_measurements.py`, read-only) against the training data:

| Mirra field | Repo range | Closest CLO measure (male, min..max; p1..p99) | Assessment |
|---|---|---|---|
| height_cm | 120-230 | Total Height 142.8..211.3; 161.3..195.0 | Looser; 120-142 and 211-230 extrapolate |
| weight_kg | 30-250 | Weight 45.8..181.4; 54.9..139.8 | Loose |
| chest / bust circumference | 50-180 | Bust 77.7..146.5; 83.9..135.4 | Loose; 50-77 is a child size |
| waist_circumference_cm | 40-220 | Waist 65.5..145.7; 71.1..131.1 | Very loose |
| hip_circumference_cm | 50-220 | Low hip 79.2..151.0; 86.5..130.3 | Very loose |
| leg_length_cm | 40-140 | Inseam 64.4..99.7; 69.7..90.0 | Very loose; definition may differ (verify) |
| shoulder_width_cm | 20-80 | Across shoulder (curvilinear) 33.3..54.4; 37.4..51.5 | Very loose; Mirra "shoulder width" may be a straight measure (verify) |
| under_bust_circumference_cm | 45-170 | Under bust 73.1..145.0 | Loose (male does not need it) |

The repo ranges are anti-garbage guards (unit mix-ups); they do not protect avatar quality. Proposed tiers ("hard" = reject, "warn" = accept and add to `ctx.warnings`):

| Field | Hard (reject) | Warn (outside p1-p99) |
|---|---|---|
| height_cm | 140 - 215 | 161 - 195 |
| weight_kg | 40 - 190 | 55 - 140 |
| chest/bust circ | 75 - 150 | 84 - 135 |
| waist circ | 62 - 150 | 71 - 131 |
| hip (low hip) circ | 76 - 155 | 87 - 130 |
| leg_length (inseam) | 62 - 102 | 70 - 90 |
| shoulder (curvilinear) | 31 - 56 | 37 - 52 |

Relational rules (apply when the fields are present):
1. `waist <= bust + 6` hard (training max +5.3, p99 -0.2); warn if `waist > bust - 0.5`. A waist well above the bust usually means swapped fields or a wrong value.
2. `waist >= bust - 31` hard (min -29.8); warn below `bust - 24` (p1).
3. `hip - bust` within -21 .. +21 hard (min -20.4, max +19.8); warn outside -14 .. +10.
4. `hip - waist` within -12 .. +27 hard (min -11.8, max +26.3); warn outside -7.5 .. +22.5. A hip much smaller than the waist, or "slim waist and very large hip", is the commonest implausible pair.
5. `inseam / height` within 0.37 .. 0.49 hard; warn outside 0.415 .. 0.473.
6. `shoulder / height` within 0.205 .. 0.30 hard; warn outside 0.216 .. 0.28.
7. `bust / height` within 0.44 .. 0.83 hard; warn outside 0.48 .. 0.74.
8. Regression residual check (strongest; conditions on the driver pair): waist = -23.8 + 1.13*bust, hip = -5.4 + 0.22*H + 0.664*bust, inseam = -8.1 + 0.55*H - 0.095*bust, shoulder = -1.9 + 0.142*H + 0.196*bust. Warn at |residual| > 2.5 sd (waist 12, hip 10, inseam 4.3, shoulder 3.4 cm); hard at > 4 sd (waist 19.5, hip 16.5, inseam 7, shoulder 5.5 cm).
9. Optional: 6-variable Mahalanobis (covariance recomputable with `scripts/ae_analyze.py`) warn > 5.1, hard > 7.5.
10. BMI hard 15 .. 56, warn outside 18 .. 41.

Caveats: the training population is CLO's vendor set, not Mirra's users, so prefer warnings between p1/p99 and min/max. Units: step 3 sends full circumferences (findings/15). The definitions of Mirra "chest", "leg_length", "shoulder_width" versus CLO Bust, Inseam Height and Across Shoulder (Curvilinear) are unverified; apply the shoulder/inseam tiers only after confirming the mapping.

## 6. Open items
- Meaning of the region ids in range_list.rlist is not decoded (irrelevant to validation).
- Whether avatar quality actually degrades outside p1/p99 needs CLO runs (none done in this lane).
- Rows 32, 33, 48, 52-54 remain unnamed.
