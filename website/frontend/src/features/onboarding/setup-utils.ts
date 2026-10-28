import type { AvatarSetup, PhotoMeasurementField } from "@/integrations/mirra-api";

export const REVIEW_FIELDS: {
  key: PhotoMeasurementField;
  label: string;
  min: number;
  max: number;
  femaleOnly?: boolean;
}[] = [
  { key: "height_cm", label: "Height", min: 120, max: 230 },
  { key: "weight_kg", label: "Weight", min: 30, max: 250 },
  { key: "shoulder_width_cm", label: "Shoulder width", min: 20, max: 80 },
  { key: "chest_circumference_cm", label: "Chest", min: 40, max: 200 },
  { key: "bust_circumference_cm", label: "Bust", min: 40, max: 200, femaleOnly: true },
  { key: "under_bust_circumference_cm", label: "Under-bust", min: 40, max: 200, femaleOnly: true },
  { key: "waist_circumference_cm", label: "Waist", min: 40, max: 200 },
  { key: "hip_circumference_cm", label: "Hips", min: 40, max: 200 },
  { key: "leg_length_cm", label: "Inseam", min: 40, max: 130 },
];

export function captureUrl(token: string, origin: string, configuredOrigin?: string): string {
  const target = new URL(
    `/capture/${encodeURIComponent(token)}`,
    configuredOrigin?.trim() || origin,
  );
  if (!/^https?:$/.test(target.protocol))
    throw new Error("Use an HTTPS address for the capture link.");
  return target.href;
}

/**
 * The server rotates a pairing's token every time a link is requested, which
 * silently breaks a phone that already scanned the previous code. Keep the
 * issued link on this browser and reuse it until shortly before it expires.
 */
const LINK_REUSE_MARGIN_MS = 60_000;
const linkKey = (pairingId: string) => `mirra-capture-link-${pairingId}`;

export interface StoredCaptureLink {
  token: string;
  expiresAt: string;
}

export function storedCaptureLink(
  pairingId: string,
  now = Date.now(),
  storage: Pick<Storage, "getItem"> | undefined = safeStorage(),
): StoredCaptureLink | null {
  try {
    const raw = storage?.getItem(linkKey(pairingId));
    if (!raw) return null;
    const link = JSON.parse(raw) as Partial<StoredCaptureLink>;
    if (typeof link.token !== "string" || typeof link.expiresAt !== "string") return null;
    return Date.parse(link.expiresAt) - now > LINK_REUSE_MARGIN_MS
      ? { token: link.token, expiresAt: link.expiresAt }
      : null;
  } catch {
    return null;
  }
}

export function rememberCaptureLink(
  pairingId: string,
  link: { token?: string; expiresAt: string },
  storage: Pick<Storage, "setItem"> | undefined = safeStorage(),
): void {
  if (!link.token) return;
  try {
    storage?.setItem(
      linkKey(pairingId),
      JSON.stringify({ token: link.token, expiresAt: link.expiresAt }),
    );
  } catch {
    // Storage unavailable — the link is simply re-issued after a reload.
  }
}

function safeStorage(): Storage | undefined {
  try {
    return window.localStorage;
  } catch {
    return undefined;
  }
}

/** How long the phone can stay on one step before the computer offers help. */
export const PHONE_QUIET_MS = 150_000;

export function setupStep(state: AvatarSetup["state"]): number {
  return ["review", "updating", "complete"].includes(state)
    ? 3
    : ["measuring", "building"].includes(state)
      ? 2
      : 1;
}
