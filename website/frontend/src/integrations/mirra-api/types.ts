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

// ── Capture / pairing ────────────────────────────────────────────────

export type CaptureSessionState =
  | "created"
  | "qr_ready"
  | "paired"
  | "consent_pending"
  | "capturing"
  | "uploading"
  | "uploaded"
  | "processing"
  | "completed"
  | "expired"
  | "cancelled"
  | "failed";

export interface CaptureStep {
  id: string;
  title: string;
  guidance: string;
  silhouette: "front" | "side" | "back";
  required: boolean;
}

export interface CaptureSession {
  captureSessionId: string;
  state: CaptureSessionState;
  /** One-time token embedded in the QR. Never exposes user IDs. */
  oneTimeToken: string;
  /** Short manual pairing code (accessibility fallback). */
  manualCode: string;
  expiresAt: string;
  steps: CaptureStep[];
  uploadedStepIds: string[];
  failureReason: string | null;
  avatarJobId: string | null;
}

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
