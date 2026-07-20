/** Solid-colour placeholder swatch as a data URI — stand-in until real garment/avatar assets exist. */
export function swatchDataUri(hex: string, label?: string): string {
  const safe = label
    ? `<text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="14" fill="rgba(255,255,255,0.75)">${label}</text>`
    : "";
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="240" height="300"><rect width="240" height="300" rx="16" fill="${hex}"/>${safe}</svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}
