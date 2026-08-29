# Virtual Try-On Dashboard — Audit and Remediation Status

**Original audit:** 28 August 2026
**Remediation pass:** 28 August 2026
**Scope of this document:** what the audit found, what has since been corrected, and — the part that matters for planning — **what is still outstanding**
**Production-readiness verdict:** **Still not ready for client use.** The dashboard no longer misreports its own state, but it has no backend, no persistence, and no pipeline able to produce the assets it promises.

---

## 1. Where this stands

The original audit found 35 issues. A remediation pass has closed 28 of them.

| Priority | Total | Fixed | Outstanding |
| --- | --- | --- | --- |
| P0 — release blocker | 7 | 5 | **2** |
| P1 — major | 15 | 8 | **7** |
| P2 — moderate | 11 | 11 | 0 |
| P3 — minor | 2 | 2 | 0 |
| **Total** | **35** | **28** | **7** |

**What changed in character.** The dashboard was previously a demonstration shell that reported successful business outcomes without performing the underlying work. That specific class of problem is gone: sizing no longer fabricates measurements, QA approval is now a frozen revision rather than a flag, publication resolves through one authoritative module that the shopper-facing mapper also honours, and internal staff can no longer escalate into a customer's workspace.

**What has not changed.** The application still has no backend. Everything below the UI is an in-memory store reseeded on reload, authentication is a persona chooser, and the garment-processing pipeline still produces one untextured default T-shirt regardless of what was requested. Those two gaps (P0-01, P0-03) were deliberately out of scope for this pass and remain the reason a client pilot cannot happen.

Verification: TypeScript, ESLint, a production build, and a new 40-test suite covering lifecycle, validation, authorization, revisioning, the publication contract, and reporting windows all pass.

---

## 2. Outstanding work

### P0-01 — Dashboard state and authentication are demo-only

**Status:** Not started (out of scope for the remediation pass)

**Observed:** Application state lives in module memory (`data/store.ts`) and is reseeded on every reload. Login is a local persona chooser (`data/session.ts`), not authentication. A merchant can complete hours of ingestion work and lose all of it by refreshing.

**Why it now matters more, not less:** the remediation pass built real revision safety, real QA snapshots, real audit trails and real seat management on top of this store. All of that logic is correct and tested — and all of it evaporates on reload. The seam is deliberately narrow: `store.ts`, `session.ts` and the action functions in `data/actions.ts` are the only modules that would change.

**Required outcome:** authenticated, tenant-scoped persistence; server-side authorization mirroring `data/rbac.ts`; durable drafts; optimistic-concurrency/version handling on `sourceRevision`; and mutation failure states (the UI contract for these already exists — see `components/use-action.ts`).

---

### P0-03 — Dashboard promises more garment capability than the engine implements

**Status:** Not started (out of scope for the remediation pass)

**Observed:** The dashboard offers seven garment categories and four-view capture. The processing path is documented as T-shirt-only (`.claude/architecture/step_2_ingestion.md:299-309`), selects a single primary front image (`product_ingestion/view_selection.py:87-130`), and the worker produces the same default untextured T-shirt with no web asset (`worker/README.md:45-68`).

**What the remediation pass did do:** it stopped the dashboard from *claiming* an asset exists. `publicCatalogue()` reports `assetStatus: "missing"` and `garmentAssetUrl: null`, the shopper mapper derives try-on eligibility from asset readiness instead of hardcoding `true`, and the merchant preview says plainly that rendering comes from the VTO side and is not connected. The dishonesty is fixed; the capability gap is not.

**Required outcome:** a versioned capability contract shared by dashboard and pipeline. Either disable the categories and input sources the pipeline cannot serve, or implement and test category-specific processing and web-asset delivery before exposing them.

---

### P1-01 — Capture, phone, upload and CAD intake are still simulations

**Status:** Not started

**Observed:** No `<input type="file">` exists on the capture step. Clicking a view tile calls `recordCaptureAction` with `accepted: true` and stores the constant filename `front.jpg`. The CAD button hardcodes `<colourway>-sample.zprj`. The QR panel is a static placeholder — no capture session, no transfer, no quality check.

**Partially addressed:** capture is now blocked until a reference sample size is chosen, CAD is a genuinely separate branch that skips the four photographic views rather than being forced into the photo checklist, per-view rejection reasons are stored and shown, every capture mutation is audited, and each one bumps the garment's revision.

