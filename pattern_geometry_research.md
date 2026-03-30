# T-Shirt Pattern Geometry Research: Mirra MVP vs Standard & CLO3D

This document provides an in-depth dive into how 2D t-shirt patterns are currently generated in the project, how standard real-world patterns should look, and how CLO3D interprets these geometries.

---

## 1. User Observation Confirmation: The "Rectangle + Semicircle" Sleeve
Yes, your observation from the video is **100% correct**. 
A standard set-in sleeve pattern is fundamentally composed of two parts:
1. **The Core Rectangle (or Trapezoid):** This forms the body of the sleeve wrapping around the bicep down to the cuff. 
2. **The Sleeve Cap (The "Semicircle"):** This is the curved section sitting on top of the rectangle. It is not a perfect semicircle, but rather a bell-like curve that arches over the shoulder and dips down to meet the armpit (underarm).

---

## 2. How Patterns Are Generated Right Now (MIRRA MVP)

Inside `product_ingestion/panels.py` and `product_ingestion/curve_config.py`, the dynamic pattern generator builds patterns procedurally based on body measurements.

### Sleeve Geometry in the Code
Your sleeve generation currently implements exactly the "rectangle + semicircle" concept. It generates a 5-edge shape for each sleeve (`sleeve_left` / `sleeve_right`):

1. **`cuff` (Edge 0):** A straight horizontal line at the very bottom.
2. **`right_underarm` & `left_underarm` (Edges 1 & 4):** Straight vertical lines going up from the cuff. These form the *sides of the rectangle*. They stop at a specific height defined as `cap_start_y` (which equals `sleeve_length - cap_height`).
3. **`cap_front` & `cap_back` (Edges 2 & 3):** The "semicircle" on top. These are built using complex `CubicBezierSegment` curves that start at the top of the underarm lines and arc up to the `apex` (the top center of the shoulder). 

**The Fit Logic:** The generator runs a highly advanced *binary search algorithm* to guarantee that the length of the sleeve cap curve perfectly matches the armhole's curve length + ease (defined in `curve_config.py` as `cap_ease_cm: 3.5`).

### Front and Back Body Panels
They are generated as 8-edged polygons. Key features include:
- **`armhole` edges:** S-curves that have a "concave hollow" near the underarm and a "shoulder flare" near the top to properly wrap around the human torso. The front armhole is generated deeper than the back armhole (`hollow_depth_frac` = 0.16 for front, 0.20 for back, positioned slightly differently), which is exactly how real tailoring works (allowing the arms to stretch forward).
- **`side` edges:** They have waist suppression. Instead of strict vertical rectangles, they bow inwards slightly at the waist using a Bezier curve to give a tailored fit, rather than a boxy drape.

---

## 3. How Standard Real-World Patterns Should Be

While the MIRRA implementation is highly sophisticated, let's compare it strictly to standard physical pattern-making for t-shirts:

1. **Sleeve Cap Shape:** In real life, a t-shirt sleeve cap is shallower (flatter) than a tailored suit jacket because knit fabrics stretch and relaxed arms require less height to lift. The cap is a compound curve: convex at the shoulder crown (bulging out) and concave at the underarm (scooping in). **Verdict:** MIRRA correctly models this via `CubicBezierSegment` with an outward bulge in `panels.py`.
2. **Armhole Depth:** T-shirts have dropped or deeper armholes compared to formal shirts to allow freedom of movement without pulling the garment up. **Verdict:** Controlled accurately in MIRRA via `m.armhole_depth` and `curve_config`.
3. **Neckline:** The front neckline must always be a deeper scoop than the back neckline to accommodate the neck's forward tilt. **Verdict:** MIRRA implements this flawlessly via `neckline_edge` passing `neck_depth_front` and `neck_depth_back`.

---

## 4. How CLO3D Reads and Models Pattern Geometry

CLO3D is fundamentally a 2D-to-3D engine. It sews flat 2D vector polygons together and simulates physics to drape them over an avatar.

