# Virtual Try-On Dashboard — Audit and Remediation Status

**Original audit:** 28 August 2026
**Remediation pass:** 28 August 2026
**Backend and pipeline pass:** 29 August 2026
**Scope of this document:** what the audit found, what has since been corrected, and — the part that matters for planning — **what is still outstanding**
**Production-readiness verdict:** **A single garment can now be taken end to end on the live path, but the client pilot is still gated.** The 29 August pass built the merchant backend, the Shopify identity mechanism, real capture intake and the Capture → Ingestion → VTO → QA → Publish loop, all persisted and all server-authorized. What blocks a pilot now is narrower and more concrete than "there is no backend": the older dashboard pages still read the in-memory store (**P0-01a**), the pipeline still only drafts tops (**P0-03**), and no Shopify store has ever been connected to verify the linked path against a real Admin API (**P0-04**).

---

## 1. Where this stands

The original audit found 35 issues. A remediation pass closed 28. The 29 August
backend pass closed 3 more and opened 4 new ones that only became visible once
real infrastructure existed to expose them.

| Priority | Total | Fixed | Outstanding |
| --- | --- | --- | --- |
| P0 — release blocker | 10 | 6 | **4** |
| P1 — major | 16 | 10 | **6** |
| P2 — moderate | 12 | 11 | **1** |
| P3 — minor | 2 | 2 | 0 |
| **Total** | **40** | **29** | **11** |

**What changed in character.** The dashboard was previously a demonstration shell that reported successful business outcomes without performing the underlying work. That specific class of problem is gone: sizing no longer fabricates measurements, QA approval is now a frozen revision rather than a flag, publication resolves through one authoritative module that the shopper-facing mapper also honours, and internal staff can no longer escalate into a customer's workspace.

**What changed on 29 August.** The application now has a backend for the
merchant surface. `website/backend/src/merchant/` owns tenants, Shopify product
identity, garments, capture assets, ingestion runs, QA previews and publication,
in Mongo, with membership and role checks enforced server-side on every call.
The `Digitise` flow (`/dashboard/portal/digitise`) drives it end to end and
persists across a reload. Capture uploads move real bytes. `POST
…/garments/{id}/ingestion` writes the pipeline's own `cloths`/`sizes` documents,
stages the photographs into `product_ingestion/input/<cloth_id>/` and queues a
Step 2 run per size on the same Redis queue the avatar and try-on jobs use;
`POST …/previews` then drapes the resulting panels on a reference avatar via
Step 3 and stores the GLB for QA.

**What has not changed.** The *older* dashboard pages — Garments, Products,
Publication, Analytics, the original `GarmentFlow` — still read the in-memory
store and still lose everything on reload. They now sit beside a persistent flow
rather than being the only one, which is why P0-01 has been split: the
foundation is built (P0-01, closed), the page-by-page migration is not
(**P0-01a**). The pipeline still drafts a crew-neck t-shirt block and nothing
else — but it now *refuses* anything else by name instead of silently returning
a t-shirt (P0-03, narrowed).

Verification: TypeScript, ESLint, a production build, the existing 40-test
dashboard suite, and a new 66-test backend suite covering URL parsing, the
pipeline mapping, the publication contract, readiness, the stage machine,
authorization and the full HTTP surface — all pass. **Not verified:** anything
requiring a live Mongo, Redis, CLO instance or Shopify store, none of which were
reachable from this environment. See P0-04 and P0-05.

---

## 2. Outstanding work

### P0-01 — Dashboard state and authentication are demo-only

**Status:** ✅ **Closed (29 August 2026)** for the foundation; the remaining page migration is tracked as P0-01a below.

**What was built:** `website/backend/src/merchant/` — a tenant-scoped merchant service on the same FastAPI app and Mongo database as the shopper side. Five collections (`merchant_tenants`, `merchant_products`, `merchant_garments`, `merchant_ingestion_runs`, `merchant_previews`), 27 routes, and `ROLE_PERMISSIONS` / `ALLOWED_TRANSITIONS` in `service.py` mirroring `data/rbac.ts` and `data/lifecycle.ts` — enforced on the server this time. A caller who is not a member of a workspace receives a 404 rather than a 403, so membership is not something an outsider can probe for.