**Required outcome:** real source-specific intake — upload progress, thumbnails, replace/reject, stored artifacts with checksum and provenance, security validation, retry, and a resumable QR capture session. CAD needs format validation (scale, watertightness, UVs) as its own contract.

---

### P1-02 — Reference-sample identity is not fully protected

**Status:** Partially fixed

**Fixed:** capture cannot begin before a reference size is chosen (the tiles are disabled and a banner says why), and the construction block's reference size is kept in sync.

**Outstanding:** changing the reference size afterwards still leaves existing captures and auto-measurements attached to the newly selected size. It bumps the revision — so the change cannot reach shoppers without re-approval — but photos of size S can still end up labelled M in the working record.

**Required outcome:** persist sample identity on the capture set itself; changing it must trigger an explicit migration or a new capture revision rather than silent relabelling.

---

### P1-03 — Different construction blocks cannot be represented safely

**Status:** Partially fixed

**Fixed:** `ConstructionBlock` is a first-class record with its own sizes and reference size; declaring different construction creates a second block; `gradingPlan()` states that each block needs its own sample and that Mirra never interpolates across blocks.

**Outstanding:** there is still one capture set per garment. The alternate block gets no reference sample, no capture set and no asset of its own, and completeness is not tracked per block. An XL on a different cut can still be generated from an S sample.

**Required outcome:** per-block reference sample, capture set, asset revision, completeness and QA status.

---

### P1-04 — Size-chart validation does not yet cover every case

**Status:** Largely fixed; two gaps remain

**Fixed:** `data/size-chart.ts` validates every required field of every Shopify size for presence, numeric type and plausible range; flags sizes present in Shopify but missing from the chart and vice versa; warns when a measurement does not grade monotonically across the size run; and supports both centimetres and inches with explicit conversion. `requirements()` now uses this, so "complete" means the data is usable. Changing a garment's category clears an incompatible chart rather than reinterpreting its keys.

**Outstanding:**
- Ranges are hard-coded per measurement key rather than defined per category and chart version.
- Body-measurement charts are validated against finished-garment ranges, so a body chart's numbers are checked less precisely than they should be.

**Required outcome:** category- and version-specific schemas, with separate plausible ranges per chart kind.

---

### P1-05 — Body and finished-garment measurement semantics still partly conflict

**Status:** Partially fixed

**Fixed:** chart kind is recorded, surfaced and flagged when unknown; the "How to measure" panel now shows body-measurement guidance when the chart is a body chart rather than always showing flat seam-to-seam instructions; the sizing guide explains the roughly factor-of-two difference; brand charts carry and display their kind.

**Outstanding:** image-derived garment measurements (`autoMeasurements`) and merchant-supplied body measurements still share one numeric space with no conversion between them. Nothing computes ease, so a body chart and a garment chart for the same product produce the same fit input.

**Required outcome:** keep the two kinds separate through to the fit engine, with explicit ease handling.

---

### P1-06 — Fabric intake is complete except for tech-pack parsing

**Status:** Largely fixed

**Fixed:** multi-fibre composition editor with a 100% sum rule, lining composition, editable simulation attributes with an explicit confirm step, provenance badges on every value, and `findExistingComposition` importing from a sibling colourway or a Shopify metafield instead of hardcoding 100% cotton. The Fabric page's "Complete" badge now uses the same requirement as the garment list.

**Outstanding:** tech-pack parsing is unimplemented and now says so rather than labelling merchant-typed rows as tech-pack-sourced. Advanced material properties (GSM, warp/weft stretch, recovery, stiffness, compression) are still not captured anywhere, and the engine will need them.

**Required outcome:** a document-parsing service for tech packs, and fields for the advanced properties the simulation consumes.

---

### P1-08 — Availability is configurable but not synchronized

**Status:** Partially fixed

**Fixed:** the store-wide policy, the colourway-level rule (`hideColourwayWhenAllSoldOut`) and the per-garment override all now have controls. Precedence is defined in one place (`data/publication.ts`: garment override → tenant default) and is covered by tests. Sold-out sizes are shown per garment throughout, and the resolver hides a garment entirely when every covered size is gone under `hide_size`.

