import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useDbVersion, getDb } from "../../data/store";
import { useSession } from "../../data/session";
import {
  setGarmentStageAction,
  completeGenerationAction,
  createGarmentAction,
  setMerchantTitleAction,
  submitForMerchantReviewAction,
  confirmVariantMappingAction,
} from "../../data/actions";
import { revisionNotice } from "../../data/revisions";
import {
  STEP_STATE_META,
  flowSteps,
  gradingPlan,
  inventoryFor,
  nextFlowStep,
  reviewIssues,
  sizesForGarment,
  variantMapping,
  type FlowStepKey,
} from "../../data/ingestion";
import { can } from "../../data/rbac";
import {
  ActionButton,
  Badge,
  Banner,
  ButtonLink,
  Card,
  EmptyState,
  KeyValue,
  NoticeBar,
  PageHeader,
} from "../../components/ui";
import { useAction } from "../../components/use-action";
import { buttonClass } from "../../components/styles";
import { StageBadge } from "../../components/catalogue-table";
import {
  CaptureStep,
  IdentifyNew,
  IdentifyStep,
  MaterialStep,
  SizingStep,
} from "../../components/ingestion-steps";
import { dashPath } from "../../routes";
import type { Garment, Product } from "../../data/types";

/**
 * The garment-ingestion flow:
 * **Identify → Capture → Material → Size & fit → Review**.
 *
 * Identity comes first and is then locked. Before a single photograph, Mirra
 * establishes which Shopify product this is — resolved from a pasted URL,
 * canonical title kept, option value named by the shop's own option — and which
 * physical sample is in the merchant's hands. Everything downstream describes
 * that sample and maps back to those variants.
 *
 * A working surface, not a summary: the merchant is stood next to a physical
 * garment doing one thing at a time. `Save and exit` is always available —
 * every answer is written as it's given.
 */
