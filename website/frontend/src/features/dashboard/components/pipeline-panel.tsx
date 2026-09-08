import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { GlbViewer } from "@/features/profile/components/avatar-glb-viewer";
import { merchantApi, type MerchantGarment, type Preview } from "../data/merchant-api";
import { Badge, Banner, Card, KeyValue } from "./ui";
import { buttonClass, inputClass } from "./styles";

/**
 * Capture → Product Ingestion → Virtual Try-On, driven and observed.
 *
 * Each stage is a real job on the CLO worker queue, not a simulated one:
 *
 *   Ingestion   Step 2 per size — segmentation, colour, design, then the CLO
 *               reference block drafted to that size's measurements. Produces
 *               DXF panels and texture atlases.
 *   Preview     Step 3 — those panels draped on Mirra's reference avatar and
 *               simulated, exported as a GLB.
 *
 * Nothing here reports success it cannot evidence. A preview shows a model
 * only when the worker recorded a file path for it; a failed run shows the
 * pipeline's own reason, because that reason is what makes it fixable.
 */
export function PipelinePanel({
  tenantId,
  garment,
  onChange,
}: {
  tenantId: string;
  garment: MerchantGarment;
  onChange: (g: MerchantGarment) => void;
}) {
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [sizeId, setSizeId] = useState("");

  const runs = useQuery({
    queryKey: ["merchant-runs", tenantId, garment.garmentId],
    queryFn: () => merchantApi.listRuns(tenantId, garment.garmentId),
    // Poll only while something is actually in flight.
    refetchInterval: (q) =>
      (q.state.data ?? []).some((r) => r.state === "queued" || r.state === "running") ? 5000 : false,
  });

  const previews = useQuery({
    queryKey: ["merchant-previews", tenantId, garment.garmentId],
    queryFn: () => merchantApi.listPreviews(tenantId, garment.garmentId),
    refetchInterval: (q) =>
      (q.state.data ?? []).some((p) => p.state === "requested" || p.state === "rendering")
        ? 5000
        : false,
  });

  const submit = useMutation({
    mutationFn: () => merchantApi.submitIngestion(tenantId, garment.garmentId),
    onSuccess: async () => {
      setError(null);
      await qc.invalidateQueries({ queryKey: ["merchant-runs", tenantId, garment.garmentId] });
      onChange(await merchantApi.getGarment(tenantId, garment.garmentId));
    },
    onError: (err: Error) => setError(err.message),
  });

  const requestPreview = useMutation({
    mutationFn: () => merchantApi.requestPreview(tenantId, garment.garmentId, sizeId || undefined),
    onSuccess: async () => {
      setError(null);
      await qc.invalidateQueries({ queryKey: ["merchant-previews", tenantId, garment.garmentId] });
      onChange(await merchantApi.getGarment(tenantId, garment.garmentId));
    },
    onError: (err: Error) => setError(err.message),
  });

  const ingested = Object.keys(garment.pipeline.ingestedRuns);
  const latestReady = (previews.data ?? []).find((p) => p.state === "ready");
  const inFlight = (previews.data ?? []).find(
    (p) => p.state === "requested" || p.state === "rendering",
  );

  return (
    <div className="flex flex-col gap-4">
      {!garment.pipeline.supported && (
        <Banner tone="danger">
          <strong>This garment cannot be processed.</strong> {garment.pipeline.unsupportedReason}
        </Banner>
      )}

      {garment.pipeline.failureReason && (
        <Banner tone="danger">
          <strong>Last pipeline run failed.</strong> {garment.pipeline.failureReason}
        </Banner>
      )}

      <Card
        title="Product ingestion"
        action={<Badge tone={stateTone(garment.pipeline.state)}>{garment.pipeline.state}</Badge>}
      >
        <p className="mb-3 text-[13px] text-muted">
          Runs segmentation, colour and design extraction on the capture set, then drafts pattern
          panels to each size&apos;s measurements. One run per size — they share the photographs but
          not the block.
        </p>

        <KeyValue
          rows={[
            ["Cloth ID", <code key="c" className="text-xs">{garment.pipeline.clothId || "—"}</code>],
            ["Sizes queued", garment.pipeline.sizeIds.length || "—"],
            ["Panels generated", `${ingested.length} of ${garment.pipeline.sizeIds.length || 0}`],
          ]}
        />

        <div className="mt-3 flex flex-wrap items-center gap-3">
          <button
            type="button"
            disabled={!garment.pipeline.supported || submit.isPending}
            onClick={() => submit.mutate()}
            className={buttonClass("primary", "sm")}
          >
            {submit.isPending ? "Queuing…" : ingested.length ? "Re-run ingestion" : "Run ingestion"}
          </button>
          <span className="text-xs text-muted">
            Runs on the CLO worker. Minutes, not seconds — the segmentation models load first.
          </span>
        </div>

        {(runs.data ?? []).length > 0 && (
          <ul className="mt-3 divide-y divide-stone-100">
            {(runs.data ?? []).map((run) => (
              <li key={run.runId} className="flex items-start justify-between gap-3 py-2 text-[13px]">
                <span>
                  <code className="text-xs text-stone-600">{run.sizeId}</code>
                  {run.failureReason && (
                    <span className="mt-0.5 block text-xs text-red-700">{run.failureReason}</span>
                  )}
                  {run.state === "succeeded" && (
                    <span className="mt-0.5 block text-xs text-muted">
                      {run.panelCount} panels · run {run.productRunId}
                    </span>
                  )}
                </span>
                <Badge tone={runTone(run.state)}>{run.state}</Badge>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card
        title="Preview on the reference avatar"
        action={
          latestReady ? (
            <Badge tone="success">Ready</Badge>
          ) : inFlight ? (
            <Badge tone="warn">{inFlight.state}</Badge>
          ) : null
        }
      >
        <p className="mb-3 text-[13px] text-muted">
          The garment simulated on Mirra&apos;s neutral reference body — the same body for every
          garment and every revision, so what changes between two previews is the garment and
          nothing else. This is exactly what QA reviews and what a shopper will see draped on their
          own avatar.
        </p>

        {ingested.length === 0 ? (
          <Banner tone="info">
            No panels exist yet. Run ingestion above first — there is nothing to drape until it has
            produced a pattern.
          </Banner>
        ) : (
          <div className="flex flex-wrap items-end gap-2">
            <div className="min-w-40">
              <label className="mb-1 block text-xs font-medium text-ink">Size to preview</label>
              <select
                value={sizeId}
                onChange={(e) => setSizeId(e.target.value)}
                className={inputClass}
              >
                <option value="">First available</option>
                {ingested.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              disabled={requestPreview.isPending || Boolean(inFlight)}
              onClick={() => requestPreview.mutate()}
              className={buttonClass("primary", "sm")}
            >
              {requestPreview.isPending ? "Queuing…" : inFlight ? "Rendering…" : "Render preview"}
            </button>
          </div>
        )}

        {error && (
          <div className="mt-3">
            <Banner tone="danger">{error}</Banner>
          </div>
        )}

        <div className="mt-4">
          <PreviewViewer tenantId={tenantId} previews={previews.data ?? []} />
        </div>
      </Card>
    </div>
  );
}

/**
 * The QA preview surface.
 *
 * Three honest states, and no fourth one that pretends: a rendered model, a
 * render in flight, or an explicit account of why there is nothing to show.
 * Substituting the pipeline's default t-shirt when a garment's own render is
 * missing would let a reviewer approve a garment they never saw.
 */
export function PreviewViewer({
  tenantId,
  previews,
}: {
  tenantId: string;
  previews: Preview[];
}) {
  const ready = previews.find((p) => p.state === "ready" && p.hasModel);
  const inFlight = previews.find((p) => p.state === "requested" || p.state === "rendering");
  const failed = previews.find((p) => p.state === "failed");

  if (ready) {
    return (
      <div>
        <GlbViewer
          queryKey={["merchant-preview-glb", ready.previewId]}
          fetchGlb={() => merchantApi.fetchPreviewGlb(tenantId, ready.previewId)}
          className="h-96"
          emptyMessage="The preview model could not be loaded."
        />
        <p className="mt-2 text-xs text-muted">
          Size {ready.sizeId} · revision {ready.revision}
          {ready.cloRunId ? ` · CLO run ${ready.cloRunId}` : ""} · rendered{" "}
          {new Date(ready.completedAt ?? ready.createdAt).toLocaleString()}
        </p>
      </div>
    );
  }

  if (inFlight) {
    return (
      <div className="flex h-48 items-center justify-center rounded-2xl border border-line bg-stone-50">
        <p className="px-6 text-center text-[13px] text-muted">
          <strong className="text-ink">Draping the garment…</strong>
          <span className="mt-1 block text-xs">
            CLO is importing the panels, sewing the seams and running the simulation. This page
            updates itself when it finishes.
          </span>
        </p>
      </div>
    );
  }

  if (failed) {
    return (
      <Banner tone="danger">
        <strong>The preview render failed.</strong>{" "}
        {failed.failureReason ?? "No reason was recorded."}
      </Banner>
    );
  }

  return (
    <div className="flex h-48 items-center justify-center rounded-2xl border border-dashed border-line bg-stone-50">
      <p className="px-6 text-center text-[13px] text-muted">
        No preview has been rendered yet. Nothing is shown here until the pipeline has produced a
        real model for this garment.
      </p>
    </div>
  );
}

function stateTone(state: string): "success" | "warn" | "danger" | "neutral" {
  if (state === "ingested" || state === "preview_ready") return "success";
  if (state === "failed") return "danger";
  if (state === "idle") return "neutral";
  return "warn";
}

function runTone(state: string): "success" | "warn" | "danger" | "neutral" {
  if (state === "succeeded") return "success";
  if (state === "failed") return "danger";
  return "warn";
}
