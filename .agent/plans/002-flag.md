# Flags: Plan 002

1. 🚩 **Vulnerability**: Blender version compatibility - tested with 5.0.1, API changes in major versions could break sewing/texturing scripts. Add version check at startup.

2. 🚩 **Vulnerability**: No input validation - corrupted images cause cryptic errors. Add validation in Step 1 (file exists, readable, minimum size).

3. 🚩 **Vulnerability**: Hardcoded Blender paths - partially addressed with OS detection, but could add user-configurable path.

4. 🔮 **Future**: Multi-view support (front + back) - back view processing not fully integrated. MVP uses front-view only.

5. 🔮 **Future**: Automated size recommendation - suggest best fit based on digital twin measurements. Requires Step 1 digital twin data.

6. 🔮 **Future**: Design extraction accuracy - edge detection works for MVP but AI-based segmentation would be more accurate for complex patterns.

7. ⚡ **Performance**: Cloth simulation can be slow (minutes per garment). Quality vs speed tradeoff, optimize post-MVP.

8. 🔮 **Future**: Asset database/inventory system - currently just files in directories. Critical for Step 3 (VTO) integration.

9. 🔮 **Future**: Batch processing - currently one t-shirt at a time. Add after MVP validation.

10. ⚠️ **Limitation**: T-shirts only - pipeline designed for standard t-shirt structure (front, back, sleeves). Intentional MVP scope.

11. ⚠️ **Limitation**: Manual measurement input - Step 4 requires 5 measurements. Use default measurements for standard sizes.

12. ⚠️ **Limitation**: No real-time preview - must check output directories. Run steps individually for debugging.

13. ⚠️ **Limitation**: Memory usage - high-res textures + simulation requires 2-4 GB RAM per garment. Monitor during testing.

14. ⚠️ **Limitation**: No undo/rollback - pipeline overwrites outputs. Manually backup before re-running.