### CLO3D's Internal Pattern Types
1. **Linear Outlines vs Curved Outlines:** CLO3D natively supports true Bézier curves. If a pattern is imported as heavily faceted straight lines (like a low-poly circle), the edge will drape poorly and the resulting 3D mesh will have zig-zag tension lines at the seams.
2. **DXF-AAMA / ASTM:** This is the industry-standard file format CLO3D uses to import patterns. It supports lines, polylines, arc, and SPLINEs (true curves). 

### Comparison to MIRRA's Architecture
* **Mathematical Curves:** MIRRA's `DynamicPatternGenerator` is exceptionally well-architected for CLO3D. By generating curves using `CubicBezierSegment` and `s_curve` types in Python, MIRRA knows the *exact, mathematical formula* for the curve.
* **Exporting True Geometry:** In `panel_export_dxf.py`, because MIRRA tracks these edges as true curves instead of just pixel-approximations from images, it exports them as strict `SPLINE` entities in the `.dxf` file. 
* **The Result in CLO3D:** When CLO3D loads MIRRA's `.dxf` files, it sees mathematically perfect Bézier curves. This prevents jittery sewing, ensures perfect seam matching (the binary search ensures the sleeve cap perfectly lengths-matches the armhole), and allows CLO3D to generate a pristine 3D garment mesh.

---

## Conclusion

Your current pattern generation framework logic (using Beziers to make the "rectangle + semicircle") is conceptually exactly what it is supposed to be doing. However, you are seeing a "leaf" because of a math logic bug feeding incorrect width proportions into the generator. 

### Why Your Sleeve Currently Looks Like a "Leaf" (The c_001-s_001-003 Case)

If you look at the **c_001-s_001-003** run (specifically `sleeve_left.svg`), the pattern resembles a long leaf rather than the expected "rectangle + cap". This is happening due to a **geometric math bug** connecting the measurements to the pattern width.

Here is the exact breakdown:
1. **The Proportion Conflict:** The metadata extracted `garment_measurements.bicep_width` as **18.0 cm** (which is the *flat* width of a standard tee sleeve, meaning its full circumference is 36.0 cm). But `panels.py` calculates the pattern width as `sleeve_width = m.bicep_width / 2`, resulting in a tiny base width of just **9.0 cm** for the entire sleeve pattern.
2. **The "Semicircle" Over-Expansion:** Meanwhile, the armhole depth is `24.0 cm` (producing an armhole arc length of **~48.5 cm**). The binary search algorithm in `panels.py` attempts to build a sleeve cap that sews cleanly into this armhole, so it forces the cap to reach **~52.0 cm** in perimeter length. 
3. **The "Leaf" Effect:** Because the algorithm is forced to cram an enormous 52.0 cm curve onto a completely shrunken 9.0 cm base, the math pushes the `cap_height` (the tip of the semicircle) extremely high, and the curves bulge widely outwards to hit the target length. This aggressive warp destroys the "straight rectangle" underarms, forming a shape identical to a leaf.

### Which is Correct and What is Better?

- **The Standard T-Shirt Pattern is Correct (The Video):** A wide rectangular base with a shallow bell-shaped semicircle (cap) on top is the physically and physically correct way to cut a t-shirt sleeve.
- **The Current Leaf Shape is Incorrect:** The leaf shape is a mathematical anomaly caused by bad data mapping. If you try to sew a 9cm wide leaf around a 36cm human bicep, it will physically fail to wrap around the arm in CLO3D.

**What is Better (The Solution):** The physically accurate "Rectangle + Semicircle" is far better and is indeed what you want. To fix the leaf shape, `panels.py` needs to be updated. If the metadata expects the *flat* bicep width (18.0 cm), then the sleeve pattern should not be divided by 2; in fact, the full flattened tube should be `18.0 * 2 = 36.0 cm` wide across the cuff. 

Once the pattern base width is restored to a normal ~36.0 cm, the 52 cm cap curve will relax and stretch gracefully across the top, restoring the correct, physically accurate "rectangle + semicircle" shape you observed in the video.
