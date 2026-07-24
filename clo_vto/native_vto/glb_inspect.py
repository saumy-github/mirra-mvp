"""GLB geometry sanity checks — did this export actually contain a simulated,
sewn, avatar-visible result, or 4 flat unsewn panels with no avatar?

Background: `Simulate()` is documented synchronous in the real CLO SDK
(`UtilityAPIInterface.h`) and `wait_for_queue()` draining is not proof the
resulting garment actually drapes onto anything — a cloth solver with no
visible avatar to collide against can still report success while producing
flat, barely-moved geometry. Rather than trust a queue-drain or a hardcoded
`true`, this module inspects the *actual exported mesh geometry* — the one
thing in this pipeline that unambiguously reflects the real post-simulation
3D result — using `pygltflib`, which is already a hard dependency of
`step_12_texture_glb.py`.

See .agent/clo-avatar-vto/vto-pipeline-debug-plan-26_7_24.md, Bugs 3 and 4.

Design notes
------------
* A flat, unsimulated pattern piece is planar: its vertices lie (near-)exactly
  on one plane, so its bounding-box extent along its own thinnest axis is
  tiny relative to its other two axes. A draped garment, and a human-shaped
  avatar, are not planar in any axis. This gives a cheap, dependency-free
  "does this look simulated" signal without needing any new, unconfirmed CLO
  SDK capability — in principle.
* Deliberately does NOT rely on `/patterns/{i}/bbox` — that endpoint is
  confirmed (via the real SDK header) to return 2D flat-pattern width/height,
  not 3D world-space geometry, so it cannot answer this question at all.

**Tested against a real known-bad export and found NOT reliable as a
blocking gate — kept as a diagnostic-only signal.** Ran `mesh_is_draped()`
against `clo_vto/output/simulation.glb`, an export confirmed to be the exact
Bug 4 failure (4 floating unsewn panels, no avatar). Every panel's flatness
ratio came back between 0.26 and 0.64 — nowhere near planar. `arrange-pattern`
apparently gives each piece enough inherent 3D curvature (it's positioned and
oriented to wrap around the body even before any simulation runs) that "is
this mesh planar" does not distinguish "arranged only" from "arranged and
simulated" for this pipeline. `mesh_is_draped()` is retained here because a
genuinely-degenerate export (zero meshes, unreadable geometry) is still worth
surfacing, and because it's cheap and harmless to log — but `step_11` treats
its result as informational, not a pass/fail gate. The mesh-*count* check
(see `step_11_export_note.py`) is the one actually confirmed against real
data — that same known-bad file has exactly 4 meshes (the 4 panels) and zero
avatar meshes, which a count-based check does catch. A more promising
future signal, not implemented here, would be checking whether panel meshes'
geometry actually touches/overlaps at shared seam edges (sewn) vs. remaining
spatially separate (merely arranged) — worth revisiting if the mesh-count
check proves too coarse in practice.
"""

from __future__ import annotations

import struct
from typing import Optional

try:
    from pygltflib import GLTF2
except ImportError:  # pragma: no cover - guarded the same way step_12 guards it
    GLTF2 = None  # type: ignore[assignment,misc]

# A mesh whose thinnest-axis extent is less than this fraction of its largest
# extent is considered "suspiciously flat" — i.e. still in its pre-simulation
# planar pattern-piece pose. Not yet calibrated against a known-good manual
# CLO export (see the debug-plan doc's recommendation to do so before relying
# on this as a blocking gate) — 1% is a conservative starting point.
_FLATNESS_RATIO_THRESHOLD = 0.01

_COMPONENT_TYPE_STRUCT = {
    5120: ("b", 1),   # BYTE
    5121: ("B", 1),   # UNSIGNED_BYTE
    5122: ("h", 2),   # SHORT
    5123: ("H", 2),   # UNSIGNED_SHORT
    5125: ("I", 4),   # UNSIGNED_INT
    5126: ("f", 4),   # FLOAT
}

_TYPE_COMPONENT_COUNT = {
    "SCALAR": 1,
    "VEC2": 2,
    "VEC3": 3,
    "VEC4": 4,
    "MAT2": 4,
    "MAT3": 9,
    "MAT4": 16,
}


