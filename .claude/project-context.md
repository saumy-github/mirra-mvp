# Mirra Project Context

## Project Overview

**Project Name**: Mirra  
**Vision**: Deliver full virtual try-on experiences for e-commerce, enabling customers to see how clothes actually look and fit on their own bodies.

## Problem Statement

E-commerce clothing purchases suffer from high return rates due to fit uncertainty. Customers can't trust standard sizing charts, which vary by brand and body type. Mirra solves this by creating personalized, measurement-specific digital twins and realistic clothing simulations, so customers can see authentic fit before purchasing.

## The 3-Step MVP Pipeline

### **Step 1: Personal Digital Twin Generation**
Create a unique, reusable 3D body model from user measurements (height, weight, chest, waist, hip, etc.). This digital twin serves as the foundation for all future try-ons.

- **Input**: User measurements (tailor tape format)
- **Process**: Load base avatar template → Apply custom measurements via morphing
- **Output**: Personalized .avt avatar file (stored and reused)
- **Benefit**: Eliminates need to recreate avatar each session; ensures consistency

### **Step 2: 2D-to-3D Clothing Asset Pipeline**
Convert product images into reusable 3D garment patterns that preserve color, texture, and fit intent.

- **Input**: 2D product images (front, back views)
- **Process**: 5-stage extraction (segment → classify → colors → design → generate patterns)
- **Output**: 4-piece DXF patterns + edge manifests + color/design metadata
- **Benefit**: Assets reused across all users; reduces redundant processing

### **Step 3: Virtual Try-On Experience**
Combine personalized avatar + prepared clothing in a physics simulation to generate realistic VTO results.

- **Input**: Avatar (Step 1) + patterns (Step 2)
- **Process**: Import → arrange on body → create seams → physics simulation (150 steps)
- **Output**: Simulated garment on personalized body
- **Benefit**: User sees authentic fit, confidence in purchase decision

## Target Users

**Primary**: E-commerce shoppers buying clothing online  
**Secondary**: Fashion retailers seeking better fit visualization tools  
**Tertiary**: Fashion brands wanting accurate digital samples

## Success Metrics

1. **Avatar Accuracy**: <5% error between measured and morphed body dimensions
2. **Garment Fidelity**: Color, texture, print preservation in 3D conversion
3. **VTO Realism**: Physics simulation feels natural, fit judgment matches real garments
4. **User Confidence**: Positive correlation between VTO and actual purchase satisfaction
5. **System Performance**: Avatar generation <30s, ingestion <2 min, VTO <5 min

## MVP Constraints & Scope

### What's Included in MVP
- **Avatar**: Silhouette-focused (fit over realism), T-pose static, black matte style
- **Clothing**: Upper wear and lower wear only (no accessories yet)
- **Garment Types**: T-shirts initially (extensible to jackets, pants post-MVP)
- **Accuracy**: Prioritizes measurement alignment over face/hair realism
- **Rendering**: Desktop web browsers optimized

### What's Explicitly Out of Scope (Post-MVP)
- Live try-on (camera-based real-time)
- Accessories (watches, bags, shoes)
- Advanced cloth physics (wind, gravity-heavy fabrics)
- Realistic rendering (skin tones, facial features, hair)
- Mobile optimization
- Animation/movement

## Current MVP Status

**Step 1**: ~70% complete
- ✅ 11-step pipeline functional
- ✅ Measurement application and morphing working
- ✅ Avatar export to .avt format
- ⏳ Accuracy improvements for edge cases

**Step 2**: ~50% complete
- ✅ Image segmentation (RMBG-1.4 + GrabCut)
- ✅ Color extraction (K-Means in LAB space)
- ✅ 4-piece T-shirt pattern generation
- ⏳ Multi-garment type support (jackets, pants, dresses)
- ⏳ Complex print/design handling

**Step 3**: ~60% complete
- ✅ Pattern import and verification
- ✅ 10-seam T-shirt wiring system
- ✅ Physics simulation (150 steps)
- ⏳ Render quality improvements
- ⏳ Auto-slot matching refinements

## Reference Documentation

For deeper business context, see:
- `.claude/context/idea.md` - Original project vision
- `.claude/context/key-words.md` - Terminology and definitions
- `.claude/context/MVP-step-1.md` - Step 1 business requirements
- `.claude/context/MVP-Step-2.md` - Step 2 business requirements
- `.claude/context/MVP-step-3.md` - Step 3 business requirements

## Project Continuity

This project uses multiple AI tools (Claude, potentially Codex in future). Documentation is organized for:
- **CLAUDE.md** (root) - Entry point for Claude sessions
- **.claude/** folder - Claude-specific documentation and setup
- **.agent/** folder - Planning phases and execution tracking (being migrated to .claude/)

For now, focus on Claude-based development. Codex/multi-agent structure deferred to future.
