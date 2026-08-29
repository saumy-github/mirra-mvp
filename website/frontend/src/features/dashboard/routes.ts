/**
 * Every dashboard path in one place. The prototype lived at the site root
 * (`/portal`, `/admin`); here the whole surface is namespaced under
 * `/dashboard` so it cannot collide with the shopper-facing routes in
 * `src/router.tsx`.
 */
export const DASH = "/dashboard";

/** Steps of the add-a-garment flow, addressable via `?step=`. */
export type GarmentFlowStep = "identify" | "capture" | "material" | "sizing" | "review";

export const dashPath = {
  login: `${DASH}/login`,
  onboarding: `${DASH}/onboarding`,

  portal: `${DASH}/portal`,
  products: `${DASH}/portal/products`,
  garments: `${DASH}/portal/garments`,
  /**
   * "+ Add garment" — opens the ingestion flow itself, which starts by asking
   * which colourway is being added and then goes straight into capture.
   */
  addGarment: `${DASH}/portal/garments/new`,
  /** The garment's summary page — everything about it, read at a glance. */
  garment: (id: string) => `${DASH}/portal/garments/${id}`,
  /**
   * The guided setup flow. Omitting `step` lands on the first outstanding one,
   * so "continue setup" always resumes rather than restarting.
   */
  garmentFlow: (id: string, step?: GarmentFlowStep) =>
    step
      ? `${DASH}/portal/garments/${id}/setup?step=${step}`
      : `${DASH}/portal/garments/${id}/setup`,
  assets: `${DASH}/portal/assets`,
  sizeFit: `${DASH}/portal/size-fit`,
  fabric: `${DASH}/portal/fabric`,
  publication: `${DASH}/portal/publication`,
  analytics: `${DASH}/portal/analytics`,
  team: `${DASH}/portal/team`,
  billing: `${DASH}/portal/billing`,
  support: `${DASH}/portal/support`,
  guides: `${DASH}/portal/support/guides`,
  guide: (slug: string) => `${DASH}/portal/support/guides/${slug}`,
  settings: `${DASH}/portal/settings`,
  audit: `${DASH}/portal/audit`,

  /**
   * The merchant's own preview of their tenant surface, rendered from the
   * same `publicCatalogue()` contract the storefront consumes — including
   * QA-approved content that isn't published yet, clearly marked as such.
   */
  preview: (slug: string, token?: string) =>
    token ? `${DASH}/preview/${slug}?token=${token}` : `${DASH}/preview/${slug}`,

  admin: `${DASH}/admin`,
  adminLeads: `${DASH}/admin/leads`,
  adminSupport: `${DASH}/admin/support`,
  adminSync: `${DASH}/admin/sync`,
  adminChurn: `${DASH}/admin/churn`,
  adminTenant: (id: string) => `${DASH}/admin/tenants/${id}`,

  /** This repo's shopper-facing try-on surface. */
  tryOnStudio: "/studio",
} as const;

/**
 * The shopper-facing addresses a merchant hands out: one company URL, and a
 * unique URL per garment so a brand can link try-on from a product page.
 *
 * The public host itself is provisioned with the tenant and served by the
 * backend. What a merchant can check *today* is the preview route above,
 * which renders the exact resolved catalogue those addresses will serve —
 * so a link is never handed out on trust alone.
 */
export const publicUrl = {
  tenant: (subdomain: string) => `https://${subdomain}`,
  garment: (subdomain: string, garmentId: string) => `https://${subdomain}/g/${garmentId}`,
  /** Token-scoped preview, resolvable in-app right now via `dashPath.preview`. */
  preview: (slug: string, previewToken: string) =>
    `${window.location.origin}${DASH}/preview/${slug}?token=${previewToken}`,
};
