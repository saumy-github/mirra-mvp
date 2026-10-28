# 20 — Merchant portal: one source of truth per tenant (2026-10-10)

## What was wrong

- A real workspace (business sign-in via `/dashboard/start`) only had Digitise,
  the Shopify card and the seat card on the backend; every other page read the
  seeded in-memory store. A garment made in Digitise vanished from Garments,
  Overview and Publication.
- Digitise could not be completed: readiness blocked on material and variant
  mapping, ingestion refused without sizing rows, and no screen called
  `setMaterial` / `setSizing` / `confirmVariantMapping`.
- No QA surface (`approve`, `addQaFinding` unused); a blocking QA finding could
  never be resolved, so one rejection locked a garment permanently;
  `set_stage("ready")` skipped the approval snapshot.
- Demo tenant (Quick Access) could open Digitise and call the API with a fake id.
- Live tenants always showed "public try-on page offline" (mirrored as
  `not_launched`; the backend has no launch gate).
- Seated colleagues never appeared on Team; reload lost the current page.

## What changed

Backend (`src/merchant/`): `GET/DELETE /{t}/members`, `POST
/{t}/garments/{g}/qa/findings/{f}/resolve`, `set_stage` refuses `ready`
(code `use_approve`), QA finding severity validated (422 not 500). 4 new tests.

Frontend (`features/dashboard/`):
- Digitise gains Material and Sizing steps, resumes at the first outstanding
  step, and Review covers QA approve/request-changes, findings, `qa_changes`,
  and resume-from-paused, gated by the backend role (`liveCan`).
- `ByTenant` routes Overview/Products/Garments/Publication/Team to
  `pages/portal/live/*` for a real workspace; demo keeps the old pages.
- `DemoOnly` hides and guards Assets, Size & fit, Fabric, Analytics, Billing,
  Support, Audit for real workspaces (no backend for them yet). Settings shows
  only Store + Shopify for real workspaces. Separate "Digitise" nav item removed.
- Digitise ↔ GarmentFlow / GarmentDetail redirect to the right flow per tenant.
- `/dashboard/start?next=` restores the page after a reload.

Verified: backend merchant suite 75 passed; frontend tsc, eslint, 88 tests and
`npm run build` pass. Not verified in a browser (extension not connected) and
not against a live CLO run.

## Still open

Analytics, billing, support tickets, audit log, theme/domains and sold-out
defaults have no backend; phone capture, `/dashboard/preview/:slug` and the
`/dashboard/login` persona picker are still demo-only.
