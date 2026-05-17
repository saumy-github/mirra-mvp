# CLO 3D Feature: Auto POM & Grading

**Source**: CLO 3D 2025.2 Update  
**Date**: 2026-05-16  
**Status**: High Priority for Post-MVP Planning

---

## Overview

**Feature Name**: Pattern Drafter | Auto POM & Grading  
**Description**: Automatically generate POMs (size grades) and apply grading simply by entering measurements. Speeds up pattern drafting with flexible and intuitive editing capabilities  
**CLO Version**: 2025.2+

---

## What It Does

- **POM** = Piece of Measurement (garment size specification)
- **Grading** = Creating size variants (XS, S, M, L, XL) from one base pattern
- Takes one base pattern + measurement inputs
- Auto-generates multiple size variants with proper proportional scaling
- Maintains fit consistency across all sizes

### Example
```
Input:  Base pattern (Size M)
        Measurement deltas (how XS differs from M, how L differs from M, etc.)
        
Output: Size XS pattern
        Size S pattern
        Size M pattern (original)
        Size L pattern
        Size XL pattern
```

### Web Research Findings
**Official Feature Names**:
- Pattern Drafter (for Trousers, Skirts, and other garments)
- Auto Grading
- POM (Point of Measurement) system

**How It Actually Works** (confirmed from official CLO documentation):

1. **Pattern Drafter**:
   - Can generate patterns from images or text descriptions
   - Quick pattern generation for multiple garment types
   - Available for Trousers, Skirts, and more

2. **Grading Integration**:
   - Click "Add Grading" in Pattern Drafter
   - Set up size table for graded patterns
   - POM tab displays length by grading size
   - Auto-generates size variants from base pattern

3. **Key Components**:
   - **Create POM**: Manually create size specifications
   - **Set Grading**: Configure grading rules and increments
   - **Apply Grading**: Apply grading to existing patterns
   - **Auto Grading**: Automatic grading generation

