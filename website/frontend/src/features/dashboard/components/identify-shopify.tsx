import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { merchantApi, type LookupResult, type MerchantProduct, type ProductDraft } from "../data/merchant-api";
import { Badge, Banner, Card, Field, KeyValue } from "./ui";
import { buttonClass, inputClass } from "./styles";

/**
 * Step 1 — Identify. Which Shopify product is being digitised.
 *
 * What changed and why
 * --------------------
 * The previous version resolved the pasted URL against a locally seeded
 * catalogue and, when nothing matched, said: "No product in your connected
 * store matches that link. Check it belongs to this store, or re-run a
 * Shopify sync." There was no Shopify sync anywhere in the product, and no
 * code path that could ever have put a product into that catalogue — so for
 * any workspace without seed data, this screen was a wall.
 *
 * Identity is now resolved server-side and always yields something usable:
 *
 *   resolved  the live Shopify Admin API returned the product
 *   matched   Mirra already holds it
 *   draft     no store is connected — here is everything the URL itself
 *             established (store domain + handle), and a short form for the
 *             parts no URL can carry: title, sizes, price
 *
 * A `draft` product is a first-class record, not a placeholder: garments
 * attach to it, ingestion runs against it, and it publishes. When the client's
 * Shopify app is finally installed, `POST /shopify/reconcile` matches these by
 * handle and fills in the GID, variants and live price without anyone
 * re-entering a thing or losing a single capture.
 */
export function IdentifyShopify({
  tenantId,
  onCreated,
}: {
  tenantId: string;
  /** Called with the new garment id once the garment exists in the backend. */
  onCreated: (garmentId: string) => void;
}) {
  const [input, setInput] = useState("");
  const [result, setResult] = useState<LookupResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const lookup = useMutation({
    mutationFn: () => merchantApi.lookupProduct(tenantId, input),
    onSuccess: (res) => {
      setResult(res);
      setError(null);
    },
    onError: (err: Error) => {
      setResult(null);
      setError(err.message);
    },
  });

  const product = result?.outcome === "draft" ? null : (result?.product ?? null);

  return (
    <div className="flex flex-col gap-4">
      <Card title="Which Shopify product are you digitising?">
        <p className="mb-3 text-[13px] text-muted">
          Paste the product&apos;s storefront URL. Mirra reads the store domain and the product
          handle from the link itself, then fills in the rest from Shopify if your store is
          connected.
        </p>
        <div className="flex flex-wrap items-end gap-2">
          <div className="min-w-72 flex-1">
            <Field
              label="Shopify product URL"
              hint="Also accepts the product handle, its numeric ID, or a gid://shopify/Product/… GID."
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && input.trim() && lookup.mutate()}
                className={inputClass}
                placeholder="https://your-store.com/products/perce-ribbed-tank"
              />
            </Field>
          </div>
          <button
            type="button"
            disabled={!input.trim() || lookup.isPending}
            onClick={() => lookup.mutate()}
            className={buttonClass("primary")}
          >
            {lookup.isPending ? "Looking up…" : "Look up"}
          </button>
        </div>
        {error && (
          <div className="mt-3">
            <Banner tone="danger">{error}</Banner>
          </div>
        )}
      </Card>

      {result?.outcome === "draft" && result.draft && (
        <CompleteDraft
          tenantId={tenantId}
          draft={result.draft}
          guidance={result.guidance}
          onCreated={(p) => setResult({ outcome: "matched", storeConnected: false, product: p })}
        />
      )}

      {product && (
        <ConfirmAndCreate
          tenantId={tenantId}
          product={product}
          storeConnected={result?.storeConnected ?? false}
          onCreated={onCreated}
        />
      )}
    </div>
  );
}

/**
 * The unconnected-store path. Everything the URL gave us is pre-filled and
 * read-only; the merchant supplies only what no URL can carry.
 */