export default function GarmentFlowPage() {
  const { id } = useParams<{ id: string }>();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const session = useSession();
  useDbVersion();

  if (!session?.tenant) return null;
  const tenant = session.tenant;
  const db = getDb();
  const g = db.garments.find((x) => x.id === id && x.tenantId === tenant.id);

  // `/garments/new` — the flow itself is the "add garment" experience. Picking
  // the colourway is its first move, not a screen in front of it.
  if (!id) {
    return (
      <NewGarmentIdentify
        tenantId={tenant.id}
        garments={db.garments.filter((x) => x.tenantId === tenant.id)}
        onCreate={(productId, optionValue, merchantTitle) => {
          const newId = createGarmentAction(productId, optionValue);
          if (!newId) return;
          setMerchantTitleAction(newId, merchantTitle);
          navigate(dashPath.garmentFlow(newId, "identify"), { replace: true });
        }}
      />
    );
  }

  if (!g) {
    return (
      <EmptyState
        icon="👗"
        title="Garment not found"
        body="It may belong to another workspace, or have been removed."
        action={<ButtonLink href={dashPath.garments} size="sm">Back to garments</ButtonLink>}
      />
    );
  }

  const product = db.products.find((p) => p.id === g.productId);
  const steps = flowSteps(g, product);
  const canEdit = can(session.role, "catalogue.edit");

  const requested = params.get("step") as FlowStepKey | null;
  const step: FlowStepKey =
    requested && steps.some((s) => s.key === requested) ? requested : nextFlowStep(g, product);
  const index = steps.findIndex((s) => s.key === step);
  const go = (next: FlowStepKey) => setParams({ step: next }, { replace: true });

  const done = steps.filter((s) => s.complete).length;

  return (
    <>
      <div className="mb-1 flex items-center justify-between gap-3 text-xs text-muted">
        <span>
          <Link to={dashPath.garments} className="hover:text-ink">Garments</Link> / Set up
        </span>
        <Link to={dashPath.garment(g.id)} className="font-medium text-accent hover:underline">
          Save and exit →
        </Link>
      </div>

      <PageHeader
        title={g.title}
        subtitle={
          <span className="flex flex-wrap items-center gap-2">
            <StageBadge stage={g.stage} />
            <span className="capitalize">{g.category}</span>
            <span>· {g.variantIds.length} SKUs</span>
            {g.referenceSize && <span>· Reference sample: Size {g.referenceSize}</span>}
            <span>· {done} of {steps.length} steps done</span>
          </span>
        }
      />

      {!canEdit && (
        <div className="mb-5">
          <Banner tone="info">Your role can view this garment but not edit it.</Banner>
        </div>
      )}

      <div className="grid grid-cols-4 gap-5 max-lg:grid-cols-1">
        {/* Vertical stepper: position, state and what each step is for, all
            visible at once. */}
        <nav aria-label="Setup steps" className="flex flex-col gap-4">
          <ol className="flex flex-col gap-0.5">
            {steps.map((s, i) => {
              const active = s.key === step;
              return (
                <li key={s.key}>
                  <button
                    onClick={() => go(s.key)}
                    aria-current={active ? "step" : undefined}
                    className={`flex w-full items-start gap-2.5 rounded-lg px-3 py-2.5 text-left transition-colors ${
                      active ? "bg-accent-soft" : "hover:bg-stone-100"
                    }`}
                  >
                    <span
                      className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold ${
                        s.state === "complete"
                          ? "bg-emerald-100 text-emerald-700"
                          : s.state === "needs_attention"
                            ? "bg-amber-100 text-amber-800"
                            : active
                              ? "bg-accent text-white"
                              : "bg-stone-200 text-stone-600"
                      }`}
                    >
                      {s.state === "complete" ? "✓" : s.state === "needs_attention" ? "!" : i + 1}
                    </span>
                    <span>
                      <span className={`block text-[13px] font-medium ${active ? "text-accent" : "text-ink"}`}>
                        {s.label}
                      </span>
                      {/* State, not just "am I standing here" — a merchant
                          needs to tell not-started from part-done from
                          done-but-unverified. */}
                      <span
                        className={`block text-[11px] ${
                          s.state === "needs_attention"
                            ? "font-medium text-amber-700"
                            : s.state === "complete"
                              ? "text-emerald-700"
                              : "text-muted"
                        }`}
                      >
                        {STEP_STATE_META[s.state].label}
                      </span>
                      <span className="block text-[11px] text-muted">{s.hint}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>

          <Card title="What you're digitising">
            <KeyValue
              rows={[
                ["Product", product?.title ?? "—"],
                [product?.optionName ?? "Option", g.optionValue || "—"],
                ["Sizes", sizesForGarment(g, product).join(" · ") || "—"],
                ["Stock", `${inventoryFor(g, product).purchasable} of ${inventoryFor(g, product).total} purchasable`],
              ]}
            />
          </Card>
        </nav>

        <div className="col-span-3 max-lg:col-span-1">
          <fieldset disabled={!canEdit} className={canEdit ? undefined : "opacity-70"}>
            <legend className="sr-only">{steps[index]?.label}</legend>
            {step === "identify" && (
              <IdentifyStep garment={g} product={product} allGarments={db.garments} />
            )}
            {step === "capture" && <CaptureStep garment={g} />}
            {step === "material" && <MaterialStep garment={g} />}
            {step === "sizing" && <SizingStep garment={g} product={product} tenant={tenant} />}
            {step === "review" && <ReviewStep garment={g} product={product} onGo={go} />}
          </fieldset>

          {g.stage === "processing" && (
            <p className="mt-4 flex flex-wrap items-center gap-1.5 text-xs text-muted">
              Generation runs in the background.
              <ActionButton variant="ghost" onAction={() => completeGenerationAction(g.id)}>
                Simulate completion
              </ActionButton>
              — a pipeline webhook advances this in production.
            </p>
          )}

          <div className="mt-5 flex items-center justify-between border-t border-line pt-4">
            <button
              disabled={index <= 0}
              onClick={() => go(steps[Math.max(0, index - 1)].key)}
              className={buttonClass("secondary", "sm")}
            >
              ← Back
            </button>
            {index < steps.length - 1 ? (
              <button onClick={() => go(steps[index + 1].key)} className={buttonClass("primary", "sm")}>
                Continue to {steps[index + 1].label} →
              </button>
            ) : (
              <button onClick={() => navigate(dashPath.garment(g.id))} className={buttonClass("primary", "sm")}>
                Done — view garment →
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

/**
 * `/garments/new` — identity first.
 *
 * Nothing is captured, measured or inferred before Mirra knows which Shopify
 * listing is being digitised. The merchant pastes the product URL, Mirra
 * resolves it against the connected store, and only then does the garment come
 * into existence — with the Shopify title locked as canonical.
 */
function NewGarmentIdentify({
  tenantId,
  garments,
  onCreate,
}: {
  tenantId: string;
  garments: Garment[];
  onCreate: (productId: string, optionValue: string, merchantTitle: string) => void;
}) {
  const steps = [
    { label: "Identify", hint: "Which Shopify product and sample" },
    { label: "Capture", hint: "Views of the sample" },
    { label: "Material", hint: "Composition and behaviour" },
    { label: "Size & fit", hint: "Measurements and how it fits" },
    { label: "Review", hint: "Check and send to QA" },
  ];

  return (
    <>
      <div className="mb-1 flex items-center justify-between gap-3 text-xs text-muted">
        <span>
          <Link to={dashPath.garments} className="hover:text-ink">Garments</Link> / Add garment
        </span>
        <Link to={dashPath.garments} className="font-medium text-accent hover:underline">
          Cancel →
        </Link>
      </div>

      <PageHeader
        title="Add a garment"
        subtitle="Digitising a product for try-on: identify the Shopify listing, shoot its sample to Mirra's capture spec, then add material and sizing."
      />

      <div className="grid grid-cols-4 gap-5 max-lg:grid-cols-1">
        <nav aria-label="Setup steps" className="flex flex-col gap-4">
          <ol className="flex flex-col gap-0.5">
            {steps.map((s, i) => (
              <li key={s.label}>
                <span
                  aria-current={i === 0 ? "step" : undefined}
                  className={`flex items-start gap-2.5 rounded-lg px-3 py-2.5 ${i === 0 ? "bg-accent-soft" : ""}`}
                >
                  <span
                    className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold ${
                      i === 0 ? "bg-accent text-white" : "bg-stone-200 text-stone-600"
                    }`}
                  >
                    {i + 1}
                  </span>
                  <span>
                    <span className={`block text-[13px] font-medium ${i === 0 ? "text-accent" : "text-ink"}`}>
                      {s.label}
                    </span>
                    <span className="block text-[11px] text-muted">
                      {i === 0 ? "In progress" : "Not started"}
                    </span>
                    <span className="block text-[11px] text-muted">{s.hint}</span>
                  </span>
                </span>
              </li>
            ))}
          </ol>
        </nav>

        <div className="col-span-3 max-lg:col-span-1">
          <IdentifyNew tenantId={tenantId} garments={garments} onCreate={onCreate} />
        </div>
      </div>
    </>
  );
}