Optimistic-concurrency handling is in place in the form the audit asked for: `revision` bumps on every shopper-visible edit, and `ApprovedSnapshot.freeze()` deep-copies the garment so an approved revision cannot be mutated through the working draft. That last point was a real defect caught by its own test — the first implementation aliased the live objects, so appending a size to a draft silently added it to the approved revision.

---

### P0-01a — The prototype dashboard pages have not been migrated to the backend

**Status:** Not started — this is now the largest single item.

**Observed:** the new `Digitise` flow (`pages/portal/Digitise.tsx`) is fully server-backed. Every other portal page — `Garments`, `GarmentDetail`, `GarmentFlow`, `Products`, `Publication`, `Analytics`, `Assets`, `SizeFit`, `Fabric`, `Team`, `Billing`, `Settings`, `Audit` — still reads `data/store.ts` and still reseeds on reload. `data/actions.ts` (1,826 lines) still mutates module memory.

**Why this is a blocker rather than a tidy-up:** a merchant can now complete a garment on the live path and see it vanish from the Garments list, because the two surfaces have different data. That is more confusing than either one alone. The nav lists "Digitise" separately for exactly this reason, which is a stopgap, not a design.

**Required outcome:** port `actions.ts` call sites to `data/merchant-api.ts` page by page, delete `store.ts`/`seed.ts`, and fold `GarmentFlow` into `Digitise`. `data/dashboard.test.ts` (40 tests) encodes the invariants and should be re-pointed at the API rather than rewritten. Login is still a persona chooser (`data/session.ts`) and needs to resolve a real session against `/auth`.

---

### P0-03 — Dashboard promises more garment capability than the engine implements

**Status:** Partially fixed — the dishonesty is gone and now enforced; the capability gap remains.

**Fixed (29 August):** `pipeline_bridge.check_pipeline_capability()` is a real gate. `SUPPORTED_CATEGORIES = ("top",)`, and a submission for anything else is refused with a reason naming the category, before any document is written or any job queued. The same verdict is returned on every garment read as `pipeline.supported` / `pipeline.unsupportedReason`, so the UI can disable rather than fail. Capture without an accepted front view, and any size missing a load-bearing measurement, are refused the same way.

**Outstanding:** the pipeline still only drafts a crew-neck set-in-sleeve t-shirt block (`product_ingestion/clo_block/`). Six of the seven categories the dashboard offers cannot be served. The category selector in `identify-shopify.tsx` marks them "(not yet supported)" and warns, but they are still selectable, because refusing to record a garment the merchant owns is worse than recording one Mirra cannot yet process.

**Required outcome:** fitted shape constants for at least raglan, V-neck and drop-shoulder blocks, plus a bottom block; or remove the categories from the product entirely.

---

### P0-04 — The linked Shopify path has never run against a real store

**Status:** Not started — blocked on the client, not on us.

**Observed:** `ShopifyAdminSource` (`product_source.py`) issues a pinned Admin GraphQL query (`2025-01`) for `productByHandle` / `product(id:)`, maps options to Mirra's colour/size axes by reading the shop's own option names, and returns a `linked` product. Every line of it is unexercised: no Shopify store, dev store or API token was available in this environment, so there is no test that has seen a real Shopify response.

**What *is* verified:** URL/handle/GID parsing across eight real-world link shapes; the unlinked path end to end; and `reconcile_unlinked_products()`'s logic. What is not: the GraphQL response shape, pagination beyond 100 variants, rate limiting, the `onlineStoreUrl` null case for unpublished products, and OAuth entirely — `connect_shopify` currently takes a token as an argument rather than obtaining one.

**Required outcome:** a Shopify Partner dev store, an embedded app with `read_products` scope, the OAuth install/callback flow, `products/update` and `inventory_levels/update` webhooks, and a first reconciliation run against real data.

---

### P0-05 — The pipeline hand-off has not been executed end to end

**Status:** Not started — blocked on infrastructure.