function CompleteDraft({
  tenantId,
  draft,
  guidance,
  onCreated,
}: {
  tenantId: string;
  draft: ProductDraft;
  guidance?: string;
  onCreated: (product: MerchantProduct) => void;
}) {
  const [title, setTitle] = useState(draft.suggestedTitle);
  const [productType, setProductType] = useState("");
  const [optionName, setOptionName] = useState("Colour");
  const [colour, setColour] = useState("");
  const [price, setPrice] = useState("");
  const [sizes, setSizes] = useState("XS, S, M, L, XL");
  const [error, setError] = useState<string | null>(null);

  const sizeList = sizes
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  const create = useMutation({
    mutationFn: () =>
      merchantApi.createManualProduct(tenantId, {
        handle: draft.handle,
        title: title.trim(),
        onlineStoreUrl: draft.onlineStoreUrl,
        storeDomain: draft.storeDomain,
        productType,
        optionName: optionName.trim() || null,
        variants: sizeList.map((size) => ({
          size,
          colour: colour.trim(),
          title: [colour.trim(), size].filter(Boolean).join(" / "),
          price: Number(price) || 0,
          // Stock is Shopify's to state. Recording a made-up number here
          // would be a fact we do not have; it stays 0 until a real store
          // is connected and reconciliation fills it in.
          inventory: 0,
        })),
      }),
    onSuccess: onCreated,
    onError: (err: Error) => setError(err.message),
  });

  return (
    <Card
      title="Complete the product details"
      action={<Badge tone="warn">No store connected</Badge>}
    >
      {guidance && (
        <div className="mb-4">
          <Banner tone="info">{guidance}</Banner>
        </div>
      )}

      {/* What the link itself established. Not editable: these are the
          identity Mirra will match on when the store is connected. */}
      <div className="mb-4 rounded-lg border border-line bg-stone-50 p-3">
        <div className="mb-1.5 text-xs font-medium text-ink">Read from your link</div>
        <KeyValue
          rows={[
            ["Store", draft.storeDomain || "—"],
            ["Product handle", <code key="h" className="text-xs">{draft.handle}</code>],
            ...(draft.shopifyId
              ? ([["Shopify ID", <code key="i" className="text-xs">{draft.shopifyId}</code>]] as [string, React.ReactNode][])
              : []),
          ]}
        />
        <p className="mt-2 text-xs text-muted">
          The handle is the identity Mirra keeps. When your Shopify store is connected, this
          product links itself to the real listing automatically — you will not re-enter any of
          this, and nothing you capture in the meantime is lost.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
        <Field label="Product title" hint="As it appears on your storefront.">
          <input value={title} onChange={(e) => setTitle(e.target.value)} className={inputClass} />
        </Field>
        <Field label="Product type" hint="Optional — e.g. Tops.">
          <input
            value={productType}
            onChange={(e) => setProductType(e.target.value)}
            className={inputClass}
            placeholder="Tops"
          />
        </Field>
        <Field label="Colour option name" hint="What your shop calls this axis.">
          <input
            value={optionName}
            onChange={(e) => setOptionName(e.target.value)}
            className={inputClass}
          />
        </Field>
        <Field label="Colourway" hint="The one you are digitising first.">
          <input
            value={colour}
            onChange={(e) => setColour(e.target.value)}
            className={inputClass}
            placeholder="Black"
          />
        </Field>
        <Field label="Sizes" hint="Comma-separated. One SKU is created per size.">
          <input value={sizes} onChange={(e) => setSizes(e.target.value)} className={inputClass} />
        </Field>
        <Field label="Price" hint="Shown in the shopper's product panel.">
          <input
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className={inputClass}
            inputMode="decimal"
            placeholder="120"
          />
        </Field>
      </div>

      {error && (
        <div className="mt-3">
          <Banner tone="danger">{error}</Banner>
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          disabled={!title.trim() || sizeList.length === 0 || create.isPending}
          onClick={() => create.mutate()}
          className={buttonClass("accent")}
        >
          {create.isPending ? "Saving…" : "Save product and continue →"}
        </button>
        <span className="text-xs text-muted">
          {sizeList.length} SKU{sizeList.length === 1 ? "" : "s"} will be created.
        </span>
      </div>
    </Card>
  );
}

/** Identity established. Pick the colourway, create the garment. */
function ConfirmAndCreate({
  tenantId,
  product,
  storeConnected,
  onCreated,
}: {
  tenantId: string;
  product: MerchantProduct;
  storeConnected: boolean;
  onCreated: (garmentId: string) => void;
}) {
  const optionValues = [...new Set(product.variants.map((v) => v.colour).filter(Boolean))];
  const hasOption = Boolean(product.optionName) && optionValues.length > 0;

  const [optionValue, setOptionValue] = useState(optionValues[0] ?? "");
  const [name, setName] = useState(product.title);
  const [category, setCategory] = useState("top");
  const [error, setError] = useState<string | null>(null);

  const matched = product.variants.filter((v) => !hasOption || v.colour === optionValue);
  const nameMismatch = name.trim() !== "" && name.trim() !== product.title;

  const create = useMutation({
    mutationFn: () =>
      merchantApi.createGarment(tenantId, {
        productId: product.productId,
        optionValue: hasOption ? optionValue : "",
        merchantTitle: nameMismatch ? name.trim() : "",
        category,
      }),
    onSuccess: (g) => onCreated(g.garmentId),
    onError: (err: Error) => setError(err.message),
  });

  return (
    <>
      <Card
        title="Confirm the product"
        action={
          product.linkState === "linked" ? (
            <Badge tone="success">Linked to Shopify</Badge>
          ) : (
            <Badge tone="warn">Not linked yet</Badge>
          )
        }
      >
        <KeyValue
          rows={[
            ["Shopify title", <strong key="t" className="text-ink">{product.title}</strong>],
            [
              "Product ID",
              product.shopifyId ? (
                <code key="i" className="text-xs">{product.shopifyId}</code>
              ) : (
                <span key="i" className="text-xs text-amber-800">
                  Assigned when the store is connected
                </span>
              ),
            ],
            ["Handle", <code key="h" className="text-xs">{product.handle}</code>],
            ["Store", product.storeDomain || "—"],
            ["Type", product.productType || "—"],
            [
              "Source",
              product.source === "shopify" ? "Shopify Admin API" : "Entered in Mirra",
            ],
          ]}
        />

        {!storeConnected && (
          <div className="mt-3">
            <Banner tone="info">
              Price and stock for this product were entered by hand and will not track Shopify
              until the store is connected. Everything else — capture, sizing, QA, publishing —
              works exactly as it will afterwards.
            </Banner>
          </div>
        )}

        <div className="mt-4">
          <Field
            label="Garment name"
            hint="Defaults to the Shopify title. Mirra keeps the Shopify title as canonical."
          >
            <input value={name} onChange={(e) => setName(e.target.value)} className={inputClass} />
          </Field>
          {nameMismatch && (
            <div className="mt-2">
              <Banner tone="warn">
                This doesn&apos;t match the Shopify title <strong>{product.title}</strong>. Mirra
                keeps the Shopify title as canonical and records yours as a display name.{" "}
                <button
                  type="button"
                  onClick={() => setName(product.title)}
                  className="font-semibold underline"
                >
                  Use the Shopify title
                </button>
              </Banner>
            </div>
          )}
        </div>
      </Card>

      <Card title={hasOption ? `Which ${product.optionName?.toLowerCase() ?? "option"}?` : "Variants"}>
        {hasOption ? (
          <>
            <p className="mb-3 text-[13px] text-muted">
              One Mirra garment covers one {product.optionName?.toLowerCase() ?? "option"} value,
              because each one needs its own photography.
            </p>
            <div className="flex flex-wrap gap-1.5">
              {optionValues.map((v) => (
                <button
                  key={v}
                  type="button"
                  onClick={() => setOptionValue(v)}
                  aria-pressed={optionValue === v}
                  className={`rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors ${
                    optionValue === v
                      ? "border-accent bg-accent-soft text-accent"
                      : "border-line bg-surface text-stone-600 hover:border-accent hover:text-ink"
                  }`}
                >
                  {v}
                </button>
              ))}
            </div>
          </>
        ) : (
          <p className="text-[13px] text-muted">
            This product has no colour-like option, so it maps to a single garment.
          </p>
        )}

        <div className="mt-4">
          <Field
            label="Garment category"
            hint="Only tops can be digitised today — the panel generator drafts a t-shirt block."
          >
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className={inputClass}
            >
              <option value="top">Top</option>
              <option value="dress">Dress (not yet supported)</option>
              <option value="bottom">Bottom (not yet supported)</option>
              <option value="outerwear">Outerwear (not yet supported)</option>
              <option value="knitwear">Knitwear (not yet supported)</option>
            </select>
          </Field>
          {category !== "top" && (
            <div className="mt-2">
              <Banner tone="warn">
                The processing pipeline drafts a crew-neck t-shirt block only. You can record this
                garment, but Mirra will refuse to run it rather than produce a t-shirt shaped like
                something it is not.
              </Banner>
            </div>
          )}
        </div>

        <div className="mt-4 rounded-lg border border-line bg-stone-50 p-3 text-xs">
          <div className="mb-1.5 font-medium text-ink">What will be created</div>
          <ul className="space-y-1 text-muted">
            <li>
              <span className="text-stone-700">Shopify product</span> — {product.title}
            </li>
            <li>
              <span className="text-stone-700">Mirra try-on garment</span> — {name || product.title}
              {hasOption && optionValue ? ` — ${optionValue}` : ""}
            </li>
            <li>
              <span className="text-stone-700">Linked purchasable variants</span> —{" "}
              {matched.length > 0
                ? `${matched.length} SKUs (${[...new Set(matched.map((v) => v.size))].join(" · ")})`
                : "—"}
            </li>
          </ul>
        </div>

        {error && (
          <div className="mt-3">
            <Banner tone="danger">{error}</Banner>
          </div>
        )}

        <button
          type="button"
          disabled={(hasOption && !optionValue) || matched.length === 0 || create.isPending}
          onClick={() => create.mutate()}
          className={`${buttonClass("accent")} mt-4`}
        >
          {create.isPending ? "Creating…" : "Create garment and continue →"}
        </button>
      </Card>
    </>
  );
}
