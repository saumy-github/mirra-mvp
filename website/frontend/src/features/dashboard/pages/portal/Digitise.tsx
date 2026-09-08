import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "../../data/session";
import { merchantApi, type MerchantGarment, type MerchantProduct } from "../../data/merchant-api";
import { IdentifyShopify } from "../../components/identify-shopify";
import { CaptureUpload } from "../../components/capture-upload";
import { PipelinePanel } from "../../components/pipeline-panel";
import { ProductContentEditor } from "../../components/product-content-editor";
import { Badge, Banner, ButtonLink, Card, EmptyState, PageHeader } from "../../components/ui";
import { buttonClass } from "../../components/styles";
import { dashPath } from "../../routes";

/**
 * Digitise — the live, server-backed ingestion flow.
 *
 * Identify → Capture → Pipeline → Review → Publish, every step persisted in
 * Mongo through `/api/v1/merchant/...` and every pipeline stage a real job on
 * the CLO worker queue.
 *
 * This exists alongside the older `GarmentFlow` page, which still reads the
 * in-memory prototype store (audit P0-01). The two are deliberately not
 * merged mid-migration: one of them loses everything on reload and the other
 * does not, and quietly mixing them would make it impossible to tell which
 * you were looking at. `GarmentFlow` is the demo; this is the one a client
 * can actually use.
 */

const STEPS = [
  { key: "identify", label: "Identify", hint: "Which Shopify product and sample" },
  { key: "capture", label: "Capture", hint: "Views of the sample" },
  { key: "pipeline", label: "Process", hint: "Panels and a 3D preview" },
  { key: "content", label: "Product page", hint: "What the shopper reads" },
  { key: "review", label: "Review", hint: "Check and send to QA" },
] as const;

type StepKey = (typeof STEPS)[number]["key"];

export default function DigitisePage() {
  const { id } = useParams<{ id: string }>();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const session = useSession();
  const qc = useQueryClient();

  const tenantId = session?.tenant?.id;

  if (!tenantId) return null;

  if (!id) {
    return (
      <>
        <Breadcrumb label="Add garment" />
        <PageHeader
          title="Add a garment"
          subtitle="Digitising a product for try-on: identify the Shopify listing, shoot its sample to Mirra's capture spec, then add material and sizing."
        />
        <div className="grid grid-cols-4 gap-5 max-lg:grid-cols-1">
          <Stepper active="identify" />
          <div className="col-span-3 max-lg:col-span-1">
            <IdentifyShopify
              tenantId={tenantId}
              onCreated={(garmentId) => {
                qc.invalidateQueries({ queryKey: ["merchant-garments", tenantId] });
                navigate(`${dashPath.digitise}/${garmentId}?step=capture`, { replace: true });
              }}
            />
          </div>
        </div>
      </>
    );
  }

  return <GarmentWorkspace tenantId={tenantId} garmentId={id} params={params} setParams={setParams} />;
}

