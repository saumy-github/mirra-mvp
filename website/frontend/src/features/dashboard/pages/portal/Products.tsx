import { Fragment, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useDbVersion, getDb } from "../../data/store";
import { useSession } from "../../data/session";
import { tenantProducts } from "../../data/queries";
import {
  createGarmentAction,
  previewSync,
  resolveSyncConflictAction,
  triggerSyncAction,
} from "../../data/actions";
import { STAGE_META } from "../../data/ingestion";
import { can } from "../../data/rbac";
import { timeAgo } from "../../data/util";
import {
  ActionButton,
  Badge,
  Card,
  EmptyState,
  NoticeBar,
  Pagination,
  PageHeader,
} from "../../components/ui";
import { useAction } from "../../components/use-action";
import { buttonClass } from "../../components/styles";
import { dashPath } from "../../routes";

export default function ProductsPage() {
  const session = useSession();
  const navigate = useNavigate();
  useDbVersion();
  const [expanded, setExpanded] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [showDelta, setShowDelta] = useState(false);
  const notice = useAction();
  if (!session?.tenant) return null;
  const tenant = session.tenant;

  const products = tenantProducts(tenant.id);
  const db = getDb();
  const syncRuns = db.syncRuns.filter((s) => s.tenantId === tenant.id).slice(0, 5);
  const errors = products.filter((p) => p.syncStatus === "error");
  const canEdit = can(session.role, "catalogue.edit");
  const deltas = previewSync(tenant.id);
  const conflicts = syncRuns
    .flatMap((r) => (r.conflicts ?? []).map((c) => ({ runId: r.id, ...c })))
    .filter((c) => !c.resolvedAt);
  const PAGE_SIZE = 25;
  const pageProducts = products.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const start = (productId: string, colour: string) => {
    const id = createGarmentAction(productId, colour);
    if (id) navigate(dashPath.garmentFlow(id));
  };

  return (
    <>
      <PageHeader
        title="Products & SKUs"
        subtitle="Your Shopify catalogue, synced automatically. Shopify stays the source of truth for products, variants and inventory — Mirra reads, never writes."
        action={
          canEdit ? (
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setShowDelta((v) => !v)}
                aria-expanded={showDelta}
                className="inline-flex cursor-pointer items-center rounded-lg border border-line bg-surface px-2.5 py-1 text-xs font-medium hover:bg-stone-50"
              >
                Preview changes ({deltas.length})
              </button>
              <ActionButton
                onAction={() => triggerSyncAction()}
                onDone={(m) => notice.setNotice(m ? { tone: "success", message: m } : null)}
              >
                ↻ Sync now
              </ActionButton>
            </div>
          ) : undefined
        }
      />

      <NoticeBar notice={notice.notice} onDismiss={notice.clear} />

      {/* What a sync would do, before it does it. Running one blind against a
          digitised catalogue is how a garment loses the SKUs it was built for. */}
      {showDelta && (
        <div className="mb-5">
          <Card title="What the next sync would change">
            {deltas.length === 0 ? (
              <p className="text-[13px] text-muted">
                Nothing pending — every product is in sync and no digitised garment references a SKU
                Shopify has stopped returning.
              </p>
            ) : (
              <ul className="divide-y divide-stone-100">
                {deltas.map((d) => (
                  <li key={`${d.productId}-${d.kind}-${d.detail}`} className="flex items-start justify-between gap-3 py-2 text-[13px]">
                    <span>
                      <span className="font-medium text-ink">{d.title}</span>
                      <span className="block text-xs text-muted">{d.detail}</span>
                    </span>
                    <Badge
                      tone={d.kind === "conflict" ? "danger" : d.kind === "failing" ? "warn" : "info"}
                    >
                      {d.kind}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      )}

      {/* Every failure, not just the first — and a retry that actually
          re-attempts them rather than skipping straight past. */}
      {errors.length > 0 && (
        <div className="mb-5">
          <Card title={`${errors.length} product${errors.length > 1 ? "s" : ""} failed to sync`}>
            <ul className="divide-y divide-stone-100">
              {errors.map((p) => (
                <li key={p.id} className="flex items-start justify-between gap-3 py-2 text-[13px]">
                  <span>
                    <span className="font-medium text-ink">{p.title}</span>
                    <span className="block text-xs text-amber-800">{p.syncError}</span>
                  </span>
                  <span className="text-xs text-muted">{timeAgo(p.lastSyncedAt)}</span>
                </li>
              ))}
            </ul>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              {canEdit && (
                <ActionButton
                  onAction={() => triggerSyncAction({ retryFailed: true })}
                  onDone={(m) => notice.setNotice(m ? { tone: "success", message: m } : null)}
                >
                  Retry failed products
                </ActionButton>
              )}
              <span className="text-xs text-muted">
                Fix the source in Shopify first where the error names one — or{" "}
                <Link to={dashPath.support} className="font-medium text-accent underline">ask support</Link>.
              </span>
            </div>
          </Card>
        </div>
      )}

      {/* Conflicts are changes Mirra refuses to apply unattended, because
          applying them would strand a digitised garment. */}
      {conflicts.length > 0 && (
        <div className="mb-5">
          <Card title={`${conflicts.length} sync conflict${conflicts.length > 1 ? "s" : ""} need a decision`}>
            <ul className="divide-y divide-stone-100">
              {conflicts.map((c) => (
                <li key={`${c.runId}-${c.productId}`} className="flex items-start justify-between gap-3 py-2 text-[13px]">
                  <span>
                    <span className="font-medium text-ink">{c.productTitle}</span>
                    <span className="block text-xs text-muted">{c.detail}</span>
                    {c.affectedGarmentIds.map((gid) => (
                      <Link
                        key={gid}
                        to={dashPath.garment(gid)}
                        className="mr-2 text-xs font-medium text-accent hover:underline"
                      >
                        Open affected garment →
                      </Link>
                    ))}
                  </span>
                  {canEdit && (
                    <ActionButton onAction={() => resolveSyncConflictAction(c.runId, c.productId)}>
                      Acknowledge
                    </ActionButton>
                  )}
                </li>
              ))}
            </ul>
          </Card>
        </div>
      )}

      {products.length === 0 ? (
        <EmptyState
          icon="▤"
          title="No products synced yet"
          body="Connect Shopify and run your first sync to import products, variants, images, and metadata."
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-line bg-surface">
          <table className="w-full text-left text-[13px]">
            <caption className="sr-only">Synced Shopify products and their try-on garments</caption>
            <thead>
              <tr className="border-b border-line text-xs text-muted">
                <th scope="col" className="px-4 py-2.5 font-medium">Product</th>
                <th scope="col" className="px-4 py-2.5 font-medium">Type</th>
                <th scope="col" className="px-4 py-2.5 font-medium">Variants</th>
                <th scope="col" className="px-4 py-2.5 font-medium">Try-on garments</th>
                <th scope="col" className="px-4 py-2.5 font-medium">Sync</th>
                <th scope="col" className="px-4 py-2.5 font-medium">Last synced</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {pageProducts.map((p) => {
                const colours = [...new Set(p.variants.map((v) => v.color))];
                const garments = db.garments.filter((g) => g.productId === p.id);
                const isOpen = expanded === p.id;
                // A keyed fragment: the two rows belong to one product, and
                // an unkeyed <> inside a map is a React warning.
                return (
                  <Fragment key={p.id}>
                    <tr className="hover:bg-stone-50/60">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2.5">
                          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-stone-100 text-base" aria-hidden>{p.imageEmoji}</span>
                          <div>
                            <div className="font-medium text-ink">{p.title}</div>
                            <div className="text-xs text-muted">{p.vendor}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-stone-600">{p.productType}</td>
                      <td className="px-4 py-3 tabular-nums text-stone-600">{p.variants.length}</td>
                      <td className="px-4 py-3">
                        {/* Expanding to per-colourway rows is the entry point
                            into ingestion: one garment per colourway, not per
                            product and not per variant. */}
                        <button
                          onClick={() => setExpanded(isOpen ? null : p.id)}
                          aria-expanded={isOpen}
                          className="text-[13px] font-medium text-accent hover:underline"
                        >
                          {garments.length === 0
                            ? `${colours.length} colourway${colours.length === 1 ? "" : "s"}, none digitised`
                            : `${garments.length} of ${colours.length} digitised`}{" "}
                          {isOpen ? "▲" : "▼"}
                        </button>
                      </td>
                      <td className="px-4 py-3">
                        {p.syncStatus === "synced" && <Badge tone="success">Synced</Badge>}
                        {p.syncStatus === "pending" && <Badge tone="info">Pending</Badge>}
                        {p.syncStatus === "error" && <Badge tone="danger">Error</Badge>}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted">{timeAgo(p.lastSyncedAt)}</td>
                    </tr>
                    {isOpen && (
                      <tr className="bg-stone-50/40">
                        <td colSpan={6} className="px-4 py-3">
                          <ul className="space-y-1.5">
                            {colours.map((colour) => {
                              const g = garments.find((x) => x.colour === colour);
                              const skus = p.variants.filter((v) => v.color === colour).length;
                              return (
                                <li key={colour} className="flex flex-wrap items-center gap-2 text-[13px]">
                                  <span className="min-w-28 font-medium text-ink">{colour}</span>
                                  <span className="text-muted">{skus} SKUs</span>
                                  {g ? (
                                    <>
                                      <Badge tone={STAGE_META[g.stage].tone}>{STAGE_META[g.stage].label}</Badge>
                                      <Link
                                        to={dashPath.garment(g.id)}
                                        className="text-xs font-medium text-accent hover:underline"
                                      >
                                        Open →
                                      </Link>
                                    </>
                                  ) : canEdit ? (
                                    <button
                                      onClick={() => start(p.id, colour)}
                                      className={buttonClass("accent", "sm")}
                                    >
                                      Create try-on garment →
                                    </button>
                                  ) : (
                                    <span className="text-xs text-muted">Not digitised</span>
                                  )}
                                </li>
                              );
                            })}
                          </ul>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <Pagination
        page={page}
        pageSize={PAGE_SIZE}
        total={products.length}
        onPage={setPage}
        label="Product pages"
      />

      <div className="mt-6">
        <Card title="Recent sync activity">
          <ul className="space-y-2.5">
            {syncRuns.map((s) => (
              <li key={s.id} className="flex items-center justify-between gap-3 text-[13px]">
                <span className="text-stone-700">
                  {s.trigger === "webhook" ? "Shopify webhook" : s.trigger === "manual" ? "Manual sync" : "Nightly reconciliation"}
                  {" · "}{s.itemsSynced} items
                  {s.failures.length > 0 && <span className="text-amber-700"> · {s.failures.length} failed</span>}
                </span>
                <span className="flex items-center gap-2">
                  <Badge tone={s.status === "success" ? "success" : s.status === "partial" ? "warn" : "danger"}>{s.status}</Badge>
                  <span className="text-xs text-muted">{timeAgo(s.startedAt)}</span>
                </span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  );
}
