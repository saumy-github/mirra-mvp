/**
 * The garment-ingestion domain: what "complete" means, what blocks publishing,
 * which measurements a category actually needs, and how a garment moves from
 * a physical sample to a live try-on record.
 *
 * The merchant-facing flow is deliberately simple — pick a product, pick the
 * sample size, take four photos, add sizing, confirm fabric, preview, submit.
 * The richness lives here rather than in the UI.
 */
import type {
  ConstructionBlock,
  Garment,
  GarmentBehaviour,
  ProductVariant,
  GarmentCategory,
  GarmentStage,
  Product,
  SizeSource,
  SoldOutPolicy,
  Tenant,
} from "./types";
import { CAPTURE_VIEWS } from "./types";
import { validateChart } from "./size-chart";
import type { Tone } from "../components/styles";

// ------------------------------------------------------------------- stages

export const STAGE_META: Record<
  GarmentStage,
  { label: string; tone: Tone; help: string }
> = {
  draft: { label: "Draft", tone: "neutral", help: "Created, not yet captured." },
  processing: { label: "Processing", tone: "info", help: "Building the digital garment from your photos." },
  needs_data: { label: "Needs data", tone: "warn", help: "Missing information required for try-on." },
  merchant_review: { label: "Your review", tone: "info", help: "Preview it on a test avatar and confirm it looks right." },
  in_qa: { label: "In QA", tone: "info", help: "With the Mirra team for quality checks." },
  ready: { label: "Ready", tone: "success", help: "QA passed. Publish whenever you like." },
  live: { label: "Live", tone: "success", help: "Visible to shoppers." },
  paused: { label: "Paused", tone: "warn", help: "Hidden from shoppers by you." },
  sync_error: { label: "Sync error", tone: "danger", help: "Shopify data for this garment failed to sync." },
};

/**
 * Merchants own everything up to `merchant_review`. The `in_qa → ready` step is
 * Mirra's alone — a merchant marking their own garment "QA passed" was the
 * prototype's most misleading control.
 */
export const MERCHANT_TRANSITIONS: Record<GarmentStage, GarmentStage[]> = {
  draft: ["processing"],
  processing: ["needs_data", "merchant_review"],
  needs_data: ["merchant_review"],
  merchant_review: ["in_qa", "needs_data"],
  in_qa: [], // Mirra QA decides
  ready: ["live"],
  live: ["paused"],
  paused: ["live"],
  sync_error: ["needs_data"],
};

export function canMerchantMove(from: GarmentStage, to: GarmentStage): boolean {
  return MERCHANT_TRANSITIONS[from]?.includes(to) ?? false;
}

/** Stages where shoppers can reach the garment. */
export function isPublished(g: Garment): boolean {
  return g.stage === "live";
}

// ------------------------------------------------------- category questions

export interface MeasurementField {
  key: string;
  label: string;
  /** Shown behind a "How to measure" affordance. */
  how: string;
}

/**
 * Asking a trouser for its bust measurement is how a form teaches merchants
 * that the tool doesn't understand their product. Each category gets only its
 * own fields.
 */
