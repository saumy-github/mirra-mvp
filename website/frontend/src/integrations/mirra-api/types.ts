/**
 * Shared Mirra domain types — the contract between the frontend and the
 * backend (see website/backend-structure-plan.md for the service that will
 * implement this). Ported from user-side's Shopper Runtime with tenant/
 * merchant/Shopify concepts removed: we own our own catalogue directly.
 */

// ── Catalogue ─────────────────────────────────────────────────────────

export type PublicationStatus = "published" | "paused" | "deleted";
export type AssetStatus = "ready" | "processing" | "failed" | "missing";
export type GarmentCategory = "top" | "bottom" | "outerwear" | "footwear" | "accessory";

export interface ProductVariant {
  publicVariantId: string;
  colorName: string;
  colorSwatch: string;
  size: string;
  price: number;
  currency: string;
  inStock: boolean;
  tryOnEligible: boolean;
  /** Rendered garment asset for this variant (colour-level). */
  garmentAssetUrl: string | null;
  assetStatus: AssetStatus;
}

export interface SizeChartRow {
  size: string;
  measurements: Record<string, string>;
}

export interface PublicProduct {
  publicProductId: string;
  name: string;
  subtitle: string | null;
  category: string;
  garmentCategory: GarmentCategory;
  description: string | null;
  materialAndCare: string | null;
  manufacturingInfo: string | null;
  fitInfo: string | null;
  taxNote: string | null;
  price: number;
  currency: string;
  thumbnailUrl: string;
  publicationStatus: PublicationStatus;
  tryOnEligible: boolean;
  sizeChart: SizeChartRow[] | null;
  variants: ProductVariant[];
}

export interface ProductListPage {
  items: PublicProduct[];
  categories: string[];
  nextCursor: string | null;
  total: number;
}

// ── Account ───────────────────────────────────────────────────────────

export interface ShopperAccount {
  shopperId: string;
  email: string;
  displayName: string;
  emailVerified: boolean;
  isGuest: boolean;
  createdAt: string;
  consents: {
    terms: boolean;
    privacy: boolean;
    preferenceStorage: boolean;
  };
}

export type MeasurementKey =
  "height" | "weight" | "chest" | "waist" | "hips" | "shoulderWidth" | "inseam";

export interface MeasurementField {
  key: MeasurementKey;
  label: string;
  value: number;
  unit: "cm" | "kg";
  min: number;
  max: number;
  step: number;
  estimated: boolean;
  supported: boolean;
}

export interface AvatarProfile {
  avatarProfileId: string;
  /** Short human-visible identifier, e.g. "09-V3". */
  avatarLabel: string;
  version: number;
  engineVersion: string;
  createdAt: string;
  updatedAt: string;
  previewAssetUrl: string;
  measurements: MeasurementField[];
  unitsPreference: "metric" | "imperial";
}

export interface AvatarGlbResult {
  blob: Blob;
  /** From X-Avatar-Measurements-Stale; null when the backend can't tell. */
  isStale: boolean | null;
}

// ── Photo measurement ────────────────────────────────────────────────
// Front + side photo → measurements the shopper reviews before saving.

export type PhotoMeasurementState = "queued" | "processing" | "ready" | "failed" | "applied";

/** Backend user_measurements field names (height_cm, chest_circumference_cm, …). */
export type PhotoMeasurementField =
  | "height_cm"
  | "weight_kg"
  | "shoulder_width_cm"
  | "chest_circumference_cm"
  | "waist_circumference_cm"
  | "hip_circumference_cm"
  | "leg_length_cm"
  | "bust_circumference_cm"
  | "under_bust_circumference_cm";

export interface PhotoMeasurement {
  captureId: string;
  state: PhotoMeasurementState;
  stageLabel: string;
  heightCm: number;
  weightKg: number | null;
  gender: "male" | "female";
  /** Ready-to-save values, keyed by backend field name; null until ready. */
  profile: Partial<Record<PhotoMeasurementField, number | null>> | null;
  bodyShapeType: string | null;
  skinToneHex: string | null;
  /** Capture problems to fix ("arm touches torso…"); numbers still returned. */
  warnings: string[];
  failureReason: string | null;
  createdAt: string;
  completedAt: string | null;
}

/** Desktop → phone QR hand-off. `token` is only present right after creation. */
export interface PhotoPairing {
  pairingId: string;
  token?: string;
  expiresAt: string;
  active: boolean;
  captureId: string | null;
  buildAvatar: boolean;
  measurementMethod: "photos" | "manual";
  phoneStage: "waiting" | "capturing" | "uploading" | "complete";
  captureComplete: boolean;
  faceSkipped: boolean;
}

