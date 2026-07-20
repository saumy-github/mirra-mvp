/**
 * Zod schemas for the REAL backend's response envelopes (website/backend)
 * plus mappers into the UI's domain types (types.ts). schemas.ts stays the
 * mock's contract; this file is the live one. Where the demo-mode backend
 * has no data yet (prices, imagery, rendered assets) the mappers emit
 * explicit placeholders rather than pretending.
 */

import { z } from "zod";
import type {
  AvatarJob,
  AvatarJobState,
  AvatarProfile,
  CaptureSession,
  CaptureSessionState,
  MeasurementField,
  MeasurementKey,
  ProductListPage,
  PublicProduct,
  ShopperAccount,
  SignatureLook,
  TryOnRender,
} from "./types";

// ── Schemas (what the backend actually sends) ─────────────────────────

export const okEnvelope = z.object({ ok: z.boolean() });

const accountSchema = z.object({
  userId: z.string(),
  email: z.string().nullable(),
  name: z.string().nullable(),
  isGuest: z.boolean(),
  emailVerified: z.boolean(),
  consents: z.record(z.string(), z.boolean()),
  createdAt: z.string(),
});

export const accountEnvelope = z.object({ account: accountSchema });
export const sessionEnvelope = z.object({
  account: accountSchema,
  accessToken: z.string(),
  tokenType: z.string(),
  expiresInSeconds: z.number(),
});

export const measurementsEnvelope = z.object({
  measurements: z.record(z.string(), z.unknown()),
});

const garmentSchema = z.object({
  sizeId: z.string(),
  fitType: z.string(),
  clothId: z.string().nullable().optional(),
  clothLabel: z.string().nullable().optional(),
  category: z.string().nullable().optional(),
  measurements: z.record(z.string(), z.number().nullable()),
  updatedAt: z.string().nullable().optional(),
});