export const MEASUREMENT_FIELDS: Record<GarmentCategory, MeasurementField[]> = {
  dress: [
    { key: "bust", label: "Bust", how: "Flat across the garment at the fullest point, seam to seam." },
    { key: "waist", label: "Waist", how: "Flat across the narrowest point of the waist seam." },
    { key: "hip", label: "Hip", how: "Flat across the fullest point below the waist." },
    { key: "shoulder", label: "Shoulder", how: "Seam to seam across the back." },
    { key: "length", label: "Length", how: "High point of the shoulder straight down to the hem." },
    { key: "sleeve", label: "Sleeve", how: "Shoulder seam to cuff along the outer arm." },
  ],
  top: [
    { key: "chest", label: "Chest", how: "Flat across, one inch below the armhole." },
    { key: "shoulder", label: "Shoulder", how: "Seam to seam across the back." },
    { key: "length", label: "Length", how: "High point of the shoulder straight down to the hem." },
    { key: "sleeve", label: "Sleeve", how: "Shoulder seam to cuff along the outer arm." },
    { key: "armhole", label: "Armhole", how: "Straight line from the shoulder seam to the underarm." },
  ],
  bottom: [
    { key: "waist", label: "Waist", how: "Flat across the top of the waistband." },
    { key: "hip", label: "Hip", how: "Flat across, roughly 20 cm below the waistband." },
    { key: "rise", label: "Rise", how: "Crotch seam up to the top of the waistband, front." },
    { key: "inseam", label: "Inseam", how: "Crotch seam down to the leg opening." },
    { key: "outseam", label: "Outseam", how: "Top of the waistband down to the leg opening." },
    { key: "thigh", label: "Thigh", how: "Flat across, just below the crotch seam." },
    { key: "legOpening", label: "Leg opening", how: "Flat across the hem of the leg." },
  ],
  outerwear: [
    { key: "chest", label: "Chest", how: "Flat across, one inch below the armhole." },
    { key: "shoulder", label: "Shoulder", how: "Seam to seam across the back." },
    { key: "length", label: "Length", how: "High point of the shoulder straight down to the hem." },
    { key: "sleeve", label: "Sleeve", how: "Shoulder seam to cuff along the outer arm." },
    { key: "hem", label: "Hem", how: "Flat across the bottom opening." },
  ],
  knitwear: [
    { key: "chest", label: "Chest", how: "Flat across, one inch below the armhole, unstretched." },
    { key: "shoulder", label: "Shoulder", how: "Seam to seam across the back." },
    { key: "length", label: "Length", how: "High point of the shoulder straight down to the hem." },
    { key: "sleeve", label: "Sleeve", how: "Shoulder seam to cuff along the outer arm." },
  ],
  swim: [
    { key: "bust", label: "Bust", how: "Flat across the cup at the fullest point, unstretched." },
    { key: "waist", label: "Waist", how: "Flat across the narrowest point, unstretched." },
    { key: "hip", label: "Hip", how: "Flat across the fullest point, unstretched." },
    { key: "length", label: "Length", how: "Shoulder strap top to gusset." },
  ],
  accessory: [
    { key: "width", label: "Width", how: "Flat across the widest point." },
    { key: "length", label: "Length", how: "End to end at the longest point." },
  ],
};

/**
 * What "shot to Mirra's specification" actually means — the reason the capture
 * flow exists at all.
 *
 * A brand's Shopify imagery is styled for merchandising: models, props, crops,
 * colour grading. None of it can be reconstructed into a wearable garment. So
 * every new drop needs its physical sample re-shot plain and flat, four ways.
 * Merchants aren't expected to understand reconstruction — they're expected to
 * follow six rules.
 */
export const CAPTURE_SPEC: { rule: string; why: string }[] = [
  {
    rule: "The garment itself, not a model shot",
    why: "A worn garment hides its own shape.",
  },
  {
    rule: "Whole garment inside the frame",
    why: "A cropped hem or sleeve becomes a guess in the 3D result.",
  },
  {
    rule: "Flat or on a plain hanger, unstyled",
    why: "Props, tucks and arranged folds read as garment geometry.",
  },
  {
    rule: "Plain, contrasting background",
    why: "Separating garment from background is the first step of every reconstruction.",
  },
  {
    rule: "Even, indirect light — no hard shadows",
    why: "Shadows get interpreted as seams and drape that aren't there.",
  },
  {
    rule: "Camera square to the garment",
    why: "Perspective skew distorts every measurement taken from the image.",
  },
];

/**
 * Which construction questions make sense for a category.
 *
 * A ribbed tank was being asked about its rigid waistband and belt. Offering
 * controls that cannot apply teaches merchants the tool doesn't understand
 * their product, and any answer they give is noise in the fit model.
 */
