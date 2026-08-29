/**
 * Step screens for the garment-ingestion flow.
 *
 * The ordering principle: **identity before evidence**. Nothing is captured,
 * measured or inferred until Mirra knows exactly which Shopify listing is being
 * digitised, and that identity is locked for the rest of the flow. Product,
 * garment, option value and SKU are distinct things here and are never treated
 * as interchangeable.
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import {
  acceptCanonicalTitleAction,
  addDetailShotAction,
  attachCadAssetAction,
  autoMeasureAction,
  confirmAttributesAction,
  confirmVariantMappingAction,
  findExistingComposition,
  recordCaptureAction,
  resolveShopifyProduct,
  reuseColourwayAction,
  setCaptureMethodAction,
  setConstructionAction,
  setFabricAction,
  setFitAction,
  setReferenceSizeAction,
  setSizeChartAction,
  startGenerationAction,
  verifyGradingAction,
} from "../data/actions";
import {
  BEHAVIOUR_LABELS,
  CAPTURE_SPEC,
  CATEGORY_BEHAVIOURS,
  MEASUREMENT_FIELDS,
  SIZE_SOURCE_LABELS,
  gradingPlan,
  reuseCandidates,
  sizesForGarment,
  variantMapping,
} from "../data/ingestion";
import {
  UNIT_LABELS,
  blankRows,
  fromCm,
  gradeFromRules,
  parseChart,
  toCm,
  validateChart,
  type FieldIssue,
  type ParsedChart,
  type Unit,
} from "../data/size-chart";
import { CAPTURE_VIEWS } from "../data/types";
import type {
  CadAsset,
  CaptureView,
  FabricSource,
  Garment,
  GarmentBehaviour,
  GarmentCategory,
  GradingSource,
  Product,
  Silhouette,
  SizeRow,
  SizeSource,
  Tenant,
} from "../data/types";
import {
  Badge,
  Banner,
  Card,
  Field,
  KeyValue,
  NoticeBar,
} from "./ui";
import { useAction } from "./use-action";
import { buttonClass, inputClass } from "./styles";
import { dashPath } from "../routes";

/** A compact multiple-choice row. */
function ChipGroup<T extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: { value: T; label: string; note?: string }[];
  value: T | undefined;
  onChange: (v: T) => void;
  label?: string;
}) {
  return (
    <div>
      {label && <div className="mb-1.5 text-xs font-medium text-ink">{label}</div>}
      <div className="flex flex-wrap gap-1.5">
        {options.map((o) => (
          <button
            key={o.value}
            type="button"
            onClick={() => onChange(o.value)}
            aria-pressed={value === o.value}
            title={o.note}
            className={`rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors ${
              value === o.value
                ? "border-accent bg-accent-soft text-accent"
                : "border-line bg-surface text-stone-600 hover:border-accent hover:text-ink"
            }`}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- identity

/**
 * Establishing identity for a garment that doesn't exist yet.
 *
 * The merchant names the listing — by pasting its storefront URL — and Mirra
 * resolves it against the connected store. Only then does it offer the option
 * values, using **the shop's own option name**, and only then can a garment be
 * created. Guessing identity from a dropdown of titles is how two different
 * products end up sharing one try-on record.
 */
export function IdentifyNew({
  tenantId,
  garments,
  onCreate,
}: {
  tenantId: string;
  garments: Garment[];
  onCreate: (productId: string, optionValue: string, merchantTitle: string) => void;
}) {
  const [url, setUrl] = useState("");
  const [resolved, setResolved] = useState<Product | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [optionValue, setOptionValue] = useState("");

  const lookUp = () => {
    const res = resolveShopifyProduct(tenantId, url);
    if (res.error || !res.product) {
      setResolved(null);
      setError(res.error ?? "Not found.");
      return;
    }
    setResolved(res.product);
    setError(null);
    setName(res.product.title);
    const values = [...new Set(res.product.variants.map((v) => v.color))];
    const free = values.filter(
      (v) => !garments.some((g) => g.productId === res.product!.id && g.optionValue === v),
    );
    setOptionValue(free[0] ?? "");
  };

  const optionValues = resolved ? [...new Set(resolved.variants.map((v) => v.color))] : [];
  const taken = (v: string) =>
    resolved ? garments.some((g) => g.productId === resolved.id && g.optionValue === v) : false;
  const available = optionValues.filter((v) => !taken(v));
  // Single-option products have no colour-like option at all — don't invent one.
  const hasOption = Boolean(resolved?.optionName) && optionValues.length > 1;
  const matchedVariants = resolved
    ? resolved.variants.filter((v) => !hasOption || v.color === optionValue)
    : [];
  const nameMismatch = Boolean(resolved && name.trim() && name.trim() !== resolved.title);

  return (
    <div className="flex flex-col gap-4">
      <Card title="Which Shopify product are you digitising?">
        <p className="mb-3 text-[13px] text-muted">
          Paste the product&apos;s storefront URL. Mirra checks it belongs to your connected store
          and locks its identity for the rest of setup.
        </p>
        <div className="flex flex-wrap items-end gap-2">
          <div className="min-w-72 flex-1">
            <Field label="Shopify product URL" hint="Also accepts the product handle or GID.">
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && lookUp()}
                className={inputClass}
                placeholder="https://your-store.com/products/perce-ribbed-tank"
              />
            </Field>
          </div>
          <button type="button" onClick={lookUp} className={buttonClass("primary")}>
            Look up
          </button>
        </div>
        {error && (
          <div className="mt-3">
            <Banner tone="danger">{error}</Banner>
          </div>
        )}
      </Card>

      {resolved && (
        <>
          <Card title="Confirm the product">
            <KeyValue
              rows={[
                ["Shopify title", <strong key="t" className="text-ink">{resolved.title}</strong>],
                ["Product ID", <code key="i" className="text-xs">{resolved.shopifyId}</code>],
                ["Handle", <code key="h" className="text-xs">{resolved.handle}</code>],
                ["Type", resolved.productType],
                ["Store", resolved.vendor],
                [
                  "Sync",
                  resolved.syncStatus === "synced" ? (
                    <Badge key="s" tone="success">Synced</Badge>
                  ) : (
                    <Badge key="s" tone="warn">{resolved.syncStatus}</Badge>
                  ),
                ],
              ]}
            />
            <div className="mt-4">
              <Field
                label="Garment name"
                hint="Defaults to the Shopify title. Mirra keeps the Shopify title as canonical."
              >
                <input value={name} onChange={(e) => setName(e.target.value)} className={inputClass} />
              </Field>
              {/* A silent rename is how a garment stops being traceable to the
                  listing it represents. Flag it; never merge it away. */}
              {nameMismatch && (
                <div className="mt-2">
                  <Banner tone="warn">
                    This doesn&apos;t match the Shopify title <strong>{resolved.title}</strong>. Mirra
                    will keep the Shopify title as canonical and record yours as a display name.{" "}
                    <button
                      type="button"
                      onClick={() => setName(resolved.title)}
                      className="font-semibold underline"
                    >
                      Use the Shopify title
                    </button>
                  </Banner>
                </div>
              )}
            </div>
          </Card>

          <Card title={hasOption ? `Which ${resolved.optionName!.toLowerCase()}?` : "Variants"}>
            {hasOption ? (
              <>
                <p className="mb-3 text-[13px] text-muted">
                  This product has {optionValues.length} {resolved.optionName!.toLowerCase()} values.
                  One Mirra garment covers one of them, because each needs its own photography.
                </p>
                <ChipGroup
                  options={available.map((v) => ({ value: v, label: v }))}
                  value={optionValue}
                  onChange={setOptionValue}
                />
                {available.length === 0 && (
                  <p className="mt-2 text-[13px] text-amber-800">
                    Every {resolved.optionName!.toLowerCase()} for this product already has a garment.
                  </p>
                )}
                {optionValues.length !== available.length && available.length > 0 && (
                  <p className="mt-2 text-xs text-muted">
                    Already digitised: {optionValues.filter(taken).join(", ")}
                  </p>
                )}
              </>
            ) : (
              <p className="text-[13px] text-muted">
                This product has no colour-like option, so it maps to a single garment.
              </p>
            )}

            {/* Product → garment → SKU, stated explicitly. */}
            <div className="mt-4 rounded-lg border border-line bg-stone-50 p-3 text-xs">
              <div className="mb-1.5 font-medium text-ink">What will be created</div>
              <ul className="space-y-1 text-muted">
                <li>
                  <span className="text-stone-700">Shopify product</span> — {resolved.title}
                </li>
                <li>
                  <span className="text-stone-700">Mirra try-on garment</span> —{" "}
                  {name || resolved.title}
                  {hasOption && optionValue ? ` — ${optionValue}` : ""}
                </li>
                <li>
                  <span className="text-stone-700">Linked purchasable variants</span> —{" "}
                  {matchedVariants.length > 0
                    ? `${matchedVariants.length} SKUs (${[...new Set(matchedVariants.map((v) => v.size))].join(" · ")})`
                    : "—"}
                </li>
              </ul>
            </div>

            <button
              type="button"
              disabled={hasOption ? !optionValue : matchedVariants.length === 0}
              onClick={() => onCreate(resolved.id, hasOption ? optionValue : optionValues[0] ?? "", name)}
              className={`${buttonClass("accent")} mt-4`}
            >
              Create garment and continue →
            </button>
          </Card>
        </>
      )}
    </div>
  );
}

/**
 * Identity for a garment that already exists: locked, plus the physical-sample
 * questions that everything downstream depends on.
 */
export function IdentifyStep({
  garment: g,
  product,
  allGarments,
}: {
  garment: Garment;
  product: Product | undefined;
  allGarments: Garment[];
}) {
  const sizes = sizesForGarment(g, product);
  const candidates = reuseCandidates(g, allGarments);
  const [extraSizes, setExtraSizes] = useState<string[]>([]);
  const mapping = variantMapping(g, product);
  const optionLabel = product?.optionName ?? "Option";

  return (
    <div className="flex flex-col gap-4">
      <Card title="Identity" action={<Badge tone="neutral">Locked</Badge>}>
        <KeyValue
          rows={[
            [
              "Shopify product",
              product ? (
                <a
                  key="p"
                  href={product.onlineStoreUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-accent hover:underline"
                >
                  {g.canonicalTitle} ↗
                </a>
              ) : (
                g.canonicalTitle
              ),
            ],
            ["Product ID", <code key="i" className="text-xs">{product?.shopifyId ?? "—"}</code>],
            [optionLabel, g.optionValue || "—"],
            ["Mirra garment", g.title],
            [
              "Linked SKUs",
              `${mapping.rows.filter((r) => r.variant).length} of ${mapping.rows.length} sizes matched`,
            ],
          ]}
        />
        {g.merchantTitle && g.merchantTitle !== g.canonicalTitle && (
          <div className="mt-3">
            <Banner tone="warn">
              Display name <strong>{g.merchantTitle}</strong> differs from the Shopify title{" "}
              <strong>{g.canonicalTitle}</strong>.{" "}
              <button
                onClick={() => acceptCanonicalTitleAction(g.id)}
                className="font-semibold underline"
              >
                Use the Shopify title
              </button>
            </Banner>
          </div>
        )}
      </Card>

      {candidates.length > 0 && !g.reusedFromGarmentId && (
        <Banner tone="info">
          <strong>{candidates[0].title}</strong> is already digitised. Same cut? Reuse its geometry,
          grading and fit — you&apos;d only need new colour imagery.
          <span className="mt-2 flex flex-wrap gap-1.5">
            <button
              onClick={() => reuseColourwayAction(g.id, candidates[0].id, "same_cut_and_fabric")}
              className={buttonClass("accent", "sm")}
            >
              Same cut and fabric
            </button>
            <button
              onClick={() => reuseColourwayAction(g.id, candidates[0].id, "same_cut_new_fabric")}
              className={buttonClass("secondary", "sm")}
            >
              Same cut, new fabric
            </button>
          </span>
        </Banner>
      )}
      {g.reusedFromGarmentId && (
        <Banner tone="success">
          Reusing geometry and grading from{" "}
          {allGarments.find((x) => x.id === g.reusedFromGarmentId)?.title ?? "a sibling colourway"}.
        </Banner>
      )}

      <Card title="Which size do you physically have?">
        <p className="mb-3 text-[13px] text-muted">
          Every photograph and measurement that follows describes this one sample. Confirm it before
          capture so the derived sizes can always be traced back.
        </p>
        <ChipGroup
          label="Reference sample"
          options={sizes.map((s) => ({ value: s, label: s }))}
          value={g.referenceSize}
          onChange={(s) => setReferenceSizeAction(g.id, s)}
        />

        {g.referenceSize && (
          <div className="mt-5 border-t border-line pt-4">
            <ChipGroup
              label="Do all sizes share the same pattern and construction?"
              options={[
                { value: "yes", label: "Yes — sizes differ only in measurements", note: "Most common" },
                { value: "no", label: "No — some sizes use a different block" },
              ]}
              value={
                g.sameConstructionAcrossSizes === null
                  ? undefined
                  : g.sameConstructionAcrossSizes
                    ? "yes"
                    : "no"
              }
              onChange={(v) => setConstructionAction(g.id, v === "yes", extraSizes)}
            />
            {g.sameConstructionAcrossSizes === true && (
              <p className="mt-2 text-xs text-emerald-700">
                Photograph size {g.referenceSize} once — Mirra derives{" "}
                {sizes.filter((s) => s !== g.referenceSize).join(", ")} from your graded measurements.
              </p>
            )}
            {g.sameConstructionAcrossSizes === false && (
              <div className="mt-3">
                <ChipGroup
                  label="Which sizes use a different block?"
                  options={sizes.map((s) => ({ value: s, label: s }))}
                  value={undefined}
                  onChange={(s) => {
                    const next = extraSizes.includes(s)
                      ? extraSizes.filter((x) => x !== s)
                      : [...extraSizes, s];
                    setExtraSizes(next);
                    setConstructionAction(g.id, false, next);
                  }}
                />
                <p className="mt-2 text-xs text-muted">
                  {extraSizes.length > 0 ? `Selected: ${extraSizes.join(", ")}. ` : ""}
                  Petite, Tall, Plus and cup-specific ranges usually need their own reference sample.
                  Mirra interpolates within a block and never across blocks.
                </p>
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}

// ----------------------------------------------------------------- capture

const VIEW_LABELS: Record<CaptureView, string> = {
  front: "Front",
  back: "Back",
  left: "Left",
  right: "Right",
};

const CAD_FORMATS: CadAsset["format"][] = ["glb", "fbx", "obj", "zprj", "usdz"];

export function CaptureStep({ garment: g }: { garment: Garment }) {
  const [anchorCm, setAnchorCm] = useState("");
  // Accepting or rejecting a view changes the garment's state; a change
  // announced only by a tile turning green is invisible to a screen reader.
  const notice = useAction();
  const accepted = g.capture.accepted.length;
  const allCaptured = accepted === CAPTURE_VIEWS.length;
  const method = g.capture.method;
  const isCad = method === "cad";

  return (
    <div className="flex flex-col gap-4">
      <NoticeBar notice={notice.notice} onDismiss={notice.clear} />
      <Card title="How are you supplying the garment?">
        <ChipGroup
          options={[
            { value: "phone", label: "Capture with phone" },
            { value: "upload", label: "Upload compliant garment photos" },
            { value: "cad", label: "Upload 3D / CAD asset" },
          ]}
          value={method}
          onChange={(m) => notice.run(() => setCaptureMethodAction(g.id, m))}
        />
        {method === "upload" && (
          <p className="mt-2 text-xs text-muted">
            Existing photography is fine <em>if it already meets the spec below</em> — Mirra runs the
            same checks on uploads as on phone captures. Marketing shots will be rejected.
          </p>
        )}
        {isCad && (
          <p className="mt-2 text-xs text-muted">
            A valid 3D asset already contains the geometry photographs are used to recover, so the
            four photographic views aren&apos;t required.
          </p>
        )}
      </Card>

      {/* 3D and photography are different pipelines — don't ask for four views
          from a merchant who has just supplied a CLO3D file. */}
      {isCad ? (
        <Card title="3D asset">
          {g.capture.cadAsset ? (
            <div className="flex items-center justify-between gap-3">
              <span className="text-[13px]">
                <span className="font-medium text-ink">{g.capture.cadAsset.filename}</span>
                <span className="ml-2 text-xs text-muted uppercase">{g.capture.cadAsset.format}</span>
              </span>
              <Badge tone="success">Accepted</Badge>
            </div>
          ) : (
            <>
              <p className="mb-3 text-[13px] text-muted">
                Accepts {CAD_FORMATS.map((f) => f.toUpperCase()).join(", ")} — including CLO3D
                project files. Mirra validates scale, watertightness and UVs on upload.
              </p>
              <button
                type="button"
                onClick={() =>
                  notice.run(() =>
                    attachCadAssetAction(g.id, {
                      filename: `${g.optionValue.toLowerCase()}-sample.zprj`,
                      format: "zprj",
                    }),
                  )
                }
                className={buttonClass("accent", "sm")}
              >
                Upload 3D asset
              </button>
            </>
          )}
        </Card>
      ) : (
        <>
          <Card title="How to shoot these">
            <p className="mb-3 text-[13px] text-muted">
              Your Shopify product photography won&apos;t work for try-on — model shots, styling and
              crops can&apos;t be reconstructed into a wearable garment. Mirra needs the physical
              sample {g.referenceSize ? `(size ${g.referenceSize}) ` : ""}shot to this specification.
            </p>
            <dl className="grid grid-cols-2 gap-x-6 gap-y-2 max-md:grid-cols-1">
              {CAPTURE_SPEC.map((s) => (
                <div key={s.rule} className="text-xs">
                  <dt className="font-medium text-ink">✓ {s.rule}</dt>
                  <dd className="text-muted">{s.why}</dd>
                </div>
              ))}
            </dl>
          </Card>

          <Card
            title="Required views"
            action={
              <span className="text-xs text-muted">
                {accepted} of {CAPTURE_VIEWS.length} accepted
              </span>
            }
          >
            {!g.referenceSize && (
              <div className="mb-3">
                <Banner tone="warn">
                  Confirm which size you physically have on the Identify step first — every view
                  describes that one sample.
                </Banner>
              </div>
            )}
            <div className="grid grid-cols-4 gap-3 max-md:grid-cols-2">
              {CAPTURE_VIEWS.map((view) => {
                const has = g.capture.accepted.includes(view);
                const issue = g.capture.issues.find((i) => i.view === view);
                return (
                  <div key={view} className="flex flex-col gap-1.5">
                    <button
                      type="button"
                      disabled={!g.referenceSize}
                      onClick={() =>
                        notice.run(() =>
                          recordCaptureAction(g.id, view, { accepted: true }, method ?? "phone"),
                        )
                      }
                      className={`flex aspect-[3/4] flex-col items-center justify-center gap-1 rounded-xl border text-center transition-colors disabled:opacity-50 ${
                        has
                          ? "border-line bg-stone-50 hover:border-accent"
                          : issue
                            ? "border-dashed border-red-300 bg-red-50/40 hover:border-red-400"
                            : "border-dashed border-amber-300 bg-amber-50/40 hover:border-accent"
                      }`}
                    >
                      <span className="text-xl" aria-hidden>{has ? "✓" : issue ? "!" : "＋"}</span>
                      <span className="text-xs font-medium text-stone-600">{VIEW_LABELS[view]}</span>
                      <span className="text-[11px] text-muted">
                        {has ? "Replace" : issue ? "Retake" : method === "upload" ? "Upload" : "Capture"}
                      </span>
                    </button>
                    {issue && <p className="text-[11px] leading-tight text-red-700">{issue.message}</p>}
                    {!has && !issue && g.referenceSize && (
                      <button
                        type="button"
                        onClick={() =>
                          notice.run(() =>
                            recordCaptureAction(g.id, view, {
                              accepted: false,
                              message: "The lower hem is outside the frame.",
                            }),
                          )
                        }
                        className="text-[11px] text-muted underline hover:text-ink"
                      >
                        Simulate reject
                      </button>
                    )}
                  </div>
                );
              })}
            </div>

            {method === "phone" && !allCaptured && (
              <div className="mt-4 flex items-center gap-3 rounded-lg border border-line bg-stone-50 p-3">
                <div className="grid h-14 w-14 shrink-0 place-items-center rounded-md border border-line bg-white text-[10px] text-muted">
                  QR
                </div>
                <p className="text-xs text-muted">
                  Scan to open the Mirra capture experience on your phone. This view updates as each
                  photo arrives; framing, sharpness, lighting and occlusion are checked on arrival.
                </p>
              </div>
            )}
          </Card>
        </>
      )}

      <div className="grid grid-cols-2 gap-4 max-md:grid-cols-1">
        <Card title="Detail shots">
          <p className="mb-3 text-xs text-muted">
            Optional, and worth it — close-ups measurably improve texture realism.
          </p>
          <div className="flex flex-wrap gap-1.5">
            {(["fabric", "closure", "collar", "hem", "other"] as const).map((kind) => (
              <button
                key={kind}
                type="button"
                onClick={() =>
                  notice.run(() =>
                    addDetailShotAction(g.id, kind, `${kind[0].toUpperCase()}${kind.slice(1)} close-up`),
                  )
                }
                className={buttonClass("secondary", "sm")}
              >
                + {kind[0].toUpperCase()}{kind.slice(1)}
              </button>
            ))}
          </div>
          {g.capture.details.length > 0 && (
            <p className="mt-3 text-xs text-muted">
              Added: {g.capture.details.map((d) => d.label).join(", ")}
            </p>
          )}
        </Card>

        {/* Photographs give shape and proportion; centimetres need a physical
            scale. Kept explicit rather than implied by the capture. */}
        <Card title="Auto-measure the sample">
          <p className="mb-3 text-xs text-muted">
            Photos infer shape, not centimetres. Give Mirra a scale — a printed calibration card, a
            LiDAR/depth capture, or one known dimension — and it can measure size{" "}
            {g.referenceSize ?? "—"} into the {MEASUREMENT_FIELDS[g.category].length} measurements
            this category needs.
          </p>
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <Field label="Known dimension — garment length (cm)">
                <input
                  type="number"
                  inputMode="decimal"
                  min={10}
                  max={250}
                  value={anchorCm}
                  onChange={(e) => setAnchorCm(e.target.value)}
                  className={inputClass}
                  placeholder="92"
                />
              </Field>
            </div>
            <button
              type="button"
              disabled={(!allCaptured && !isCad) || Number(anchorCm) <= 0}
              onClick={() =>
                notice.run(() =>
                autoMeasureAction(
                  g.id,
                  "known_dimension",
                  MEASUREMENT_FIELDS[g.category].map((f, i) => ({
                    key: f.key,
                    valueCm: Math.round(Number(anchorCm) * (0.7 + i * 0.12) * 10) / 10,
                    confidence: i < 2 ? "high" : "review",
                  })),
                ))
              }
              className={buttonClass("secondary", "sm")}
            >
              Measure
            </button>
          </div>
          {!allCaptured && !isCad && (
            <p className="mt-1 text-[11px] text-muted">Available once all four views are accepted.</p>
          )}
          {g.autoMeasurements && (
            <ul className="mt-3 space-y-1">
              {g.autoMeasurements.values.map((m) => (
                <li key={m.key} className="flex items-center justify-between text-xs">
                  <span className="capitalize text-stone-600">
                    {MEASUREMENT_FIELDS[g.category].find((f) => f.key === m.key)?.label ?? m.key}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="tabular-nums text-ink">{m.valueCm} cm</span>
                    <Badge tone={m.confidence === "high" ? "success" : "warn"}>
                      {m.confidence === "high" ? "High" : "Review"}
                    </Badge>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {(allCaptured || (isCad && g.capture.cadAsset)) && g.stage === "draft" && (
        <Banner live tone="info">
          {isCad ? "3D asset accepted." : "All four views accepted."}{" "}
          <button
            onClick={() => notice.run(() => startGenerationAction(g.id))}
            className="font-semibold underline"
          >
            Start building the digital garment
          </button>{" "}
          — carry on with material and sizing meanwhile.
        </Banner>
      )}
      {g.stage === "processing" && (
        <Banner tone="info">
          <strong>Creating digital garment…</strong> Carry on below — nothing here waits for it.
        </Banner>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- material

const FABRIC_SOURCE_LABELS: Record<FabricSource, string> = {
  shopify: "Shopify description",
  metafield: "Shopify metafield",
  brand_profile: "Brand material profile",
  tech_pack: "Tech pack",
  manual: "Merchant entered",
  estimated: "Mirra estimate",
};

/** Composition rows that must total 100%. */
function CompositionEditor({
  rows,
  onChange,
}: {
  rows: { material: string; pct: number }[];
  onChange: (rows: { material: string; pct: number }[]) => void;
}) {
  const total = rows.reduce((n, r) => n + (Number(r.pct) || 0), 0);
  return (
    <div>
      <div className="flex flex-col gap-2">
        {rows.map((row, i) => (
          <div key={i} className="flex items-center gap-2">
            <input
              value={row.material}
              onChange={(e) =>
                onChange(rows.map((r, j) => (i === j ? { ...r, material: e.target.value } : r)))
              }
              className={inputClass}
              placeholder="Material"
              aria-label={`Material ${i + 1}`}
            />
            <div className="flex w-24 shrink-0 items-center gap-1">
              <input
                type="number"
                inputMode="numeric"
                min={0}
                max={100}
                value={row.pct}
                onChange={(e) =>
                  onChange(rows.map((r, j) => (i === j ? { ...r, pct: Number(e.target.value) } : r)))
                }
                className={inputClass}
                aria-label={`Percentage ${i + 1}`}
              />
              <span className="text-xs text-muted">%</span>
            </div>
            <button
              type="button"
              onClick={() => onChange(rows.filter((_, j) => j !== i))}
              className={buttonClass("ghost", "sm")}
              aria-label={`Remove material ${i + 1}`}
            >
              ✕
            </button>
          </div>
        ))}
      </div>
      <div className="mt-2 flex items-center gap-3">
        <button
          type="button"
          onClick={() => onChange([...rows, { material: "", pct: 0 }])}
          className={buttonClass("secondary", "sm")}
        >
          + Add material
        </button>
        <span className={`text-xs ${total === 100 ? "text-emerald-700" : "text-amber-800"}`}>
          Total {total}%{total !== 100 && " — must be 100%"}
        </span>
      </div>
    </div>
  );
}

export function MaterialStep({ garment: g }: { garment: Garment }) {
  const notice = useAction();
  const found = g.fabricComposition.length === 0 ? findExistingComposition(g.id) : null;
  const [rows, setRows] = useState(
    g.fabricComposition.length > 0 ? g.fabricComposition : [{ material: "", pct: 100 }],
  );
  const [lining, setLining] = useState(g.liningComposition);
  const total = rows.reduce((n, r) => n + (Number(r.pct) || 0), 0);
  const composition = g.fabricComposition.map((f) => `${f.pct}% ${f.material}`).join(", ");

  return (
    <div className="flex flex-col gap-4">
      <NoticeBar notice={notice.notice} onDismiss={notice.clear} />
      {/* Import before asking anyone to type. The answer usually already
          exists, and a retyped one tends to disagree with the listing. */}
      {found && (
        <Banner tone="info">
          Mirra found <strong>{found.composition.map((f) => `${f.pct}% ${f.material}`).join(", ")}</strong>{" "}
          in {found.label}.{" "}
          <button
            onClick={() => notice.run(() => setFabricAction(g.id, found.composition, found.source))}
            className="font-semibold underline"
          >
            Use it
          </button>{" "}
          — or enter it manually below.
        </Banner>
      )}

      <Card
        title="Composition"
        action={
          g.fabricComposition.length > 0 && g.fabricSource ? (
            <Badge tone={g.fabricConfirmed ? "success" : "warn"}>
              {FABRIC_SOURCE_LABELS[g.fabricSource]}
              {g.fabricConfirmed ? " · confirmed" : " · unconfirmed"}
            </Badge>
          ) : undefined
        }
      >
        {g.fabricComposition.length > 0 && g.fabricConfirmed ? (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="text-[15px] font-medium text-ink">{composition}</span>
            <button
              onClick={() => setFabricAction(g.id, [], "manual")}
              className={buttonClass("secondary", "sm")}
            >
              Edit
            </button>
          </div>
        ) : (
          <>
            <p className="mb-3 text-[13px] text-muted">
              Proportions, not just the main fibre — stretch and drape follow from the blend.
            </p>
            <CompositionEditor rows={rows} onChange={setRows} />

            <details className="mt-4">
              <summary className="cursor-pointer text-xs font-medium text-ink">
                Lining (optional)
              </summary>
              <div className="mt-2">
                <CompositionEditor rows={lining} onChange={setLining} />
              </div>
            </details>

            <div className="mt-4 flex flex-wrap gap-2">
              <button
                disabled={total !== 100 || rows.some((r) => !r.material.trim())}
                onClick={() => notice.run(() => setFabricAction(g.id, rows, "manual", lining))}
                className={buttonClass("accent", "sm")}
              >
                Save composition
              </button>
              {/* Parsing a tech pack needs the document service. Labelling
                  merchant-typed rows as "from a tech pack" would put a
                  provenance on them that nothing supports. */}
              <span className="self-center text-xs text-muted">
                Tech-pack parsing arrives with the document service — enter the blend here for now.
              </span>
            </div>
          </>
        )}
      </Card>

      {g.fabricComposition.length > 0 && (
        <Card
          title="How it behaves"
          action={
            g.attributesSuggested ? (
              <Badge tone="warn">Mirra suggestion · unconfirmed</Badge>
            ) : (
              <Badge tone="success">Confirmed</Badge>
            )
          }
        >
          <p className="mb-3 text-xs text-muted">
            {g.attributesSuggested
              ? `Inferred from ${composition}. Correct anything that's off, then confirm — nothing here is treated as fact until you do.`
              : "These drive how the garment moves and falls in try-on."}
          </p>
          <div className="grid grid-cols-4 gap-3 max-md:grid-cols-2">
            {(
              [
                ["stretch", ["none", "low", "medium", "high"]],
                ["drape", ["structured", "moderate", "fluid"]],
                ["opacity", ["opaque", "semi", "sheer"]],
                ["thickness", ["light", "mid", "heavy"]],
              ] as const
            ).map(([attr, opts]) => (
              <Field key={attr} label={attr[0].toUpperCase() + attr.slice(1)}>
                <select
                  value={g.attributes[attr]}
                  onChange={(e) =>
                    notice.run(() =>
                      confirmAttributesAction(g.id, { ...g.attributes, [attr]: e.target.value }),
                    )
                  }
                  className={inputClass}
                >
                  {opts.map((v) => (
                    <option key={v} value={v}>{v}</option>
                  ))}
                </select>
              </Field>
            ))}
          </div>
          {g.attributesSuggested && (
            <button
              onClick={() => notice.run(() => confirmAttributesAction(g.id, g.attributes))}
              className={`${buttonClass("accent", "sm")} mt-3`}
            >
              Confirm these values
            </button>
          )}
          <details className="mt-4">
            <summary className="cursor-pointer text-xs font-medium text-ink">
              Advanced material properties
            </summary>
            <p className="mt-2 text-xs text-muted">
              GSM, warp/weft stretch, recovery, stiffness and compression are managed on the{" "}
              <Link to={dashPath.fabric} className="font-medium text-accent hover:underline">
                Fabric &amp; material
              </Link>{" "}
              page once a profile exists.
            </p>
          </details>
        </Card>
      )}
    </div>
  );
}

// -------------------------------------------------------------- size & fit

/**
 * The editable measurement grid.
 *
 * Cells start empty and stay empty until a person types in them. That is the
 * whole point: the previous build offered five "sources" that all called one
 * function generating `80 + 4n` for every field, so a garment could reach QA
 * carrying numbers nobody had measured.
 */
function ChartGrid({
  rows,
  category,
  unit,
  referenceSize,
  issues,
  onChange,
}: {
  rows: SizeRow[];
  category: GarmentCategory;
  unit: Unit;
  referenceSize?: string;
  issues: FieldIssue[];
  onChange: (rows: SizeRow[]) => void;
}) {
  const fields = MEASUREMENT_FIELDS[category];
  const issueAt = (size: string, key: string) =>
    issues.find((i) => i.size === size && i.key === key);

  const setCell = (size: string, key: string, raw: string) =>
    onChange(
      rows.map((r) =>
        r.size !== size
          ? r
          : {
              ...r,
              values: {
                ...r.values,
                // Empty means empty. Never coerce a blank cell to zero.
                [key]: raw.trim() === "" ? undefined : toCm(Number(raw), unit),
              },
            },
      ),
    );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-[13px]">
        <caption className="sr-only">
          Measurements per size, entered in {UNIT_LABELS[unit].toLowerCase()}
        </caption>
        <thead>
          <tr className="text-xs text-muted">
            <th scope="col" className="py-1.5 pr-3 font-medium">Size</th>
            {fields.map((f) => (
              <th key={f.key} scope="col" className="py-1.5 pr-3 font-medium" title={f.how}>
                {f.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-stone-100">
          {rows.map((row) => (
            <tr key={row.size}>
              <th scope="row" className="py-1.5 pr-3 text-left font-medium whitespace-nowrap">
                {row.size}
                {row.size === referenceSize && (
                  <span className="ml-1.5 text-[11px] font-normal text-muted">reference</span>
                )}
              </th>
              {fields.map((f) => {
                const issue = issueAt(row.size, f.key);
                const v = row.values[f.key];
                return (
                  <td key={f.key} className="py-1.5 pr-3">
                    <input
                      type="number"
                      inputMode="decimal"
                      step="0.1"
                      aria-label={`${f.label} for size ${row.size}`}
                      aria-invalid={issue ? true : undefined}
                      title={issue?.detail}
                      value={typeof v === "number" ? String(fromCm(v, unit)) : ""}
                      onChange={(e) => setCell(row.size, f.key, e.target.value)}
                      className={`w-20 rounded-md border px-2 py-1 text-[13px] tabular-nums focus:outline-none ${
                        issue
                          ? "border-red-300 bg-red-50/50 text-red-900"
                          : "border-line bg-surface focus:border-accent"
                      }`}
                    />
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Import from a file or a paste, with the mapping shown before it is applied. */
function ChartImport({
  category,
  unit,
  onParsed,
}: {
  category: GarmentCategory;
  unit: Unit;
  onParsed: (rows: SizeRow[], source: SizeSource) => void;
}) {
  const [text, setText] = useState("");
  const [preview, setPreview] = useState<ParsedChart | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [source, setSource] = useState<SizeSource>("uploaded_chart");

  const parse = (raw: string, from: SizeSource) => {
    const result = parseChart(raw, category, unit);
    if ("error" in result) {
      setPreview(null);
      setError(result.error);
      return;
    }
    setSource(from);
    setPreview(result);
    setError(null);
  };

  const onFile = async (file: File | undefined) => {
    if (!file) return;
    if (file.size > 2_000_000) {
      setError("That file is larger than 2 MB — export just the size chart sheet as CSV.");
      return;
    }
    const raw = await file.text();
    setText(raw);
    parse(raw, "uploaded_chart");
  };

  return (
    <div className="flex flex-col gap-3">
      <Field
        label="Upload a CSV or TSV size chart"
        hint="First column is the size label; one column per measurement. Exported straight from a spreadsheet is fine."
      >
        <input
          type="file"
          accept=".csv,.tsv,.txt,text/csv,text/tab-separated-values,text/plain"
          onChange={(e) => void onFile(e.target.files?.[0])}
          className="block w-full text-[13px] file:mr-3 file:cursor-pointer file:rounded-lg file:border file:border-line file:bg-surface file:px-3 file:py-1.5 file:text-[13px] file:font-medium"
        />
      </Field>

      <details>
        <summary className="cursor-pointer text-xs font-medium text-ink">
          …or paste it from a spreadsheet
        </summary>
        <div className="mt-2">
          <textarea
            rows={4}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={"Size,Chest,Shoulder,Length,Sleeve\nS,49,41,68,60\nM,52,43,70,61"}
            className={`${inputClass} font-mono text-xs`}
            aria-label="Paste size chart"
          />
          <button
            type="button"
            disabled={!text.trim()}
            onClick={() => parse(text, "manual")}
            className={`${buttonClass("secondary", "sm")} mt-2`}
          >
            Read this
          </button>
        </div>
      </details>

      {error && (
        <Banner live tone="danger">
          {error}
        </Banner>
      )}

      {/* The mapping is shown before anything is applied: which of your columns
          became which measurement, and what didn't match. */}
      {preview && (
        <div className="rounded-lg border border-line bg-stone-50 p-3">
          <div className="text-[13px] font-medium text-ink">
            Read {preview.rowCount} size{preview.rowCount === 1 ? "" : "s"}, in{" "}
            {UNIT_LABELS[unit].toLowerCase()}.
          </div>
          {preview.unmatchedFields.length > 0 && (
            <p className="mt-1 text-xs text-amber-800">
              No column for: {preview.unmatchedFields.join(", ")} — you can fill these in below.
            </p>
          )}
          {preview.unmappedColumns.length > 0 && (
            <p className="mt-1 text-xs text-muted">
              Ignored columns this category doesn&apos;t use: {preview.unmappedColumns.join(", ")}.
            </p>
          )}
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              onClick={() => {
                onParsed(preview.rows, source);
                setPreview(null);
                setText("");
              }}
              className={buttonClass("accent", "sm")}
            >
              Use these {preview.rowCount} rows
            </button>
            <button type="button" onClick={() => setPreview(null)} className={buttonClass("ghost", "sm")}>
              Discard
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export function SizingStep({
  garment: g,
  product,
  tenant,
}: {
  garment: Garment;
  product: Product | undefined;
  tenant: Tenant;
}) {
  const sizes = sizesForGarment(g, product);
  const fields = MEASUREMENT_FIELDS[g.category];
  const brandChart = tenant.defaults.brandSizeCharts.find((c) => !c.archived);
  const mapping = variantMapping(g, product);
  const plan = gradingPlan(g, product);

  const [unit, setUnit] = useState<Unit>("cm");
  const [draft, setDraft] = useState<SizeRow[] | null>(null);
  const [draftSource, setDraftSource] = useState<SizeSource>("manual");
  const [draftGrading, setDraftGrading] = useState<GradingSource>("chart");
  const notice = useAction();

  const working = draft ?? g.sizeChart;
  const validation = validateChart(working, g.category, sizes, g.referenceSize);
  const dirty = draft !== null;

  const startManual = () => {
    setDraft(blankRows(sizes, g.category));
    setDraftSource("manual");
    setDraftGrading("chart");
  };

  const startEdit = () => {
    setDraft(g.sizeChart.map((r) => ({ size: r.size, values: { ...r.values } })));
    setDraftSource(g.sizeSource ?? "manual");
    setDraftGrading(g.gradingSource ?? "chart");
  };

  const save = () =>
    notice.run(
      () => setSizeChartAction(g.id, working, draftSource, g.sizeChartKind ?? "garment", draftGrading),
      () => setDraft(null),
    );

  // Grading from brand rules needs a measured reference row to grade *from*.
  const referenceRow = working.find((r) => r.size === g.referenceSize);
  const referenceMeasured =
    referenceRow !== undefined &&
    fields.every((f) => typeof referenceRow.values[f.key] === "number");

  const autoRow: SizeRow | null =
    g.autoMeasurements && g.referenceSize
      ? {
          size: g.referenceSize,
          values: Object.fromEntries(g.autoMeasurements.values.map((m) => [m.key, m.valueCm])),
        }
      : null;

  return (
    <div className="flex flex-col gap-4">
      <NoticeBar notice={notice.notice} onDismiss={notice.clear} />

      <Card
        title="Where does the sizing come from?"
        action={
          <span className="flex items-center gap-1.5 text-xs">
            <span className="text-muted">Working in</span>
            {(["cm", "in"] as Unit[]).map((u) => (
              <button
                key={u}
                type="button"
                onClick={() => setUnit(u)}
                aria-pressed={unit === u}
                className={`rounded-md border px-2 py-0.5 font-medium ${
                  unit === u ? "border-accent bg-accent-soft text-accent" : "border-line text-muted"
                }`}
              >
                {u}
              </button>
            ))}
          </span>
        }
      >
        <p className="mb-3 text-xs text-muted">
          Whatever you supply has to cover this product&apos;s Shopify sizes:{" "}
          <strong>{sizes.join(" · ") || "—"}</strong>. Mirra records where each chart came from, so
          a fit problem can always be traced back to its source.
        </p>

        <ChartImport
          category={g.category}
          unit={unit}
          onParsed={(rows, source) => {
            setDraft(rows);
            setDraftSource(source);
            setDraftGrading("chart");
          }}
        />

        <div className="mt-4 flex flex-wrap gap-1.5 border-t border-line pt-4">
          <button onClick={startManual} className={buttonClass("secondary", "sm")}>
            Enter measurements by hand
          </button>
          {autoRow && (
            <button
              onClick={() => {
                setDraft([autoRow]);
                setDraftSource("auto_measured");
                setDraftGrading("estimated");
              }}
              className={buttonClass("secondary", "sm")}
            >
              Use the {g.autoMeasurements!.values.length} measurements taken from size{" "}
              {g.referenceSize}
            </button>
          )}
        </div>
        {!autoRow && (
          <p className="mt-2 text-[11px] text-muted">
            Measuring the sample from its photographs needs a calibration on the Capture step first —
            photographs give shape, not centimetres.
          </p>
        )}

        {/* Two sources that need a backend to be real. Disabled and labelled,
            rather than quietly producing numbers of their own. */}
        <details className="mt-4">
          <summary className="cursor-pointer text-xs font-medium text-ink">
            Import from Shopify or a tech pack
          </summary>
          <div className="mt-2">
            <Banner tone="info">
              Reading a size chart out of a Shopify metafield, a PDF tech pack or a photographed
              chart needs the merchant API and the parsing service. Neither is connected here, so
              neither is offered — export your chart as CSV and upload it above.
            </Banner>
          </div>
        </details>

        {/* A brand chart applied blind is a fast way to size a garment wrongly.
            Show what it contains and whether it actually fits this product. */}
        {brandChart && (
          <div className="mt-4 rounded-lg border border-line bg-stone-50 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-[13px] font-medium text-ink">
                {brandChart.label} <span className="text-xs text-muted">v{brandChart.version}</span>
              </span>
              <Badge tone={brandChart.gradingRules ? "info" : "neutral"}>
                {brandChart.gradingRules ? "Grades by rule" : "Chart only"}
              </Badge>
            </div>
            <p className="mt-1 text-xs text-muted">
              {brandChart.kind === "body" ? "Body measurements" : "Finished garment"}
              {brandChart.gradingRules &&
                ` · ${Object.entries(brandChart.gradingRules)
                  .map(([k, v]) => `${k} +${v} cm`)
                  .join(", ")} per size step`}
            </p>
            {brandChart.gradingRules ? (
              <>
                <p className="mt-2 text-xs text-stone-700">
                  Grading rules step your measured reference size out to the rest. They need size{" "}
                  {g.referenceSize ?? "—"} measured first — the rules say how sizes differ, not what
                  this garment actually is.
                </p>
                <button
                  disabled={!referenceMeasured}
                  onClick={() => {
                    setDraft(gradeFromRules(referenceRow!, sizes, brandChart.gradingRules!));
                    setDraftSource("brand_chart");
                    setDraftGrading("rules");
                  }}
                  className={`${buttonClass(referenceMeasured ? "accent" : "secondary", "sm")} mt-2`}
                >
                  Grade from size {g.referenceSize ?? "—"}
                </button>
                {!referenceMeasured && (
                  <p className="mt-1 text-[11px] text-amber-800">
                    Measure every field of size {g.referenceSize ?? "the reference"} below first.
                  </p>
                )}
              </>
            ) : (
              <p className="mt-2 text-xs text-amber-800">
                This chart has no rows or grading rules stored yet — add them under Settings → Brand
                size charts before it can size a garment.
              </p>
            )}
          </div>
        )}
      </Card>

      {(working.length > 0 || dirty) && (
        <>
          <Card
            title={
              dirty
                ? `Draft measurements (${UNIT_LABELS[unit].toLowerCase()})`
                : `Measurements — ${g.sizeSource ? SIZE_SOURCE_LABELS[g.sizeSource] : "unknown source"}`
            }
            action={
              dirty ? (
                <Badge tone={validation.valid ? "success" : "warn"}>
                  {validation.valid
                    ? "Ready to save"
                    : `${validation.issues.length + validation.missingSizes.length} to fix`}
                </Badge>
              ) : (
                <button onClick={startEdit} className={buttonClass("secondary", "sm")}>
                  Edit
                </button>
              )
            }
          >
            <div className="mb-3">
              <ChipGroup
                label="What do these numbers describe?"
                options={[
                  { value: "garment", label: "Finished garment" },
                  { value: "body", label: "Body measurements" },
                  { value: "unknown", label: "I'm not sure" },
                ]}
                value={g.sizeChartKind}
                onChange={(kind) =>
                  notice.run(() =>
                    setSizeChartAction(
                      g.id,
                      g.sizeChart,
                      g.sizeSource ?? "manual",
                      kind,
                      g.gradingSource ?? "chart",
                    ),
                  )
                }
              />
              {g.sizeChartKind === "unknown" && (
                <p className="mt-2 text-xs text-amber-800">
                  Treated as finished-garment measurements and flagged for QA. These fit very
                  differently — confirming which noticeably improves accuracy.
                </p>
              )}
            </div>

            {dirty ? (
              <ChartGrid
                rows={working}
                category={g.category}
                unit={unit}
                referenceSize={g.referenceSize}
                issues={validation.issues}
                onChange={setDraft}
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-[13px]">
                  <caption className="sr-only">Saved measurements per size, in centimetres</caption>
                  <thead>
                    <tr className="text-xs text-muted">
                      <th scope="col" className="py-1.5 pr-4 font-medium">Size</th>
                      {fields.map((f) => (
                        <th key={f.key} scope="col" className="py-1.5 pr-4 font-medium" title={f.how}>
                          {f.label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-100">
                    {g.sizeChart.map((row) => (
                      <tr key={row.size}>
                        <th scope="row" className="py-2 pr-4 text-left font-medium">
                          {row.size}
                          {row.size === g.referenceSize && (
                            <span className="ml-1.5 text-[11px] font-normal text-muted">reference</span>
                          )}
                        </th>
                        {fields.map((f) => (
                          <td key={f.key} className="py-2 pr-4 tabular-nums">
                            {typeof row.values[f.key] === "number" ? (
                              `${fromCm(row.values[f.key] as number, unit)}`
                            ) : (
                              <span className="text-amber-700">—</span>
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Validation is per cell, per size and per SKU — a chart is only
                complete when every required field of every Shopify size holds
                a plausible number. */}
            {(validation.issues.length > 0 ||
              validation.missingSizes.length > 0 ||
              validation.extraSizes.length > 0 ||
              validation.orderingWarnings.length > 0) && (
              <div className="mt-3 flex flex-col gap-2">
                {validation.missingSizes.length > 0 && (
                  <Banner tone="warn">
                    <strong>{validation.missingSizes.join(", ")}</strong> exist as Shopify variants
                    but have no row here. Shoppers on those sizes would get no try-on.
                    {dirty && (
                      <button
                        onClick={() =>
                          setDraft([
                            ...working,
                            ...blankRows(validation.missingSizes, g.category),
                          ])
                        }
                        className="ml-1.5 font-semibold underline"
                      >
                        Add the missing rows
                      </button>
                    )}
                  </Banner>
                )}
                {validation.extraSizes.length > 0 && (
                  <Banner tone="warn">
                    <strong>{validation.extraSizes.join(", ")}</strong> are in the chart but match no
                    Shopify variant. Check the size labels agree with your store.
                  </Banner>
                )}
                {validation.issues.length > 0 && (
                  <details open className="rounded-lg border border-red-200 bg-red-50 px-3 py-2">
                    <summary className="cursor-pointer text-[13px] font-medium text-red-800">
                      {validation.issues.length} measurement
                      {validation.issues.length === 1 ? "" : "s"} to fix
                    </summary>
                    <ul className="mt-1.5 space-y-1">
                      {validation.issues.slice(0, 12).map((i) => (
                        <li key={`${i.size}-${i.key}-${i.problem}`} className="text-xs text-red-900">
                          {i.detail}
                        </li>
                      ))}
                      {validation.issues.length > 12 && (
                        <li className="text-xs text-red-900">
                          …and {validation.issues.length - 12} more.
                        </li>
                      )}
                    </ul>
                  </details>
                )}
                {validation.orderingWarnings.length > 0 && (
                  <p className="text-xs text-amber-800">
                    {validation.orderingWarnings.join(", ")} don&apos;t change consistently across
                    the size run. That&apos;s usually a chart pasted in a different order — worth a
                    look before QA.
                  </p>
                )}
              </div>
            )}

            {dirty && (
              <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-line pt-3">
                <button
                  disabled={!validation.valid || notice.pending}
                  onClick={save}
                  className={buttonClass("accent", "sm")}
                >
                  {notice.pending ? "Saving…" : `Save ${working.length} sizes`}
                </button>
                <button onClick={() => setDraft(null)} className={buttonClass("ghost", "sm")}>
                  Discard changes
                </button>
                <span className="text-xs text-muted">
                  Saved as <strong>{SIZE_SOURCE_LABELS[draftSource]}</strong>
                  {draftGrading === "estimated" && " · flagged as a draft until you verify it"}
                </span>
              </div>
            )}

            <details className="mt-3">
              <summary className="cursor-pointer text-xs font-medium text-ink">
                How to measure {g.sizeChartKind === "body" ? "(body)" : "(finished garment)"}
              </summary>
              {g.sizeChartKind === "body" ? (
                <p className="mt-2 text-xs text-muted">
                  Body measurements are taken around the wearer — chest, waist and hip are full
                  circumferences, measured level and snug but not tight. They are <em>not</em> the
                  flat seam-to-seam numbers below, and are typically about half of a garment&apos;s
                  circumference plus its ease.
                </p>
              ) : (
                <dl className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1 max-md:grid-cols-1">
                  {fields.map((f) => (
                    <div key={f.key} className="text-xs">
                      <dt className="inline font-medium text-ink">{f.label}: </dt>
                      <dd className="inline text-muted">{f.how}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </details>
          </Card>

          {g.gradingUnverified && (
            <Banner live tone="warn">
              <strong>Draft sizes — verification required.</strong> Derived from one sample rather
              than measured or supplied.{" "}
              <button
                onClick={() => notice.run(() => verifyGradingAction(g.id))}
                className="font-semibold underline"
              >
                I&apos;ve checked these
              </button>
            </Banner>
          )}

          {/* What the merchant most needs to understand: how the sizes they did
              not photograph came to exist. */}
          <Card title="How the other sizes are generated">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-[13px] font-medium text-ink">{plan.headline}</div>
                <p className="mt-0.5 text-xs text-muted">{plan.detail}</p>
              </div>
              <Badge tone={plan.tone}>{plan.method === "estimated" ? "Draft" : "Source"}</Badge>
            </div>
          </Card>

          {/* Explicit SKU mapping, confirmed by a human before QA. */}
          <Card
            title="Size → Shopify variant"
            action={
              <Badge tone={g.variantMappingConfirmed ? "success" : mapping.allMatched ? "info" : "warn"}>
                {g.variantMappingConfirmed
                  ? "Confirmed"
                  : mapping.allMatched
                    ? "Auto-matched"
                    : "Incomplete"}
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
            {mapping.unmatchedVariants.length > 0 && (
              <p className="mt-2 text-xs text-amber-800">
                Shopify has variants with no generated size:{" "}
                {mapping.unmatchedVariants.map((v) => v.size).join(", ")}
              </p>
            )}
            <label className="mt-3 flex items-center gap-2 text-[13px]">
              <input
                type="checkbox"
                checked={g.variantMappingConfirmed}
                onChange={(e) => notice.run(() => confirmVariantMappingAction(g.id, e.target.checked))}
              />
              I&apos;ve checked each size maps to the right variant
            </label>
          </Card>
        </>
      )}

      <FitCard garment={g} />
    </div>
  );
}

/** Structured fit, with only the controls this category can actually have. */
function FitCard({ garment: g }: { garment: Garment }) {
  const fields = MEASUREMENT_FIELDS[g.category];
  const behaviours = CATEGORY_BEHAVIOURS[g.category];
  const [notes, setNotes] = useState(g.fitNotes);

  const update = (patch: {
    silhouette?: Silhouette;
    behaviours?: GarmentBehaviour[];
    areas?: string[];
    notes?: string;
  }) =>
    setFitAction(
      g.id,
      patch.silhouette ?? g.silhouette ?? "regular",
      patch.behaviours ?? g.behaviours,
      patch.areas ?? g.fitCriticalAreas,
      patch.notes ?? notes,
    );

  return (
    <Card title="How it fits">
      <div className="flex flex-col gap-4">
        <ChipGroup
          label="Intended silhouette"
          options={(["fitted", "regular", "relaxed", "oversized"] as const).map((s) => ({
            value: s,
            label: s[0].toUpperCase() + s.slice(1),
          }))}
          value={g.silhouette}
          onChange={(s) => update({ silhouette: s })}
        />

        <div>
          <div className="mb-1.5 text-xs font-medium text-ink">
            Fit-critical areas <span className="font-normal text-muted">— for a {g.category}</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {fields.map((f) => {
              const on = g.fitCriticalAreas.includes(f.key);
              return (
                <button
                  key={f.key}
                  type="button"
                  onClick={() =>
                    update({
                      areas: on
                        ? g.fitCriticalAreas.filter((a) => a !== f.key)
                        : [...g.fitCriticalAreas, f.key],
                    })
                  }
                  aria-pressed={on}
                  className={`rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors ${
                    on ? "border-accent bg-accent-soft text-accent" : "border-line bg-surface text-stone-600 hover:border-accent"
                  }`}
                >
                  {f.label}
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <div className="mb-1.5 text-xs font-medium text-ink">Construction</div>
          <div className="flex flex-wrap gap-1.5">
            {behaviours.map((b) => {
              const on = g.behaviours.includes(b);
              return (
                <button
                  key={b}
                  type="button"
                  onClick={() =>
                    update({
                      behaviours: on ? g.behaviours.filter((x) => x !== b) : [...g.behaviours, b],
                    })
                  }
                  aria-pressed={on}
                  className={`rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors ${
                    on ? "border-accent bg-accent-soft text-accent" : "border-line bg-surface text-stone-600 hover:border-accent"
                  }`}
                >
                  {BEHAVIOUR_LABELS[b]}
                </button>
              );
            })}
          </div>
        </div>

        <Field label="Shopper-facing fit note" hint="Generated from the answers above. Edit freely.">
          <textarea
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            onBlur={() => update({ notes })}
            className={inputClass}
            placeholder="High rise, full-length wide leg. Runs slightly long."
          />
        </Field>
      </div>
    </Card>
  );
}