export const garmentEnvelope = z.object({ garment: garmentSchema });
export const garmentListEnvelope = z.object({
  items: z.array(garmentSchema),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

const jobSchema = z.object({
  jobId: z.string(),
  state: z.enum(["queued", "processing", "ready", "failed"]),
  stageLabel: z.string(),
  engineMode: z.string(),
  failureReason: z.string().nullable(),
  avatarProfileId: z.string().nullable(),
  createdAt: z.string(),
  completedAt: z.string().nullable(),
});
export const jobEnvelope = z.object({ job: jobSchema });

const profileSchema = z.object({
  avatarProfileId: z.string(),
  gender: z.string().nullable(),
  measurements: z.record(z.string(), z.unknown()),
  bodyShapeType: z.string().nullable(),
  skinToneHex: z.string().nullable(),
  sourceJobId: z.string().nullable(),
  createdAt: z.string(),
  updatedAt: z.string(),
});
export const profileEnvelope = z.object({ profile: profileSchema.nullable() });

const captureSchema = z.object({
  sessionId: z.string(),
  state: z.enum(["created", "paired", "consented", "uploaded", "completed", "cancelled"]),
  manualCode: z.string(),
  photoUploaded: z.boolean(),
  avatarJobId: z.string().nullable(),
  expiresAt: z.string(),
  createdAt: z.string(),
  token: z.string().optional(),
});
export const captureEnvelope = z.object({ session: captureSchema });
export const tokenEnvelope = z.object({ token: z.string() });

export const tryonSessionEnvelope = z.object({
  session: z.object({ sessionId: z.string(), createdAt: z.string() }),
});

const renderSchema = z.object({
  renderId: z.string(),
  sessionId: z.string(),
  state: z.enum(["requested", "rendering", "ready", "failed"]),
  stageLabel: z.string(),
  engineMode: z.string(),
  sizeId: z.string(),
  avatarProfileId: z.string(),
  failureReason: z.string().nullable(),
  createdAt: z.string(),
  completedAt: z.string().nullable(),
  result: z
    .object({
      kind: z.string(),
      demoNotice: z.string().nullable(),
      garment: garmentSchema,
    })
    .nullable(),
});
export const renderEnvelope = z.object({ render: renderSchema });
export const renderListEnvelope = z.object({ items: z.array(renderSchema) });

const lookSchema = z.object({
  lookId: z.string(),
  name: z.string(),
  isDefault: z.boolean(),
  items: z.array(z.object({ sizeId: z.string(), renderId: z.string().nullable() })),
  createdAt: z.string(),
  updatedAt: z.string(),
});
export const lookEnvelope = z.object({ look: lookSchema });
export const lookListEnvelope = z.object({ items: z.array(lookSchema) });

type BackendAccount = z.infer<typeof accountSchema>;
type BackendGarment = z.infer<typeof garmentSchema>;
type BackendJob = z.infer<typeof jobSchema>;
type BackendProfile = z.infer<typeof profileSchema>;
type BackendCapture = z.infer<typeof captureSchema>;
type BackendRender = z.infer<typeof renderSchema>;
type BackendLook = z.infer<typeof lookSchema>;

// ── Measurement key translation ───────────────────────────────────────

export const KEY_TO_FIELD: Record<MeasurementKey, string> = {
  height: "height_cm",
  weight: "weight_kg",
  chest: "chest_circumference_cm",
  waist: "waist_circumference_cm",
  hips: "hip_circumference_cm",
  shoulderWidth: "shoulder_width_cm",
  inseam: "leg_length_cm",
};

const FIELD_META: Record<
  MeasurementKey,
  { label: string; unit: "cm" | "kg"; min: number; max: number; fallback: number }
> = {
  height: { label: "Height", unit: "cm", min: 120, max: 220, fallback: 175 },
  weight: { label: "Weight", unit: "kg", min: 35, max: 180, fallback: 70 },
  chest: { label: "Chest", unit: "cm", min: 70, max: 140, fallback: 96 },
  waist: { label: "Waist", unit: "cm", min: 50, max: 140, fallback: 82 },
  hips: { label: "Hips", unit: "cm", min: 70, max: 150, fallback: 98 },
  shoulderWidth: { label: "Shoulder width", unit: "cm", min: 30, max: 60, fallback: 44 },
  inseam: { label: "Inseam", unit: "cm", min: 55, max: 110, fallback: 80 },
};

function buildMeasurementFields(raw: Record<string, unknown>): MeasurementField[] {
  return (Object.keys(FIELD_META) as MeasurementKey[]).map((key) => {
    const meta = FIELD_META[key];
    const value = raw[KEY_TO_FIELD[key]];
    const present = typeof value === "number";
    return {
      key,
      label: meta.label,
      value: present ? value : meta.fallback,
      unit: meta.unit,
      min: meta.min,
      max: meta.max,
      step: 0.5,
      estimated: !present,
      supported: true,
    };
  });
}

// ── Mappers (backend shape → UI domain types) ─────────────────────────

export function mapAccount(a: BackendAccount): ShopperAccount {
  return {
    shopperId: a.userId,
    email: a.email ?? "",
    displayName: a.name ?? (a.isGuest ? "Guest" : ""),
    emailVerified: a.emailVerified,
    isGuest: a.isGuest,
    createdAt: a.createdAt,
    consents: {
      terms: !!a.consents.terms,
      privacy: !!a.consents.privacy,
      preferenceStorage: !!a.consents.preferenceStorage,
    },
  };
}

export function mapGarment(g: BackendGarment): PublicProduct {
  const sizeChartMeasurements: Record<string, string> = {};
  for (const [field, value] of Object.entries(g.measurements)) {
    if (value !== null) sizeChartMeasurements[field] = `${value} cm`;
  }
  return {
    publicProductId: g.sizeId,
    name: g.clothLabel ?? `T-shirt ${g.sizeId}`,
    subtitle: null,
    category: g.category ?? "tops",
    garmentCategory: "top",
    description: null,
    materialAndCare: null,
    manufacturingInfo: null,
    fitInfo: `Fit: ${g.fitType}`,
    taxNote: null,
    // Step 2 output carries no commerce data yet — placeholder, not real.
    price: 0,
    currency: "INR",
    thumbnailUrl: "",
    publicationStatus: "published",
    tryOnEligible: true,
    sizeChart: [{ size: g.fitType, measurements: sizeChartMeasurements }],
    variants: [
      {
        publicVariantId: g.sizeId,
        colorName: "Default",
        colorSwatch: "#c7c7cc",
        size: g.fitType,
        price: 0,
        currency: "INR",
        inStock: true,
        tryOnEligible: true,
        garmentAssetUrl: null,
        assetStatus: "missing",
      },
    ],
  };
}

export function mapGarmentList(page: {
  items: BackendGarment[];
  total: number;
  limit: number;
  offset: number;
}): ProductListPage {
  const items = page.items.map(mapGarment);
  const next = page.offset + page.items.length;
  return {
    items,
    categories: [...new Set(items.map((i) => i.category))],
    nextCursor: next < page.total ? String(next) : null,
    total: page.total,
  };
}

const JOB_STATE: Record<BackendJob["state"], AvatarJobState> = {
  queued: "queued",
  processing: "generating",
  ready: "ready",
  failed: "failed",
};

export function mapJob(j: BackendJob): AvatarJob {
  return {
    jobId: j.jobId,
    state: JOB_STATE[j.state],
    stageLabel: j.stageLabel,
    startedAt: j.createdAt,
    failureReason: j.failureReason,
    avatarProfileId: j.avatarProfileId,
  };
}

export function mapProfile(p: BackendProfile): AvatarProfile {
  return {
    avatarProfileId: p.avatarProfileId,
    avatarLabel: p.avatarProfileId.slice(-4).toUpperCase(),
    version: 1,
    engineVersion: "demo",
    createdAt: p.createdAt,
    updatedAt: p.updatedAt,
    previewAssetUrl: "",
    measurements: buildMeasurementFields(p.measurements),
    unitsPreference: "metric",
  };
}

/** A profile shaped from a bare measurements doc, for the window between
 * "measurements saved" and "first avatar job completed". */
export function profileFromMeasurements(raw: Record<string, unknown>): AvatarProfile {
  const now = new Date().toISOString();
  return {
    avatarProfileId: "ap_pending",
    avatarLabel: "NEW",
    version: 0,
    engineVersion: "demo",
    createdAt: now,
    updatedAt: now,
    previewAssetUrl: "",
    measurements: buildMeasurementFields(raw),
    unitsPreference: "metric",
  };
}

const CAPTURE_STATE: Record<BackendCapture["state"], CaptureSessionState> = {
  created: "qr_ready",
  paired: "consent_pending",
  consented: "capturing",
  uploaded: "uploaded",
  completed: "completed",
  cancelled: "cancelled",
};

export function mapCapture(s: BackendCapture, fallbackToken?: string): CaptureSession {
  return {
    captureSessionId: s.sessionId,
    state: CAPTURE_STATE[s.state],
    oneTimeToken: s.token ?? fallbackToken ?? "",
    manualCode: s.manualCode,
    expiresAt: s.expiresAt,
    steps: [
      {
        id: "front",
        title: "Front photo",
        guidance: "Stand facing the camera, arms slightly away from your body.",
        silhouette: "front",
        required: true,
      },
    ],
    uploadedStepIds: s.photoUploaded ? ["front"] : [],
    failureReason: null,
    avatarJobId: s.avatarJobId,
  };
}

export function mapRender(r: BackendRender): TryOnRender {
  const ready = r.state === "ready";
  return {
    renderId: r.renderId,
    tryOnSessionId: r.sessionId,
    state: r.state === "failed" ? "failed" : ready ? "ready" : "processing",
    productPublicId: r.sizeId,
    variantPublicId: r.sizeId,
    size: r.result?.garment.fitType ?? null,
    layers: ready
      ? { top: { productPublicId: r.sizeId, variantPublicId: r.sizeId, assetUrl: "" } }
      : {},
    avatarProfileVersion: 1,
    engineVersion: r.engineMode,
    // Demo engine produces no imagery — the UI's demo notice covers this.
    renderedAssetUrl: null,
    generatedAt: r.completedAt ?? r.createdAt,
    failureReason: r.failureReason,
  };
}

export function mapLook(l: BackendLook): SignatureLook {
  return {
    lookId: l.lookId,
    name: l.name,
    isDefault: l.isDefault,
    avatarProfileVersion: 1,
    thumbnailUrl: null,
    layers: l.items.map((item) => ({
      category: "top" as const,
      productPublicId: item.sizeId,
      variantPublicId: item.sizeId,
      assetUrl: "",
      thumbnailUrl: "",
      name: item.sizeId,
    })),
    createdAt: l.createdAt,
    updatedAt: l.updatedAt,
  };
}