export const CATEGORY_BEHAVIOURS: Record<GarmentCategory, GarmentBehaviour[]> = {
  dress: ["adjustable_straps", "wrap_closure", "zip", "belt", "lining", "elastic_waist", "stretch_panel"],
  top: ["adjustable_straps", "wrap_closure", "zip", "stretch_panel", "lining"],
  bottom: ["elastic_waist", "rigid_waistband", "drawstring", "zip", "belt", "stretch_panel", "lining"],
  outerwear: ["zip", "belt", "lining", "drawstring"],
  knitwear: ["stretch_panel", "zip", "lining"],
  swim: ["adjustable_straps", "elastic_waist", "stretch_panel", "lining"],
  accessory: ["lining", "zip"],
};

export const BEHAVIOUR_LABELS: Record<GarmentBehaviour, string> = {
  elastic_waist: "Elastic waist",
  adjustable_straps: "Adjustable straps",
  wrap_closure: "Wrap closure",
  drawstring: "Drawstring",
  stretch_panel: "Stretch panel",
  zip: "Zip",
  rigid_waistband: "Rigid waistband",
  belt: "Belt",
  lining: "Lining",
};

// ------------------------------------------------------- grading & mapping

export interface GradingPlan {
  method: "chart" | "rules" | "estimated" | "second_block" | "none";
  headline: string;
  detail: string;
  tone: Tone;
}

/**
 * How the sizes the merchant did *not* photograph will be produced. A merchant
 * who hands over one size S should be able to see exactly how XS, M and L come
 * into existence — and how much to trust them.
 */
export function gradingPlan(g: Garment, product: Product | undefined): GradingPlan {
  const sizes = sizesForGarment(g, product);
  const others = sizes.filter((s) => s !== g.referenceSize);
  if (!g.referenceSize) {
    return {
      method: "none",
      headline: "No reference sample yet",
      detail: "Confirm which size you physically have before sizes can be generated.",
      tone: "neutral",
    };
  }
  if (others.length === 0) {
    return {
      method: "none",
      headline: "Single size",
      detail: "This garment has one size, so nothing needs grading.",
      tone: "neutral",
    };
  }
  if (g.constructionBlocks.length > 1) {
    return {
      method: "second_block",
      headline: `${g.constructionBlocks.length} construction blocks`,
      detail: `Each block needs its own reference sample; Mirra interpolates within a block and never across blocks.`,
      tone: "info",
    };
  }
  switch (g.gradingSource) {
    case "chart":
      return {
        method: "chart",
        headline: "From your graded size chart",
        detail: `${others.join(", ")} come from measurements you supplied. This is the strongest source.`,
        tone: "success",
      };
    case "rules":
      return {
        method: "rules",
        headline: "From your brand grading rules",
        detail: `${others.join(", ")} are stepped from size ${g.referenceSize} using your brand increments.`,
        tone: "success",
      };
    case "estimated":
      return {
        method: "estimated",
        headline: "Estimated from one sample — draft only",
        detail: `${others.join(", ")} are inferred from size ${g.referenceSize}. Mirra will not treat these as measured until you verify them.`,
        tone: "warn",
      };
    default:
      return {
        method: "none",
        headline: "Not yet determined",
        detail: "Add a size chart, apply brand grading rules, or measure the sample.",
        tone: "warn",
      };
  }
}

export interface VariantMappingRow {
  size: string;
  variant?: ProductVariant;
  inventory: number;
}

/**
 * Every generated size resolved to the Shopify variant a shopper would buy.
 * Sizes with no variant, and variants with no generated size, are both faults
 * worth surfacing before QA rather than after a shopper hits them.
 */
export function variantMapping(g: Garment, product: Product | undefined) {
  const variants = product?.variants.filter((v) => v.color === g.optionValue) ?? [];
  const generated = g.sizeChart.length > 0 ? g.sizeChart.map((r) => r.size) : sizesForGarment(g, product);

  const rows: VariantMappingRow[] = generated.map((size) => {
    const variant = variants.find((v) => v.size === size);
    return { size, variant, inventory: variant?.inventory ?? 0 };
  });
  const unmatchedVariants = variants.filter((v) => !generated.includes(v.size));
  return {
    rows,
    unmatchedVariants,
    allMatched: rows.every((r) => r.variant) && unmatchedVariants.length === 0,
  };
}

