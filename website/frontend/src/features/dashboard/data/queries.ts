// Read-side helpers shared by portal pages. All are tenant-scoped.
import { getDb } from "./store";
import { completionCount, inventoryFor } from "./ingestion";
import { resolveGarment } from "./publication";
import { revisionState } from "./revisions";
import type { GarmentRow } from "../components/catalogue-table";
import type { AnalyticsEventType, Garment, Product, Tenant } from "./types";

export function tenantProducts(tenantId: string): Product[] {
  return getDb().products.filter((p) => p.tenantId === tenantId);
}

export function tenantGarments(tenantId: string): Garment[] {
  return getDb().garments.filter((g) => g.tenantId === tenantId);
}

const BLOCKED_LABELS: Record<string, string> = {
  subscription: "Subscription is not active",
  tenant_paused: "Your page is paused or not launched",
  not_live: "Not published",
  tryon_disabled: "Try-on switched off",
  not_approved: "No QA-approved revision",
  no_purchasable_variant: "No eligible size",
};

export function garmentRows(tenantId: string): GarmentRow[] {
  const db = getDb();
  const tenant = db.tenants.find((t) => t.id === tenantId);
  return tenantGarments(tenantId).map((g) => {
    const p = db.products.find((x) => x.id === g.productId);
    const { done, total, reqs } = completionCount(g, p);
    const inventory = inventoryFor(g, p);
    // The table shows what shoppers actually get, resolved by the same module
    // the storefront reads — not a second opinion computed from the stage.
    const resolved = tenant ? resolveGarment(g, tenant, p) : null;
    return {
      id: g.id,
      title: g.title,
      emoji: p?.imageEmoji ?? "👗",
      category: g.category,
      colour: g.colour,
      skuCount: g.variantIds.length,
      productTitle: p?.title ?? "—",
      productType: p?.productType ?? "—",
      stage: g.stage,
      referenceSize: g.referenceSize,
      tryOnEnabled: g.tryOnEnabled,
      // "3 / 5 complete" plus the per-requirement breakdown, so a merchant can
      // see which chore is outstanding without opening the garment.
      completeCount: done,
      requirementCount: total,
      requirements: reqs,
      soldOutSizes: inventory.soldOut,
      syncStatus: p?.syncStatus ?? "synced",
      updatedAt: g.updatedAt,
      publiclyVisible: resolved?.visible ?? false,
      publicBlockedReason: resolved?.blockedReason
        ? BLOCKED_LABELS[resolved.blockedReason]
        : undefined,
      draftAhead: revisionState(g) === "draft_ahead",
      liveSkus: resolved?.variants.filter((v) => v.tryOnEligible).length ?? 0,
      scheduledGoLive: g.scheduledGoLive,
      openQaFindings: g.qaFindings.filter((f) => !f.resolvedAt).length,
    };
  });
}

export interface DailyMetric {
  /** Real Date — the chart's x-axis is a time scale, not a category list. */
  date: Date;
  /** "Jun 14" — for the table view and any direct label. */
  label: string;
  counts: Record<AnalyticsEventType, number>;
}

/**
 * One window definition for every metric on a screen.
 *
 * Analytics headlined "Last 30 days" over an all-time sum while the table
 * beneath it used a rolling window, so the two disagreed on the same page.
 * `windowStart` is the single boundary; both the series and the totals filter
 * on it, and both report the window they used.
 */
export function windowStart(days: number): Date {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() - (days - 1));
  return d;
}

function eventsInWindow(tenantId: string, days: number) {
  const from = windowStart(days).getTime();
  return getDb().analyticsEvents.filter(
    (e) => e.tenantId === tenantId && new Date(e.at).getTime() >= from,
  );
}

export function dailyMetrics(tenant: Tenant, days = 30): DailyMetric[] {
  const events = eventsInWindow(tenant.id, days);
  const out: DailyMetric[] = [];
  for (let d = days - 1; d >= 0; d--) {
    const day = new Date();
    day.setDate(day.getDate() - d);
    const key = day.toISOString().slice(0, 10);
    const counts: Record<AnalyticsEventType, number> = {
      page_view: 0, tryon_click: 0, session_start: 0, session_complete: 0, sku_view: 0,
    };
    for (const e of events) {
      if (e.at.slice(0, 10) === key) counts[e.type] += 1;
    }
    out.push({
      date: day,
      label: day.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      counts,
    });
  }
  return out;
}

export interface Totals {
  pageViews: number;
  tryOnClicks: number;
  sessionStarts: number;
  sessionCompletes: number;
  completionRate: number;
  /** The window these numbers describe — rendered next to them, never assumed. */
  days: number;
  from: Date;
  to: Date;
}

export function totals(tenant: Tenant, days = 30): Totals {
  const events = eventsInWindow(tenant.id, days);
  const count = (t: AnalyticsEventType) => events.filter((e) => e.type === t).length;
  const starts = count("session_start");
  const completes = count("session_complete");
  return {
    pageViews: count("page_view"),
    tryOnClicks: count("tryon_click"),
    sessionStarts: starts,
    sessionCompletes: completes,
    completionRate: starts === 0 ? 0 : Math.round((completes / starts) * 100),
    days,
    from: windowStart(days),
    to: new Date(),
  };
}

export function skuUsage(tenant: Tenant, days = 30): { label: string; value: number }[] {
  const db = getDb();
  const byGarment = new Map<string, number>();
  // Same window as every other number on the page.
  for (const e of eventsInWindow(tenant.id, days)) {
    if (e.garmentId && e.type === "tryon_click") {
      byGarment.set(e.garmentId, (byGarment.get(e.garmentId) ?? 0) + 1);
    }
  }
  return [...byGarment.entries()]
    .map(([id, value]) => ({
      label: db.garments.find((g) => g.id === id)?.title ?? id,
      value,
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);
}

/** CSV of the daily series — the Analytics+ export, actually implemented. */
export function metricsCsv(metrics: DailyMetric[]): string {
  const header = ["date", "page_views", "tryon_clicks", "sessions_started", "sessions_completed"];
  const rows = metrics.map((m) => [
    m.date.toISOString().slice(0, 10),
    m.counts.page_view,
    m.counts.tryon_click,
    m.counts.session_start,
    m.counts.session_complete,
  ]);
  return [header, ...rows].map((r) => r.join(",")).join("\n");
}