/**
 * Review: what exists, where it came from, what blocks a publish.
 *
 * The old summary printed "low stretch · moderate · mid-weight" while Material
 * was still blank — defaults rendered as if they were findings. Nothing here
 * shows a value without its source and whether a human confirmed it.
 */
function ReviewStep({
  garment: g,
  product,
  onGo,
}: {
  garment: Garment;
  product: Product | undefined;
  onGo: (s: FlowStepKey) => void;
}) {
  const { blocking, suggestions } = reviewIssues(g, product);
  const sizes = sizesForGarment(g, product);
  const mapping = variantMapping(g, product);
  const plan = gradingPlan(g, product);
  const inventory = inventoryFor(g, product);
  const hasMaterial = g.fabricComposition.length > 0;

  return (
    <div className="flex flex-col gap-4">
      <Card title="What Mirra has">
        <KeyValue
          rows={[
            ["Shopify product", g.canonicalTitle],
            ["Garment", g.title],
            [
              "Capture",
              g.capture.method === "cad"
                ? g.capture.cadAsset
                  ? `3D asset · ${g.capture.cadAsset.filename}`
                  : "3D asset pending"
                : `${g.capture.accepted.length}/4 views${g.capture.details.length ? ` · ${g.capture.details.length} detail` : ""}`,
            ],
            ["Reference sample", g.referenceSize ? `Size ${g.referenceSize}` : "Not recorded"],
            [
              "Material",
              hasMaterial ? (
                <span key="m" className="flex items-center justify-end gap-2">
                  {g.fabricComposition.map((f) => `${f.pct}% ${f.material}`).join(", ")}
                  <Badge tone={g.fabricConfirmed ? "success" : "warn"}>
                    {g.fabricConfirmed ? "confirmed" : "unconfirmed"}
                  </Badge>
                </span>
              ) : (
                <span key="m" className="text-amber-800">Not recorded</span>
              ),
            ],
            [
              "Behaviour",
              // Never printed as fact while the composition it derives from is
              // missing or the inference is unconfirmed.
              !hasMaterial ? (
                <span key="b" className="text-amber-800">Awaiting composition</span>
              ) : (
                <span key="b" className="flex items-center justify-end gap-2">
                  {`${g.attributes.stretch} stretch · ${g.attributes.drape} · ${g.attributes.thickness}-weight`}
                  <Badge tone={g.attributesSuggested ? "warn" : "success"}>
                    {g.attributesSuggested ? "Mirra suggestion" : "confirmed"}
                  </Badge>
                </span>
              ),
            ],
            [
              "Fit",
              g.silhouette ? (
                <span key="f" className="capitalize">{g.silhouette}</span>
              ) : (
                <span key="f" className="text-amber-800">Not set</span>
              ),
            ],
          ]}
        />
      </Card>

      <Card title="Generated sizes">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-[13px] font-medium text-ink">{plan.headline}</div>
            <p className="mt-0.5 text-xs text-muted">{plan.detail}</p>
          </div>
          <Badge tone={plan.tone}>{plan.method === "estimated" ? "Draft" : "Source"}</Badge>
        </div>
      </Card>

      {/* Explicit SKU confirmation before QA — an unchecked auto-mapping is a
          guess a shopper discovers for you. */}
      <Card
        title="Size → Shopify variant"
        action={
          <Badge tone={g.variantMappingConfirmed ? "success" : "warn"}>
            {g.variantMappingConfirmed ? "Confirmed" : "Needs confirming"}
          </Badge>
        }
      >
        <ul className="divide-y divide-stone-100">
          {mapping.rows.map((r) => (
            <li key={r.size} className="flex items-center justify-between gap-3 py-2 text-[13px]">
              <span className="font-medium text-ink">{r.size}</span>
              {r.variant ? (
                <span className="flex items-center gap-2 text-muted">
                  <code className="text-xs text-stone-600">{r.variant.sku}</code>
                  {r.inventory > 0 ? (
                    <span className="text-xs">{r.inventory} in stock</span>
                  ) : (
                    <span className="text-xs text-amber-800">Sold out</span>
                  )}
                </span>
              ) : (
                <span className="text-xs text-red-700">No matching Shopify variant</span>
              )}
            </li>
          ))}
        </ul>
        {!g.variantMappingConfirmed && (
          <button
            onClick={() => confirmVariantMappingAction(g.id, true)}
            className={`${buttonClass("accent", "sm")} mt-3`}
          >
            Confirm mapping
          </button>
        )}
      </Card>

      <Card title="Inventory">
        <p className="text-[13px] text-muted">
          Shopify is the source of truth and Mirra never writes stock.{" "}
          {inventory.soldOut.length > 0 ? (
            <>
              <strong className="text-ink">{inventory.soldOut.join(", ")}</strong>{" "}
              {inventory.soldOut.length === 1 ? "is" : "are"} sold out right now.
            </>
          ) : (
            "Every size is currently purchasable."
          )}
        </p>
        <p className="mt-2 text-xs text-muted">
          When a size sells out:{" "}
          <strong className="font-medium text-ink">
            keep it available for try-on and disable purchase
          </strong>{" "}
          — a generated size doesn&apos;t stop existing at zero stock, and shoppers still save and
          compare. Change this in{" "}
          <Link to={dashPath.settings} className="font-medium text-accent hover:underline">Settings</Link>.
        </p>
      </Card>

      {blocking.length > 0 ? (
        <Card title={`Blocking — ${blocking.length} to fix before publishing`}>
          <ul className="space-y-2.5">
            {blocking.map((i) => (
              <li key={i.label} className="flex items-start justify-between gap-3 text-[13px]">
                <span>
                  <span className="font-medium text-red-700">{i.label}</span>
                  <span className="block text-xs text-muted">{i.detail}</span>
                </span>
                <button
                  onClick={() =>
                    onGo(i.label === "Images" ? "capture" : i.label === "Material" ? "material" : "sizing")
                  }
                  className="shrink-0 text-xs font-medium text-accent hover:underline"
                >
                  Fix →
                </button>
              </li>
            ))}
          </ul>
        </Card>
      ) : (
        <Banner tone="success">Nothing blocking — ready for your preview and then QA.</Banner>
      )}

      {suggestions.length > 0 && (
        <Card title="Suggestions — you can publish without these">
          <ul className="space-y-2">
            {suggestions.map((i) => (
              <li key={i.label} className="text-[13px]">
                <span className="font-medium text-ink">{i.label}</span>
                <span className="block text-xs text-muted">{i.detail}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Generation and merchant preview sit between data collection and QA. */}
      <Card title="Your preview">
        {g.stage === "processing" ? (
          <p className="text-[13px] text-muted">
            <strong className="text-ink">Building the digital garment…</strong> Preview opens when
            generation finishes.
          </p>
        ) : (
          <p className="text-[13px] text-muted">
            Preview on a neutral test avatar isn&apos;t connected yet — rendering comes from the VTO
            side. Sizes generated: {sizes.join(" · ") || "—"}.
          </p>
        )}
        <div className="mt-3 flex gap-2">
          <ButtonLink href={dashPath.tryOnStudio} size="sm">Open try-on studio →</ButtonLink>
          <Link to={dashPath.support} className={buttonClass("ghost", "sm")}>Report an issue</Link>
        </div>
      </Card>

      <SubmitBlock garment={g} blocking={blocking.length} />
    </div>
  );
}

/**
 * The last two steps of the merchant-owned lifecycle, in order.
 *
 * `needs_data → merchant_review → in_qa` is the path the state machine has
 * always described and that nothing performed: the flow jumped straight at
 * `in_qa`, which the machine refuses, and the refusal was discarded — so a
 * finished garment had a button that did nothing at all. Each rung is now its
 * own control, offered only when the garment is actually on it.
 */
function SubmitBlock({ garment: g, blocking }: { garment: Garment; blocking: number }) {
  const { notice, run, clear } = useAction();
  const ready = blocking === 0 && g.variantMappingConfirmed;
  const rev = revisionNotice(g);

  return (
    <div className="flex flex-col gap-3">
      <NoticeBar notice={notice} onDismiss={clear} />

      {rev && (
        <Banner tone={rev.tone}>
          <strong>{rev.headline}</strong> {rev.detail}
        </Banner>
      )}

      {g.stage === "in_qa" ? (
        <Banner live tone="info">
          <strong>With Mirra QA.</strong> We&apos;re checking revision {g.sourceRevision}. You&apos;ll
          get it back either approved and publishable, or with specific findings to fix.
        </Banner>
      ) : g.stage === "merchant_review" ? (
        <Card title="Your review">
          <p className="mb-3 text-[13px] text-muted">
            Everything Mirra needs is here. Check it over — the measurements, the material, the
            capture set — then hand it to QA. QA approves this exact revision and freezes it, and
            that frozen copy is what shoppers are served.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <ActionButton variant="primary" size="md" onAction={() => setGarmentStageAction(g.id, "in_qa")}>
              Send to Mirra QA
            </ActionButton>
            <ActionButton onAction={() => setGarmentStageAction(g.id, "needs_data")}>
              Something needs changing
            </ActionButton>
          </div>
        </Card>
      ) : (
        <div className="flex flex-wrap items-center gap-3">
          <button
            disabled={!ready}
            title={
              ready
                ? undefined
                : blocking > 0
                  ? `${blocking} blocking issue${blocking === 1 ? "" : "s"} still to fix`
                  : "Confirm the size → variant mapping first"
            }
            onClick={() => run(() => submitForMerchantReviewAction(g.id))}
            className={buttonClass("primary")}
          >
            I&apos;m ready to review it
          </button>
          <span className="text-xs text-muted">
            You look at it first, then send it to Mirra QA. QA marks it Ready; you publish from{" "}
            <Link to={dashPath.publication} className="font-medium text-accent hover:underline">
              Publication
            </Link>
            .
          </span>
        </div>
      )}
    </div>
  );
}