export const SIZE_SOURCE_LABELS: Record<SizeSource, string> = {
  shopify: "Shopify",
  uploaded_chart: "Uploaded chart",
  tech_pack: "Tech pack",
  auto_measured: "Measured sample",
  manual: "Entered manually",
  brand_chart: "Brand chart",
};

// -------------------------------------------------------------- completion

export type RequirementKey = "mapping" | "capture" | "sizing" | "material" | "fit";

export interface Requirement {
  key: RequirementKey;
  label: string;
  complete: boolean;
  /** Blocking requirements prevent publishing; the rest are quality nudges. */
  blocking: boolean;
  detail: string;
}

/**
 * The five things a garment needs. Surfaced as "3 / 5 complete" plus the
 * breakdown, rather than the prototype's flat "4 missing" — which told a
 * merchant how much was wrong but not what to do next.
 */
export function requirements(g: Garment, product: Product | undefined): Requirement[] {
  const acceptedViews = g.capture.accepted.length;
  const mappedVariants = g.variantIds.length;
  const expectedVariants =
    product?.variants.filter((v) => v.color === g.colour).length ?? mappedVariants;

  // A CAD asset already contains the geometry the four views exist to recover,
  // so it satisfies capture on its own.
  const captureComplete =
    g.capture.method === "cad"
      ? Boolean(g.capture.cadAsset)
      : acceptedViews === CAPTURE_VIEWS.length;

  // "Has rows" is not "has usable measurements". The chart has to cover every
  // Shopify size with a plausible number in every field the category needs.
  const chart = validateChart(g.sizeChart, g.category, sizesForGarment(g, product), g.referenceSize);
  const sizingComplete = chart.valid && Boolean(g.referenceSize) && !g.gradingUnverified;

  return [
    {
      key: "mapping",
      label: "Shopify mapping",
      complete: mappedVariants > 0 && mappedVariants === expectedVariants,
      blocking: true,
      detail:
        expectedVariants === 0
          ? "No Shopify variants for this colourway."
          : `${mappedVariants} of ${expectedVariants} variants matched.`,
    },
    {
      key: "capture",
      label: "Images",
      complete: captureComplete,
      blocking: true,
      // Shopify's product imagery never satisfies this — see the capture spec.
      detail:
        g.capture.method === "cad"
          ? g.capture.cadAsset
            ? `3D asset ${g.capture.cadAsset.filename} accepted.`
            : "No 3D asset uploaded yet."
          : `${acceptedViews} of ${CAPTURE_VIEWS.length} required views accepted.`,
    },
    {
      key: "sizing",
      label: "Size & fit",
      complete: sizingComplete,
      blocking: true,
      detail: !g.referenceSize
        ? "No reference sample size recorded."
        : g.sizeChart.length === 0
          ? "No size chart."
          : chart.missingSizes.length > 0
            ? `No measurements for ${chart.missingSizes.join(", ")}.`
            : chart.issues.length > 0
              ? `${chart.issues.length} measurement${chart.issues.length === 1 ? "" : "s"} missing or out of range.`
              : g.gradingUnverified
                ? "Derived sizes still need verifying."
                : `${g.sizeChart.length} sizes from ${g.sizeSource ? SIZE_SOURCE_LABELS[g.sizeSource] : "an unknown source"}.`,
    },
    {
      key: "material",
      label: "Material",
      complete: g.fabricComposition.length > 0 && g.fabricConfirmed && !g.attributesSuggested,
      blocking: true,
      detail:
        g.fabricComposition.length === 0
          ? "No composition recorded."
          : !g.fabricConfirmed
            ? "Composition imported but not confirmed."
            : g.attributesSuggested
              ? "Drape and stretch are suggestions awaiting confirmation."
              : "Composition and behaviour confirmed.",
    },
    {
      key: "fit",
      label: "Fit",
      complete: Boolean(g.silhouette) && g.fitNotes.trim().length > 0,
      blocking: false,
      detail: g.silhouette ? "Silhouette and notes recorded." : "No intended silhouette set.",
    },
  ];
}

