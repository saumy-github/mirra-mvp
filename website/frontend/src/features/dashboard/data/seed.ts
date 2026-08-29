import { MEASUREMENT_FIELDS } from "./ingestion";
import type {
  AnalyticsEvent,
  Db,
  GarmentCategory,
  Garment,
  Plan,
  Product,
  Tenant,
} from "./types";

const now = new Date("2026-07-13T10:00:00Z");
const iso = (daysAgo: number, hour = 10) => {
  const d = new Date(now);
  d.setDate(d.getDate() - daysAgo);
  d.setUTCHours(hour, 0, 0, 0);
  return d.toISOString();
};

export const PLANS: Plan[] = [
  {
    id: "pilot",
    name: "Pilot",
    monthlyUsd: 0,
    annualUsd: 0,
    skuLimit: 25,
    seatLimit: 3,
    supportTier: "standard",
    trialDays: 30,
    features: ["25 live SKUs", "Mirra subdomain", "Standard support", "Core analytics"],
  },
  {
    id: "boutique",
    name: "Boutique",
    monthlyUsd: 299,
    annualUsd: 2990,
    skuLimit: 100,
    seatLimit: 5,
    supportTier: "standard",
    trialDays: 14,
    features: ["100 live SKUs", "Mirra subdomain", "Standard support", "Core analytics", "Bulk publishing"],
  },
  {
    id: "atelier",
    name: "Atelier",
    monthlyUsd: 899,
    annualUsd: 8990,
    skuLimit: 500,
    seatLimit: 15,
    supportTier: "priority",
    trialDays: 14,
    features: ["500 live SKUs", "Priority support", "Advanced analytics", "Scheduled go-lives", "Add-on: custom domain"],
  },
  {
    id: "enterprise",
    name: "Enterprise",
    monthlyUsd: null,
    annualUsd: null,
    skuLimit: 10000,
    seatLimit: 100,
    supportTier: "dedicated",
    trialDays: 0,
    features: ["Unlimited SKUs", "Dedicated CSM", "Custom domains", "SSO / SAML", "Custom contracts & SLAs"],
  },
];

function makeProduct(
  id: string,
  tenantId: string,
  title: string,
  productType: string,
  vendor: string,
  emoji: string,
  colors: string[],
  sizes: string[],
  price: number,
  opts: { syncStatus?: Product["syncStatus"]; syncError?: string; optionName?: string } = {}
): Product {
  const variants = colors.flatMap((color, ci) =>
    sizes.map((size, si) => ({
      id: `${id}_v${ci}${si}`,
      sku: `${title.slice(0, 3).toUpperCase().replace(/\s/g, "")}-${color.slice(0, 3).toUpperCase()}-${size}`,
      title: `${color} / ${size}`,
      color,
      size,
      priceUsd: price,
      // Stock comes from Shopify. Deterministic here, and deliberately
      // includes sold-out sizes so the sold-out policy has something to act on.
      inventory: (ci + si) % 5 === 2 ? 0 : 3 + ((ci * 7 + si * 3) % 12),
    }))
  );
  const handle = title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return {
    id,
    tenantId,
    shopifyId: `gid://shopify/Product/${id.replace(/\D/g, "")}9${id.length}`,
    title,
    handle,
    onlineStoreUrl: `https://ateliernoir.com/products/${handle}`,
    productType,
    vendor,
    imageEmoji: emoji,
    // Shops name this option differently; Mirra reads it rather than assuming
    // "Colour". A single-colour product has no such option at all.
    optionName: colors.length > 1 ? opts.optionName ?? "Colour" : undefined,
    variants,
    syncStatus: opts.syncStatus ?? "synced",
    syncError: opts.syncError,
    lastSyncedAt: iso(0, 6),
  };
}

/** How many of the four required views this garment has accepted. */
type CaptureLevel = "none" | "partial" | "full";

function makeCapture(level: CaptureLevel): Garment["capture"] {
  if (level === "none") {
    return { views: {}, accepted: [], issues: [], details: [] };
  }
  if (level === "partial") {
    return {
      method: "phone",
      views: { front: "front.jpg", back: "back.jpg", left: "left.jpg" },
      accepted: ["front", "back", "left"],
      issues: [{ view: "right", message: "The lower hem is outside the frame." }],
      details: [],
    };
  }
  return {
    method: "phone",
    views: { front: "front.jpg", back: "back.jpg", left: "left.jpg", right: "right.jpg" },
    accepted: ["front", "back", "left", "right"],
    issues: [],
    details: [{ kind: "fabric", label: "Fabric close-up" }],
  };
}

