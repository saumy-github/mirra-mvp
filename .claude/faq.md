# Mirra FAQ - Frequently Asked Questions

---

## Step 1: Avatar Generation FAQs

**Q: What base avatar template is used?**
A: Gender-specific templates (male/female) are selected based on user gender. Each template is a T-posed mesh designed for measurement morphing. See `step_04_resolve_base_avatar.py` for template resolution logic.

**Q: How accurate is the avatar morphing?**
A: Target accuracy is <5% error. Accuracy varies by measurement and body shape. Check `error_report.json` for per-measurement accuracy percentages. Extreme body shapes (very tall, very short, very wide) may show higher error.

**Q: Can I run Step 1 without CLO 3D installed?**
A: No. CLO plugin must be running and responding. Step 1 communicates exclusively via REST API to CLO. Install CLO 3D and build the plugin first (see `clo_workspace/build_plugin.py`).

**Q: Where do user measurements come from?**
A: MongoDB "measurements" collection (primary) or JSON file (fallback). Query by user_id. Must contain all required fields (height, weight, circumferences, lengths).

**Q: What if a measurement is missing?**
A: Step 5 (normalize_targets.py) will fail validation. All required fields must be present. Check `mongo_snapshot.json` in output to see what was actually fetched.

**Q: Can I edit the avatar file (.avt) directly?**
A: Not recommended. The .avt file is binary CLO format. Modifications must go through the CLO plugin REST API. Use Step 1 to re-generate if changes needed.

**Q: How long does avatar generation typically take?**
A: ~30 seconds for a typical run (depending on CLO responsiveness). Times are logged in output artifacts.

**Q: Why is the avatar in T-pose (arms out)?**
A: T-pose is optimal for garment placement and measurement consistency. It's the industry standard for virtual try-on. Poses are post-MVP improvements.

---

## Step 2: Product Ingestion FAQs

**Q: What image formats do you support?**
A: PNG, JPG, JPEG. Recommended: 300+ DPI, clear background, visible garment details, good lighting. See `segmentation.py` for detailed support.

**Q: Why is the half-girth convention important?**
A: Step 3 uses `edge_manifest.json` to create seams. If measurements are wrong (absolute instead of half-girth), seams will be off-size. Garment won't fit correctly. This is CRITICAL for Step 1 → Step 3 integration.

**Q: Can I use Step 2 without Step 1 or 3?**
A: Yes. Step 2 is completely independent. It generates patterns from images. You can generate patterns anytime, use them later for try-ons.

**Q: How do I add a new garment type (jacket, pants)?**
A: Extend `DynamicPatternGenerator` in `panels.py`. Add new panel topology logic. Update `garment_router.py` for type detection. See `.claude/architecture/step_2_ingestion.md` for details.

**Q: What does edge_manifest.json do?**
A: Maps panel edge names (e.g., "front-left-shoulder") to CLO geometry indices. Step 3 uses these names to wire seams. Edge names must exactly match between Step 2 and Step 3.

**Q: What if segmentation fails (garment not isolated)?**
A: Check input image quality. If background is complex, try GrabCut method instead of RMBG-1.4. Inspect `base_garment.png` output - is garment fully separated?

**Q: How many colors does K-Means extract?**
A: Default is 5-7 colors. Check `colour_extraction.py` for parameter. Increase k for more detail, decrease for simpler palette.

**Q: Can I manually edit the DXF files?**
A: Not recommended. DXF files are auto-generated with correct geometry for your measurements. Manual edits may break Step 3 seam creation.

**Q: How long does product ingestion typically take?**
A: ~2 minutes per garment (depends on image processing speed). Times are logged in `run_summary.json`.

**Q: What if design extraction fails (logo not detected)?**
A: Try adjusting Canny edge detection thresholds in `design_extraction.py`. Inspect `graphic_diffuse.png` - is logo visible? Check contrast ratio (must be 1-80% of garment area).

---

## Step 3: Virtual Try-On FAQs

**Q: What does the physics simulation do?**
A: 150-step Verlet integration applies gravity, fabric properties, and constraints. Result: realistic draping, wrinkles, fit on the avatar. Makes VTO look like real fabric on real body.

**Q: Why does avatar import have an optional CSV?**
A: Optional measurements can be applied to avatar before VTO (see `step_03_import_avatar.py`). Allows on-the-fly adjustments without regenerating Step 1.

**Q: What's a "slot"?**
A: Predefined placement location on avatar where patterns go (e.g., "front", "left_sleeve"). Avatar provides multiple slots. Pipeline auto-selects best slot for each pattern using keyword matching.

**Q: What if auto-arrange fails?**
A: Manual slot mapping available. Specify pattern-to-slot assignments in config. See `step_07_arrange_patterns.py`.

