# Mirra MVP - Current Roadmap

## Current Phase

**MVP Development** - Steps 1, 2, 3 of the virtual try-on pipeline

---

## Step 1: Avatar Generation - Status

**Completion**: ~70%

### What's Working ✅
- 11-step pipeline fully implemented
- Measurement fetching from MongoDB and JSON
- Base avatar template loading and resolution
- Measurement morphing algorithm (vertex displacement)
- Accuracy error computation
- Avatar export to .avt file format
- Output artifact generation and logging

### Currently In Progress 🔄
- Accuracy improvements for extreme body shapes
- Edge case handling (very tall, very short, etc.)
- Base avatar template expansion (more body archetypes)

### Known Issues ⚠️
- Very extreme measurements (outliers) show >5% error
- Single T-pose may not suit all body shapes equally
- Head/hands/feet simplification reduces anatomical accuracy

### Next Priorities 📋
1. Improve base template selection logic for better body archetype matching
2. Expand body shape archetype options
3. Increase avatar template library for better baseline coverage
4. Accuracy target: <5% error for 95% of population

---

## Step 2: Product Ingestion - Status

**Completion**: ~50%

### What's Working ✅
- Image segmentation (RMBG-1.4 with GrabCut fallback)
- View classification (CLIP zero-shot learning)
- Color extraction (K-Means clustering in LAB space)
- Design/logo detection (edge detection + contour analysis)
- 4-piece T-shirt pattern generation
- DXF export format working
- SVG export format working
- Edge manifest generation (for Step 3 seam creation)
- Panel metadata documentation

### Currently In Progress 🔄
- Support for jacket garments
- Support for pants/lower-wear patterns
- Improved complex print/pattern handling
- Automation of quality verification

### Known Issues ⚠️
- Complex prints sometimes fail color separation
- Very tight or very loose fits sometimes under-segment
- Unusual angles/poses in product images cause misclassification
- Design extraction threshold tuning needed for different garment types

### Next Priorities 📋
1. Extend DynamicPatternGenerator to support jackets (requires new panel topology)
2. Add pants pattern support (different measurement conventions)
3. Improve design extraction robustness (threshold tuning)
4. Expand from ~50-100 test garments to full production catalog
5. Implement semi-auto QA verification

---

## Step 3: Virtual Try-On - Status

**Completion**: ~60%

### What's Working ✅
- CLO project creation and initialization
- Avatar import from .avt files
- Pattern import from DXF files
- Pattern verification (geometry validation)
- Edge and slot metadata extraction
- Pattern arrangement (auto and manual slot selection)
- 10-seam system for T-shirt assembly (shoulder, side, sleeve, armhole)
- Fabric property application (colors, textures)
- Physics simulation (150-step Verlet integration)
- Final state export and reporting

### Currently In Progress 🔄
- Render quality improvements (lighting, viewing angles)
- Auto-slot matching robustness
- Performance optimization for complex garments
- Output visualization and presentation

### Known Issues ⚠️
- Very complex seams sometimes timeout (>60s simulation)
- Auto-slot matching fails for unusual avatar shapes
- Physics parameters not fully tuned for all fabric types
- Render output lacks final polish (lighting, shadows)

### Next Priorities 📋
1. Improve render quality (lighting, camera angles, presentation)
2. Tune physics parameters per fabric type
3. Optimize simulation performance (early termination when stable)
4. Extend seam system to jackets and pants
5. Add output visualization (web preview, 360° view)

---

## Cross-Step Integration Status

### Data Flow Working ✅
- Step 1 → Step 3: Avatar export/import chain functional
- Step 2 → Step 3: Pattern + edge manifest import chain functional
- Step 1 + Step 2 → Step 3: Full VTO pipeline executable

### Known Integration Issues ⚠️
- Edge manifest naming inconsistencies between Step 2 and Step 3 (half-girth rule critical)
- Measurement convention mismatches can break Step 3 seam creation
- Very large avatars sometimes break pattern arrangement

---

## Known Blockers & Challenges

1. **Measurement Convention Consistency**: Half-girth rule in Step 2 must be perfectly aligned with Step 3 expectations. Mismatches break seam creation. (Mitigation: documented in architecture/step_2 and quick-reference)

2. **CLO Plugin Stability**: REST API sometimes times out on complex operations. (Mitigation: timeout handling, retry logic needed)

---

## Next Phase: Beyond MVP

### Immediate Post-MVP (Quarter 2)
- Live try-on (camera-based real-time, same-device rendering)
- Extended garment types (dresses, jackets, shirts, pants)
- Performance optimization for mobile browsers
- User interface and web integration

### Medium-term (Quarter 3-4)
- Accessory support (bags, watches, shoes)
- Advanced cloth physics (gravity, wind, wrinkles)
- Realistic avatar rendering (skin tones, faces, hair)
- Multi-size variants (XS, S, M, L, XL handling)
- Social features (Live Try-On Conference - group feedback)

### Long-term (Year 2)
- Video generation (GIF/MP4 animations)
- AR integration (camera overlay)
- Feedback loop (learn from actual returns/reviews)
- Marketplace integration (direct shopping)

---

## Success Metrics & Targets

### Accuracy
- **Avatar**: <5% error between measured and morphed dimensions (target: 95% of users)
- **Garment Fit**: User perception matches real garment fit (target: >80% confidence)

### Performance
- **Step 1**: Avatar generation <30 seconds
- **Step 2**: Image ingestion <2 minutes
- **Step 3**: VTO generation <5 minutes

### Quality
- **Render**: Photorealistic clothing appearance
- **Simulation**: Natural-looking draping and wrinkles
- **User Experience**: Intuitive, fast, reliable

---

## Testing & Quality Assurance

### Current QA Status
- Manual testing of each step with sample inputs
- Output artifacts preserved for visual inspection
- Error reporting via JSON artifacts

### Planned QA Improvements
- Automated test suite for each step
- Visual regression testing (expected output artifacts)
- Performance benchmarking
- End-to-end pipeline testing

---

## Documentation Status

- ✅ Business requirements (context/ folder)
- ✅ Architecture documentation (.claude/architecture/)
- ✅ Quick reference guides (.claude/quick-reference.md)
- ✅ FAQ and troubleshooting (.claude/faq.md, troubleshooting.md)
- 🔄 Code-level documentation (in-progress as code updates)
- ⏳ API documentation (future)
- ⏳ User guide (future)

---

## Recent Work & Git History

See `.agent/plans/` for recent planning documents and `.agent/` folder for execution tracking.

Recent commits show:
- Avatar generation pipeline refinements
- CLO plugin improvements (Windows/Mac parity)
- Step 2 segmentation accuracy improvements
- Step 3 seam wiring fixes

---

## Dependencies & Prerequisites

- **CLO 3D**: Must be installed and running (for all steps)
- **MongoDB**: Must be accessible with measurements/products collections
- **Python 3.9+**: With requirements from requirements.txt
- **Windows/Mac/Linux**: Plugin available for Windows and macOS

---

*Last updated: 2026-05-16*