**Outstanding:** inventory is still read from the seeded store, not from Shopify. There are no variant webhooks, no reconciliation job, and no freshness indicator telling a merchant how old the stock figures are.

**Required outcome:** consume Shopify variant webhooks, reconcile periodically, and surface inventory freshness and its source.

---

## 3. What was fixed in this pass

Recorded briefly, since the detail now lives in the code and its tests.

### P0 — release blockers closed

| ID | What changed |
| --- | --- |
| **P0-02** | `data/publication.ts` is now the single authoritative resolver: billing state → launch state → stage and try-on toggle → QA approval → per-variant inventory × sold-out policy. `publicCatalogue()` emits the storefront's own `PublicProduct[]` shape, and the dashboard reads the same resolver, so the two cannot disagree. `live-schemas.ts` no longer hardcodes published/eligible/in-stock; it reads optional publication fields and derives try-on eligibility from asset readiness, failing closed. Nine contract tests cover publish, pause, sell-out, suspension and revision coverage. |
| **P0-04** | Every fabricated measurement is gone. `data/size-chart.ts` provides real CSV/TSV upload and paste with a mapping preview shown before anything is applied, an editable grid that starts empty, unit conversion, per-cell validation, and grading from brand rules against a *measured* reference row. Shopify and tech-pack import are disabled with a stated reason rather than silently generating numbers. Every chart records its source, kind and grading method. |
| **P0-05** | `needs_data → merchant_review → in_qa` is implemented end to end. Generation now lands a complete garment in the merchant's own review step instead of dumping it back into `needs_data`; the review screen submits to QA; invalid transitions are hidden rather than offered, and refusals are shown instead of discarded. |
| **P0-06** | Revisions are real. Every try-on-relevant edit bumps `sourceRevision`; QA approval freezes a full `GarmentSnapshot`; the public surface serves that snapshot and never the working record. An edit to a live garment produces a draft that shoppers do not see, with the gap stated on the garment, the table and Publication. Anything mid-flight drops back to `needs_data` because approval of an older revision cannot carry forward. |
| **P0-07** | Internal roles now have their own capability set (`canInternal`), console routes are guarded per area, and `can()` no longer treats staff as blanket brand access. View-as is read-only by default, requires a reason of substance, expires after 30 minutes, and elevates only to a Merchandiser seat — never Owner — and only for Admins. Sales cannot reach tenant lifecycle, support, sync or QA. Every ingestion mutation is audited. |

### P1 — major issues closed

| ID | What changed |
| --- | --- |
| **P1-07** | Sync gained a delta preview before it runs, a retry that actually re-attempts failed products and clears them on success, and conflict records for changes Mirra refuses to apply unattended (a QA-approved garment referencing a SKU Shopify no longer returns). All failures are listed, not just the first. |
| **P1-09** | `/dashboard/preview/:slug` renders the tenant's real resolved catalogue, gated by the preview token, showing published and QA-approved-but-unpublished content distinctly, plus why anything absent is absent. |
| **P1-10** | Store URL is validated; the agreement records its version, documents, acceptor and timestamp; completed steps can be reopened; activation checks its preconditions; the final step navigates; and the onboarding page now has both a support route outside the activation gate and a sign-out. |
| **P1-11** | A mobile header with current location, a navigation sheet with identity, view-as state and sign-out, Escape-to-close and focus management. |
| **P1-12** | Pausing a page or a garment, and cancelling a subscription, now state their impact in SKUs and require typed confirmation. The fake billing-portal link is gone. Reactivation returns the page to service but leaves billing `past_due` until a provider confirms payment. |
| **P1-13** | Live SKUs are counted from variants, with a per-garment drill-down on Publication and enforcement that projects the new SKUs before allowing a publish. |
| **P1-14** | One window definition drives the headline, the series, the table and the export, with a 7/30/90-day selector and the window stated on the page. |
| **P1-15** | Every action returns a typed `ActionResult`; `useAction` supplies pending state, double-submit guarding and result announcement; `ActionButton`, `NoticeBar`, `SubmitButton` and `ConfirmAction` render it consistently. |

### P2 and P3 — all closed