**Observed:** `submit_for_ingestion` → `worker.tasks.run_merchant_ingestion` → Step 2 → `run_merchant_preview` → Step 3 → GLB is complete in code and unit-tested at every seam, including that the size documents it writes satisfy `mirra_measurements.size_model.validate_size_doc` and that its ids match `product_ingestion/run_manifest.py`'s own regexes. But no Mongo, Redis or CLO instance was reachable from this environment, so **no ingestion run and no preview render has ever actually executed.**

**Specific risks that only a real run will surface:** `run_product_ingestion` is invoked through `build_parser().parse_args([...])` and returns an exit code — a non-zero return is handled, an interactive prompt is not, and the runner prompts when `--cloth-id`/`--size-id` are absent (they are always passed, but that is the assumption to check first). The reference avatar defaults to `clo_avatar_generation/input/base-1.avt`, which must have been exported from the installed CLO version. CLO concurrency is 1 and merchant jobs now share the queue with shopper try-ons, so a long ingestion run will delay a shopper's render.

**Required outcome:** one full run on the CLO machine — submit a garment, watch Step 2 produce panels, render a preview, view the GLB in QA. That single run is the highest-value next action in this document.

---

### P1-01 — Capture, phone, upload and CAD intake are still simulations

**Status:** Mostly fixed (29 August) — upload and CAD are real; phone capture is not.

**Fixed:** `POST /merchant/{t}/garments/{g}/capture` receives an actual file. `storage.store_capture_file` validates the content type against what the segmentation stage can decode, rejects HEIC with the fix rather than a format list, enforces a 640px short edge (below which segmentation quality metrics stop meaning anything), caps size, writes the bytes under the upload root, and records the SHA-256, byte count and pixel dimensions on the asset. `capture-upload.tsx` posts real files, shows real thumbnails fetched through the authed client, and re-uploading a view supersedes the old file rather than accumulating a second "front". CAD goes through the same path with its own type and size limits.

**Outstanding:** the QR phone-capture panel is still a static placeholder — no capture session, no pairing, no transfer, no resumability. CAD format validation (scale, watertightness, UVs) is still only a type and size check; a `.zprj` that CLO cannot open is accepted here and fails later.

---

### P1-02 — Reference-sample identity is not fully protected

**Status:** Fixed (29 August).

**Fixed:** `CaptureAsset.sample_size` pins the sample each frame was shot against, at upload time. `set_reference_size` no longer relabels anything: it changes the garment's reference size and then *reports the mismatch* — `capture.issues` gains an explicit "N image(s) were shot on size X, not Y" entry, which surfaces in the capture step and in `readiness.advisory`. Photos of a size S can no longer end up silently labelled M.

**Note:** the mismatch is advisory, not blocking. A merchant who genuinely reshot the sample and is correcting the label should not be stopped; one who changed it by accident is told.

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

## 2b. New issues found while building the backend

These did not exist on 28 August. Three are defects the new code introduced and
fixed under test; the fourth is a gap the new architecture exposed.

### P1-09 — QA preview and shopper try-on share one single-threaded CLO queue

**Status:** Known, unmitigated.

Merchant previews are enqueued on the same `clo` Redis queue as shopper try-on
renders, because CLO's plugin is single-threaded and one queue is what
serialises against it. A 25-minute ingestion plus preview therefore sits in
front of a shopper waiting for a try-on. Acceptable at pilot volume; not
acceptable once both are real. Needs either a second CLO instance with a
separate queue, or priority scheduling that lets shopper work pre-empt merchant
work between jobs.

### P2-12 — The default preview avatar is an unversioned file on disk

**Status:** Known.

`MIRRA_REFERENCE_AVATAR` defaults to `clo_avatar_generation/input/base-1.avt`.
Nothing records which avatar a given preview was rendered against, so two
previews compared across a CLO upgrade may differ because the body changed. The
preview document should record the reference avatar's identity and checksum.

### Fixed under test during this pass

- **Approval aliased the working draft.** `ApprovedSnapshot` held references to
  the garment's own `sizing`/`capture`/`material`, so appending a size to a
  draft added it to the approved revision too. Now `ApprovedSnapshot.freeze()`
  deep-copies, and that is the only supported way to construct one.