function makeGarment(
  id: string,
  p: Product,
  category: Garment["category"],
  // `capture` is a shorthand here, not the stored CaptureSet.
  o: Omit<Partial<Garment>, "capture"> & { colour: string; capture?: CaptureLevel },
): Garment {
  const captureLevel: CaptureLevel = o.capture ?? "none";
  const sizes = [...new Set(p.variants.filter((v) => v.color === o.colour).map((v) => v.size))];
  return {
    id,
    tenantId: p.tenantId,
    productId: p.id,
    variantIds: p.variants.filter((v) => v.color === o.colour).map((v) => v.id),
    title: `${p.title} — ${o.colour}`,
    canonicalTitle: p.title,
    category,
    optionValue: o.colour,
    colour: o.colour,

    capture: makeCapture(captureLevel),

    referenceSize: o.referenceSize,
    sameConstructionAcrossSizes: o.sameConstructionAcrossSizes ?? (o.referenceSize ? true : null),
    constructionBlocks: o.constructionBlocks ?? [
      { id: "b_standard", label: "Standard", sizes, referenceSize: o.referenceSize },
    ],

    sizeChart: o.sizeChart ?? [],
    sizeSource: o.sizeSource,
    sizeChartKind: o.sizeChartKind,
    gradingSource: o.gradingSource,
    gradingUnverified: o.gradingUnverified ?? false,
    autoMeasurements: o.autoMeasurements,

    fabricComposition: o.fabricComposition ?? [],
    liningComposition: o.liningComposition ?? [],
    fabricSource: o.fabricSource,
    fabricConfirmed: o.fabricConfirmed ?? false,
    attributes: o.attributes ?? { stretch: "low", drape: "moderate", opacity: "opaque", thickness: "mid" },
    attributesSuggested: o.attributesSuggested ?? false,

    silhouette: o.silhouette,
    fitCriticalAreas: o.fitCriticalAreas ?? [],
    behaviours: o.behaviours ?? [],
    fitNotes: o.fitNotes ?? "",

    careNotes: o.careNotes ?? "Machine wash cold. Lay flat to dry.",
    tags: o.tags ?? [],
    collections: o.collections ?? [],

    stage: o.stage ?? "draft",
    variantMappingConfirmed: o.variantMappingConfirmed ?? (o.stage === "live" || o.stage === "paused" || o.stage === "in_qa"),
    soldOutPolicy: o.soldOutPolicy,
    tryOnEnabled: o.tryOnEnabled ?? false,
    publishedAt: o.publishedAt,
    reusedFromGarmentId: o.reusedFromGarmentId,

    // Seeded garments start at revision 1. Anything already past QA carries
    // an approved snapshot, because that snapshot — not the live record — is
    // what the public surface serves.
    sourceRevision: o.sourceRevision ?? 1,
    assetRevision: o.assetRevision ?? (captureLevel === "full" ? 1 : undefined),
    approved: o.approved,
    qaFindings: o.qaFindings ?? [],
    qaHistory: o.qaHistory ?? [],
    scheduledGoLive: o.scheduledGoLive,

    updatedBy: o.updatedBy ?? "Priya Nair",
    updatedAt: o.updatedAt ?? iso(2),
  };
}

/**
 * Freeze what QA approved for garments seeded past the gate. Without this a
 * seeded "live" garment would resolve as unpublishable, which is correct
 * behaviour but a confusing first screen.
 */
function withApproval(g: Garment): Garment {
  if (!["live", "paused", "ready"].includes(g.stage)) return g;
  g.approved = {
    revision: g.sourceRevision,
    assetRevision: g.assetRevision ?? g.sourceRevision,
    approvedAt: iso(6),
    approvedBy: "Maya Chen (Mirra QA)",
    category: g.category,
    referenceSize: g.referenceSize,
    captureAccepted: [...g.capture.accepted],
    sizeChart: g.sizeChart.map((r) => ({ size: r.size, values: { ...r.values } })),
    sizeChartKind: g.sizeChartKind,
    sizeSource: g.sizeSource,
    fabricComposition: g.fabricComposition.map((f) => ({ ...f })),
    attributes: { ...g.attributes },
    silhouette: g.silhouette,
    fitNotes: g.fitNotes,
    variantIds: [...g.variantIds],
  };
  g.qaHistory = [
    { at: iso(6), by: "Maya Chen (Mirra QA)", decision: "pass", revision: g.sourceRevision },
  ];
  return g;
}

