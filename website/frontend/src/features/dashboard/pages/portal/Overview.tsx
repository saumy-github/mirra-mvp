import { Link } from "react-router-dom";
import { useDbVersion, getDb } from "../../data/store";
import { useSession } from "../../data/session";
import { getEntitlements } from "../../data/entitlements";
import { can } from "../../data/rbac";
import { dailyMetrics, garmentRows, totals } from "../../data/queries";
import { liveSkuCount } from "../../data/publication";
import { fmtDate, timeAgo } from "../../data/util";
import { ButtonLink, Card, KeyValue, PageHeader } from "../../components/ui";
import { StatRow } from "../../components/metrics";
import { AuditTarget } from "../../components/audit-target";
import { TenantStatusBadge } from "../../components/shell";
import { SessionsChart } from "../../components/analytics-charts";
import { dashPath } from "../../routes";

export default function OverviewPage() {
  const session = useSession();
  useDbVersion();
  if (!session?.tenant) return null; // PortalLayout owns the redirect
  const tenant = session.tenant;

  const db = getDb();
  const ent = getEntitlements(tenant);
  const rows = garmentRows(tenant.id);

  // "Live SKUs" is the billable unit, so it counts variants — a four-size
  // colourway is four, not one.
  const liveSkus = liveSkuCount(tenant.id);
  const liveGarments = rows.filter((r) => r.publiclyVisible).length;
  const missingData = rows.filter((r) => r.completeCount < r.requirementCount);
  const t = totals(tenant, 30);
  const metrics = dailyMetrics(tenant, 30);

  const canManagePublication = can(session.role, "publication.manage");
  const lastSync = db.syncRuns.filter((s) => s.tenantId === tenant.id)[0];
  const openTickets = db.tickets.filter((x) => x.tenantId === tenant.id && x.status !== "resolved");
  const recentAudit = db.auditEvents.filter((a) => a.tenantId === tenant.id).slice(0, 5);

  const ctas: { label: string; href: string }[] = [];
  const canEdit = can(session.role, "catalogue.edit");
  if (missingData.length > 0)
    ctas.push({
      label: canEdit
        ? `Complete data for ${missingData.length} garment${missingData.length > 1 ? "s" : ""}`
        : `${missingData.length} garment${missingData.length > 1 ? "s are" : " is"} missing data`,
      href: dashPath.garments,
    });
  const inQa = rows.filter((r) => r.stage === "in_qa").length;
  if (inQa > 0) ctas.push({ label: `${inQa} garment${inQa > 1 ? "s" : ""} with Mirra QA`, href: dashPath.publication });
  if (lastSync?.failures.length) ctas.push({ label: `Fix ${lastSync.failures.length} sync error${lastSync.failures.length > 1 ? "s" : ""}`, href: dashPath.products });
  if (tenant.status === "trial") ctas.push({ label: `Trial ends ${fmtDate(tenant.billing.trialEndsAt)} — add billing details`, href: dashPath.billing });

  return (
    <>
      <PageHeader
        title="Overview"
        subtitle={`Everything that matters for ${tenant.name}'s try-on experience, at a glance.`}
        action={
          <ButtonLink href={dashPath.publication} variant="primary" size="sm">
            {canManagePublication ? "Manage publication" : "View publication status"}
          </ButtonLink>
        }
      />

      {ctas.length > 0 && (
        <nav aria-label="Needs your attention" className="mb-6 flex flex-wrap gap-2">
          {ctas.map((c) => (
            <Link
              key={c.href + c.label}
              to={c.href}
              className="rounded-full border border-indigo-200 bg-accent-soft px-3.5 py-1.5 text-[13px] font-medium text-indigo-800 transition-colors hover:bg-indigo-100"
            >
              → {c.label}
            </Link>
          ))}
        </nav>
      )}

      <StatRow
        items={[
          {
            label: "Subscription",
            value: <TenantStatusBadge status={tenant.status} />,
            hint: tenant.billing.renewalDate
              ? `Renews ${fmtDate(tenant.billing.renewalDate)}`
              : tenant.billing.trialEndsAt
                ? `Trial ends ${fmtDate(tenant.billing.trialEndsAt)}`
                : undefined,
          },
          {
            label: "Launch status",
            value: <span className="capitalize">{tenant.launchStatus.replace("_", " ")}</span>,
            hint: ent.publicSurfaceEnabled ? tenant.domain.subdomain : "Public page offline",
          },
          {
            label: "Live SKUs",
            value: `${liveSkus} / ${ent.skuLimit}`,
            hint: `${liveGarments} garment${liveGarments === 1 ? "" : "s"} reaching shoppers`,
          },
          {
            label: "Sync health",
            value: lastSync?.status === "success" ? "Healthy" : lastSync?.status === "partial" ? "Partial" : "Attention",
            hint: lastSync ? `Last sync ${timeAgo(lastSync.startedAt)}` : "Never synced",
            tone: lastSync?.status === "success" ? "success" : "warn",
          },
        ]}
      />

      <div className="mt-6 grid grid-cols-3 gap-4 max-lg:grid-cols-1">
        {/* Headline totals live on Analytics, not here — this card used to be
            followed by a second row of tiles repeating them. */}
        <Card
          title="Try-on sessions — last 30 days"
          className="col-span-2 max-lg:col-span-1"
          action={
            <Link to={dashPath.analytics} className="text-xs font-medium text-accent hover:underline">
              View analytics →
            </Link>
          }
        >
          {t.sessionStarts > 0 ? (
            <SessionsChart metrics={metrics} />
          ) : (
            <p className="py-8 text-center text-[13px] text-muted">
              No shopper sessions yet — publish garments and share your try-on page to start seeing usage here.
            </p>
          )}
        </Card>
        <div className="flex flex-col gap-4">
          <Card title="Support">
            <KeyValue
              rows={[
                ["Open tickets", openTickets.length === 0 ? "None 🎉" : String(openTickets.length)],
                ["Support tier", <span key="t" className="capitalize">{ent.supportTier}</span>],
              ]}
            />
            <ButtonLink href={dashPath.support} size="sm">Go to support →</ButtonLink>
          </Card>
          <Card title="Recent changes">
            {recentAudit.length === 0 ? (
              <p className="text-[13px] text-muted">No changes yet.</p>
            ) : (
              <ul className="space-y-2.5">
                {recentAudit.map((a) => (
                  <li key={a.id} className="text-[13px]">
                    <span className="font-medium text-ink">{a.actorName}</span>{" "}
                    <span className="text-muted">
                      {a.action.split(".")[1]?.replace("_", " ")} ·{" "}
                      <AuditTarget tenantId={tenant.id} target={a.target} />
                    </span>
                    <span className="block text-xs text-stone-400">{timeAgo(a.at)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
