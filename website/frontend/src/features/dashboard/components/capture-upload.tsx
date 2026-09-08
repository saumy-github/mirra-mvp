import { useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { merchantApi, type MerchantGarment } from "../data/merchant-api";
import { Badge, Banner, Card, Field } from "./ui";
import { buttonClass, inputClass } from "./styles";

/**
 * Step 2 — Capture. Real files, really uploaded.
 *
 * The prototype recorded a capture by writing the constant filename
 * `front.jpg` with `accepted: true`; no `<input type="file">` existed and no
 * bytes ever moved (audit P1-01). Every tile here posts the actual file to
 * `POST /merchant/{t}/garments/{g}/capture`, which validates the format and
 * the short edge, hashes the bytes, stores them under the upload root, and
 * returns the garment with the asset recorded — size, checksum, dimensions
 * and the sample size it was shot against.
 */

const VIEWS = [
  { key: "front", label: "Front", hint: "Flat, centred, full garment in frame" },
  { key: "back", label: "Back", hint: "Same distance and lighting as the front" },
  { key: "left", label: "Left side", hint: "Sleeve and side seam visible" },
  { key: "right", label: "Right side", hint: "Mirror of the left" },
] as const;

export function CaptureUpload({
  tenantId,
  garment,
  onChange,
}: {
  tenantId: string;
  garment: MerchantGarment;
  onChange: (g: MerchantGarment) => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [size, setSize] = useState(garment.capture.referenceSize);

  const setReference = useMutation({
    mutationFn: (value: string) => merchantApi.setReferenceSize(tenantId, garment.garmentId, value),
    onSuccess: onChange,
    onError: (err: Error) => setError(err.message),
  });

  const upload = useMutation({
    mutationFn: ({ view, file }: { view: string; file: File }) =>
      merchantApi.uploadCapture(tenantId, garment.garmentId, view, file),
    onSuccess: (g) => {
      onChange(g);
      setError(null);
    },
    onError: (err: Error) => setError(err.message),
  });

  const sizes: string[] = (garment.sizing.rows as { size?: string }[])
    .map((r) => r.size ?? "")
    .filter(Boolean);
  const needsReference = !garment.capture.referenceSize;

  return (
    <div className="flex flex-col gap-4">
      <Card title="Which sample are you photographing?">
        <p className="mb-3 text-[13px] text-muted">
          Every measurement Mirra takes from these photos belongs to one physical sample. Naming it
          first is what stops a size S being measured as an M later on.
        </p>
        <div className="flex flex-wrap items-end gap-2">
          <div className="min-w-48">
            <Field label="Reference sample size" hint="The garment in your hands right now.">
              {sizes.length > 0 ? (
                <select value={size} onChange={(e) => setSize(e.target.value)} className={inputClass}>
                  <option value="">Choose…</option>
                  {sizes.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  value={size}
                  onChange={(e) => setSize(e.target.value)}
                  className={inputClass}
                  placeholder="M"
                />
              )}
            </Field>
          </div>
          <button
            type="button"
            disabled={!size || size === garment.capture.referenceSize || setReference.isPending}
            onClick={() => setReference.mutate(size)}
            className={buttonClass("secondary")}
          >
            {garment.capture.referenceSize ? "Change sample" : "Set sample"}
          </button>
          {garment.capture.referenceSize && (
            <Badge tone="success">Size {garment.capture.referenceSize}</Badge>
          )}
        </div>

        {garment.capture.issues.map((issue) => (
          <div key={issue} className="mt-3">
            <Banner tone="warn">{issue}</Banner>
          </div>
        ))}
      </Card>

      <Card
        title="Capture set"
        action={
          <span className="text-xs text-muted">
            {garment.capture.assets.filter((a) => a.accepted).length} of {VIEWS.length} views
          </span>
        }
      >
        {needsReference && (
          <div className="mb-3">
            <Banner tone="warn">
              Choose the sample size above before uploading — otherwise the photographs have no
              garment to be measurements of.
            </Banner>
          </div>
        )}

        <div className="grid grid-cols-4 gap-3 max-md:grid-cols-2">
          {VIEWS.map((view) => (
            <ViewTile
              key={view.key}
              tenantId={tenantId}
              garment={garment}
              view={view}
              disabled={needsReference || upload.isPending}
              uploading={upload.isPending && upload.variables?.view === view.key}
              onPick={(file) => upload.mutate({ view: view.key, file })}
              onChange={onChange}
            />
          ))}
        </div>

        {error && (
          <div className="mt-3">
            <Banner tone="danger">{error}</Banner>
          </div>
        )}

        <p className="mt-3 text-xs text-muted">
          JPEG, PNG or WebP, at least 640px on the short edge. HEIC is rejected — set the phone
          camera to &ldquo;Most Compatible&rdquo;. The front view is the one segmentation runs on,
          so it is the one worth getting right.
        </p>
      </Card>
    </div>
  );
}

function ViewTile({
  tenantId,
  garment,
  view,
  disabled,
  uploading,
  onPick,
  onChange,
}: {
  tenantId: string;
  garment: MerchantGarment;
  view: { key: string; label: string; hint: string };
  disabled: boolean;
  uploading: boolean;
  onPick: (file: File) => void;
  onChange: (g: MerchantGarment) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const asset = garment.capture.assets.find((a) => a.view === view.key);

  // The capture route needs an Authorization header, which an <img src> cannot
  // send — so the file is fetched through the authed client and shown as an
  // object URL, the same trade the avatar viewer makes.
  const { data: blobUrl } = useQuery({
    queryKey: ["capture-thumb", tenantId, garment.garmentId, asset?.assetId, asset?.sha256],
    enabled: Boolean(asset),
    staleTime: Infinity,
    retry: false,
    queryFn: async () => {
      const blob = await merchantApi.fetchCaptureBlob(tenantId, garment.garmentId, asset!.assetId);
      return URL.createObjectURL(blob);
    },
  });

  const reject = useMutation({
    mutationFn: (reason: string) =>
      merchantApi.rejectCapture(tenantId, garment.garmentId, asset!.assetId, reason),
    onSuccess: onChange,
  });

  return (
    <div className="flex flex-col gap-1.5">
      <button
        type="button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        className={`relative flex aspect-[3/4] w-full items-center justify-center overflow-hidden rounded-lg border transition-colors ${
          asset?.accepted
            ? "border-emerald-300 bg-emerald-50/40"
            : asset
              ? "border-amber-300 bg-amber-50/40"
              : "border-dashed border-line bg-stone-50 hover:border-accent"
        } ${disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer"}`}
      >
        {blobUrl ? (
          <img src={blobUrl} alt={`${view.label} view`} className="h-full w-full object-cover" />
        ) : uploading ? (
          <span className="text-xs text-muted">Uploading…</span>
        ) : (
          <span className="px-2 text-center text-xs text-muted">
            {asset ? "Re-upload" : `Add ${view.label.toLowerCase()}`}
          </span>
        )}
      </button>

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onPick(file);
          // Reset so re-picking the same file still fires a change event.
          e.target.value = "";
        }}
      />

      <div className="text-[13px] font-medium text-ink">{view.label}</div>
      {asset ? (
        <div className="text-[11px] text-muted">
          {asset.width && asset.height ? `${asset.width}×${asset.height} · ` : ""}
          {(asset.bytes / 1024).toFixed(0)} KB
          {asset.sampleSize ? ` · size ${asset.sampleSize}` : ""}
          {!asset.accepted && asset.rejectedReason ? (
            <span className="block text-amber-800">Rejected: {asset.rejectedReason}</span>
          ) : null}
          {asset.accepted && (
            <button
              type="button"
              onClick={() => reject.mutate("Rejected during review")}
              className="mt-0.5 block text-[11px] font-medium text-accent hover:underline"
            >
              Mark unusable
            </button>
          )}
        </div>
      ) : (
        <div className="text-[11px] text-muted">{view.hint}</div>
      )}
    </div>
  );
}
