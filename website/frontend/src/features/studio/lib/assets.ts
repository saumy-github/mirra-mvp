/**
 * Which assets are real enough to put on the stage.
 *
 * Until the CLO3D pipeline is wired in, the runtime hands back inline SVG
 * stand-ins for avatar previews and garment layers. Those are fine in a
 * catalogue thumbnail — they read as a neutral silhouette — but stacking them
 * on the figure would fake a try-on result that hasn't happened.
 *
 * So the stage asks this first: only genuine, backend-produced assets get
 * composited; anything else leaves the render slot in its empty, elegant
 * state. When the pipeline starts returning real URLs, this returns true and
 * the slot fills in with no other change.
 */
export function isRenderableAsset(url: string | null | undefined): url is string {
  if (!url) return false;
  return !url.startsWith("data:image/svg+xml");
}
