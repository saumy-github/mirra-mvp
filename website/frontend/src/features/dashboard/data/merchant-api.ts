/**
 * Typed client for the merchant backend (`/api/v1/merchant/...`).
 *
 * This is the other half of the seam `store.ts` has always described: the
 * dashboard's in-memory `Db` was written so that "swap these four functions
 * for calls to the API and every page above keeps working". This module is
 * what they get swapped for.
 *
 * Every response is validated with Zod before it reaches application code,
 * matching `integrations/mirra-api/client.ts` — a shape drift between backend
 * and dashboard should fail loudly at the boundary, not three components deep.
 */
import { z } from "zod";
import { MirraHttpClient } from "@/integrations/mirra-api/client";

let client: MirraHttpClient | null = null;

export function merchantHttp(): MirraHttpClient {
  if (!client) {
    const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
    client = new MirraHttpClient({ baseUrl });
  }
  return client;
}

// ------------------------------------------------------------------ schemas

const contentSchema = z.object({
  description: z.string().nullable(),
  materialAndCare: z.string().nullable(),
  manufacturingInfo: z.string().nullable(),
  fitInfo: z.string().nullable(),
  taxNote: z.string().nullable(),
  sources: z.record(z.string(), z.string()),
});

const variantSchema = z.object({
  variantId: z.string(),
  sku: z.string(),
  title: z.string(),
  size: z.string(),
  colour: z.string(),
  price: z.number(),
  currency: z.string(),
  inventory: z.number(),
});

export const merchantProductSchema = z.object({
  productId: z.string(),
  source: z.enum(["shopify", "manual", "csv"]),
  /** `unlinked` means identity came from the pasted URL, not from Shopify. */
  linkState: z.enum(["linked", "unlinked"]),
  shopifyId: z.string(),
  handle: z.string(),
  storeDomain: z.string(),
  onlineStoreUrl: z.string(),
  title: z.string(),
  productType: z.string(),
  vendor: z.string(),
  optionName: z.string().nullable(),
  imageUrls: z.array(z.string()),
  content: contentSchema,
  variants: z.array(variantSchema),
  syncStatus: z.string(),
  syncError: z.string(),
  lastSyncedAt: z.string().nullable(),
});

export const productDraftSchema = z.object({
  handle: z.string(),
  suggestedTitle: z.string(),
  storeDomain: z.string(),
  onlineStoreUrl: z.string(),
  shopifyId: z.string(),
});

/**
 * The three outcomes of a lookup. There is deliberately no error outcome for
 * "no store connected" — that case returns `draft`, which is what makes the
 * Identify step passable before a Shopify app exists.
 */
export const lookupResultSchema = z.object({
  outcome: z.enum(["resolved", "matched", "draft"]),
  storeConnected: z.boolean(),
  product: merchantProductSchema.optional(),
  draft: productDraftSchema.optional(),
  guidance: z.string().optional(),
});

const captureAssetSchema = z.object({
  assetId: z.string(),
  view: z.string(),
  filename: z.string(),
  contentType: z.string(),
  bytes: z.number(),
  sha256: z.string(),
  width: z.number().nullable(),
  height: z.number().nullable(),
  accepted: z.boolean(),
  rejectedReason: z.string(),
  sampleSize: z.string(),
  uploadedAt: z.string(),
});

const issueSchema = z.object({
  area: z.string(),
  label: z.string(),
  detail: z.string(),
});