function GarmentWorkspace({
  tenantId,
  garmentId,
  params,
  setParams,
}: {
  tenantId: string;
  garmentId: string;
  params: URLSearchParams;
  setParams: (next: Record<string, string>, opts?: { replace?: boolean }) => void;
}) {
  const qc = useQueryClient();
  const [garment, setGarment] = useState<MerchantGarment | null>(null);
  const [product, setProduct] = useState<MerchantProduct | null>(null);

  const garmentQuery = useQuery({
    queryKey: ["merchant-garment", tenantId, garmentId],
    queryFn: () => merchantApi.getGarment(tenantId, garmentId),
  });
  const productsQuery = useQuery({
    queryKey: ["merchant-products", tenantId],
    queryFn: () => merchantApi.listProducts(tenantId),
  });

  const g = garment ?? garmentQuery.data ?? null;
  const p =
    product ??
    (g ? (productsQuery.data ?? []).find((x) => x.productId === g.productId) ?? null : null);

  const apply = (next: MerchantGarment) => {
    setGarment(next);
    qc.setQueryData(["merchant-garment", tenantId, garmentId], next);
  };

  if (garmentQuery.isLoading) {
    return <p className="text-[13px] text-muted">Loading garment…</p>;
  }

  if (garmentQuery.isError || !g) {
    return (
      <EmptyState
        icon="👗"
        title="Garment not found"
        body="It may belong to another workspace, or have been removed."
        action={<ButtonLink href={dashPath.garments} size="sm">Back to garments</ButtonLink>}
      />
    );
  }

  const requested = params.get("step") as StepKey | null;
  const step: StepKey = requested && STEPS.some((s) => s.key === requested) ? requested : "capture";
  const index = STEPS.findIndex((s) => s.key === step);
  const go = (next: StepKey) => setParams({ step: next }, { replace: true });

  return (
    <>
      <Breadcrumb label="Set up" />
      <PageHeader
        title={g.title}
        subtitle={
          <span className="flex flex-wrap items-center gap-2">
            <Badge tone={g.stage === "live" ? "success" : "neutral"}>{g.stage.replace("_", " ")}</Badge>
            <span className="capitalize">{g.category}</span>
            <span>· revision {g.revision}</span>
            {g.draftAhead && <Badge tone="warn">Draft ahead of approved</Badge>}
          </span>
        }
      />

      <div className="grid grid-cols-4 gap-5 max-lg:grid-cols-1">
        <Stepper active={step} onGo={go} garment={g} />

        <div className="col-span-3 max-lg:col-span-1">
          {step === "identify" && <IdentitySummary garment={g} product={p} />}
          {step === "capture" && (
            <CaptureUpload tenantId={tenantId} garment={g} onChange={apply} />
          )}
          {step === "pipeline" && (
            <PipelinePanel tenantId={tenantId} garment={g} onChange={apply} />
          )}
          {step === "content" && (
            <ProductContentEditor
              tenantId={tenantId}
              garment={g}
              product={p}
              onGarmentChange={apply}
              onProductChange={setProduct}
            />
          )}
          {step === "review" && (
            <ReviewAndSubmit tenantId={tenantId} garment={g} onChange={apply} onGo={go} />
          )}

          <div className="mt-5 flex items-center justify-between border-t border-line pt-4">
            <button
              disabled={index <= 0}
              onClick={() => go(STEPS[Math.max(0, index - 1)].key)}
              className={buttonClass("secondary", "sm")}
            >
              ← Back
            </button>
            {index < STEPS.length - 1 && (
              <button onClick={() => go(STEPS[index + 1].key)} className={buttonClass("primary", "sm")}>
                Continue to {STEPS[index + 1].label} →
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

function Breadcrumb({ label }: { label: string }) {
  return (
    <div className="mb-1 flex items-center justify-between gap-3 text-xs text-muted">
      <span>
        <Link to={dashPath.garments} className="hover:text-ink">
          Garments
        </Link>{" "}
        / {label}
      </span>
      <Link to={dashPath.garments} className="font-medium text-accent hover:underline">
        Save and exit →
      </Link>
    </div>
  );
}

function Stepper({
  active,
  onGo,
  garment,
}: {
  active: StepKey;
  onGo?: (s: StepKey) => void;
  garment?: MerchantGarment;
}) {
  const stateOf = (key: StepKey): "complete" | "attention" | "todo" => {
    if (!garment) return key === "identify" ? "todo" : "todo";
    switch (key) {
      case "identify":
        return "complete";
      case "capture":
        return garment.capture.assets.some((a) => a.accepted && a.view === "front")
          ? "complete"
          : "todo";
      case "pipeline":
        if (garment.pipeline.state === "failed") return "attention";
        return Object.keys(garment.pipeline.ingestedRuns).length > 0 ? "complete" : "todo";
      case "content":
        return garment.content.description ? "complete" : "todo";
      case "review":
        return garment.readiness.ready ? "complete" : "todo";
    }
  };

  return (
    <nav aria-label="Setup steps" className="flex flex-col gap-4">
      <ol className="flex flex-col gap-0.5">
        {STEPS.map((s, i) => {
          const isActive = s.key === active;
          const state = stateOf(s.key);
          const Tag = onGo ? "button" : "span";
          return (
            <li key={s.key}>
              <Tag
                {...(onGo ? { onClick: () => onGo(s.key), type: "button" as const } : {})}
                aria-current={isActive ? "step" : undefined}
                className={`flex w-full items-start gap-2.5 rounded-lg px-3 py-2.5 text-left transition-colors ${
                  isActive ? "bg-accent-soft" : onGo ? "hover:bg-stone-100" : ""
                }`}
              >
                <span
                  className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold ${
                    state === "complete"
                      ? "bg-emerald-100 text-emerald-700"
                      : state === "attention"
                        ? "bg-amber-100 text-amber-800"
                        : isActive
                          ? "bg-accent text-white"
                          : "bg-stone-200 text-stone-600"
                  }`}
                >
                  {state === "complete" ? "✓" : state === "attention" ? "!" : i + 1}
                </span>
                <span>
                  <span
                    className={`block text-[13px] font-medium ${isActive ? "text-accent" : "text-ink"}`}
                  >
                    {s.label}
                  </span>
                  <span className="block text-[11px] text-muted">
                    {state === "complete" ? "Done" : isActive ? "In progress" : "Not started"}
                  </span>
                  <span className="block text-[11px] text-muted">{s.hint}</span>
                </span>
              </Tag>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

function IdentitySummary({
  garment,
  product,
}: {
  garment: MerchantGarment;
  product: MerchantProduct | null;
}) {
  return (
    <Card
      title="Locked identity"
      action={
        product?.linkState === "linked" ? (
          <Badge tone="success">Linked to Shopify</Badge>
        ) : (
          <Badge tone="warn">Not linked yet</Badge>
        )
      }
    >
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-[13px] max-sm:grid-cols-1">
        <div>
          <dt className="text-[11px] uppercase tracking-wide text-muted">Shopify title</dt>
          <dd className="font-medium text-ink">{garment.canonicalTitle}</dd>
        </div>
        <div>
          <dt className="text-[11px] uppercase tracking-wide text-muted">Handle</dt>
          <dd className="font-mono text-xs text-ink">{product?.handle ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-[11px] uppercase tracking-wide text-muted">Colourway</dt>
          <dd className="font-medium text-ink">{garment.optionValue || "—"}</dd>
        </div>
        <div>
          <dt className="text-[11px] uppercase tracking-wide text-muted">Cloth ID</dt>
          <dd className="font-mono text-xs text-ink">{garment.pipeline.clothId}</dd>
        </div>
      </dl>
      <p className="mt-3 text-xs text-muted">
        Identity is fixed once a garment exists. The cloth ID is what the pipeline&apos;s run
        folders and the shopper&apos;s try-on request are both keyed on.
      </p>
    </Card>
  );
}

function ReviewAndSubmit({
  tenantId,
  garment,
  onChange,
  onGo,
}: {
  tenantId: string;
  garment: MerchantGarment;
  onChange: (g: MerchantGarment) => void;
  onGo: (s: StepKey) => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async (fn: () => Promise<MerchantGarment>) => {
    setBusy(true);
    setError(null);
    try {
      onChange(await fn());
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const { blocking, advisory, ready } = garment.readiness;

  return (
    <div className="flex flex-col gap-4">
      {blocking.length > 0 ? (
        <Card title={`Blocking — ${blocking.length} to fix`}>
          <ul className="space-y-2.5">
            {blocking.map((issue, i) => (
              <li key={i} className="flex items-start justify-between gap-3 text-[13px]">
                <span>
                  <span className="font-medium text-red-700">{issue.label}</span>
                  <span className="block text-xs text-muted">{issue.detail}</span>
                </span>
                {(issue.area === "capture" || issue.area === "pipeline") && (
                  <button
                    onClick={() => onGo(issue.area === "capture" ? "capture" : "pipeline")}
                    className="shrink-0 text-xs font-medium text-accent hover:underline"
                  >
                    Fix →
                  </button>
                )}
              </li>
            ))}
          </ul>
        </Card>
      ) : (
        <Banner tone="success">Nothing blocking — ready for QA.</Banner>
      )}

      {advisory.length > 0 && (
        <Card title="Worth knowing — these don't block">
          <ul className="space-y-2">
            {advisory.map((issue, i) => (
              <li key={i} className="text-[13px]">
                <span className="font-medium text-ink">{issue.label}</span>
                <span className="block text-xs text-muted">{issue.detail}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {error && <Banner tone="danger">{error}</Banner>}

      <Card title="Hand it on">
        <p className="mb-3 text-[13px] text-muted">
          You look at it first, then send it to Mirra QA. QA approves this exact revision and
          freezes it — that frozen copy is what shoppers are served, so a later edit cannot reach
          them without another approval.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          {garment.stage === "needs_data" && (
            <button
              disabled={!ready || busy}
              onClick={() => run(() => merchantApi.setStage(tenantId, garment.garmentId, "merchant_review"))}
              className={buttonClass("primary")}
            >
              I&apos;m ready to review it
            </button>
          )}
          {garment.stage === "merchant_review" && (
            <>
              <button
                disabled={busy}
                onClick={() => run(() => merchantApi.setStage(tenantId, garment.garmentId, "in_qa"))}
                className={buttonClass("primary")}
              >
                Send to Mirra QA
              </button>
              <button
                disabled={busy}
                onClick={() => run(() => merchantApi.setStage(tenantId, garment.garmentId, "needs_data"))}
                className={buttonClass("secondary")}
              >
                Something needs changing
              </button>
            </>
          )}
          {garment.stage === "in_qa" && (
            <Banner tone="info">
              <strong>With Mirra QA.</strong> They are checking revision {garment.revision} against
              the preview you rendered.
            </Banner>
          )}
          {garment.stage === "ready" && (
            <button
              disabled={busy}
              onClick={() => run(() => merchantApi.setPublication(tenantId, garment.garmentId, true))}
              className={buttonClass("accent")}
            >
              Publish to shoppers
            </button>
          )}
          {garment.stage === "live" && (
            <>
              <Badge tone="success">Live</Badge>
              <button
                disabled={busy}
                onClick={() => run(() => merchantApi.setPublication(tenantId, garment.garmentId, false))}
                className={buttonClass("secondary")}
              >
                Pause
              </button>
            </>
          )}
        </div>
      </Card>
    </div>
  );
}
