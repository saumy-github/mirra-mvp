# Flags: Plan 001

1. 🔮 **Learn**: Understand what the STAR `scale` parameter does and how it affects mesh generation and measurements.
2. 🔮 **Learn**: Deep dive into how STAR generates digital twins using beta and theta parameters - what each controls, valid ranges, and optimal number of betas for accurate fitting.
3. ⚡ **Performance**: Add GPU acceleration for beta fitting. Current CPU-based fitting takes ~8-10 seconds per digital twin (1,100 STAR mesh generations per run). GPU could reduce this to ~2-3 seconds (3-5x speedup), critical for production with many users.
4. 🔧 **Tooling**: Blender MCP integration for automated preview generation and visual testing. Not needed for MVP (manual Blender verification is sufficient). Future use: auto-generate preview images (front/side/back views), automated regression testing, quality gates for mesh validation.