export interface AvatarSetup {
  pairing: PhotoPairing;
  capture: PhotoMeasurement | null;
  face: FaceCapture | null;
  job: AvatarJob | null;
  state:
    | "waiting"
    | "capturing"
    | "syncing"
    | "measuring"
    | "building"
    | "review"
    | "updating"
    | "complete"
    | "failed";
  measurements: Partial<Record<PhotoMeasurementField, number>>;
  failureReason: string | null;
}

/** What the signed-out phone sees through a pairing link. */
export interface CaptureLink {
  expiresAt: string;
  gender?: "male" | "female";
  heightCm?: number | null;
  weightKg?: number | null;
  buildAvatar: boolean;
  measurementMethod: "photos" | "manual";
  captureId: string | null;
  faceId: string | null;
  complete: boolean;
}

/** Progress only — the numbers are reviewed on the signed-in screen. */
export interface CaptureLinkProgress {
  captureId: string;
  state: PhotoMeasurementState;
  stageLabel: string;
  warnings: string[];
  failureReason: string | null;
}

export interface PhotoCaptureInput {
  front: File;
  side: File;
  heightCm: number;
  gender: "male" | "female";
  weightKg?: number | null;
  shoeSoleCm?: number;
}

// ── Face ─────────────────────────────────────────────────────────────
// 1-3 face photos → a textured face mesh attached to the avatar's head.

export type FaceState = "queued" | "processing" | "ready" | "failed";

export interface FaceCapture {
  faceId: string;
  state: FaceState;
  stageLabel: string;
  hasModel: boolean;
  views: string[];
  skinToneHex: string | null;
  warnings: string[];
  failureReason: string | null;
  createdAt: string;
  completedAt: string | null;
}

export interface FacePhotosInput {
  front: File;
  /** Head turned ~45° to the subject's left / right. Optional, improve the sides. */
  left?: File | null;
  right?: File | null;
}

/** Face progress as the signed-out phone sees it through the QR link. */
export type FaceLinkProgress = Pick<
  FaceCapture,
  "faceId" | "state" | "stageLabel" | "warnings" | "failureReason"
>;

// ── Avatar job ───────────────────────────────────────────────────────
// This is the CLO3D integration seam — see backend-structure-plan.md.

export type AvatarJobState =
  | "queued"
  | "validating"
  | "estimating"
  | "generating"
  | "optimising"
  | "ready"
  | "failed"
  | "cancelled";

export interface AvatarJob {
  jobId: string;
  state: AvatarJobState;
  stageLabel: string;
  startedAt: string;
  failureReason: string | null;
  avatarProfileId: string | null;
}

// ── Try-on ────────────────────────────────────────────────────────────
// Also routes through the CLO3D seam eventually.

export type TryOnState =
  | "idle"
  | "requesting"
  | "processing"
  | "ready"
  | "cached"
  | "restoring"
  | "unsupported"
  | "failed";

export interface TryOnRender {
  renderId: string;
  tryOnSessionId: string;
  state: Extract<TryOnState, "processing" | "ready" | "failed" | "unsupported">;
  productPublicId: string;
  variantPublicId: string;
  size: string | null;
  /** Garment layers composing this render, keyed by category. */
  layers: Partial<
    Record<GarmentCategory, { productPublicId: string; variantPublicId: string; assetUrl: string }>
  >;
  avatarProfileVersion: number;
  engineVersion: string;
  renderedAssetUrl: string | null;
  generatedAt: string;
  failureReason: string | null;
}

export interface TryOnSession {
  tryOnSessionId: string;
  createdAt: string;
}

// ── Signature Looks ───────────────────────────────────────────────────

export interface SignatureLookLayer {
  category: GarmentCategory;
  productPublicId: string;
  variantPublicId: string;
  assetUrl: string;
  thumbnailUrl: string;
  name: string;
}

export interface SignatureLook {
  lookId: string;
  name: string;
  isDefault: boolean;
  avatarProfileVersion: number;
  thumbnailUrl: string | null;
  layers: SignatureLookLayer[];
  createdAt: string;
  updatedAt: string;
}

// ── Analytics ─────────────────────────────────────────────────────────

export interface AnalyticsEvent {
  event: string;
  productPublicId?: string | null;
  variantPublicId?: string | null;
  sessionId?: string | null;
  authenticated: boolean;
  engineVersion?: string | null;
  appVersion: string;
  environment: string;
  occurredAt: string;
  properties?: Record<string, string | number | boolean | null>;
}