export const merchantGarmentSchema = z.object({
  garmentId: z.string(),
  productId: z.string(),
  optionValue: z.string(),
  canonicalTitle: z.string(),
  merchantTitle: z.string(),
  title: z.string(),
  category: z.string(),
  stage: z.string(),
  revision: z.number(),
  capture: z.object({
    method: z.string(),
    referenceSize: z.string(),
    assets: z.array(captureAssetSchema),
    cadAsset: captureAssetSchema.nullable(),
    issues: z.array(z.string()),
  }),
  material: z.object({
    composition: z.array(z.object({ material: z.string(), pct: z.number() })),
    confirmed: z.boolean(),
    stretch: z.string(),
    drape: z.string(),
    thickness: z.string(),
    attributesSuggested: z.boolean(),
  }),
  sizing: z.object({
    fitType: z.string(),
    silhouette: z.string(),
    fitNotes: z.string(),
    source: z.string(),
    variantMappingConfirmed: z.boolean(),
    rows: z.array(z.record(z.string(), z.unknown())),
  }),
  content: contentSchema,
  pipeline: z.object({
    state: z.string(),
    clothId: z.string(),
    sizeIds: z.array(z.string()),
    ingestedRuns: z.record(z.string(), z.string()),
    previewId: z.string(),
    failureReason: z.string(),
    /** False when the pipeline cannot draft this garment at all. */
    supported: z.boolean(),
    unsupportedReason: z.string(),
  }),
  publication: z.object({
    published: z.boolean(),
    tryOnEnabled: z.boolean(),
    soldOutPolicy: z.string(),
    publishedAt: z.string().nullable(),
  }),
  qaFindings: z.array(
    z.object({
      findingId: z.string(),
      severity: z.string(),
      area: z.string(),
      detail: z.string(),
      raisedAt: z.string(),
      resolved: z.boolean(),
    }),
  ),
  approved: z
    .object({ revision: z.number(), approvedAt: z.string(), previewId: z.string() })
    .nullable(),
  draftAhead: z.boolean(),
  readiness: z.object({
    blocking: z.array(issueSchema),
    advisory: z.array(issueSchema),
    ready: z.boolean(),
  }),
  updatedAt: z.string(),
});

export const ingestionRunSchema = z.object({
  runId: z.string(),
  garmentId: z.string(),
  clothId: z.string(),
  sizeId: z.string(),
  state: z.enum(["queued", "running", "succeeded", "failed"]),
  productRunId: z.string(),
  panelCount: z.number(),
  failureReason: z.string(),
  createdAt: z.string(),
  completedAt: z.string().nullable(),
});

export const previewSchema = z.object({
  previewId: z.string(),
  garmentId: z.string(),
  clothId: z.string(),
  sizeId: z.string(),
  revision: z.number(),
  state: z.enum(["requested", "rendering", "ready", "failed"]),
  /** Never inferred from state — true only when a file actually exists. */
  hasModel: z.boolean(),
  glbUrl: z.string().nullable(),
  failureReason: z.string().nullable(),
  cloRunId: z.string().nullable(),
  createdAt: z.string(),
  completedAt: z.string().nullable(),
});

export const workspaceSchema = z.object({
  tenantId: z.string(),
  slug: z.string(),
  name: z.string(),
  storeUrl: z.string(),
  status: z.string(),
  shopify: z.object({
    connected: z.boolean(),
    storeDomain: z.string(),
    customDomain: z.string(),
    scopes: z.array(z.string()),
    connectedAt: z.string().nullable(),
    lastSyncAt: z.string().nullable(),
    lastSyncError: z.string(),
  }),
});

export type MerchantProduct = z.infer<typeof merchantProductSchema>;
export type ProductDraft = z.infer<typeof productDraftSchema>;
export type LookupResult = z.infer<typeof lookupResultSchema>;
export type MerchantGarment = z.infer<typeof merchantGarmentSchema>;
export type IngestionRun = z.infer<typeof ingestionRunSchema>;
export type Preview = z.infer<typeof previewSchema>;
export type Workspace = z.infer<typeof workspaceSchema>;

const garmentEnvelope = z.object({ garment: merchantGarmentSchema });
const productEnvelope = z.object({ product: merchantProductSchema });
const previewEnvelope = z.object({ preview: previewSchema });

// -------------------------------------------------------------------- calls