/**
 * A fully graded four-size chart, in finished-garment centimetres.
 *
 * Generated from the category's own required fields rather than a hand-picked
 * four, because "complete" now means every field of every Shopify size holds a
 * plausible number — a seed that half-fills its charts would show every seeded
 * garment as unpublishable.
 */
function fullChart(category: GarmentCategory): Garment["sizeChart"] {
  // Rough but realistic starting points, stepped 4 cm per size for girths and
  // 1 cm for lengths, which is roughly how a real grade behaves.
  const base: Record<string, [number, number]> = {
    bust: [82, 4], chest: [88, 4], waist: [64, 4], hip: [88, 4],
    shoulder: [37, 1], length: [90, 1], sleeve: [58, 1], armhole: [21, 1],
    rise: [26, 1], inseam: [74, 1], outseam: [100, 1], thigh: [56, 2],
    legOpening: [32, 1], hem: [96, 4], width: [45, 2],
  };
  return ["XS", "S", "M", "L"].map((size, i) => ({
    size,
    values: Object.fromEntries(
      MEASUREMENT_FIELDS[category].map((f) => {
        const [start, step] = base[f.key] ?? [50, 2];
        return [f.key, Math.round((start + step * i) * 10) / 10];
      }),
    ),
  }));
}

const DRESS_CHART = fullChart("dress");
const TOP_CHART = fullChart("top");
const BOTTOM_CHART = fullChart("bottom");


/** Store-wide ingestion defaults. Brands with a house chart set it once. */
function makeDefaults(brandChartLabel?: string): Tenant["defaults"] {
  return {
    soldOutPolicy: "keep_tryon",
    hideColourwayWhenAllSoldOut: false,
    brandSizeCharts: brandChartLabel
      ? [
          {
            id: "bsc_1",
            label: brandChartLabel,
            category: "all",
            kind: "garment",
            sizes: ["XS", "S", "M", "L"],
            rows: [],
            gradingRules: { bust: 4, chest: 4, waist: 4, hip: 4, length: 1 },
            version: 2,
            updatedAt: iso(45),
            updatedBy: "Elodie Marchand",
          },
        ]
      : [],
  };
}

