// Mirra domain model — the control-plane system of record.
// In production this maps to Postgres tables (see docs/02-data-model.md);
// the prototype persists the same shapes to a local JSON store.

export type InternalRole = "mirra_admin" | "mirra_sales" | "mirra_support";
export type BrandRole =
  | "brand_owner"
  | "brand_merchandiser"
  | "brand_finance"
  | "brand_viewer";
export type Role = InternalRole | BrandRole;

export interface User {
  id: string;
  name: string;
  email: string;
  internalRole?: InternalRole; // set only for Mirra staff
}

export interface Membership {
  userId: string;
  tenantId: string;
  role: BrandRole;
  /** `invited` seats count against the plan but cannot sign in yet. */
  status: MembershipStatus;
  invitedAt?: string;
  invitedBy?: string;
  /** Invitations expire; an expired seat is reclaimable. */
  expiresAt?: string;
}

export type MembershipStatus = "active" | "invited" | "expired";

// ---------------------------------------------------------------- lifecycle

export type TenantStatus =
  | "lead"
  | "onboarding"
  | "trial"
  | "active"
  | "past_due"
  | "suspended"
  | "cancelled"
  | "archived";

export type LaunchStatus = "not_launched" | "preview" | "live" | "paused";

export type PlanId = "pilot" | "boutique" | "atelier" | "enterprise";

export interface Plan {
  id: PlanId;
  name: string;
  monthlyUsd: number | null; // null = contact sales
  annualUsd: number | null;
  skuLimit: number;
  seatLimit: number;
  supportTier: "standard" | "priority" | "dedicated";
  features: string[];
  trialDays: number;
}

export type AddOnId =
  | "extra_sku_pack"
  | "premium_support"
  | "custom_domain"
  | "analytics_plus";

export interface OnboardingState {
  storeVerified: boolean;
  storeUrlConfirmed: boolean;
  shopifyConnected: boolean;
  teamInvited: boolean;
  planChosen: boolean;
  termsAccepted: boolean;
  billingEntered: boolean;
  activated: boolean;
  checklistReviewed: boolean;
}

export interface TenantBilling {
  planId: PlanId;
  interval: "monthly" | "annual";
  addOns: AddOnId[];
  paymentStatus: "none" | "trialing" | "paid" | "past_due" | "cancelled";
  trialEndsAt?: string;
  renewalDate?: string;
  cancellationDate?: string;
  cancellationReason?: string;
}

export interface TenantTheme {
  brandColor: string;
  accentColor: string;
  logoText: string;
  welcomeHeadline: string;
}

/**
 * A reusable graded chart. Once a brand has 100+ products, filling sizing in
 * per garment is the single biggest source of ingestion work — this removes it.
 */
export interface BrandSizeChart {
  id: string;
  label: string; // "Atelier Noir standard womenswear"
  category: GarmentCategory | "all";
  kind: SizeChartKind;
  sizes: string[];
  rows: SizeRow[];
  /** Per-size increments, when the brand grades by rule rather than by chart. */
  gradingRules?: Record<string, number>; // measurement key → cm per size step
  /**
   * Charts are versioned rather than edited in place: a garment sized from
   * v2 must not silently start claiming v3's numbers. Editing publishes a new
   * version and archives the old one, which stays readable for existing
   * garments.
   */
  version: number;
  updatedAt: string;
  updatedBy: string;
  archived?: boolean;
  /** Set on a version that superseded this one. */
  supersededById?: string;
}

/** Store-wide ingestion defaults, overridable per garment. */
export interface TenantDefaults {
  soldOutPolicy: SoldOutPolicy;
  hideColourwayWhenAllSoldOut: boolean;
  brandSizeCharts: BrandSizeChart[];
}

export interface Tenant {
  id: string;
  slug: string; // shopname → shopname.vto.mirra.com
  name: string;
  storeUrl: string;
  storeOwnershipVerified: boolean;
  status: TenantStatus;
  launchStatus: LaunchStatus;
  billing: TenantBilling;
  theme: TenantTheme;
  defaults: TenantDefaults;
  onboarding: OnboardingState;
  salesLed: boolean;
  healthScore: number; // 0–100, computed by success tooling
  churnRisk: "low" | "medium" | "high";
  accountNotes: { at: string; by: string; note: string }[];
  domain: { subdomain: string; customDomain?: string };
  suspendedAt?: string;
  graceUntil?: string; // data preserved until this date after cancellation
  createdAt: string;
  previewToken: string; // lets merchants preview draft content on the public surface
  /**
   * Evidence that someone accepted a specific version of the agreement, not
   * just that a checkbox was once ticked. Without the version and the actor,
   * an acceptance record proves nothing.
   */
  agreement?: AgreementAcceptance;
}

