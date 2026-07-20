import { z } from "zod";

/**
 * Zod runtime validation for every payload crossing the API boundary.
 * The typed client refuses to hand unvalidated JSON to the UI.
 */

export const garmentCategorySchema = z.enum([
  "top",
  "bottom",
  "outerwear",
  "footwear",
  "accessory",
]);

export const assetStatusSchema = z.enum(["ready", "processing", "failed", "missing"]);

export const productVariantSchema = z.object({
  publicVariantId: z.string(),
  colorName: z.string(),
  colorSwatch: z.string(),
  size: z.string(),
  price: z.number(),
  currency: z.string(),
  inStock: z.boolean(),
  tryOnEligible: z.boolean(),
  garmentAssetUrl: z.string().nullable(),
  assetStatus: assetStatusSchema,
});

export const sizeChartRowSchema = z.object({
  size: z.string(),
  measurements: z.record(z.string(), z.string()),
});

export const publicProductSchema = z.object({
  publicProductId: z.string(),
  name: z.string(),
  subtitle: z.string().nullable(),
  category: z.string(),
  garmentCategory: garmentCategorySchema,
  description: z.string().nullable(),
  materialAndCare: z.string().nullable(),
  manufacturingInfo: z.string().nullable(),
  fitInfo: z.string().nullable(),
  taxNote: z.string().nullable(),
  price: z.number(),
  currency: z.string(),
  thumbnailUrl: z.string(),
  publicationStatus: z.enum(["published", "paused", "deleted"]),
  tryOnEligible: z.boolean(),
  sizeChart: z.array(sizeChartRowSchema).nullable(),
  variants: z.array(productVariantSchema),
});

export const productListPageSchema = z.object({
  items: z.array(publicProductSchema),
  categories: z.array(z.string()),
  nextCursor: z.string().nullable(),
  total: z.number(),
});

export const shopperAccountSchema = z.object({
  shopperId: z.string(),
  email: z.string(),
  displayName: z.string(),
  emailVerified: z.boolean(),
  isGuest: z.boolean(),
  createdAt: z.string(),
  consents: z.object({
    terms: z.boolean(),
    privacy: z.boolean(),
    preferenceStorage: z.boolean(),
  }),
});

export const measurementFieldSchema = z.object({
  key: z.enum(["height", "weight", "chest", "waist", "hips", "shoulderWidth", "inseam"]),
  label: z.string(),
  value: z.number(),
  unit: z.enum(["cm", "kg"]),
  min: z.number(),
  max: z.number(),
  step: z.number(),
  estimated: z.boolean(),
  supported: z.boolean(),
});

export const avatarProfileSchema = z.object({
  avatarProfileId: z.string(),
  avatarLabel: z.string(),
  version: z.number(),
  engineVersion: z.string(),
  createdAt: z.string(),
  updatedAt: z.string(),
  previewAssetUrl: z.string(),
  measurements: z.array(measurementFieldSchema),
  unitsPreference: z.enum(["metric", "imperial"]),
});

export const captureSessionStateSchema = z.enum([
  "created",
  "qr_ready",
  "paired",
  "consent_pending",
  "capturing",
  "uploading",
  "uploaded",
  "processing",
  "completed",
  "expired",
  "cancelled",
  "failed",
]);

export const captureStepSchema = z.object({
  id: z.string(),
  title: z.string(),
  guidance: z.string(),
  silhouette: z.enum(["front", "side", "back"]),
  required: z.boolean(),
});

export const captureSessionSchema = z.object({
  captureSessionId: z.string(),
  state: captureSessionStateSchema,
  oneTimeToken: z.string(),
  manualCode: z.string(),
  expiresAt: z.string(),
  steps: z.array(captureStepSchema),
  uploadedStepIds: z.array(z.string()),
  failureReason: z.string().nullable(),
  avatarJobId: z.string().nullable(),
});

export const avatarJobSchema = z.object({
  jobId: z.string(),
  state: z.enum([
    "queued",
    "validating",
    "estimating",
    "generating",
    "optimising",
    "ready",
    "failed",
    "cancelled",
  ]),
  stageLabel: z.string(),
  startedAt: z.string(),
  failureReason: z.string().nullable(),
  avatarProfileId: z.string().nullable(),
});

export const tryOnRenderSchema = z.object({
  renderId: z.string(),
  tryOnSessionId: z.string(),
  state: z.enum(["processing", "ready", "failed", "unsupported"]),
  productPublicId: z.string(),
  variantPublicId: z.string(),
  size: z.string().nullable(),
  layers: z.record(
    z.string(),
    z.object({
      productPublicId: z.string(),
      variantPublicId: z.string(),
      assetUrl: z.string(),
    }),
  ),
  avatarProfileVersion: z.number(),
  engineVersion: z.string(),
  renderedAssetUrl: z.string().nullable(),
  generatedAt: z.string(),
  failureReason: z.string().nullable(),
});

export const tryOnSessionSchema = z.object({
  tryOnSessionId: z.string(),
  createdAt: z.string(),
});

export const signatureLookLayerSchema = z.object({
  category: garmentCategorySchema,
  productPublicId: z.string(),
  variantPublicId: z.string(),
  assetUrl: z.string(),
  thumbnailUrl: z.string(),
  name: z.string(),
});

export const signatureLookSchema = z.object({
  lookId: z.string(),
  name: z.string(),
  isDefault: z.boolean(),
  avatarProfileVersion: z.number(),
  thumbnailUrl: z.string().nullable(),
  layers: z.array(signatureLookLayerSchema),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export const apiErrorBodySchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
  }),
});
