import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { merchantApi, type MerchantGarment } from "../data/merchant-api";
import { Badge, Banner, Card, Field } from "./ui";
import { buttonClass, inputClass } from "./styles";

/**
 * Material — fibre composition from the care label, plus the three behaviour
 * attributes the simulation reads. Persisted through PUT …/material.
 */

const STRETCH = ["none", "low", "moderate", "high"] as const;
const DRAPE = ["structured", "moderate", "fluid"] as const;
const THICKNESS = ["light", "mid", "heavy"] as const;

type Row = { material: string; pct: string };

export function MaterialEditor({
  tenantId,
  garment,
  onChange,
}: {
  tenantId: string;
  garment: MerchantGarment;
  onChange: (g: MerchantGarment) => void;
}) {
  const m = garment.material;
  const [rows, setRows] = useState<Row[]>(
    m.composition.length
      ? m.composition.map((c) => ({ material: c.material, pct: String(c.pct) }))
      : [{ material: "", pct: "100" }],
  );
  const [stretch, setStretch] = useState(m.stretch);
  const [drape, setDrape] = useState(m.drape);
  const [thickness, setThickness] = useState(m.thickness);
  const [confirmed, setConfirmed] = useState(m.confirmed);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const filled = rows.filter((r) => r.material.trim());
  const total = filled.reduce((sum, r) => sum + (Number(r.pct) || 0), 0);
  const valid = filled.length > 0 && total === 100;

  const save = useMutation({
    mutationFn: () =>
      merchantApi.setMaterial(tenantId, garment.garmentId, {
        composition: filled.map((r) => ({ material: r.material.trim(), pct: Number(r.pct) })),
        confirmed,
        stretch,
        drape,
        thickness,
      }),
    onSuccess: (g) => {
      setError(null);
      setSaved(true);
      onChange(g);
    },
    onError: (err: Error) => setError(err.message),
  });

  const edit = (fn: () => void) => {
    setSaved(false);
    fn();
  };
  const setRow = (i: number, patch: Partial<Row>) =>
    edit(() => setRows((rs) => rs.map((r, j) => (j === i ? { ...r, ...patch } : r))));

  return (
    <div className="flex flex-col gap-4">
      <Card
        title="Fabric composition"
        action={
          m.composition.length ? (
            <Badge tone={m.confirmed ? "success" : "warn"}>{m.confirmed ? "Confirmed" : "Unconfirmed"}</Badge>
          ) : (
            <Badge tone="danger">Required</Badge>
          )
        }
      >
        <p className="mb-3 text-[13px] text-muted">
          Copy it from the sample&apos;s care label. Every fibre on the label, and the percentages
          must total 100%.
        </p>
        <div className="flex flex-col gap-2">
          {rows.map((row, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                aria-label={`Fibre ${i + 1}`}
                value={row.material}
                onChange={(e) => setRow(i, { material: e.target.value })}
                placeholder="Cotton"
                className={inputClass}
              />
              <input
                aria-label={`Fibre ${i + 1} percentage`}
                type="number"
                min={1}
                max={100}
                value={row.pct}
                onChange={(e) => setRow(i, { pct: e.target.value })}
                className={`${inputClass} w-24`}
              />
              <span className="text-xs text-muted">%</span>
              <button
                type="button"
                disabled={rows.length === 1}
                onClick={() => edit(() => setRows((rs) => rs.filter((_, j) => j !== i)))}
                className="text-xs text-muted hover:text-red-700 disabled:opacity-40"
                aria-label={`Remove fibre ${i + 1}`}
              >
                Remove
              </button>
            </div>
          ))}
        </div>
        <div className="mt-2 flex items-center justify-between text-xs">
          <button
            type="button"
            onClick={() => edit(() => setRows((rs) => [...rs, { material: "", pct: "" }]))}
            className="font-medium text-accent hover:underline"
          >
            + Add fibre
          </button>
          <span className={total === 100 ? "text-emerald-700" : "text-amber-700"}>Total {total}%</span>
        </div>
      </Card>

      <Card title="How it behaves">
        <p className="mb-3 text-[13px] text-muted">
          The simulation reads these. Until you set them they are Mirra&apos;s suggestion and are
          flagged as such in review.
        </p>
        <div className="grid grid-cols-3 gap-3 max-sm:grid-cols-1">
          <Field label="Stretch">
            <select value={stretch} onChange={(e) => edit(() => setStretch(e.target.value))} className={inputClass}>
              {STRETCH.map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          </Field>
          <Field label="Drape">
            <select value={drape} onChange={(e) => edit(() => setDrape(e.target.value))} className={inputClass}>
              {DRAPE.map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          </Field>
          <Field label="Weight">
            <select value={thickness} onChange={(e) => edit(() => setThickness(e.target.value))} className={inputClass}>
              {THICKNESS.map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          </Field>
        </div>
        {m.attributesSuggested && (
          <p className="mt-2 text-xs text-muted">Currently Mirra&apos;s suggestion — saving makes them yours.</p>
        )}
      </Card>

      <label className="flex items-start gap-2 text-[13px]">
        <input
          type="checkbox"
          checked={confirmed}
          onChange={(e) => edit(() => setConfirmed(e.target.checked))}
          className="mt-0.5"
        />
        <span>I checked this composition against the label on the physical sample.</span>
      </label>

      {error && <Banner tone="danger">{error}</Banner>}

      <div className="flex items-center gap-3">
        <button
          type="button"
          disabled={!valid || save.isPending}
          onClick={() => save.mutate()}
          className={buttonClass("primary", "sm")}
        >
          {save.isPending ? "Saving…" : "Save material"}
        </button>
        {!valid && <span className="text-xs text-muted">Name at least one fibre and total 100%.</span>}
        {saved && <span className="text-xs text-emerald-700">Saved.</span>}
      </div>
    </div>
  );
}