export interface AgreementAcceptance {
  documentVersion: string; // "2026-06-01"
  acceptedAt: string;
  acceptedByUserId: string;
  acceptedByName: string;
  /** The exact documents that were accepted, as shown. */
  documents: { title: string; href: string }[];
}

// -------------------------------------------------------------------- CRM

export type LeadStatus =
  | "new"
  | "qualifying"
  | "qualified"
  | "invited"
  | "converted"
  | "disqualified";

export type LeadRole = "founder" | "ecommerce" | "product" | "engineering" | "other";
export type MonthlyOrders = "under-1k" | "1k-10k" | "10k-50k" | "50k-plus";

/**
 * A brand that filled in the verification form on the marketing site — step 2
 * of the merchant flow, before sales ever talks to them.
 *
 * These fields mirror `JoinApplicationRequest` in
 * `website/backend/src/join/schemas.py` exactly, because that form is where
 * real leads come from: `/join` already POSTs to `/api/v1/join`, which writes
 * the `join_applications` collection. The prototype invented `estSkuCount` and
 * `market`, which no form on the site ever captured — showing them to sales
 * would have been fiction.
 *
 * The one field that is ours rather than the applicant's is `status`, the
 * qualification state sales moves through.
 */
export interface Lead {
  id: string;
  company: string;
  contactName: string; // JoinApplicationRequest.name
  email: string;
  storeUrl: string; // JoinApplicationRequest.website
  role: LeadRole;
  monthlyOrders?: MonthlyOrders;
  goals: string;
  source: "demo_request" | "early_access" | "contact_sales";
  status: LeadStatus;
  ownerId?: string; // mirra_sales user
  notes: string[];
  createdAt: string;
  tenantId?: string; // set once converted
}

// -------------------------------------------------------- catalogue & sync

export interface ProductVariant {
  id: string;
  sku: string;
  title: string; // e.g. "Black / S"
  color: string;
  size: string;
  priceUsd: number;
  /** Shopify is the source of truth for stock; Mirra never edits this. */
  inventory: number;
}

export interface Product {
  id: string;
  tenantId: string;
  shopifyId: string;
  /** Canonical Shopify title. Mirra never lets a merchant overwrite this. */
  title: string;
  handle: string;
  /** The storefront URL a merchant would paste to identify this product. */
  onlineStoreUrl: string;
  productType: string;
  vendor: string;
  imageEmoji: string; // prototype stand-in for CDN imagery
  /**
   * What this shop calls its colour-like option — "Colour", "Color", "Shade",
   * "Finish", "Pattern"… Read from Shopify rather than assumed, and absent
   * entirely on products that have no such option (one garment per product).
   */
  optionName?: string;
  variants: ProductVariant[];
  syncStatus: "synced" | "pending" | "error";
  syncError?: string;
  lastSyncedAt: string;
}

export type GarmentCategory =
  | "dress"
  | "top"
  | "bottom"
  | "outerwear"
  | "knitwear"
  | "swim"
  | "accessory";

/**
 * One stage per garment, replacing the prototype's split of `qaStatus` +
 * `publication.status`. Those could disagree — a garment could read "QA
 * passed" and "Draft" at once — and QA was a dropdown the merchant could set
 * themselves, which is exactly what a QA gate must not be.
 *
 * Merchants drive the stages up to `merchant_review`. `in_qa` → `ready` is
 * Mirra's to grant. `paused` and `sync_error` are operational states that can
 * interrupt from anywhere.
 */
export type GarmentStage =
  | "draft" // created, nothing captured yet
  | "processing" // digital garment generating from the capture set
  | "needs_data" // generation done, blocking requirements outstanding
  | "merchant_review" // merchant previews on a test avatar
  | "in_qa" // submitted to Mirra QA
  | "ready" // QA passed, publishable
  | "live"
  | "paused"
  | "sync_error";

