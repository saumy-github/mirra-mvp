import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useSession } from "../../../data/session";
import { liveCan } from "../../../data/live-session";
import { merchantApi } from "../../../data/merchant-api";
import { useLiveGarments, useLiveProducts } from "../../../data/merchant-queries";
import { Badge, Banner, ButtonLink, EmptyState, PageHeader, Table, Td } from "../../../components/ui";
import { buttonClass } from "../../../components/styles";
import { dashPath } from "../../../routes";

/** Products for a real workspace: linked from Shopify, hand-entered, or CSV-imported. */
export default function LiveProductsPage() {
  const session = useSession();
  const tenantId = session?.tenant?.id ?? "";
  const qc = useQueryClient();
  const products = useLiveProducts(tenantId);
  const garments = useLiveGarments(tenantId);
  const canEdit = liveCan(tenantId, "catalogue.edit");
  const fileRef = useRef<HTMLInputElement>(null);
  const [result, setResult] = useState<string | null>(null);

  const importCsv = useMutation({
    mutationFn: (file: File) => merchantApi.importProductsCsv(tenantId, file),
    onSuccess: (r) => {
      const failed = r.failed.map((f) => `${f.handle}: ${f.reason}`).join("; ");
      setResult(
        `Imported ${r.created.length}, skipped ${r.skipped.length} already present` +
          (r.failed.length ? `, ${r.failed.length} failed — ${failed}` : "."),
      );
      qc.invalidateQueries({ queryKey: ["merchant-products", tenantId] });
    },
    onError: () => setResult(null),
  });

  const rows = products.data ?? [];
  const garmentCount = (productId: string) =>
    (garments.data ?? []).filter((g) => g.productId === productId).length;

  return (
    <>
      <PageHeader
        title="Products & SKUs"
        subtitle="The listings garments are digitised from. Linked products follow Shopify; hand-entered ones reconcile when the store is connected in Settings."
        action={
          canEdit ? (
            <div className="flex gap-2">
              <input
                ref={fileRef}
                type="file"
                accept=".csv,text/csv"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) importCsv.mutate(file);
                  e.target.value = "";
                }}
              />
              <button
                type="button"
                disabled={importCsv.isPending}
                onClick={() => fileRef.current?.click()}
                className={buttonClass("secondary", "sm")}
              >
                {importCsv.isPending ? "Importing…" : "Import CSV"}
              </button>
              <ButtonLink href={dashPath.digitise} variant="primary" size="sm">
                + Add garment
              </ButtonLink>
            </div>
          ) : undefined
        }
      />
      {canEdit && (
        <p className="-mt-3 mb-4 text-xs text-muted">
          CSV import accepts Shopify&apos;s own product export as-is.
        </p>
      )}
      {result && (
        <div className="mb-4">
          <Banner tone="success">{result}</Banner>
        </div>
      )}
      {importCsv.isError && (
        <div className="mb-4">
          <Banner tone="danger">{(importCsv.error as Error).message}</Banner>
        </div>
      )}
      {products.isLoading ? (
        <p className="text-[13px] text-muted">Loading products…</p>
      ) : products.isError ? (
        <Banner tone="danger">Could not load products: {(products.error as Error).message}</Banner>
      ) : rows.length === 0 ? (
        <EmptyState
          icon="▤"
          title="No products yet"
          body="Products are added when you identify a garment by its product link, or in bulk from a CSV."
        />
      ) : (
        <Table caption="Products" headers={["Product", "Source", "Variants", "Garments", "Sync"]}>
          {rows.map((p) => (
            <tr key={p.productId}>
              <Td>
                <span className="font-medium text-ink">{p.title}</span>
                <span className="block font-mono text-xs text-muted">{p.handle}</span>
              </Td>
              <Td>
                <Badge tone={p.linkState === "linked" ? "success" : "warn"}>
                  {p.linkState === "linked" ? "Shopify" : p.source === "csv" ? "CSV" : "By hand"}
                </Badge>
              </Td>
              <Td>
                {p.variants.length}
                <span className="block text-xs text-muted">
                  {[...new Set(p.variants.map((v) => v.size).filter(Boolean))].join(" · ")}
                </span>
              </Td>
              <Td>{garmentCount(p.productId)}</Td>
              <Td>
                {p.syncError ? (
                  <span className="text-xs text-red-700">{p.syncError}</span>
                ) : (
                  <span className="text-xs text-muted">
                    {p.lastSyncedAt ? new Date(p.lastSyncedAt).toLocaleString() : p.syncStatus || "—"}
                  </span>
                )}
              </Td>
            </tr>
          ))}
        </Table>
      )}
    </>
  );
}