**Q: Can I run Step 3 without Step 1 or Step 2?**
A: No. Step 3 requires avatar (.avt) from Step 1 AND patterns (DXF) + edge_manifest.json from Step 2. Both inputs are mandatory.

**Q: Why might seam creation fail?**
A: Most common cause: Edge names in `edge_manifest.json` don't exactly match names in `seams.py`. Check for spelling/capitalization mismatches. See troubleshooting.md.

**Q: How do I improve render quality?**
A: See `step_08_apply_fabric.py` for material properties. Adjust lighting, camera angle, texture mapping. Post-MVP improvements focus on render polish.

**Q: Why does simulation timeout?**
A: Complex garments with many seams can exceed time limit. Solutions: reduce garment complexity, reduce step count, optimize physics parameters.

**Q: Can I use the same avatar for different garments?**
A: Yes. Avatar from Step 1 can be used with any patterns from Step 2. Same patterns can be used with different avatars.

**Q: How long does a full VTO typically take?**
A: ~5 minutes (breakdown: import 10s, arrange 20s, simulation 4m, export 10s). Varies by complexity.

**Q: What's the native_vto_report.json?**
A: Complete diagnostic record of VTO generation. Shows all 11 steps' results, success/failure, timing, edge counts, seam info. Essential for debugging.

---

## General Mirra FAQs

**Q: What's the full pipeline flow?**
A: Step 1 (measurements → avatar) → Step 2 (image → patterns) → Step 3 (avatar + patterns → VTO). Each step independent until Step 3.

**Q: Can steps run in parallel?**
A: Step 1 and 2 are independent - run in parallel. Step 3 requires both complete first - run sequentially.

**Q: How do I test locally?**
A: Use sample measurements/images in input folders. Run each step independently. Check output/ for artifacts. Inspect JSON files for results.

**Q: Where's the REST plugin defined?**
A: `clo_workspace/plugin_contract.json` defines 27 endpoints. See high-level architecture for overview. `clo_workspace/build_plugin.py` builds it.

**Q: How do I add debugging output?**
A: Add `print()` statements in relevant step files. Output artifacts in output/ folder contain JSON results. Check logs for step timing and errors.

**Q: What if a step fails silently?**
A: Check output/ folder for error_report.json or run_summary.json. Run step in isolation with added logging. Check context.json for state at each step.

**Q: Can I modify .agent/ or .claude/ files?**
A: Only with explicit instructions. These are documentation, not code. They're meant to stay current across sessions.

**Q: What's the difference between .agent/ and .claude/ folders?**
A: `.agent/` is for planning phases and execution tracking. `.claude/` is for ongoing reference, context, and commands. Both support Claude-based development.

**Q: How do I report a bug?**
A: Check troubleshooting.md first. If issue persists, add debugging output, run in isolation, inspect artifacts. Then provide: error message, output JSON, reproduction steps.

**Q: Can I use this on Mac/Linux?**
A: Mac plugin exists in `clo_workspace/mac/`. Linux support TBD (requires CLO 3D on Linux). Most code is platform-agnostic Python.

**Q: What's the minimum CLO 3D version required?**
A: Check `clo_workspace/plugin_contract.json` for API version. Plugin built by `clo_workspace/build_plugin.py` states compatibility.

**Q: How do I update the measurement fields?**
A: Edit `avatar_runtime/field_contract.py` (Step 1) or `garment_measurements.py` (Step 2). Add/remove fields, update validation rules.

**Q: Can I extend Mirra for new features?**
A: Yes. Follow .claude/repo-rules.md conventions. Keep changes scoped. Test locally. Create plan first (see .agent/plans/).

**Q: What's the project's long-term vision?**
A: See `.claude/project-context.md` for post-MVP roadmap. Includes live try-on, extended garment types, advanced physics, realistic rendering, mobile optimization.

**Q: Who maintains this codebase?**
A: Saumy (primary). Claude helps with development. See `.claude/project-context.md` for more context.

**Q: How do I get help?**
A: Check CLAUDE.md entry point → relevant documentation files → faq.md (this file) → troubleshooting.md. If stuck, ask with full context (error messages, artifacts, reproduction steps).

---

## Step-Specific Deep Dives

For more detailed information:
- **Step 1 Details**: See `.claude/architecture/step_1_avatar.md`
- **Step 2 Details**: See `.claude/architecture/step_2_ingestion.md`
- **Step 3 Details**: See `.claude/architecture/step_3_vto.md`

For quick checklists and references:
- **Quick Reference**: See `.claude/quick-reference.md`

For troubleshooting specific issues:
- **Troubleshooting Guide**: See `.claude/troubleshooting.md`

---

*Last updated: 2026-05-16*
