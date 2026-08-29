import { Link } from "react-router-dom";
import { useDbVersion, getDb } from "../../data/store";
import { fmtDate } from "../../data/util";
import { Card, PageHeader, Badge } from "../../components/ui";
import { TenantStatusBadge } from "../../components/shell";
import { dashPath } from "../../routes";

const PLAYBOOKS = [
  { trigger: "Trial ending in < 5 days, no billing details", action: "CSM call + offer 7-day extension" },
  { trigger: "Payment failed (dunning)", action: "Automated emails day 0/3/6, personal outreach day 7, suspend day 10" },
  { trigger: "Health score < 40 for 2 weeks", action: "Success review: check sync errors, missing data, and adoption blockers" },
  { trigger: "Cancelled within grace period", action: "Win-back sequence with cancellation-reason-specific offer" },
];

export default function AdminChurnPage() {
  useDbVersion();
  const db = getDb();
  const atRisk = db.tenants.filter(
    (t) => t.churnRisk !== "low" || ["past_due", "suspended", "cancelled"].includes(t.status) || t.status === "trial"
  );
  const reactivation = db.tenants.filter((t) => t.status === "cancelled" || t.status === "suspended");

  return (
    <>
      <PageHeader
        title="Churn & renewals"
        subtitle={
          atRisk.length === 0
            ? "No accounts need proactive attention right now."
            : `${atRisk.length} account${atRisk.length === 1 ? "" : "s"} need proactive attention${reactivation.length > 0 ? `, and ${reactivation.length} can still be reactivated` : ""}.`
        }
      />
      <div className="grid grid-cols-2 gap-4 max-lg:grid-cols-1">
        <Card title="Watchlist">
          <ul className="divide-y divide-stone-100">
            {atRisk.map((t) => (
              <li key={t.id} className="flex items-center justify-between gap-3 py-3">
                <div>
                  <Link to={dashPath.adminTenant(t.id)} className="text-[13px] font-medium text-ink hover:text-accent">{t.name}</Link>
                  <div className="text-xs text-muted">
                    {t.status === "trial" && `Trial ends ${fmtDate(t.billing.trialEndsAt)}`}
                    {t.status === "suspended" && `Suspended — payment past due`}
                    {t.status === "cancelled" && `Cancelled: ${t.billing.cancellationReason ?? "no reason given"}`}
                    {t.status === "active" && `Health ${t.healthScore} · ${t.churnRisk} risk`}
                    {t.status === "past_due" && `Dunning in progress`}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone={t.churnRisk === "high" ? "danger" : t.churnRisk === "medium" ? "warn" : "success"}>{t.churnRisk} risk</Badge>
                  <TenantStatusBadge status={t.status} />
                </div>
              </li>
            ))}
            {atRisk.length === 0 && <li className="py-3 text-[13px] text-muted">Nothing at risk right now.</li>}
          </ul>
        </Card>
        <div className="flex flex-col gap-4">
          <Card title="Reactivation opportunities">
            <ul className="space-y-3">
              {reactivation.map((t) => (
                <li key={t.id} className="text-[13px]">
                  <Link to={dashPath.adminTenant(t.id)} className="font-medium text-ink hover:text-accent">{t.name}</Link>
                  <span className="ml-2 text-xs text-muted">
                    {t.graceUntil ? `Data preserved until ${fmtDate(t.graceUntil)}` : "Within grace window"} — one-click reactivation restores their page.
                  </span>
                </li>
              ))}
              {reactivation.length === 0 && <li className="text-[13px] text-muted">No cancelled or suspended tenants.</li>}
            </ul>
          </Card>
          <Card title="Success playbooks">
            <ul className="space-y-3">
              {PLAYBOOKS.map((p) => (
                <li key={p.trigger} className="text-[13px]">
                  <div className="font-medium text-ink">{p.trigger}</div>
                  <div className="text-xs text-muted">{p.action}</div>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </>
  );
}
