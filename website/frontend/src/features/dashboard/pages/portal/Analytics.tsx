import { useDbVersion } from "../../data/store";
import { useSession } from "../../data/session";
import { getEntitlements } from "../../data/entitlements";
import { useState } from "react";
import { dailyMetrics, metricsCsv, skuUsage, totals } from "../../data/queries";
import { fmtDate } from "../../data/util";
import { Badge, Card, EmptyState, PageHeader } from "../../components/ui";
import { buttonClass } from "../../components/styles";
import { HeroMetric, StatRow } from "../../components/metrics";
import { SessionsChart, TopGarmentsChart } from "../../components/analytics-charts";

export default function AnalyticsPage() {
  const session = useSession();
  const [days, setDays] = useState(30);
  useDbVersion();
  if (!session?.tenant) return null;
  const tenant = session.tenant;

  const ent = getEntitlements(tenant);
  // One window, read by the headline, the series, the table and the export.
  // These used to disagree: an all-time sum under a "Last 30 days" heading.
  const t = totals(tenant, days);
  const metrics = dailyMetrics(tenant, days);
  const usage = skuUsage(tenant, days);

  if (t.pageViews === 0 && days === 30) {
    return (
      <>
        <PageHeader title="Analytics" subtitle="Shopper engagement with your try-on experience." />
        <EmptyState
          icon="∿"
          title="No shopper activity yet"
          body="Once your page is live and shoppers start trying on garments, you'll see visits, sessions, completion rates, and per-SKU engagement here."
        />
      </>
    );
  }

  // The hero answers this screen's one question — "is try-on actually working
  // for shoppers?" Volume without completion says nothing; completion rate is
  // the quality signal, so it leads and the counts support it.
  const healthy = t.completionRate >= 60;

  return (
    <>
      <PageHeader
        title="Analytics"
        subtitle={
          <span>
            {fmtDate(t.from.toISOString())} – {fmtDate(t.to.toISOString())} · every number on this
            page covers the same window.{" "}
            {!ent.analyticsPlus && <span>CSV export is part of the Analytics+ add-on.</span>}
          </span>
        }
        action={
          <div className="flex flex-wrap items-center gap-2">
            <label className="sr-only" htmlFor="analytics-window">Reporting window</label>
            <select
              id="analytics-window"
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="rounded-lg border border-line bg-surface px-2.5 py-1.5 text-[13px]"
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
            {/* Analytics+ claimed CSV export for months. It is a client-side
                serialisation of data already on screen, so there was never a
                reason for it not to exist. */}
            {ent.analyticsPlus ? (
              <button
                onClick={() => {
                  const blob = new Blob([metricsCsv(metrics)], { type: "text/csv" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `mirra-analytics-${tenant.slug}-${days}d.csv`;
                  a.click();
                  URL.revokeObjectURL(url);
                }}
                className={buttonClass("secondary", "sm")}
              >
                ↓ Export CSV
              </button>
            ) : (
              <Badge tone="neutral">Analytics+ for CSV export</Badge>
            )}
          </div>
        }
      />

      <HeroMetric
        label="Session completion rate"
        value={`${t.completionRate}%`}
        status={{ tone: healthy ? "success" : "warn", label: healthy ? "Healthy" : "Below target" }}
        caption={
          healthy
            ? `${t.sessionCompletes.toLocaleString()} of ${t.sessionStarts.toLocaleString()} try-on sessions ran to completion. Above the 60% target we see across brands.`
            : `${t.sessionCompletes.toLocaleString()} of ${t.sessionStarts.toLocaleString()} try-on sessions ran to completion, below the 60% target. Garments missing size or fabric data are the usual cause.`
        }
      />

      <StatRow
        items={[
          { label: "Page visits", value: t.pageViews.toLocaleString() },
          {
            label: "Try-on clicks",
            value: t.tryOnClicks.toLocaleString(),
            hint: `${Math.round((t.tryOnClicks / Math.max(1, t.pageViews)) * 100)}% of visits`,
          },
          { label: "Sessions started", value: t.sessionStarts.toLocaleString() },
          { label: "Sessions completed", value: t.sessionCompletes.toLocaleString() },
        ]}
      />

      <div className="mt-6 grid grid-cols-3 gap-4 max-lg:grid-cols-1">
        <Card title="Adoption — sessions per day" className="col-span-2 max-lg:col-span-1">
          <SessionsChart metrics={metrics} aspectRatio="5 / 2" />
        </Card>
        <Card title="Most tried-on garments">
          {usage.length === 0 ? (
            <p className="text-[13px] text-muted">No try-on clicks recorded in this window.</p>
          ) : (
            <>
              <TopGarmentsChart items={usage} />
              {/* The chart itself is aria-hidden, so the same data has to be
                  readable as text rather than being lost to a screen reader. */}
              <table className="mt-3 w-full text-left text-xs">
                <caption className="sr-only">
                  Try-on clicks per garment over the selected window
                </caption>
                <thead>
                  <tr className="text-muted">
                    <th scope="col" className="py-1 pr-3 font-medium">Garment</th>
                    <th scope="col" className="py-1 font-medium">Try-on clicks</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {usage.map((u) => (
                    <tr key={u.label}>
                      <td className="py-1 pr-3 text-stone-600">{u.label}</td>
                      <td className="py-1 tabular-nums">{u.value.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </Card>
      </div>

      <div className="mt-6">
        {/* The table view is the accessible equivalent of the line chart above:
            same series, same period, readable without colour. */}
        <Card title="Daily detail">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <caption className="sr-only">
                Daily shopper engagement — the same series as the chart above
              </caption>
              <thead>
                <tr className="text-xs text-muted">
                  <th scope="col" className="py-1.5 pr-4 font-medium">Date</th>
                  <th scope="col" className="py-1.5 pr-4 font-medium">Visits</th>
                  <th scope="col" className="py-1.5 pr-4 font-medium">Try-on clicks</th>
                  <th scope="col" className="py-1.5 pr-4 font-medium">Sessions started</th>
                  <th scope="col" className="py-1.5 font-medium">Completed</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {[...metrics].reverse().slice(0, 14).map((m) => (
                  <tr key={m.label}>
                    <td className="py-2 pr-4">{m.label}</td>
                    <td className="py-2 pr-4 tabular-nums">{m.counts.page_view}</td>
                    <td className="py-2 pr-4 tabular-nums">{m.counts.tryon_click}</td>
                    <td className="py-2 pr-4 tabular-nums">{m.counts.session_start}</td>
                    <td className="py-2 tabular-nums">{m.counts.session_complete}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </>
  );
}