/** The four views every garment needs before reconstruction can run. */
export type CaptureView = "front" | "back" | "left" | "right";
export const CAPTURE_VIEWS: readonly CaptureView[] = ["front", "back", "left", "right"];

export type DetailShotKind = "fabric" | "closure" | "collar" | "hem" | "other";

/**
 * How the four views arrive. `upload` means photography that already meets the
 * capture specification — not the brand's marketing shots, which is why it is
 * never labelled just "upload photography" in the UI.
 */
export type CaptureMethod = "phone" | "upload" | "cad";

/** Why a captured view was rejected — specific enough to act on. */
export interface CaptureIssue {
  view: CaptureView;
  message: string;
}

/** A 3D asset supplied instead of photography. */
export interface CadAsset {
  filename: string;
  format: "glb" | "fbx" | "obj" | "zprj" | "usdz";
}

export interface CaptureSet {
  method?: CaptureMethod;
  /** Present only when `method === "cad"` — photographic views aren't required. */
  cadAsset?: CadAsset;
  views: Partial<Record<CaptureView, string>>;
  accepted: CaptureView[];
  issues: CaptureIssue[];
  details: { kind: DetailShotKind; label: string }[];
}

/**
 * Where sizing numbers came from. Recorded because six months later "is this
 * chart trustworthy?" is unanswerable without it.
 */
export type SizeSource =
  | "shopify"
  | "uploaded_chart"
  | "tech_pack"
  | "auto_measured"
  | "manual"
  | "brand_chart";

/**
 * Body measurements and finished-garment measurements are different numbers
 * for the same garment, and fitting them as if they were the same is wrong.
 * Merchants must say which they gave us.
 */
export type SizeChartKind = "body" | "garment" | "unknown";

/** How the non-reference sizes were produced. */
export type GradingSource =
  | "chart" // full graded chart supplied — strongest
  | "rules" // brand grading increments applied to the reference
  | "estimated"; // inferred from one sample — draft only, never authoritative

export type MeasurementConfidence = "high" | "review";

export interface Measurement {
  key: string;
  valueCm: number;
  confidence?: MeasurementConfidence;
}

export interface SizeRow {
  size: string;
  /** Category-appropriate measurements, keyed by MEASUREMENT_FIELDS. */
  values: Record<string, number | undefined>;
}

/**
 * A construction block groups sizes that share a pattern. Most garments have
 * exactly one; extended-size, petite/tall or cup-specific ranges get their own
 * block and their own physical reference sample.
 */
export interface ConstructionBlock {
  id: string;
  label: string; // "Standard", "Extended 2XL–3XL"
  sizes: string[];
  referenceSize?: string;
}

export type Silhouette = "fitted" | "regular" | "relaxed" | "oversized";

export type GarmentBehaviour =
  | "elastic_waist"
  | "adjustable_straps"
  | "wrap_closure"
  | "drawstring"
  | "stretch_panel"
  | "zip"
  | "rigid_waistband"
  | "belt"
  | "lining";

/** Where composition came from — shown as provenance on the Fabric page. */
export type FabricSource =
  | "shopify" // product description
  | "metafield" // structured Shopify metafield
  | "brand_profile" // a saved brand material profile
  | "tech_pack"
  | "manual"
  | "estimated"; // Mirra's inference — never presented as confirmed

/** What happens on the try-on surface when a variant sells out. */
export type SoldOutPolicy = "keep_tryon" | "hide_size";

export interface GarmentAttributes {
  stretch: "none" | "low" | "medium" | "high";
  drape: "structured" | "moderate" | "fluid";
  opacity: "opaque" | "semi" | "sheer";
  thickness: "light" | "mid" | "heavy";
}

/**
 * One garment = one colourway of a Shopify product, digitised from a single
 * physical sample.
 *
 * The load-bearing idea the prototype lacked is `referenceSize`: every capture
 * and auto-measurement describes one physical garment, and without recording
 * which size that was, none of the derived sizes can be trusted later.
 */
