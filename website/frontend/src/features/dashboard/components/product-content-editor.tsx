import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { merchantApi, type MerchantGarment, type MerchantProduct } from "../data/merchant-api";
import { Badge, Banner, Card, Field } from "./ui";
import { buttonClass, inputClass } from "./styles";

/**
 * The shopper-facing product panel — what fills the right-hand side of the
 * studio next to the avatar.
 *
 * Where this data comes from is a real question with a real answer, and the
 * answer is "both, with the source recorded". Shopify supplies the title,
 * price, stock and usually the description; nobody's Shopify listing carries
 * "how this fits on a 3D avatar" copy, because until now nothing needed it.
 * So each field resolves in a fixed order and shows which source won:
 *
 *   1. this garment's own copy (colourway-specific — "in the deadstock silk")
 *   2. the product's copy (from Shopify, or entered when it was created)
 *   3. nothing — the field is omitted rather than filled with a default
 *
 * Title and price are deliberately not editable here. They are Shopify's, and
 * a merchant editing them in Mirra would create a listing that disagrees with
 * the one shoppers buy from.
 */

const FIELDS = [
  {
    key: "description" as const,
    label: "Description",
    hint: "The main product copy. Inherited from Shopify when the store is connected.",
    rows: 4,
  },
  {
    key: "materialAndCare" as const,
    label: "Material and care",
    hint: "Falls back to the confirmed fabric composition when left empty.",
    rows: 3,
  },
  {
    key: "fitInfo" as const,
    label: "Fit",
    hint: "Falls back to the silhouette and fit notes from Size & fit.",
    rows: 3,
  },
  {
    key: "manufacturingInfo" as const,
    label: "Manufacturing",
    hint: "Where and how it was made. Optional.",
    rows: 3,
  },
  {
    key: "taxNote" as const,
    label: "Tax note",
    hint: "Shown beside the price. Optional.",
    rows: 2,
  },
];

type FieldKey = (typeof FIELDS)[number]["key"];
type Draft = Partial<Record<FieldKey, string>>;

