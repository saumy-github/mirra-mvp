import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { merchantApi, type MerchantGarment, type MerchantProduct } from "../data/merchant-api";
import { Badge, Banner, Card, Field } from "./ui";
import { buttonClass, inputClass } from "./styles";

/**
 * Sizing — one row per size, in the pipeline's own field names and cm. Each
 * row becomes its own ingestion run, so the four required measurements are
 * what Step 2 cannot draft without. Widths are flat, seam to seam (half the
 * circumference), never the full girth.
 */

const MEASUREMENTS = [
  { key: "half_chest_width_cm", label: "Chest ½", hint: "Flat, armpit to armpit", required: true },
  { key: "garment_length_cm", label: "Length", hint: "High point of shoulder to hem", required: true },
  { key: "shoulder_width_cm", label: "Shoulder", hint: "Seam to seam across the back", required: true },
  { key: "armhole_depth_cm", label: "Armhole", hint: "Shoulder seam to underarm, straight", required: true },
  { key: "sleeve_length_cm", label: "Sleeve", hint: "Shoulder seam to cuff" },
  { key: "bicep_width_cm", label: "Bicep ½", hint: "Flat, 2.5 cm below the armhole" },
  { key: "neck_width_cm", label: "Neck", hint: "Seam to seam at the collar" },
  { key: "neck_depth_front_cm", label: "Neck drop F", hint: "Front neckline depth" },
  { key: "neck_depth_back_cm", label: "Neck drop B", hint: "Back neckline depth" },
  { key: "hem_width_cm", label: "Hem ½", hint: "Flat; derived if empty" },
  { key: "wrist_width_cm", label: "Cuff ½", hint: "Flat; derived if empty" },
] as const;

type MeasurementKey = (typeof MEASUREMENTS)[number]["key"];
type Row = { size: string; variantId: string } & Partial<Record<MeasurementKey, string>>;

const FIT_TYPES = ["slim", "regular", "relaxed", "oversized"] as const;
const SOURCES = [
  { value: "measured", label: "Measured from the samples" },
  { value: "brand_chart", label: "Our finished-garment size chart" },
  { value: "estimated", label: "Estimated" },
] as const;

function colourwayVariants(garment: MerchantGarment, product: MerchantProduct | null) {
  return (product?.variants ?? []).filter(
    (v) => !garment.optionValue || !v.colour || v.colour === garment.optionValue,
  );
}

function initialRows(garment: MerchantGarment, product: MerchantProduct | null): Row[] {
  if (garment.sizing.rows.length) {
    return garment.sizing.rows.map((raw) => {
      const r = raw as Record<string, unknown>;
      const row: Row = { size: String(r.size ?? ""), variantId: String(r.variant_id ?? "") };
      for (const m of MEASUREMENTS) {
        const v = r[m.key];
        if (typeof v === "number") row[m.key] = String(v);
      }
      return row;
    });
  }
  const sizes = [...new Set(colourwayVariants(garment, product).map((v) => v.size).filter(Boolean))];
  return (sizes.length ? sizes : [""]).map((size) => ({ size, variantId: "" }));
}