**Official Documentation**:
- [CLO Pattern Drafter](https://support.clo3d.com/hc/en-us/articles/45053653355545-Pattern-Drafter)
- [CLO Create POM](https://support.clo3d.com/hc/en-us/articles/360025716774-Create-POM)
- [CLO Set Grading](https://support.clo3d.com/hc/en-us/articles/115015798567-Set-Grading)
- [CLO Apply Grading](https://support.clo3d.com/hc/en-us/articles/360000742948-Apply-Grading)
- [CLO Grading Section](https://support.clo3d.com/hc/en-us/sections/115003621087-2D-Pattern-Grading)
- [CLO 2025.2 Release](https://www.clo3d.com/en/resources/notices/1158)

---

## Current Mirra Impact

**MVP**: ⚠️ Low (but important to understand)
- Step 2 currently generates patterns for single size_id only
- MVP doesn't require multi-size support yet
- But blocks future scaling

**Current Limitation**:
```
To support all sizes in MVP:
  Step 2: Image → Pattern (M)
  Manual: Repeat for XS
  Manual: Repeat for S
  Manual: Repeat for L
  Manual: Repeat for XL
  (5 separate runs of Step 2!)
```

---

## Post-MVP Potential

**Post-MVP**: ⭐⭐⭐ CRITICAL - High Priority

### Problem It Solves
Creating a multi-size clothing inventory is currently inefficient:
- Each size requires re-running Step 2
- Time-consuming and error-prone
- Doesn't scale for large catalog

### Solution with Auto POM & Grading
```
Future Workflow (with Auto Grading):
  Step 2: Image → Pattern (M)
  CLO Auto Grading: M → XS, S, L, XL (automatic)
  (Single Step 2 run, instant multi-size support!)
```

### Business Impact
- **10x faster inventory creation** (one run instead of 5)
- **Consistent sizing** across all variants
- **Scalable** for large product catalogs
- **Enables** multi-size try-on experience
- **Better user experience** (more size options)

---

## Technical Details

### What We Need to Know

**Measurement Inputs Required**:
- Base pattern measurements (M size)
- Size increment specs (how XS, S, L, XL differ from base)
- Grade rules (proportional, fit-based, custom)

**What CLO Does**:
- Takes measurements
- Applies grading algorithm
- Generates new pattern pieces per size
- Maintains proper proportions

**Output Formats**:
- DXF files per size (XS_front.dxf, S_front.dxf, etc.)
- Pattern specifications for each size
- Fit parameters per size

---

## Integration with Mirra

### Current Step 2 Limitations
```
product_ingestion/run_product_ingestion.py
├── Input: cloth image, size_id (M)
├── Process: 5-stage extraction (segment, classify, colors, design, generate)
└── Output: Patterns for size M only
```

### Future Step 2 with Auto Grading
```
product_ingestion/run_product_ingestion.py
├── Input: cloth image, base_size_id (M)
├── Process: 5-stage extraction (segment, classify, colors, design, generate)
├── Auto Grade: M → XS, S, L, XL (CLO API call)
└── Output: Patterns for ALL sizes (5 DXF variants)
```

### Impact on Inventory System
- **Current**: One garment = one size
- **Future**: One garment = 5 size variants
- **Storage**: Minimal overhead (just DXF files)
- **Step 3**: Can select appropriate size for try-on

---

## Implementation Path

### Phase 1: Research (Now)
- [ ] Check CLO 2025.2 API documentation
- [ ] Does REST API expose grading endpoints?
- [ ] What are input/output formats?
- [ ] Performance: Time to grade one size?

### Phase 2: Planning (Post-MVP)
- [ ] Design measurement input schema for grading
- [ ] Plan Step 2 extension (add grading step)
- [ ] Design inventory system for multi-size storage
- [ ] Update Step 3 for size selection

### Phase 3: Implementation (Post-MVP)
- [ ] Implement grading API calls
- [ ] Test multi-size pattern generation
- [ ] Store size variants in inventory
- [ ] Update Step 3 to support size selection
- [ ] Test VTO with different sizes

---

## Questions for developer.clo3d.com

**Critical Research Items**:
1. Does CLO plugin REST API expose Auto POM & Grading?
2. What are the input parameters (measurements, grade rules)?
3. Can grading be fully automated (no interactive UI required)?
4. What format are outputs (DXF, JSON, native CLO)?
5. Performance: How long to grade one size to all variants?
6. Can grades be customized (proportional vs. fit-based)?
7. How are size increments specified?

---

## Comparison: With vs. Without Auto Grading

| Aspect | Without Grading (MVP) | With Grading (Post-MVP) |
|--------|----------------------|------------------------|
| Inventory Model | Single size per product | Multi-size variants |
| Pattern Creation | One size at a time | All sizes at once |
| Time per Garment | 5 × 2 min = 10 min | 1 × 2 min + auto grade ≈ 2.5 min |
| Catalog Size | Limited | Unlimited |
| User Experience | Limited size options | Full size range (XS-XL) |
| Consistency | Manual (error-prone) | Automatic (consistent) |

---

## Recommendation

**MVP**: Don't implement (not needed yet)  
**Post-MVP Phase 1**: RESEARCH (understand CLO API support)  
**Post-MVP Phase 2**: IMPLEMENT (integrate into Step 2)  
**Priority**: ⭐⭐⭐ HIGH (critical for scaling)

**Timeline**:
- Q2 2026: Research CLO 2025.2 API
- Q3 2026: Plan grading integration
- Q4 2026: Implement multi-size support

---

## Related Features

- Sketch on Avatar (see `sketch-on-avatar.md`) - Design tool
- Avatar Generation (Step 1) - Personalized sizing
- VTO (Step 3) - Display by size

---

## Research TODO

- [ ] Visit developer.clo3d.com
- [ ] Find CLO 2025.2 API documentation
- [ ] Search for "POM", "grading", "auto-grade" endpoints
- [ ] Document REST API endpoints for grading
- [ ] Test grading with sample patterns
- [ ] Benchmark performance

---

*Last updated: 2026-05-16*
