import type { MeasurementField, PublicProduct } from "@/integrations/mirra-api/types";
import { swatchDataUri } from "./placeholder";

/**
 * Sample catalogue for local dev / the pilot demo. Not a line-for-line port
 * of user-side's fixtures.ts (~600 lines, largely tenant/entitlement logic
 * that no longer applies) — a smaller, purpose-built set covering the
 * "choose clothes from preset" step with real variety (category, price,
 * try-on eligibility, an out-of-stock case).
 */

interface GarmentSpec {
  id: string;
  name: string;
  subtitle?: string;
  category: string;
  garmentCategory: PublicProduct["garmentCategory"];
  price: number;
  colors: { name: string; hex: string }[];
  sizes?: string[];
  tryOnEligible?: boolean;
}

const SPECS: GarmentSpec[] = [
  {
    id: "shirt-oxford-noir",
    name: "Oxford Shirt: Noir",
    category: "Shirts",
    garmentCategory: "top",
    price: 3200,
    colors: [
      { name: "Black", hex: "#1c1c1e" },
      { name: "Sand", hex: "#cfc3b0" },
      { name: "Lilac", hex: "#d9d4ec" },
    ],
  },
  {
    id: "shirt-linen-dune",
    name: "Linen Shirt: Dune",
    category: "Shirts",
    garmentCategory: "top",
    price: 2800,
    colors: [{ name: "Sand", hex: "#cfc3b0" }],
  },
  {
    id: "tee-studio-cloud",
    name: "Studio Tee: Cloud",
    category: "T-Shirts",
    garmentCategory: "top",
    price: 1200,
    colors: [{ name: "Cloud", hex: "#f2f0ea" }],
  },
  {
    id: "tee-heavy-olive",
    name: "Heavy Tee: Olive",
    category: "T-Shirts",
    garmentCategory: "top",
    price: 1400,
    colors: [{ name: "Olive", hex: "#8a8a72" }],
  },
  {
    id: "hoodie-graphite",
    name: "Graphite Hoodie",
    category: "Outerwear",
    garmentCategory: "outerwear",
    price: 4200,
    colors: [{ name: "Graphite", hex: "#1d1d20" }],
  },
  {
    id: "polo-knit-ash",
    name: "Knit Polo: Ash",
    category: "Shirts",
    garmentCategory: "top",
    price: 2600,
    colors: [{ name: "Ash", hex: "#b9bcbf" }],
  },
  {
    id: "trouser-tailored-charcoal",
    name: "Tailored Trouser: Charcoal",
    category: "Trousers",
    garmentCategory: "bottom",
    price: 3600,
    colors: [{ name: "Charcoal", hex: "#33343a" }],
  },
  {
    id: "denim-straight-indigo",
    name: "Straight Denim: Indigo",
    category: "Denim",
    garmentCategory: "bottom",
    price: 3100,
    colors: [{ name: "Indigo", hex: "#3d5a80" }],
  },
  {
    id: "overshirt-flannel-umber",
    name: "Flannel Overshirt: Umber",
    category: "Outerwear",
    garmentCategory: "outerwear",
    price: 3900,
    colors: [{ name: "Umber", hex: "#7a4b32" }],
    tryOnEligible: false, // demonstrates the "still preparing this garment" path
  },
];

const SIZES = ["XS", "S", "M", "L", "XL"];

function buildProduct(spec: GarmentSpec): PublicProduct {
  const tryOnEligible = spec.tryOnEligible ?? true;
  return {
    publicProductId: spec.id,
    name: spec.name,
    subtitle: spec.subtitle ?? null,
    category: spec.category,
    garmentCategory: spec.garmentCategory,
    description: null,
    materialAndCare: null,
    manufacturingInfo: null,
    fitInfo: "True to size — model is wearing size M.",
    taxNote: null,
    price: spec.price,
    currency: "INR",
    thumbnailUrl: swatchDataUri(spec.colors[0].hex),
    publicationStatus: "published",
    tryOnEligible,
    sizeChart: null,
    variants: spec.colors.flatMap((color) =>
      (spec.sizes ?? SIZES).map((size) => ({
        publicVariantId: `${spec.id}::${color.name.toLowerCase()}::${size}`,
        colorName: color.name,
        colorSwatch: color.hex,
        size,
        price: spec.price,
        currency: "INR",
        inStock: !(spec.id === "denim-straight-indigo" && size === "XS"),
        tryOnEligible,
        garmentAssetUrl: tryOnEligible ? swatchDataUri(color.hex, spec.name) : null,
        assetStatus: tryOnEligible ? "ready" : "processing",
      })),
    ),
  };
}

export const mockProducts: PublicProduct[] = SPECS.map(buildProduct);

export const mockCategories = Array.from(new Set(mockProducts.map((p) => p.category)));

export function freshMeasurements(): MeasurementField[] {
  return [
    {
      key: "height",
      label: "Height",
      value: 178,
      unit: "cm",
      min: 120,
      max: 230,
      step: 1,
      estimated: true,
      supported: true,
    },
    {
      key: "weight",
      label: "Weight",
      value: 74,
      unit: "kg",
      min: 30,
      max: 250,
      step: 1,
      estimated: true,
      supported: true,
    },
    {
      key: "chest",
      label: "Chest",
      value: 99,
      unit: "cm",
      min: 50,
      max: 180,
      step: 1,
      estimated: true,
      supported: true,
    },
    {
      key: "waist",
      label: "Waist",
      value: 84,
      unit: "cm",
      min: 40,
      max: 220,
      step: 1,
      estimated: true,
      supported: true,
    },
    {
      key: "hips",
      label: "Hips",
      value: 97,
      unit: "cm",
      min: 50,
      max: 220,
      step: 1,
      estimated: true,
      supported: true,
    },
    {
      key: "shoulderWidth",
      label: "Shoulder width",
      value: 45,
      unit: "cm",
      min: 20,
      max: 80,
      step: 1,
      estimated: true,
      supported: true,
    },
    {
      key: "inseam",
      label: "Inseam",
      value: 81,
      unit: "cm",
      min: 40,
      max: 140,
      step: 1,
      estimated: true,
      supported: true,
    },
  ];
}