export interface Garment {
  id: string;
  tenantId: string;
  // ------------------------------------------------------------- identity
  /**
   * Identity is established before a single photograph and locked afterwards.
   * `productId` is the Shopify product; `optionValue` is one value of that
   * product's colour-like option; `variantIds` are the purchasable SKUs those
   * two together resolve to. Product ≠ garment ≠ SKU, and conflating them is
   * how a catalogue fills with garments nobody can trace to a listing.
   */
  productId: string;
  variantIds: string[];
  /** Mirra's display name — `${canonicalTitle} — ${optionValue}`. Derived. */
  title: string;
  /** Snapshot of the Shopify title at link time. Never merchant-editable. */
  canonicalTitle: string;
  /**
   * What the merchant typed when confirming the garment. Kept only so a
   * divergence from `canonicalTitle` can be surfaced rather than silently
   * creating a garment disconnected from the listing.
   */
  merchantTitle?: string;
  category: GarmentCategory;
  /** The option value — "Slate", "Ivory". Labelled by `Product.optionName`. */
  optionValue: string;
  /** @deprecated Kept as an alias of `optionValue` while call sites migrate. */
  colour: string;

  // ------------------------------------------------------------- capture
  capture: CaptureSet;

  // --------------------------------------------------- reference & sizing
  /** The physical sample that was photographed and measured. */
  referenceSize?: string;
  /** null until the merchant answers; false opens up multi-block capture. */
  sameConstructionAcrossSizes: boolean | null;
  constructionBlocks: ConstructionBlock[];

  sizeChart: SizeRow[];
  sizeSource?: SizeSource;
  sizeChartKind?: SizeChartKind;
  gradingSource?: GradingSource;
  /** Set when sizes were derived rather than supplied — needs verification. */
  gradingUnverified: boolean;
  /** Auto-extracted measurements of the reference sample, with confidence. */
  autoMeasurements?: {
    calibration: "card" | "known_dimension" | "depth" | "none";
    sizeLabel: string;
    values: Measurement[];
  };

  // ------------------------------------------------------------- material
  /** Proportions, not a single material name — they must total 100%. */
  fabricComposition: { material: string; pct: number }[];
  liningComposition: { material: string; pct: number }[];
  fabricSource?: FabricSource;
  fabricConfirmed: boolean;
  attributes: GarmentAttributes;
  /** True while `attributes` are Mirra's suggestion awaiting confirmation. */
  attributesSuggested: boolean;

  // ------------------------------------------------------------------ fit
  silhouette?: Silhouette;
  fitCriticalAreas: string[];
  behaviours: GarmentBehaviour[];
  fitNotes: string;

  careNotes: string;
  tags: string[];
  collections: string[];

  // ---------------------------------------------------------------- state
  stage: GarmentStage;
  /**
   * The merchant has seen each generated size mapped to its Shopify variant and
   * agreed. Required before QA — an unchecked auto-mapping is a guess.
   */
  variantMappingConfirmed: boolean;
  /** Per-garment override of the tenant default. */
  soldOutPolicy?: SoldOutPolicy;
  tryOnEnabled: boolean;
  scheduledGoLive?: string;
  publishedAt?: string;
  /** Set when this colourway reused geometry/grading from a sibling. */
  reusedFromGarmentId?: string;

  // ------------------------------------------------------------ revisions
  /**
   * Monotonic counter over everything try-on depends on: capture set,
   * reference sample, size chart, material, category, construction blocks.
   * Every edit to those bumps it.
   *
   * The load-bearing rule is that QA approves a *number*, not a garment. When
   * `approved.revision !== sourceRevision` the live surface keeps serving the
   * approved snapshot and the newer draft is not published — a merchant can
   * never move a shopper onto photos, measurements or a material that nobody
   * checked.
   */
  sourceRevision: number;
  /** The revision the generated digital garment was built from. */
  assetRevision?: number;
  /** Frozen copy of everything QA signed off, and the only thing served. */
  approved?: GarmentSnapshot;
  /** Structured QA feedback against a revision, not a free-text reason. */
  qaFindings: QaFinding[];
  qaHistory: QaDecisionRecord[];

  updatedBy: string;
  updatedAt: string;
}

/**
 * What QA approved, frozen. The public surface reads this — never the live
 * garment record — so an edit made after approval cannot reach shoppers
 * without going back through generation, review and QA.
 */