export function SizingEditor({
  tenantId,
  garment,
  product,
  onChange,
}: {
  tenantId: string;
  garment: MerchantGarment;
  product: MerchantProduct | null;
  onChange: (g: MerchantGarment) => void;
}) {
  const variants = colourwayVariants(garment, product);
  const [rows, setRows] = useState<Row[]>(() => initialRows(garment, product));
  const [fitType, setFitType] = useState(garment.sizing.fitType);
  const [source, setSource] = useState(garment.sizing.source);
  const [fitNotes, setFitNotes] = useState(garment.sizing.fitNotes);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const variantFor = (row: Row) =>
    variants.find((v) => v.variantId === row.variantId) ?? variants.find((v) => v.size === row.size);

  const save = useMutation({
    mutationFn: () =>
      merchantApi.setSizing(tenantId, garment.garmentId, {
        rows: rows
          .filter((r) => r.size.trim())
          .map((r) => {
            const out: Record<string, unknown> = {
              size: r.size.trim(),
              variant_id: variantFor(r)?.variantId ?? "",
            };
            for (const m of MEASUREMENTS) {
              const n = Number(r[m.key]);
              if (r[m.key] && Number.isFinite(n) && n > 0) out[m.key] = n;
            }
            return out;
          }),
        fitType,
        fitNotes,
        source,
      }),
    onSuccess: (g) => {
      setError(null);
      setDirty(false);
      onChange(g);
    },
    onError: (err: Error) => setError(err.message),
  });

  const confirm = useMutation({
    mutationFn: () => merchantApi.confirmVariantMapping(tenantId, garment.garmentId, true),
    onSuccess: (g) => {
      setError(null);
      onChange(g);
    },
    onError: (err: Error) => setError(err.message),
  });

  const setRow = (i: number, patch: Partial<Row>) => {
    setDirty(true);
    setRows((rs) => rs.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  };

  const sizes = rows.map((r) => r.size.trim()).filter(Boolean);
  const duplicate = sizes.length !== new Set(sizes).size;
  const missingRequired = rows.some(
    (r) => r.size.trim() && MEASUREMENTS.some((m) => "required" in m && !(Number(r[m.key]) > 0)),
  );
  const saved = garment.sizing.rows as Record<string, unknown>[];

  return (
    <div className="flex flex-col gap-4">
      <Card title="Fit">
        <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
          <Field label="Fit type">
            <select
              value={fitType}
              onChange={(e) => {
                setDirty(true);
                setFitType(e.target.value);
              }}
              className={inputClass}
            >
              {FIT_TYPES.map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          </Field>
          <Field label="Where these numbers come from">
            <select
              value={source}
              onChange={(e) => {
                setDirty(true);
                setSource(e.target.value);
              }}
              className={inputClass}
            >
              {SOURCES.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </Field>
        </div>
        <div className="mt-3">
          <Field label="Fit notes" hint="Optional. Shown to shoppers when the product page has no fit copy.">
            <textarea
              rows={2}
              value={fitNotes}
              onChange={(e) => {
                setDirty(true);
                setFitNotes(e.target.value);
              }}
              className={`${inputClass} resize-y`}
            />
          </Field>
        </div>
      </Card>

      <Card title="Measurements (cm)">
        <p className="mb-3 text-[13px] text-muted">
          Finished-garment measurements, laid flat. Widths marked ½ are seam to seam — half the
          circumference. The first four columns are required for every size.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[12px]">
            <thead>
              <tr className="text-muted">
                <th scope="col" className="py-1.5 pr-2 font-medium">Size</th>
                {MEASUREMENTS.map((m) => (
                  <th key={m.key} scope="col" title={m.hint} className="py-1.5 pr-2 font-medium whitespace-nowrap">
                    {m.label}
                    {"required" in m && <span className="text-red-700">*</span>}
                  </th>
                ))}
                <th scope="col"><span className="sr-only">Remove</span></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>
                  <td className="py-1 pr-2">
                    <input
                      aria-label={`Size label, row ${i + 1}`}
                      value={row.size}
                      onChange={(e) => setRow(i, { size: e.target.value, variantId: "" })}
                      className={`${inputClass} w-16`}
                      placeholder="M"
                    />
                  </td>
                  {MEASUREMENTS.map((m) => (
                    <td key={m.key} className="py-1 pr-2">
                      <input
                        aria-label={`${m.label} for ${row.size || `row ${i + 1}`}`}
                        type="number"
                        step="0.1"
                        min={0}
                        value={row[m.key] ?? ""}
                        onChange={(e) => setRow(i, { [m.key]: e.target.value })}
                        className={`${inputClass} w-20`}
                      />
                    </td>
                  ))}
                  <td className="py-1">
                    <button
                      type="button"
                      disabled={rows.length === 1}
                      onClick={() => {
                        setDirty(true);
                        setRows((rs) => rs.filter((_, j) => j !== i));
                      }}
                      className="text-xs text-muted hover:text-red-700 disabled:opacity-40"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <button
          type="button"
          onClick={() => {
            setDirty(true);
            setRows((rs) => [...rs, { size: "", variantId: "" }]);
          }}
          className="mt-2 text-xs font-medium text-accent hover:underline"
        >
          + Add size
        </button>
      </Card>

      {error && <Banner tone="danger">{error}</Banner>}

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          disabled={!dirty || duplicate || sizes.length === 0 || save.isPending}
          onClick={() => save.mutate()}
          className={buttonClass("primary", "sm")}
        >
          {save.isPending ? "Saving…" : "Save sizes"}
        </button>
        {duplicate && <span className="text-xs text-red-700">Each size may appear only once.</span>}
        {!duplicate && missingRequired && (
          <span className="text-xs text-amber-700">
            Saved sizes missing a required measurement can&apos;t be processed yet.
          </span>
        )}
        {dirty && !duplicate && <span className="text-xs text-muted">Unsaved changes.</span>}
      </div>

      <Card
        title="Match sizes to Shopify variants"
        action={
          <Badge tone={garment.sizing.variantMappingConfirmed ? "success" : "warn"}>
            {garment.sizing.variantMappingConfirmed ? "Confirmed" : "Not confirmed"}
          </Badge>
        }
      >
        {saved.length === 0 ? (
          <p className="text-[13px] text-muted">Save at least one size first.</p>
        ) : (
          <>
            <ul className="mb-3 divide-y divide-stone-100 text-[13px]">
              {saved.map((r) => {
                const v = variants.find((x) => x.variantId === r.variant_id);
                return (
                  <li key={String(r.size)} className="flex items-center justify-between py-1.5">
                    <span className="font-medium">{String(r.size)}</span>
                    {v ? (
                      <span className="text-muted">{v.title || v.sku || v.variantId}</span>
                    ) : (
                      <span className="text-red-700">No Shopify variant with this size</span>
                    )}
                  </li>
                );
              })}
            </ul>
            <p className="mb-3 text-xs text-muted">
              Shoppers who pick a size on the try-on page are sold the variant shown beside it.
              Saving sizes again clears this confirmation.
            </p>
            <button
              type="button"
              disabled={dirty || garment.sizing.variantMappingConfirmed || confirm.isPending}
              onClick={() => confirm.mutate()}
              className={buttonClass("secondary", "sm")}
            >
              {confirm.isPending ? "Confirming…" : "Confirm mapping"}
            </button>
          </>
        )}
      </Card>
    </div>
  );
}