export function completionCount(g: Garment, product: Product | undefined) {
  const reqs = requirements(g, product);
  return { done: reqs.filter((r) => r.complete).length, total: reqs.length, reqs };
}

// ------------------------------------------------------------------- flow

export type FlowStepKey = "identify" | "capture" | "material" | "sizing" | "review";

/**
 * Navigation and completion are different things. A merchant standing on
 * Material has not thereby completed Capture, and a step that has been part
 * filled is not the same as one never opened — nor the same as one that was
 * filled and then invalidated (a rejected view, an unconfirmed inference).
 */
export type StepState = "not_started" | "in_progress" | "complete" | "needs_attention";

export const STEP_STATE_META: Record<StepState, { label: string; tone: Tone }> = {
  not_started: { label: "Not started", tone: "neutral" },
  in_progress: { label: "In progress", tone: "info" },
  complete: { label: "Complete", tone: "success" },
  needs_attention: { label: "Needs attention", tone: "warn" },
};

export interface FlowStep {
  key: FlowStepKey;
  label: string;
  hint: string;
  state: StepState;
  complete: boolean;
}

/**
 * The steps of the add-a-garment flow, in the order a merchant physically
 * works: photograph the sample in front of them, say what it's made of, say
 * how it's sized, check it over.
 *
 * Identifying the sample used to be a step of its own. It isn't work — it's
 * two clicks — so it now sits at the top of Capture, where the answer is
 * needed anyway. A merchant who has just added a garment starts by shooting it.
 */
export function flowSteps(g: Garment, product: Product | undefined): FlowStep[] {
  const reqs = requirements(g, product);
  const done = (key: RequirementKey) => reqs.find((r) => r.key === key)?.complete ?? false;

  const state = (opts: { complete: boolean; started: boolean; attention?: boolean }): StepState =>
    opts.complete ? "complete" : opts.attention ? "needs_attention" : opts.started ? "in_progress" : "not_started";

  const identityComplete =
    Boolean(g.productId) && Boolean(g.referenceSize) && g.sameConstructionAcrossSizes !== null;

  const capture = g.capture;
  const isCad = capture.method === "cad";
  const captureComplete = isCad
    ? Boolean(capture.cadAsset)
    : capture.accepted.length === CAPTURE_VIEWS.length;

  const materialComplete = done("material");
  const sizingComplete = done("sizing") && done("fit");
  const blocking = reviewIssues(g, product).blocking.length;

  const steps: FlowStep[] = [
    {
      key: "identify",
      label: "Identify",
      hint: "Which Shopify product and sample",
      state: state({
        complete: identityComplete,
        started: Boolean(g.productId),
        // A merchant-typed name that drifted from the Shopify title.
        attention: Boolean(g.merchantTitle && g.merchantTitle !== g.canonicalTitle),
      }),
      complete: identityComplete,
    },
    {
      key: "capture",
      label: "Capture",
      hint: isCad ? "3D asset" : "Four views of the sample",
      state: state({
        complete: captureComplete,
        started: Boolean(capture.method) || capture.accepted.length > 0,
        attention: capture.issues.length > 0,
      }),
      complete: captureComplete,
    },
    {
      key: "material",
      label: "Material",
      hint: "Composition and behaviour",
      state: state({
        complete: materialComplete,
        started: g.fabricComposition.length > 0,
        // Inferred values sitting unconfirmed are not "in progress" — someone
        // has to look at them before they can be trusted.
        attention: g.fabricComposition.length > 0 && (!g.fabricConfirmed || g.attributesSuggested),
      }),
      complete: materialComplete,
    },
    {
      key: "sizing",
      label: "Size & fit",
      hint: "Measurements and how it fits",
      state: state({
        complete: sizingComplete,
        started: g.sizeChart.length > 0 || Boolean(g.silhouette),
        attention: g.gradingUnverified || g.sizeChartKind === "unknown",
      }),
      complete: sizingComplete,
    },
    {
      key: "review",
      label: "Review",
      hint: "Check and send to QA",
      state: state({
        complete: blocking === 0 && g.variantMappingConfirmed,
        started: blocking === 0,
        attention: blocking > 0 && identityComplete && captureComplete,
      }),
      complete: blocking === 0 && g.variantMappingConfirmed,
    },
  ];
  return steps;
}