export interface GarmentSnapshot {
  revision: number;
  assetRevision: number;
  approvedAt: string;
  approvedBy: string;
  category: GarmentCategory;
  referenceSize?: string;
  captureAccepted: CaptureView[];
  sizeChart: SizeRow[];
  sizeChartKind?: SizeChartKind;
  sizeSource?: SizeSource;
  fabricComposition: { material: string; pct: number }[];
  attributes: GarmentAttributes;
  silhouette?: Silhouette;
  fitNotes: string;
  /** SKUs the approved revision covers. A variant added later is not covered. */
  variantIds: string[];
}

export type QaArea = "capture" | "sizing" | "material" | "mapping" | "fit" | "other";

/**
 * A QA rejection a merchant can act on: which area, which view or
 * measurement, what is wrong, and what to do about it. "Returned for rework"
 * is not a finding.
 */
export interface QaFinding {
  id: string;
  area: QaArea;
  severity: "blocker" | "advisory";
  /** The specific view or measurement key at fault, where there is one. */
  view?: CaptureView;
  measurementKey?: string;
  detail: string;
  instruction: string;
  raisedBy: string;
  raisedAt: string;
  /** The revision this was raised against — findings do not follow an edit. */
  revision: number;
  resolvedAt?: string;
  resolvedBy?: string;
}

export interface QaDecisionRecord {
  at: string;
  by: string;
  decision: "pass" | "fail";
  revision: number;
  note?: string;
  findingCount?: number;
}

export interface SyncRun {
  id: string;
  tenantId: string;
  trigger: "webhook" | "manual" | "reconciliation";
  startedAt: string;
  finishedAt?: string;
  status: "running" | "success" | "partial" | "failed";
  itemsSynced: number;
  failures: { item: string; error: string; productId?: string }[];
  /**
   * Changes the sync would make that Mirra will not apply unattended, because
   * applying them silently would break a digitised garment.
   */
  conflicts?: SyncConflict[];
}

export type SyncConflictKind =
  | "variant_removed"
  | "option_renamed"
  | "product_archived"
  | "image_missing";

export interface SyncConflict {
  kind: SyncConflictKind;
  productId: string;
  productTitle: string;
  detail: string;
  /** Garments whose data depends on the thing that changed. */
  affectedGarmentIds: string[];
  resolvedAt?: string;
}

// ------------------------------------------------------------------ support

export type TicketStatus = "open" | "pending" | "resolved" | "escalated";

export interface Ticket {
  id: string;
  tenantId: string;
  subject: string;
  category: "onboarding" | "catalogue" | "billing" | "production_issue" | "other";
  priority: "low" | "normal" | "high" | "urgent";
  status: TicketStatus;
  createdById: string;
  createdAt: string;
  /** Mirra staff user id, once the queue has picked it up. */
  assigneeId?: string;
  messages: { at: string; from: string; internal: boolean; body: string }[];
}

// ------------------------------------------------------------------- events

export interface AuditEvent {
  id: string;
  tenantId?: string;
  actorId: string;
  actorName: string;
  action: string; // e.g. "garment.publish", "tenant.suspend", "impersonation.start"
  target: string;
  detail?: string;
  at: string;
}

export interface BillingEvent {
  id: string;
  tenantId: string;
  type:
    | "subscription_created"
    | "trial_started"
    | "payment_succeeded"
    | "payment_failed"
    | "plan_changed"
    | "cancellation_requested"
    | "subscription_cancelled"
    | "reactivated";
  detail: string;
  at: string;
}

export type AnalyticsEventType =
  | "page_view"
  | "tryon_click"
  | "session_start"
  | "session_complete"
  | "sku_view";

export interface AnalyticsEvent {
  id: string;
  tenantId: string;
  type: AnalyticsEventType;
  garmentId?: string;
  source: "public" | "preview";
  at: string; // ISO date
}

// ------------------------------------------------------------------- store

export interface Db {
  users: User[];
  memberships: Membership[];
  plans: Plan[];
  tenants: Tenant[];
  leads: Lead[];
  products: Product[];
  garments: Garment[];
  syncRuns: SyncRun[];
  tickets: Ticket[];
  auditEvents: AuditEvent[];
  billingEvents: BillingEvent[];
  analyticsEvents: AnalyticsEvent[];
}
