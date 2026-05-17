# CLO 3D Feature: Sketch on Avatar

**Source**: CLO 3D 2025.2 Update  
**Date**: 2026-05-16  
**Status**: Research & Future Planning

---

## Overview

**Feature Name**: Sketch on Avatar  
**Description**: Sketch garments directly on the avatar and instantly convert them into patterns  
**CLO Version**: 2025.2+

---

## What It Does

- Users can draw/sketch garment designs directly on a 3D avatar
- Sketches are automatically converted into 2D pattern pieces
- Instant pattern generation (no manual tracing needed)
- Maintains avatar measurements/proportions in patterns

### Web Research Findings
**Feature Name**: 3D Pen on Avatar (or Create 3D Pen)

**How It Actually Works** (confirmed from official CLO documentation):
- Users draw lines on the avatar surface in 3D space
- Draw garment silhouettes around avatar directly
- Automatically extract patterns from drawn lines
- Auto-convert 3D sketch to 2D pattern pieces

**Official Documentation**:
- [CLO 3D Create 3D Pen Support](https://support.clo3d.com/hc/en-us/articles/115008920368-Create-3D-Pen)
- [CLO 3D Key Features](https://www.clo3d.com/en/clo/features)
- [CLO 3D Main Website](https://www.clo3d.com/en/)

---

## Current Mirra Impact

**MVP**: ❌ Not applicable
- MVP uses 2D product images → 3D patterns (Step 2)
- Sketch on Avatar is a design tool, not a measurement-based tool
- Different workflow than current image extraction

---

## Post-MVP Potential

**Post-MVP**: ⭐⭐ Medium Priority

### Use Case
1. User creates personalized avatar (Step 1) ✅
2. Designer sketches garment on avatar
3. Auto-conversion to 3D patterns
4. VTO simulation (Step 3) ✅

### Benefits
- More intuitive design experience
- Direct avatar-centric workflow
- Instant pattern generation from sketch
- Could supplement product image extraction

### Challenges
- Requires new UI/workflow in Step 2
- Needs designer training
- Would need to integrate with REST API
- May not be practical for retail product ingestion (vs. manual sketch)

---

## Technical Considerations

**Questions for Research**:
- [ ] Does CLO plugin API expose Sketch on Avatar functionality?
- [ ] What are the inputs (sketch data format)?
- [ ] What are the outputs (pattern format)?
- [ ] Can it be automated via REST API?
- [ ] Does it require interactive CLO UI or headless support?

**Integration Path** (If pursued):
1. User draws sketch on avatar in CLO
2. Export sketch as data
3. Send to Step 2 pipeline
4. Auto-convert to DXF patterns
5. Proceed to Step 3 VTO

---

## Comparison with Current Approach

| Aspect | Current (Image-based) | Sketch on Avatar |
|--------|----------------------|------------------|
| Input | 2D product photos | Sketch on 3D avatar |
| Accuracy | Good for existing products | Good for new designs |
| Speed | ~2 minutes per garment | Potentially faster |
| Use Case | Retail inventory | Custom/designer creations |
| Automation | Fully automated | Semi-automated |

---

## Recommendation

**MVP**: Skip (not needed)  
**Post-MVP Phase 2**: Consider as alternative design workflow  
**Priority**: Lower (complements, not critical)

**Potential Value**: Could enable custom design workflow, useful for B2B designer tools

---

## Related Features

- Also new in CLO 2025.2: Auto POM & Grading (see `auto-pom-grading.md`)
- Works best combined with personalized avatars (Step 1)
- Feeding into VTO pipeline (Step 3)

---

## Research TODO

- [ ] Check CLO 2025.2 API documentation
- [ ] Understand sketch data format
- [ ] Evaluate REST API support
- [ ] Assess integration complexity

---

*Last updated: 2026-05-16*