/** The step a merchant should land on — the first one still outstanding. */
export function nextFlowStep(g: Garment, product: Product | undefined): FlowStepKey {
  return flowSteps(g, product).find((s) => !s.complete)?.key ?? "review";
}

export interface ReviewIssue {
  label: string;
  detail: string;
}

/** Split into what stops a publish and what merely improves the result. */
export function reviewIssues(g: Garment, product: Product | undefined) {
  const reqs = requirements(g, product);
  const blocking: ReviewIssue[] = reqs
    .filter((r) => r.blocking && !r.complete)
    .map((r) => ({ label: r.label, detail: r.detail }));

  const suggestions: ReviewIssue[] = [];
  if (g.capture.details.length === 0) {
    suggestions.push({
      label: "Add a fabric close-up",
      detail: "Detail shots noticeably improve texture realism in try-on.",
    });
  }
  if (g.sizeChartKind === "unknown") {
    suggestions.push({
      label: "Confirm what the measurements describe",
      detail: "Body and finished-garment measurements fit very differently.",
    });
  }
  if (!g.silhouette) {
    suggestions.push({
      label: "Set the intended silhouette",
      detail: "It tells the fit engine how close to the body this should sit.",
    });
  }
  if (g.gradingSource === "estimated") {
    suggestions.push({
      label: "Verify the generated sizes",
      detail: "These were derived from one sample and are a draft, not measurements.",
    });
  }
  return { blocking, suggestions };
}

// --------------------------------------------------------------- inventory

export interface InventoryState {
  total: number;
  purchasable: number;
  soldOut: string[];
  allSoldOut: boolean;
}

/** Read-only view of Shopify stock. Mirra never writes inventory. */
export function inventoryFor(g: Garment, product: Product | undefined): InventoryState {
  const variants = product?.variants.filter((v) => g.variantIds.includes(v.id)) ?? [];
  const soldOut = variants.filter((v) => v.inventory <= 0).map((v) => v.size);
  return {
    total: variants.length,
    purchasable: variants.length - soldOut.length,
    soldOut,
    allSoldOut: variants.length > 0 && soldOut.length === variants.length,
  };
}

export function soldOutPolicyFor(g: Garment, tenant: Tenant): SoldOutPolicy {
  return g.soldOutPolicy ?? tenant.defaults.soldOutPolicy;
}

export const SOLD_OUT_POLICY_LABELS: Record<SoldOutPolicy, string> = {
  keep_tryon: "Keep available for try-on, disable purchase",
  hide_size: "Hide that size from try-on",
};

// ------------------------------------------------------------------ blocks

/** The single default block covering every size in the colourway. */
export function defaultBlock(sizes: string[], referenceSize?: string): ConstructionBlock {
  return { id: "b_standard", label: "Standard", sizes, referenceSize };
}

/** Sizes in the colourway, ordered as Shopify returned them. */
export function sizesForGarment(g: Garment, product: Product | undefined): string[] {
  const variants = product?.variants.filter((v) => v.color === g.colour) ?? [];
  return [...new Set(variants.map((v) => v.size))];
}

/**
 * Sibling colourways of the same product that are already digitised — the
 * candidates for reusing geometry and grading instead of capturing again.
 */
export function reuseCandidates(g: Garment, all: Garment[]): Garment[] {
  return all.filter(
    (other) =>
      other.id !== g.id &&
      other.productId === g.productId &&
      other.capture.accepted.length === CAPTURE_VIEWS.length &&
      other.sizeChart.length > 0,
  );
}