- **Material composition was stored as raw dicts.** Pydantic does not validate
  on assignment by default, so `list[FabricComponent]` quietly held dicts and
  every subsequent garment read raised `AttributeError` while shaping the
  response — a 500 on the next page load after saving a material. Fixed at the
  call site, and `MaterialSpec` now sets `validate_assignment=True` so the same
  mistake cannot recur silently.
- **The publication contract returned no variants for anything not live.** That
  made the QA preview an empty product panel — the one thing it exists to show.
  Variant resolution and the visibility decision are now separate.
- **Dashboard query keys were not tenant-scoped.** Cached garment, run and
  preview data would have been shared across workspaces on a tenant switch.

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

### 29 August backend pass

- **Merchant backend** — `src/merchant/`: 5 collections, 27 routes, server-side membership/role/transition enforcement, 66 tests.
- **Shopify identity mechanism** — a pasted URL now always advances. `resolved` (live Admin API), `matched` (already in Mirra), or `draft` (provisional identity from the URL, completed by hand and reconciled later by handle).
- **CSV import** — Shopify's own product export is accepted with its native headers.
- **Real capture intake** — validated, hashed, dimension-checked, stored, served back through an authed route.
- **Capture → Ingestion → VTO** — `pipeline_bridge` writes the pipeline's `cloths`/`sizes` documents and stages images into `input/<cloth_id>/`; worker tasks run Step 2 per size and Step 3 on a reference avatar.
- **QA preview** — a real GLB in an orbitable viewer when one exists, the pipeline's own failure reason when the render failed, and an explicit "nothing rendered yet" otherwise. No fallback to the default t-shirt.
- **Product page data** — per-field resolution with the winning source recorded, editable at colourway or listing scope; title and price stay Shopify's.

### P2 and P3 — all closed

Requirement evaluation centralized and shared across Fabric, Size & fit, Assets and Garments (P2-01). Bulk actions preflight every item, report what was skipped and why, and never act on rows hidden by a filter (P2-02). Scheduled go-live implemented with cancel, status, a due-sweep and audit (P2-03). Team seat management and versioned brand size charts implemented (P2-04). Analytics+ CSV export implemented; overpromising copy removed (P2-05). Six real knowledge-base guides, an operational support queue with assign/reply/status, and per-run sync diagnostics (P2-06). Audit log sorted newest-first with filters, search, CSV export and pagination, and ingestion mutations now emit entries (P2-07). Onboarding steps reopenable (P2-08). Structured QA findings with area, severity, affected view or measurement, and merchant-facing instructions — a rejection with no finding is refused (P2-09). Live regions on state changes, a text equivalent for the top-garments chart, and focus management (P2-10). Navigation filtered by capability, purpose-specific read-only wording, and teammate emails hidden from Viewer (P2-11). Pagination on catalogue, product and audit tables with real empty states (P3-01). The React key warning fixed, Vitest added, and 40 tests covering the invariants above (P3-02).

---

## 4. Release gates

