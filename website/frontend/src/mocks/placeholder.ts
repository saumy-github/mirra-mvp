/**
 * Stand-in imagery until real garment/avatar assets exist.
 *
 * These are deliberately *neutral silhouettes on bone*, not photographs and
 * not flat colour blocks: the fitting room reads as a catalogue even before
 * the merchant's photography is wired up, and nothing here pretends to be a
 * rendered try-on result.
 */

export type PlaceholderGarment = "top" | "bottom" | "outerwear" | "footwear" | "accessory";

const GROUND = "#f6f3ed";

/** Garment outlines drawn in a shared 240×300 space. */
const SILHOUETTES: Record<PlaceholderGarment, string> = {
  top:
    "M96 64 L64 78 L44 98 L62 132 L86 120 L86 238 " +
    "Q86 246 94 246 L146 246 Q154 246 154 238 L154 120 " +
    "L178 132 L196 98 L176 78 L144 64 Q120 86 96 64 Z",
  outerwear:
    "M94 62 L60 78 L40 100 L60 136 L84 124 L84 242 " +
    "Q84 250 92 250 L148 250 Q156 250 156 242 L156 124 " +
    "L180 136 L200 100 L180 78 L146 62 Q120 88 94 62 Z",
  bottom:
    "M86 62 L154 62 L162 116 L166 246 Q166 252 160 252 L140 252 " +
    "Q134 252 134 246 L120 152 L106 246 Q106 252 100 252 L80 252 " +
    "Q74 252 74 246 L78 116 Z",
  footwear:
    "M68 184 Q68 172 82 172 L102 172 Q110 172 116 180 L146 208 " +
    "Q164 218 172 226 Q178 232 176 240 L72 240 Q66 240 66 232 Z",
  accessory:
    "M76 108 Q76 96 88 96 L152 96 Q164 96 164 108 L164 200 Q164 212 152 212 L88 212 Q76 212 76 200 Z",
};

/** A hairline that reads on pale garments and disappears on dark ones. */
function outlineFor(hex: string): string {
  return isLight(hex) ? "rgba(23,19,15,0.16)" : "rgba(23,19,15,0.08)";
}

function isLight(hex: string): boolean {
  const value = hex.replace("#", "");
  if (value.length !== 6) return false;
  const r = parseInt(value.slice(0, 2), 16);
  const g = parseInt(value.slice(2, 4), 16);
  const b = parseInt(value.slice(4, 6), 16);
  return (r * 299 + g * 587 + b * 114) / 1000 > 190;
}

function encode(svg: string): string {
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

/** Catalogue thumbnail: one garment, centred, on the studio's bone ground. */
export function garmentThumbDataUri(hex: string, kind: PlaceholderGarment = "top"): string {
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="240" height="300" viewBox="0 0 240 300">` +
    `<rect width="240" height="300" fill="${GROUND}"/>` +
    `<ellipse cx="120" cy="262" rx="62" ry="7" fill="rgba(23,19,15,0.05)"/>` +
    `<path d="${SILHOUETTES[kind]}" fill="${hex}" stroke="${outlineFor(hex)}" stroke-width="1.25"/>` +
    `</svg>`;
  return encode(svg);
}

/**
 * A plain tonal card. Still used where the subject isn't a garment (avatar
 * previews, generic layer stand-ins) — no baked-in label text, because the
 * surrounding UI already names what it is.
 */
export function swatchDataUri(hex: string, label?: string): string {
  const title = label ? `<title>${label}</title>` : "";
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="240" height="300" viewBox="0 0 240 300">` +
    `${title}<rect width="240" height="300" fill="${hex}"/>` +
    `</svg>`;
  return encode(svg);
}