export function ProductContentEditor({
  tenantId,
  garment,
  product,
  onGarmentChange,
  onProductChange,
}: {
  tenantId: string;
  garment: MerchantGarment;
  product: MerchantProduct | null;
  onGarmentChange: (g: MerchantGarment) => void;
  onProductChange: (p: MerchantProduct) => void;
}) {
  // "colourway" writes to the garment, "listing" writes to the product. A
  // merchant with one colourway wants the listing; one with five wants both.
  const [scope, setScope] = useState<"colourway" | "listing">("colourway");
  const source = scope === "colourway" ? garment.content : product?.content;

  const [draft, setDraft] = useState<Draft>({});
  useEffect(() => {
    setDraft({});
  }, [scope, garment.garmentId, product?.productId]);

  const [error, setError] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: async () => {
      const changes = Object.fromEntries(
        Object.entries(draft).map(([k, v]) => [k, v?.trim() ? v.trim() : null]),
      );
      if (scope === "colourway") {
        return { kind: "garment" as const, value: await merchantApi.setGarmentContent(tenantId, garment.garmentId, changes) };
      }
      if (!product) throw new Error("No product is attached to this garment.");
      return { kind: "product" as const, value: await merchantApi.updateProductContent(tenantId, product.productId, changes) };
    },
    onSuccess: (res) => {
      setError(null);
      setDraft({});
      if (res.kind === "garment") onGarmentChange(res.value);
      else onProductChange(res.value);
    },
    onError: (err: Error) => setError(err.message),
  });

  const dirty = Object.keys(draft).length > 0;

  return (
    <div className="flex flex-col gap-4">
      <Card title="What the shopper reads">
        <p className="mb-3 text-[13px] text-muted">
          This is the panel beside the avatar in the try-on studio. Name, price and stock come from
          Shopify and are not editable here — everything below is the copy that sits under them.
        </p>

        <KeyFacts garment={garment} product={product} />
      </Card>

      <Card
        title="Product copy"
        action={
          <div className="flex gap-1">
            {(["colourway", "listing"] as const).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setScope(s)}
                aria-pressed={scope === s}
                className={`rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors ${
                  scope === s
                    ? "border-accent bg-accent-soft text-accent"
                    : "border-line bg-surface text-stone-600 hover:border-accent hover:text-ink"
                }`}
              >
                {s === "colourway" ? `This colourway${garment.optionValue ? ` (${garment.optionValue})` : ""}` : "Whole listing"}
              </button>
            ))}
          </div>
        }
      >
        <p className="mb-4 text-[13px] text-muted">
          {scope === "colourway"
            ? "Copy written here applies to this colourway only and overrides the listing's."
            : "Copy written here applies to every colourway of this listing that has none of its own."}
        </p>

        <div className="flex flex-col gap-4">
          {FIELDS.map((field) => {
            const stored = source?.[field.key] ?? null;
            const value = draft[field.key] ?? stored ?? "";
            const origin = source?.sources?.[field.key];
            const inherited =
              scope === "colourway" && !garment.content[field.key] && product?.content[field.key];
            return (
              <div key={field.key}>
                <Field label={field.label} hint={field.hint}>
                  <textarea
                    value={value}
                    rows={field.rows}
                    onChange={(e) => setDraft((d) => ({ ...d, [field.key]: e.target.value }))}
                    className={`${inputClass} resize-y`}
                    placeholder={
                      inherited ? String(product?.content[field.key] ?? "") : "Not set"
                    }
                  />
                </Field>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-muted">
                  {origin && <Badge tone="neutral">from {origin}</Badge>}
                  {inherited && <span>Inheriting the listing&apos;s copy. Type here to override it.</span>}
                  {!origin && !inherited && !stored && (
                    <span>Empty — this field is omitted from the shopper&apos;s panel.</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {error && (
          <div className="mt-3">
            <Banner tone="danger">{error}</Banner>
          </div>
        )}

        <div className="mt-4 flex items-center gap-3">
          <button
            type="button"
            disabled={!dirty || save.isPending || (scope === "listing" && !product)}
            onClick={() => save.mutate()}
            className={buttonClass("primary", "sm")}
          >
            {save.isPending ? "Saving…" : "Save copy"}
          </button>
          {dirty && <span className="text-xs text-muted">Unsaved changes.</span>}
        </div>
      </Card>
    </div>
  );
}

/** The facts Shopify owns. Shown, never edited. */
function KeyFacts({
  garment,
  product,
}: {
  garment: MerchantGarment;
  product: MerchantProduct | null;
}) {
  const variants = (product?.variants ?? []).filter(
    (v) => !garment.optionValue || !v.colour || v.colour === garment.optionValue,
  );
  const prices = variants.map((v) => v.price).filter((p) => p > 0);
  const currency = variants[0]?.currency ?? "USD";

  return (
    <>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-[13px] max-sm:grid-cols-1">
        <Fact label="Name" value={garment.canonicalTitle} />
        <Fact label="Colourway" value={garment.optionValue || "—"} />
        <Fact
          label="Price"
          value={
            prices.length
              ? `${currency} ${Math.min(...prices).toFixed(2)}${
                  Math.max(...prices) !== Math.min(...prices)
                    ? `–${Math.max(...prices).toFixed(2)}`
                    : ""
                }`
              : "Not set"
          }
        />
        <Fact
          label="Sizes"
          value={variants.map((v) => v.size).filter(Boolean).join(" · ") || "—"}
        />
      </dl>
      {product?.linkState === "unlinked" && (
        <div className="mt-3">
          <Banner tone="warn">
            Price and stock were entered by hand — this product is not linked to Shopify yet, so
            they will not follow changes made in Shopify. Connecting the store reconciles them
            automatically.
          </Banner>
        </div>
      )}
    </>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[11px] uppercase tracking-wide text-muted">{label}</dt>
      <dd className="font-medium text-ink">{value}</dd>
    </div>
  );
}