export function buildSeed(): Db {
  // ------------------------------------------------------------- tenants
  const atelierNoir: Tenant = {
    id: "t_atelier",
    slug: "atelier-noir",
    name: "Atelier Noir",
    storeUrl: "https://ateliernoir.com",
    storeOwnershipVerified: true,
    status: "active",
    launchStatus: "live",
    salesLed: true,
    billing: {
      planId: "atelier",
      interval: "annual",
      addOns: ["analytics_plus"],
      paymentStatus: "paid",
      renewalDate: iso(-212),
    },
    theme: {
      brandColor: "#141414",
      accentColor: "#B08D57",
      logoText: "ATELIER NOIR",
      welcomeHeadline: "See it on you before it ships.",
    },
    defaults: makeDefaults("Atelier Noir standard womenswear"),
    onboarding: {
      storeVerified: true, storeUrlConfirmed: true, shopifyConnected: true,
      teamInvited: true, planChosen: true, termsAccepted: true,
      billingEntered: true, activated: true, checklistReviewed: true,
    },
    healthScore: 86,
    churnRisk: "low",
    accountNotes: [
      { at: iso(30), by: "Maya Chen", note: "QBR done — happy with adoption, exploring custom domain add-on for FW26 launch." },
      { at: iso(90), by: "Devon Park", note: "Expanded from 40 to 120 live SKUs after strong pilot conversion metrics." },
    ],
    domain: { subdomain: "atelier-noir.vto.mirra.com" },
    createdAt: iso(160),
    previewToken: "pvt_atelier_9f2c1a",
  };

  const solstice: Tenant = {
    id: "t_solstice",
    slug: "solstice-swim",
    name: "Solstice Swim",
    storeUrl: "https://solsticeswim.co",
    storeOwnershipVerified: false,
    status: "onboarding",
    launchStatus: "not_launched",
    salesLed: false,
    billing: {
      planId: "boutique",
      interval: "monthly",
      addOns: [],
      paymentStatus: "none",
    },
    theme: {
      brandColor: "#0E3B43",
      accentColor: "#F4A259",
      logoText: "Solstice",
      welcomeHeadline: "Find your fit for the season.",
    },
    defaults: makeDefaults(),
    onboarding: {
      storeVerified: false, storeUrlConfirmed: false, shopifyConnected: false,
      teamInvited: false, planChosen: false, termsAccepted: false,
      billingEntered: false, activated: false, checklistReviewed: false,
    },
    healthScore: 61,
    churnRisk: "medium",
    accountNotes: [
      { at: iso(4), by: "Maya Chen", note: "Self-serve trial. Ready for onboarding." },
    ],
    domain: { subdomain: "solstice-swim.vto.mirra.com" },
    createdAt: iso(5),
    previewToken: "pvt_solstice_4d8b0e",
  };

  const verre: Tenant = {
    id: "t_verre",
    slug: "verre",
    name: "Maison Verre",
    storeUrl: "https://maisonverre.fr",
    storeOwnershipVerified: true,
    status: "suspended",
    launchStatus: "paused",
    salesLed: true,
    billing: {
      planId: "boutique",
      interval: "monthly",
      addOns: [],
      paymentStatus: "past_due",
      renewalDate: iso(18),
    },
    theme: {
      brandColor: "#2B2118",
      accentColor: "#C0B283",
      logoText: "Maison Verre",
      welcomeHeadline: "L'essayage, réinventé.",
    },
    defaults: makeDefaults("Maison Verre house chart"),
    onboarding: {
      storeVerified: true, storeUrlConfirmed: true, shopifyConnected: true,
      teamInvited: true, planChosen: true, termsAccepted: true,
      billingEntered: true, activated: true, checklistReviewed: true,
    },
    healthScore: 34,
    churnRisk: "high",
    accountNotes: [
      { at: iso(3), by: "Devon Park", note: "Card failed 3 dunning attempts. Public page auto-suspended. Reached out to finance contact." },
    ],
    domain: { subdomain: "verre.vto.mirra.com" },
    suspendedAt: iso(6),
    graceUntil: iso(-24),
    createdAt: iso(120),
    previewToken: "pvt_verre_71aa32",
  };

  // ------------------------------------------------------------ catalogue
  const products: Product[] = [
    makeProduct("p_an1", "t_atelier", "Colonne Slip Dress", "Dress", "Atelier Noir", "🖤", ["Noir", "Ivory"], ["XS", "S", "M", "L"], 340),
    makeProduct("p_an2", "t_atelier", "Rive Wrap Blouse", "Top", "Atelier Noir", "🎀", ["Noir", "Bordeaux"], ["S", "M", "L"], 210),
    makeProduct("p_an3", "t_atelier", "Marais Wide Trouser", "Bottom", "Atelier Noir", "👖", ["Noir", "Camel"], ["XS", "S", "M", "L"], 265),
    makeProduct("p_an4", "t_atelier", "Ombre Cashmere Crew", "Knitwear", "Atelier Noir", "🧶", ["Graphite"], ["S", "M", "L"], 390),
    makeProduct("p_an5", "t_atelier", "Sable Trench", "Outerwear", "Atelier Noir", "🧥", ["Sand"], ["S", "M", "L"], 620, { syncStatus: "error", syncError: "Variant image 404 from Shopify CDN" }),
    makeProduct("p_an6", "t_atelier", "Lune Silk Scarf", "Accessory", "Atelier Noir", "🧣", ["Print"], ["OS"], 120),
    makeProduct("p_ss1", "t_solstice", "Riptide One-Piece", "Swim", "Solstice Swim", "🩱", ["Sea Glass", "Coral"], ["XS", "S", "M", "L"], 128),
    makeProduct("p_ss2", "t_solstice", "Cove Bikini Top", "Swim", "Solstice Swim", "👙", ["Sea Glass", "Midnight"], ["S", "M", "L"], 72),
    makeProduct("p_ss3", "t_solstice", "Dune Linen Cover-Up", "Dress", "Solstice Swim", "🏖️", ["Natural"], ["S", "M", "L"], 96, { syncStatus: "pending" }),
    makeProduct("p_mv1", "t_verre", "Opaline Midi Dress", "Dress", "Maison Verre", "🥂", ["Champagne"], ["S", "M", "L"], 410),
    makeProduct("p_mv2", "t_verre", "Givre Mohair Cardigan", "Knitwear", "Maison Verre", "🧶", ["Frost"], ["S", "M", "L"], 350),
    // Freshly synced from Shopify and not yet digitised — this is what the
    // "Add a garment" screen exists for.
    makeProduct("p_an7", "t_atelier", "Perce Ribbed Tank", "Top", "Atelier Noir", "🎽", ["Chalk", "Slate"], ["XS", "S", "M", "L"], 145),
  ];

  const silk = [{ material: "Silk", pct: 92 }, { material: "Elastane", pct: 8 }];

  /** Everything a fully ingested, published garment carries. */
  const complete = {
    capture: "full" as const,
    sizeSource: "uploaded_chart" as const,
    sizeChartKind: "garment" as const,
    gradingSource: "chart" as const,
    fabricSource: "shopify" as const,
    fabricConfirmed: true,
    stage: "live" as const,
    tryOnEnabled: true,
  };

  const garments: Garment[] = ([
    makeGarment("g_an1n", products[0], "dress", {
      ...complete,
      colour: "Noir", referenceSize: "S", sizeChart: DRESS_CHART, fabricComposition: silk,
      silhouette: "fitted", fitCriticalAreas: ["bust", "hip"], behaviours: ["lining"],
      fitNotes: "Bias cut, skims the body. True to size; size up between sizes.",
      attributes: { stretch: "low", drape: "fluid", opacity: "opaque", thickness: "light" },
      tags: ["evening", "bestseller"], collections: ["Core"],
      publishedAt: iso(88),
    }),
    // Second colourway of the same product — reused the Noir geometry and
    // grading, so it only needed new colour imagery.
    makeGarment("g_an2n", products[1], "top", {
      ...complete,
      colour: "Noir", referenceSize: "M", sizeChart: TOP_CHART,
      fabricComposition: [{ material: "Viscose", pct: 100 }],
      silhouette: "relaxed", fitCriticalAreas: ["chest"], behaviours: ["wrap_closure"],
      fitNotes: "Relaxed through the shoulder, adjustable wrap waist.",
      attributes: { stretch: "none", drape: "fluid", opacity: "opaque", thickness: "light" },
      publishedAt: iso(45),
    }),
    // Waiting on Mirra QA — merchant has done everything they can.
    makeGarment("g_an2b", products[1], "top", {
      colour: "Bordeaux", referenceSize: "M", capture: "full", sizeChart: TOP_CHART,
      sizeSource: "brand_chart", sizeChartKind: "garment", gradingSource: "chart",
      fabricComposition: [{ material: "Viscose", pct: 100 }],
      fabricSource: "shopify", fabricConfirmed: true,
      silhouette: "relaxed", fitNotes: "Same block as the Noir colourway.",
      reusedFromGarmentId: "g_an2n",
      stage: "in_qa",
    }),
    makeGarment("g_an3n", products[2], "bottom", {
      ...complete,
      colour: "Noir", referenceSize: "S", sizeChart: BOTTOM_CHART,
      fabricComposition: [{ material: "Wool", pct: 70 }, { material: "Polyamide", pct: 30 }],
      silhouette: "relaxed", fitCriticalAreas: ["waist", "hip"], behaviours: ["rigid_waistband", "zip"],
      fitNotes: "High rise, full-length wide leg. Runs long.",
      attributes: { stretch: "low", drape: "structured", opacity: "opaque", thickness: "mid" },
      publishedAt: iso(45),
    }),
    // The worked example in the brief: capture started, nothing else done.
    makeGarment("g_an3c", products[2], "bottom", {
      colour: "Camel", capture: "partial", stage: "needs_data",
    }),
    makeGarment("g_an4", products[3], "knitwear", {
      ...complete,
      colour: "Graphite", referenceSize: "M", sizeChart: TOP_CHART,
      fabricComposition: [{ material: "Cashmere", pct: 100 }],
      silhouette: "oversized", fitCriticalAreas: ["chest"],
      fitNotes: "Boxy crew, cropped. Consider sizing down for a closer fit.",
      attributes: { stretch: "medium", drape: "moderate", opacity: "opaque", thickness: "mid" },
      publishedAt: iso(30),
    }),
    // Auto-measured from a single sample: sizes are a draft, not measurements.
    makeGarment("g_an5", products[4], "outerwear", {
      colour: "Sand", referenceSize: "S", capture: "full",
      sizeChart: TOP_CHART, sizeSource: "auto_measured", sizeChartKind: "garment",
      gradingSource: "estimated", gradingUnverified: true,
      autoMeasurements: {
        calibration: "known_dimension",
        sizeLabel: "S",
        values: [
          { key: "chest", valueCm: 108.4, confidence: "high" },
          { key: "shoulder", valueCm: 46.2, confidence: "high" },
          { key: "length", valueCm: 104.9, confidence: "review" },
          { key: "sleeve", valueCm: 61.5, confidence: "review" },
        ],
      },
      fabricComposition: [{ material: "Cotton", pct: 100 }],
      fabricSource: "estimated", attributesSuggested: true,
      silhouette: "oversized", fitNotes: "Oversized; model wears S.",
      stage: "needs_data",
    }),
    makeGarment("g_an6", products[5], "accessory", {
      colour: "Print", capture: "full", referenceSize: "OS",
      fabricComposition: silk, fabricSource: "shopify", fabricConfirmed: true,
      fitNotes: "90×90cm square.",
      stage: "paused", publishedAt: iso(20),
    }),
    makeGarment("g_ss1s", products[6], "swim", {
      ...complete,
      colour: "Sea Glass", referenceSize: "S", sizeChart: DRESS_CHART,
      sizeSource: "auto_measured",
      fabricComposition: [{ material: "Recycled nylon", pct: 82 }, { material: "Elastane", pct: 18 }],
      silhouette: "fitted", fitCriticalAreas: ["bust", "hip"],
      fitNotes: "Compressive fit; true to size.",
      attributes: { stretch: "high", drape: "moderate", opacity: "opaque", thickness: "light" },
      updatedBy: "Isla Berg", publishedAt: iso(2),
    }),
    // Mid-generation, so the merchant can carry on with sizing meanwhile.
    makeGarment("g_ss1c", products[6], "swim", {
      colour: "Coral", capture: "full", referenceSize: "S",
      stage: "processing", updatedBy: "Isla Berg",
    }),
    makeGarment("g_ss2s", products[7], "swim", {
      colour: "Sea Glass", updatedBy: "Isla Berg", stage: "draft",
    }),
    makeGarment("g_mv1", products[9], "dress", {
      colour: "Champagne", referenceSize: "M", capture: "full", sizeChart: DRESS_CHART,
      sizeSource: "tech_pack", sizeChartKind: "garment", gradingSource: "chart",
      fabricComposition: silk, fabricSource: "tech_pack", fabricConfirmed: true,
      silhouette: "relaxed", behaviours: ["belt"], fitNotes: "Fluid midi, self-belt.",
      updatedBy: "Camille Roux", stage: "paused", publishedAt: iso(80),
    }),
    makeGarment("g_mv2", products[10], "knitwear", {
      colour: "Frost", referenceSize: "M", capture: "full", sizeChart: TOP_CHART,
      sizeSource: "brand_chart", sizeChartKind: "body", gradingSource: "rules",
      fabricComposition: [{ material: "Mohair", pct: 45 }, { material: "Wool", pct: 40 }, { material: "Polyamide", pct: 15 }],
      fabricSource: "manual", fabricConfirmed: true,
      silhouette: "relaxed", fitNotes: "Relaxed fit.",
      updatedBy: "Camille Roux", stage: "paused", publishedAt: iso(70),
    }),
  ] as Garment[]).map(withApproval);

  // ------------------------------------------------------------- analytics
  const analyticsEvents: AnalyticsEvent[] = [];
  let ai = 0;
  const liveGarments = ["g_an1n", "g_an2n", "g_an3n", "g_an4"];
  for (let d = 30; d >= 1; d--) {
    const lift = 1 + (30 - d) * 0.06; // gentle adoption growth
    const visits = Math.round((28 + (d % 5) * 6) * lift);
    const clicks = Math.round(visits * 0.42);
    const starts = Math.round(clicks * 0.78);
    const completes = Math.round(starts * (0.62 + (d % 3) * 0.04));
    const push = (type: AnalyticsEvent["type"], count: number) => {
      for (let i = 0; i < count; i++) {
        analyticsEvents.push({
          id: `ae_${ai++}`,
          tenantId: "t_atelier",
          type,
          garmentId: type === "sku_view" || type === "tryon_click" ? liveGarments[i % liveGarments.length] : undefined,
          source: "public",
          at: iso(d, 9 + (i % 10)),
        });
      }
    };
    push("page_view", visits);
    push("tryon_click", clicks);
    push("session_start", starts);
    push("session_complete", completes);
    push("sku_view", Math.round(visits * 0.9));
  }
  for (let d = 3; d >= 1; d--) {
    for (let i = 0; i < 6; i++) {
      analyticsEvents.push({
        id: `ae_${ai++}`, tenantId: "t_solstice", type: i % 2 ? "page_view" : "tryon_click",
        garmentId: i % 2 ? undefined : "g_ss1s", source: "preview", at: iso(d, 11 + i),
      });
    }
  }

  return {
    plans: PLANS,
    users: [
      { id: "u_admin", name: "Devon Park", email: "devon@mirra.com", internalRole: "mirra_admin" },
      { id: "u_sales", name: "Ravi Menon", email: "ravi@mirra.com", internalRole: "mirra_sales" },
      { id: "u_support", name: "Maya Chen", email: "maya@mirra.com", internalRole: "mirra_support" },
      { id: "u_owner", name: "Elodie Marchand", email: "elodie@ateliernoir.com" },
      { id: "u_merch", name: "Priya Nair", email: "priya@ateliernoir.com" },
      { id: "u_finance", name: "Tomas Lind", email: "tomas@ateliernoir.com" },
      { id: "u_viewer", name: "June Okafor", email: "june@ateliernoir.com" },
      { id: "u_solstice", name: "Isla Berg", email: "isla@solsticeswim.co" },
      { id: "u_verre", name: "Camille Roux", email: "camille@maisonverre.fr" },
    ],
    memberships: [
      { userId: "u_owner", tenantId: "t_atelier", role: "brand_owner", status: "active" },
      { userId: "u_merch", tenantId: "t_atelier", role: "brand_merchandiser", status: "active" },
      { userId: "u_finance", tenantId: "t_atelier", role: "brand_finance", status: "active" },
      { userId: "u_viewer", tenantId: "t_atelier", role: "brand_viewer", status: "active" },
      { userId: "u_solstice", tenantId: "t_solstice", role: "brand_owner", status: "active" },
      { userId: "u_verre", tenantId: "t_verre", role: "brand_owner", status: "active" },
    ],
    tenants: [atelierNoir, solstice, verre],
    leads: [
      {
        id: "l_1", company: "Harbour & Fray", contactName: "Nina Fray", email: "nina@harbourfray.com",
        storeUrl: "https://harbourfray.com", role: "founder", monthlyOrders: "10k-50k",
        goals: "Returns from sizing are our biggest cost line. We want shoppers to see fit on their own body before they buy.",
        source: "demo_request", status: "qualified", ownerId: "u_sales",
        notes: ["Strong fit — DTC womenswear, high AOV.", "Demo booked for Jul 17."], createdAt: iso(6),
      },
      {
        id: "l_2", company: "Kōyō Studio", contactName: "Aki Tan", email: "aki@koyostudio.jp",
        storeUrl: "https://koyostudio.jp", role: "ecommerce", monthlyOrders: "1k-10k",
        goals: "Small run capsule collections. We would start with one drop and expand if try-on converts.",
        source: "early_access", status: "qualifying", ownerId: "u_sales",
        notes: ["Waiting on catalogue size confirmation."], createdAt: iso(3),
      },
      {
        id: "l_3", company: "Bramble Kids", contactName: "Sam Ortiz", email: "sam@bramblekids.com",
        storeUrl: "https://bramblekids.com", role: "product", monthlyOrders: "50k-plus",
        goals: "Childrenswear sizing varies wildly between our suppliers and parents cannot tell from a photo.",
        source: "contact_sales", status: "new", notes: [], createdAt: iso(1),
      },
    ],
    products,
    garments,
    syncRuns: [
      { id: "sr_1", tenantId: "t_atelier", trigger: "webhook", startedAt: iso(0, 6), finishedAt: iso(0, 6), status: "partial", itemsSynced: 22, failures: [{ item: "Sable Trench", error: "Variant image 404 from Shopify CDN" }] },
      { id: "sr_2", tenantId: "t_atelier", trigger: "reconciliation", startedAt: iso(1, 3), finishedAt: iso(1, 3), status: "success", itemsSynced: 23, failures: [] },
      { id: "sr_3", tenantId: "t_solstice", trigger: "manual", startedAt: iso(0, 8), finishedAt: iso(0, 8), status: "success", itemsSynced: 3, failures: [] },
      { id: "sr_4", tenantId: "t_verre", trigger: "reconciliation", startedAt: iso(2, 3), finishedAt: iso(2, 3), status: "success", itemsSynced: 2, failures: [] },
    ],
    tickets: [
      {
        id: "tk_1", tenantId: "t_atelier", subject: "Trench images failing to sync",
        category: "catalogue", priority: "normal", status: "open", createdById: "u_merch", createdAt: iso(1),
        messages: [
          { at: iso(1), from: "Priya Nair", internal: false, body: "The Sable Trench keeps showing a sync error — images 404. Can you take a look?" },
          { at: iso(0, 9), from: "Maya Chen", internal: false, body: "Looking into it — the CDN URL from Shopify returns 404. Can you re-upload the front image in Shopify and we'll re-sync?" },
        ],
      },
      {
        id: "tk_2", tenantId: "t_atelier", subject: "Invoice copy for FY26 audit",
        category: "billing", priority: "low", status: "resolved", createdById: "u_finance", createdAt: iso(12),
        messages: [
          { at: iso(12), from: "Tomas Lind", internal: false, body: "Need consolidated invoices Jan–Jun for our audit." },
          { at: iso(11), from: "Maya Chen", internal: false, body: "Sent to your billing email — also available anytime under Billing → Invoices." },
        ],
      },
      {
        id: "tk_3", tenantId: "t_solstice", subject: "How do size charts affect fit accuracy?",
        category: "onboarding", priority: "normal", status: "pending", createdById: "u_solstice", createdAt: iso(2),
        messages: [
          { at: iso(2), from: "Isla Berg", internal: false, body: "Do I need full measurements for every SKU before launch?" },
        ],
      },
    ],
    auditEvents: [
      { id: "au_1", tenantId: "t_atelier", actorId: "u_merch", actorName: "Priya Nair", action: "garment.publish", target: "Ombre Cashmere Crew — Graphite", at: iso(30) },
      { id: "au_2", tenantId: "t_atelier", actorId: "u_merch", actorName: "Priya Nair", action: "garment.pause", target: "Lune Silk Scarf — Print", detail: "Awaiting new detail imagery", at: iso(8) },
      { id: "au_3", tenantId: "t_atelier", actorId: "u_owner", actorName: "Elodie Marchand", action: "team.invite", target: "june@ateliernoir.com (viewer)", at: iso(40) },
      { id: "au_4", tenantId: "t_verre", actorId: "system", actorName: "System", action: "tenant.suspend", target: "Maison Verre", detail: "Payment past due after 3 dunning attempts", at: iso(6) },
      { id: "au_5", tenantId: "t_atelier", actorId: "u_support", actorName: "Maya Chen", action: "impersonation.start", target: "Atelier Noir workspace", detail: "Ticket tk_1 investigation", at: iso(1) },
    ],
    billingEvents: [
      { id: "be_1", tenantId: "t_atelier", type: "subscription_created", detail: "Atelier plan, annual", at: iso(150) },
      { id: "be_2", tenantId: "t_atelier", type: "payment_succeeded", detail: "$8,990 annual renewal", at: iso(150) },
      { id: "be_3", tenantId: "t_solstice", type: "trial_started", detail: "Boutique trial (14 days)", at: iso(5) },
      { id: "be_4", tenantId: "t_verre", type: "payment_failed", detail: "$299 monthly — card declined (attempt 3/3)", at: iso(6) },
    ],
    analyticsEvents,
  };
}