| Gate | Status |
| --- | --- |
| Durable account | ⚠️ Backend built and persistent on the `Digitise` path; the other pages still reseed on reload (**P0-01a**), login is still a persona chooser |
| Authorization | ✅ Enforced server-side — membership, roles and stage transitions, with a 404 (not 403) for non-members |
| Product identity | ✅ URL → (store domain, handle) → product, linked or provisional, with reconciliation. Verified against eight real link shapes |
| Shopify connection | ❌ **P0-04** — adapter written, never run against a real store; no OAuth |
| Catalogue identity | ✅ Garments trace to tenant, product, colourway, variant, cloth id and size ids |
| Reference sample | ✅ Pinned per capture asset; a changed reference reports a mismatch instead of relabelling (**P1-02** closed) |
| Real capture | ⚠️ Upload and CAD are real, validated, hashed and stored; QR phone capture is still a placeholder (**P1-01**) |
| Construction blocks | ⚠️ Modelled and explained; not yet independently captured or tracked (**P1-03**) |
| Real sizing | ✅ No synthetic rows; rows map one-to-one onto pipeline size documents and pass the pipeline's own validator |
| Material | ⚠️ Composition and behaviour are real and validated; advanced engine properties absent (**P1-06**) |
| Pipeline contract | ⚠️ Capability gate enforced and surfaced; still tops-only (**P0-03**) |
| Pipeline execution | ❌ **P0-05** — Capture → Ingestion → VTO is wired and unit-tested but has never actually run |
| Lifecycle | ✅ Enforced server-side; illegal transitions are refused with the allowed set named |
| Revision safety | ✅ Approval deep-copies the revision; a later edit sets `draftAhead` and cannot reach shoppers |
| Preview / public | ⚠️ QA preview renders a real GLB when one exists and says why when it doesn't; the public tenant host still needs DNS and a live storefront link |
| Product page data | ✅ Per-field resolution (garment → product → omitted) with the winning source recorded and shown |
| Inventory | ⚠️ Policy precedence is correct and tested; live Shopify inventory is not connected (**P1-08**, **P0-04**) |
| Operations | ⚠️ Ingestion and preview failures carry the pipeline's own reason; no retry UI, no alerting |
| Mobile / accessibility | ✅ Full ingestion and support path usable by keyboard, screen reader and phone viewport |

---

## 5. Suggested order for the remaining work

**Phase 0 — run it once.** P0-05. Everything below assumes the pipeline hand-off works, and nobody has watched it work. One garment, on the CLO machine, from capture to a GLB in the QA preview. Expect to find something; the code has never met a real CLO instance.

**Phase 1 — connect a store.** P0-04. A Partner dev store, the OAuth flow, and one `reconcile` run. This is what turns the provisional-identity path from a workaround into the fallback it was designed to be, and it is the only way to test the linked path at all. It is also client-dependent, so start the conversation early.

**Phase 2 — finish the migration.** P0-01a. Port the remaining pages off `data/store.ts` and fold `GarmentFlow` into `Digitise`. Until this lands the dashboard has two sources of truth, which is worse than having one bad one.

**Phase 3 — real capture, the rest of it.** The QR phone session (P1-01), then per-block capture (P1-03).

**Phase 4 — close the pipeline contract.** P0-03. Either fit the remaining blocks or remove the categories.

**Phase 5 — connect commerce.** P1-08 inventory webhooks; then P1-04 and P1-05 schema refinements; then P1-06 tech-pack parsing.

---

## 6. Foundations worth preserving

- `data/publication.ts` — one resolver, consumed by both the dashboard and the storefront contract. Keep it the only answer to "can a shopper see this?"
- `data/revisions.ts` — QA approves a number, not a garment. This is the property that makes everything else safe to change.
- `data/size-chart.ts` — nothing fabricates a measurement. Keep it that way when Shopify and tech-pack import land.
- `data/rbac.ts` — brand and console capabilities are separate systems with separate blast radii.
- `components/use-action.ts` — the mutation contract the backend migration should preserve verbatim.
- `data/dashboard.test.ts` — the invariants above, as tests. Extend it rather than replacing it when the backend arrives.
- `src/merchant/publication.py` — the server-side twin of `data/publication.ts`. Variant resolution and the visibility decision are separate on purpose: a QA reviewer previewing an unpublished garment still needs to see its sizes and prices. Keep it the only answer to "can a shopper see this?" on the server.
- `src/merchant/product_source.py` — the reason a workspace with no Shopify store is not a dead end. The `linked`/`unlinked` split, and `reconcile_unlinked_products()` matching on handle, are what let the client work today and lose nothing when the store arrives.
- `src/merchant/pipeline_bridge.py` — the only place that knows how a dashboard garment becomes `cloths`/`sizes` documents and an `input/<cloth_id>/` folder. Derived, dash-free ids are load-bearing: `product_ingestion/run_manifest.py` parses `<cloth>-<size>-<run>`, so a dash in either id makes a run folder ambiguous.
- `ApprovedSnapshot.freeze()` — approval is a deep copy, not a flag. The first implementation aliased the working draft and its own test caught it.

---

*Original audit 28 August 2026. Remediation and status update, same date. Backend, Shopify identity and pipeline hand-off pass, 29 August 2026.*