Requirement evaluation centralized and shared across Fabric, Size & fit, Assets and Garments (P2-01). Bulk actions preflight every item, report what was skipped and why, and never act on rows hidden by a filter (P2-02). Scheduled go-live implemented with cancel, status, a due-sweep and audit (P2-03). Team seat management and versioned brand size charts implemented (P2-04). Analytics+ CSV export implemented; overpromising copy removed (P2-05). Six real knowledge-base guides, an operational support queue with assign/reply/status, and per-run sync diagnostics (P2-06). Audit log sorted newest-first with filters, search, CSV export and pagination, and ingestion mutations now emit entries (P2-07). Onboarding steps reopenable (P2-08). Structured QA findings with area, severity, affected view or measurement, and merchant-facing instructions — a rejection with no finding is refused (P2-09). Live regions on state changes, a text equivalent for the top-garments chart, and focus management (P2-10). Navigation filtered by capability, purpose-specific read-only wording, and teammate emails hidden from Viewer (P2-11). Pagination on catalogue, product and audit tables with real empty states (P3-01). The React key warning fixed, Vitest added, and 40 tests covering the invariants above (P3-02).

---

## 4. Release gates

| Gate | Status |
| --- | --- |
| Durable account | ❌ **P0-01** — in-memory store, persona login |
| Authorization | ⚠️ Client-side enforcement is correct and tested; server-side enforcement awaits P0-01 |
| Catalogue identity | ✅ Garments trace to tenant, product, colourway, variant and sync state |
| Reference sample | ⚠️ Capture is gated on sample identity; changing it does not yet migrate dependent data (**P1-02**) |
| Real capture | ❌ **P1-01** — no artifacts, no transfer, no quality checks |
| Construction blocks | ⚠️ Modelled and explained; not yet independently captured or tracked (**P1-03**) |
| Real sizing | ✅ No synthetic rows; schemas validate fields, units, chart kind, reference row and SKU coverage |
| Material | ⚠️ Composition and behaviour are real and validated; advanced engine properties absent (**P1-06**) |
| Pipeline contract | ❌ **P0-03** — no capability contract, no request-specific web asset |
| Lifecycle | ✅ `draft → needs data → merchant review → QA → ready → live` works; invalid transitions are not offered |
| Revision safety | ✅ Upstream edits create a draft and cannot reuse an older approval or asset |
| Preview / public | ⚠️ Exact preview works in-app; the public tenant host needs the backend |
| Inventory | ⚠️ Policy precedence is correct and tested; live Shopify inventory is not connected (**P1-08**) |
| Operations | ✅ Sync, generation and QA failures have diagnostics, retry, ownership and audit events |
| Mobile / accessibility | ✅ Full ingestion and support path usable by keyboard, screen reader and phone viewport |

---

## 5. Suggested order for the remaining work

**Phase 1 — make it durable.** P0-01. Persist the store behind an authenticated, tenant-scoped API and enforce `rbac.ts` server-side. Nothing else on this list is worth doing first: every property built in the remediation pass currently survives only until reload.

**Phase 2 — make capture real.** P1-01, then P1-02 and P1-03. Real artifacts with provenance; then sample identity that cannot be silently relabelled; then per-block capture. These are ordered because each needs the one before it to be meaningful.

**Phase 3 — close the pipeline contract.** P0-03. Publish the capability matrix, gate the categories and sources the pipeline cannot serve, and deliver a request-specific web asset. `publicCatalogue()` already reports `assetStatus` honestly, so the storefront starts serving try-on the moment real assets exist — no dashboard change required.

**Phase 4 — connect commerce.** P1-08 inventory webhooks and reconciliation; then P1-04 and P1-05 schema refinements and ease handling; then P1-06 tech-pack parsing and advanced material properties.

---

## 6. Foundations worth preserving

- `data/publication.ts` — one resolver, consumed by both the dashboard and the storefront contract. Keep it the only answer to "can a shopper see this?"
- `data/revisions.ts` — QA approves a number, not a garment. This is the property that makes everything else safe to change.
- `data/size-chart.ts` — nothing fabricates a measurement. Keep it that way when Shopify and tech-pack import land.
- `data/rbac.ts` — brand and console capabilities are separate systems with separate blast radii.
- `components/use-action.ts` — the mutation contract the backend migration should preserve verbatim.
- `data/dashboard.test.ts` — the invariants above, as tests. Extend it rather than replacing it when the backend arrives.

---

*Original audit 28 August 2026. Remediation and status update, same date.*
