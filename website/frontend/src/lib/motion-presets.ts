/**
 * Shared `motion` spring presets. Each component that needs its own distinct
 * "feel" (RAIL_SPRING, HANGER_SPRING, FIGURE_SPRING, etc.) still defines that
 * locally — these three are the ones that turned out byte-identical across
 * multiple files, so they live here instead of being copy-pasted.
 */

export const MATERIAL_SPRING = {
  type: "spring" as const,
  stiffness: 420,
  damping: 41,
  mass: 1,
};

export const CONTROL_SPRING = {
  type: "spring" as const,
  stiffness: 520,
  damping: 38,
  mass: 0.7,
};

export const PANEL_SPRING = {
  type: "spring" as const,
  stiffness: 420,
  damping: 40,
  mass: 0.9,
};
