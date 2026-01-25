# Problems: Plan 001

1. **Problem**: Shoulder Width Measurement Error

   The fitted STAR mesh predicts a shoulder width value that has 61.7% error compared to the target measurement, far exceeding the 2% tolerance gate.

   **Found in**: Phase 2B, Step 2 (Beta fitting)

   **Evidence**: From `values-user_m_001-001.json` - target was 45.0 cm but predicted value has 61.71% error. Analysis of `mesh_measure.py` lines 19-56 shows the measurement includes arm width.

2. **Problem**: STAR Model Generates T-Pose Instead of A-Pose

   The exported avatars display in T-pose (arms horizontally straight) instead of A-pose (arms at ~45° down).

   **Found in**: Phase 3 (GLB export verification in Blender)

   **Evidence**: Visual inspection in Blender shows T-pose. `pose_catalog.py` line 14 sets all thetas to zero, which is STAR's default T-pose, not A-pose.

   **Solution**: Not found