def _read_vec3_accessor(gltf: "GLTF2", accessor_index: int) -> list[tuple[float, float, float]]:
    """Decode a VEC3 FLOAT accessor (e.g. POSITION) into a list of (x, y, z).

    Assumes the buffer is embedded in the GLB binary chunk (buffer 0), which
    is guaranteed here since step_11 always exports with format="glb".
    """
    accessor = gltf.accessors[accessor_index]
    if accessor.type != "VEC3" or accessor.componentType != 5126:
        raise ValueError(f"Unsupported accessor for vertex read: type={accessor.type} componentType={accessor.componentType}")

    buffer_view = gltf.bufferViews[accessor.bufferView]
    blob = gltf.binary_blob()
    if blob is None:
        raise ValueError("GLB has no embedded binary blob (buffer 0)")

    fmt_char, comp_size = _COMPONENT_TYPE_STRUCT[accessor.componentType]
    n_components = _TYPE_COMPONENT_COUNT[accessor.type]
    element_size = comp_size * n_components

    base_offset = (buffer_view.byteOffset or 0) + (accessor.byteOffset or 0)
    stride = buffer_view.byteStride or element_size

    vertices: list[tuple[float, float, float]] = []
    fmt = f"<{n_components}{fmt_char}"
    for i in range(accessor.count):
        start = base_offset + i * stride
        chunk = blob[start:start + element_size]
        vertices.append(struct.unpack(fmt, chunk))
    return vertices


def _mesh_axis_extents(gltf: "GLTF2", mesh) -> Optional[tuple[float, float, float]]:
    """Return (extent_x, extent_y, extent_z) across all of a mesh's primitives, or None."""
    mins = [float("inf")] * 3
    maxs = [float("-inf")] * 3
    found_any = False

    for primitive in mesh.primitives:
        pos_accessor = primitive.attributes.POSITION
        if pos_accessor is None:
            continue
        try:
            vertices = _read_vec3_accessor(gltf, pos_accessor)
        except Exception:
            continue
        for v in vertices:
            found_any = True
            for axis in range(3):
                mins[axis] = min(mins[axis], v[axis])
                maxs[axis] = max(maxs[axis], v[axis])

    if not found_any:
        return None
    return tuple(maxs[axis] - mins[axis] for axis in range(3))


def mesh_is_draped(gltf: "GLTF2", flatness_ratio_threshold: float = _FLATNESS_RATIO_THRESHOLD) -> tuple[bool, str]:
    """Heuristic: does this GLB look like a simulated drape, or flat unsewn panels?

    Returns (looks_draped, reason). looks_draped is False when every mesh in
    the export is suspiciously planar — the exact signature of "arranged but
    never simulated" (Bug 3) combined with "no avatar mesh present" (Bug 4),
    since a real avatar mesh is never planar in any axis.
    """
    if GLTF2 is None:
        return True, "pygltflib not installed — cannot verify, not blocking"

    if not gltf.meshes:
        return False, "GLB has zero meshes"

    per_mesh_ratios: list[float] = []
    per_mesh_details: list[str] = []

    for i, mesh in enumerate(gltf.meshes):
        extents = _mesh_axis_extents(gltf, mesh)
        name = mesh.name or f"mesh_{i}"
        if extents is None:
            per_mesh_details.append(f"{name}: no readable POSITION data")
            continue

        largest = max(extents)
        smallest = min(extents)
        if largest <= 0:
            per_mesh_details.append(f"{name}: degenerate (zero extent)")
            continue

        ratio = smallest / largest
        per_mesh_ratios.append(ratio)
        per_mesh_details.append(f"{name}: extents={tuple(round(e, 2) for e in extents)} flatness_ratio={ratio:.4f}")

    if not per_mesh_ratios:
        return False, "No mesh had readable geometry: " + "; ".join(per_mesh_details)

    all_flat = all(r < flatness_ratio_threshold for r in per_mesh_ratios)
    reason = "; ".join(per_mesh_details)

    if all_flat:
        return False, f"All {len(per_mesh_ratios)} mesh(es) are suspiciously planar (looks unsimulated): {reason}"
    return True, f"At least one mesh has real 3D depth (looks simulated): {reason}"
