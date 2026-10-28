/** Cache key holding the staleness flag that rides along with the avatar GLB.
 * Kept out of the viewer module so that file only exports components. */
export const AVATAR_GLB_STALE_KEY = ["account", "avatar-glb-stale"];

/** The shopper's face mesh (backend /faces); invalidate it when the face changes. */
export const FACE_GLB_KEY = ["account", "face-glb"] as const;