export const merchantApi = {
  // --- workspace ---
  listWorkspaces: () =>
    merchantHttp()
      .request("GET", "/merchant/workspaces", z.object({ items: z.array(workspaceSchema) }))
      .then((r) => r.items),

  getWorkspace: (tenantId: string) =>
    merchantHttp()
      .request("GET", `/merchant/${tenantId}`, z.object({ workspace: workspaceSchema }))
      .then((r) => r.workspace),

  connectShopify: (tenantId: string, body: { storeDomain: string; accessToken: string; scopes?: string[] }) =>
    merchantHttp()
      .request("POST", `/merchant/${tenantId}/shopify/connect`, z.object({ workspace: workspaceSchema }), body)
      .then((r) => r.workspace),

  reconcile: (tenantId: string) =>
    merchantHttp().request(
      "POST",
      `/merchant/${tenantId}/shopify/reconcile`,
      z.object({
        linked: z.array(z.string()),
        unmatched: z.array(z.string()),
        storeConnected: z.boolean().optional(),
        store_connected: z.boolean().optional(),
      }),
      {},
    ),

  // --- products ---
  /** Resolve a pasted URL / handle / GID. Never a dead end — see LookupResult. */
  lookupProduct: (tenantId: string, input: string) =>
    merchantHttp().request("POST", `/merchant/${tenantId}/products/lookup`, lookupResultSchema, {
      input,
    }),

  listProducts: (tenantId: string) =>
    merchantHttp()
      .request("GET", `/merchant/${tenantId}/products`, z.object({ items: z.array(merchantProductSchema) }))
      .then((r) => r.items),

  createManualProduct: (
    tenantId: string,
    body: {
      handle: string;
      title: string;
      onlineStoreUrl?: string;
      storeDomain?: string;
      productType?: string;
      vendor?: string;
      optionName?: string | null;
      description?: string | null;
      variants: {
        sku?: string;
        title?: string;
        size?: string;
        colour?: string;
        price?: number;
        currency?: string;
        inventory?: number;
      }[];
    },
  ) =>
    merchantHttp()
      .request("POST", `/merchant/${tenantId}/products`, productEnvelope, body)
      .then((r) => r.product),

  importProductsCsv: (tenantId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return merchantHttp().postMultipart(
      `/merchant/${tenantId}/products/import`,
      z.object({
        created: z.array(z.string()),
        skipped: z.array(z.string()),
        failed: z.array(z.object({ handle: z.string(), reason: z.string() })),
      }),
      form,
    );
  },

  updateProductContent: (
    tenantId: string,
    productId: string,
    changes: Partial<Record<"description" | "materialAndCare" | "manufacturingInfo" | "fitInfo" | "taxNote", string | null>>,
  ) =>
    merchantHttp()
      .request("PATCH", `/merchant/${tenantId}/products/${productId}/content`, productEnvelope, changes)
      .then((r) => r.product),

  // --- garments ---
  listGarments: (tenantId: string) =>
    merchantHttp()
      .request("GET", `/merchant/${tenantId}/garments`, z.object({ items: z.array(merchantGarmentSchema) }))
      .then((r) => r.items),

  getGarment: (tenantId: string, garmentId: string) =>
    merchantHttp()
      .request("GET", `/merchant/${tenantId}/garments/${garmentId}`, garmentEnvelope)
      .then((r) => r.garment),

  createGarment: (
    tenantId: string,
    body: { productId: string; optionValue?: string; merchantTitle?: string; category?: string },
  ) =>
    merchantHttp()
      .request("POST", `/merchant/${tenantId}/garments`, garmentEnvelope, body)
      .then((r) => r.garment),

  setReferenceSize: (tenantId: string, garmentId: string, size: string) =>
    merchantHttp()
      .request("PUT", `/merchant/${tenantId}/garments/${garmentId}/reference-size`, garmentEnvelope, { size })
      .then((r) => r.garment),

  // --- capture ---
  /** Upload one real file. The browser sets the multipart boundary itself. */
  uploadCapture: (tenantId: string, garmentId: string, view: string, file: File, isCad = false) => {
    const form = new FormData();
    form.append("file", file);
    form.append("view", view);
    form.append("is_cad", String(isCad));
    return merchantHttp()
      .postMultipart(`/merchant/${tenantId}/garments/${garmentId}/capture`, garmentEnvelope, form)
      .then((r) => r.garment);
  },

  captureFileUrl: (tenantId: string, garmentId: string, assetId: string) =>
    `/merchant/${tenantId}/garments/${garmentId}/capture/${assetId}`,

  /** Authenticated binary fetch — an <img src> cannot send the bearer token. */
  fetchCaptureBlob: (tenantId: string, garmentId: string, assetId: string) =>
    merchantHttp().getBlob(`/merchant/${tenantId}/garments/${garmentId}/capture/${assetId}`),

  rejectCapture: (tenantId: string, garmentId: string, assetId: string, reason: string) =>
    merchantHttp()
      .request(
        "POST",
        `/merchant/${tenantId}/garments/${garmentId}/capture/${assetId}/reject`,
        garmentEnvelope,
        { reason },
      )
      .then((r) => r.garment),

  // --- material / sizing / content ---
  setMaterial: (
    tenantId: string,
    garmentId: string,
    body: {
      composition: { material: string; pct: number }[];
      confirmed: boolean;
      stretch?: string;
      drape?: string;
      thickness?: string;
    },
  ) =>
    merchantHttp()
      .request("PUT", `/merchant/${tenantId}/garments/${garmentId}/material`, garmentEnvelope, body)
      .then((r) => r.garment),

  setSizing: (
    tenantId: string,
    garmentId: string,
    body: {
      rows: Record<string, unknown>[];
      fitType?: string;
      silhouette?: string;
      fitNotes?: string;
      source?: string;
    },
  ) =>
    merchantHttp()
      .request("PUT", `/merchant/${tenantId}/garments/${garmentId}/sizing`, garmentEnvelope, body)
      .then((r) => r.garment),

  confirmVariantMapping: (tenantId: string, garmentId: string, confirmed: boolean) =>
    merchantHttp()
      .request("PUT", `/merchant/${tenantId}/garments/${garmentId}/variant-mapping`, garmentEnvelope, {
        confirmed,
      })
      .then((r) => r.garment),

  setGarmentContent: (
    tenantId: string,
    garmentId: string,
    changes: Partial<Record<"description" | "materialAndCare" | "manufacturingInfo" | "fitInfo" | "taxNote", string | null>>,
  ) =>
    merchantHttp()
      .request("PATCH", `/merchant/${tenantId}/garments/${garmentId}/content`, garmentEnvelope, changes)
      .then((r) => r.garment),

  // --- lifecycle ---
  setStage: (tenantId: string, garmentId: string, stage: string) =>
    merchantHttp()
      .request("PUT", `/merchant/${tenantId}/garments/${garmentId}/stage`, garmentEnvelope, { stage })
      .then((r) => r.garment),

  addQaFinding: (
    tenantId: string,
    garmentId: string,
    body: { severity: string; area: string; detail: string },
  ) =>
    merchantHttp()
      .request("POST", `/merchant/${tenantId}/garments/${garmentId}/qa/findings`, garmentEnvelope, body)
      .then((r) => r.garment),

  approve: (tenantId: string, garmentId: string) =>
    merchantHttp()
      .request("POST", `/merchant/${tenantId}/garments/${garmentId}/qa/approve`, garmentEnvelope, {})
      .then((r) => r.garment),

  setPublication: (tenantId: string, garmentId: string, published: boolean, tryOnEnabled?: boolean) =>
    merchantHttp()
      .request("PUT", `/merchant/${tenantId}/garments/${garmentId}/publication`, garmentEnvelope, {
        published,
        tryOnEnabled,
      })
      .then((r) => r.garment),

  // --- pipeline ---
  /** Capture → Product Ingestion. Queues one Step 2 run per size. */
  submitIngestion: (tenantId: string, garmentId: string) =>
    merchantHttp()
      .request(
        "POST",
        `/merchant/${tenantId}/garments/${garmentId}/ingestion`,
        z.object({ runs: z.array(ingestionRunSchema) }),
        {},
      )
      .then((r) => r.runs),

  listRuns: (tenantId: string, garmentId: string) =>
    merchantHttp()
      .request(
        "GET",
        `/merchant/${tenantId}/garments/${garmentId}/ingestion`,
        z.object({ items: z.array(ingestionRunSchema) }),
      )
      .then((r) => r.items),

  /** Product Ingestion → VTO, on the reference avatar. */
  requestPreview: (tenantId: string, garmentId: string, sizeId?: string) =>
    merchantHttp()
      .request("POST", `/merchant/${tenantId}/garments/${garmentId}/previews`, previewEnvelope, {
        sizeId: sizeId ?? null,
      })
      .then((r) => r.preview),

  listPreviews: (tenantId: string, garmentId: string) =>
    merchantHttp()
      .request(
        "GET",
        `/merchant/${tenantId}/garments/${garmentId}/previews`,
        z.object({ items: z.array(previewSchema) }),
      )
      .then((r) => r.items),

  getPreview: (tenantId: string, previewId: string) =>
    merchantHttp()
      .request("GET", `/merchant/${tenantId}/previews/${previewId}`, previewEnvelope)
      .then((r) => r.preview),

  fetchPreviewGlb: (tenantId: string, previewId: string) =>
    merchantHttp().getBlob(`/merchant/${tenantId}/previews/${previewId}/glb`),

  // --- shopper view ---
  /** Exactly what the studio renders. `preview` adds approved-but-unpublished. */
  publicCatalogue: (tenantId: string, preview = false) =>
    merchantHttp().request(
      "GET",
      `/merchant/${tenantId}/catalogue?preview=${preview ? "true" : "false"}`,
      z.object({ items: z.array(z.record(z.string(), z.unknown())) }),
    ),
};
