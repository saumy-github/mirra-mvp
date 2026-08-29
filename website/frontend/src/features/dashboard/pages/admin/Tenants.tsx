import { Link } from "react-router-dom";
import { useDbVersion, getDb } from "../../data/store";
import { getEntitlements } from "../../data/entitlements";
import { garmentRows } from "../../data/queries";
import { fmtDate } from "../../data/util";
import { Badge, PageHeader, Table, Td } from "../../components/ui";
import { StatRow } from "../../components/metrics";
import { TenantStatusBadge } from "../../components/shell";
import { dashPath } from "../../routes";

export default function AdminTenantsPage() {
  useDbVersion();
  const db = getDb();
  const tenants = db.tenants;
  const active = tenants.filter((t) => t.status === "active" || t.status === "trial").length;
  const atRisk = tenants.filter((t) => t.churnRisk === "high" || t.status === "past_due" || t.status === "suspended").length;
  const openTickets = db.tickets.filter((t) => t.status !== "resolved").length;
  const newLeads = db.leads.filter((l) => l.status === "new" || l.status === "qualifying").length;

  return (
    <>
      <PageHeader title="Tenants" subtitle="Every brand on Mirra — lifecycle, billing, launch readiness, and health." />
      <div className="mb-6">
        <StatRow
          items={[
            { label: "Active + trialing", value: active },
            {
              label: "At risk",
              value: atRisk,
              hint: atRisk > 0 ? "Needs attention" : undefined,
              tone: atRisk > 0 ? "danger" : undefined,
            },
            { label: "Open tickets", value: openTickets },
            { label: "Leads in pipeline", value: newLeads },
          ]}
        />
      </div>
      <Table caption="All brands on Mirra with lifecycle, billing and health" headers={["Tenant", "Status", "Plan", "Launch", "Live SKUs", "Health", "Renewal / trial", ""]}>
        {tenants.map((t) => {
          const rows = garmentRows(t.id);
          const live = rows.filter((r) => r.stage === "live").length;
          const ent = getEntitlements(t);
          return (
            <tr key={t.id} className="hover:bg-stone-50/60">
              <Td>
                <Link to={dashPath.adminTenant(t.id)} className="font-medium text-ink hover:text-accent">
                  {t.name}
                </Link>
                <div className="text-xs text-muted">{t.domain.subdomain}</div>
              </Td>
              <Td><TenantStatusBadge status={t.status} /></Td>
              <Td className="capitalize text-stone-600">{t.billing.planId}</Td>
              <Td>
                <Badge tone={ent.publicSurfaceEnabled ? "success" : "warn"}>
                  {ent.publicSurfaceEnabled ? "Serving" : "Offline"}
                </Badge>
              </Td>
              <Td className="tabular-nums text-stone-600">{live} / {ent.skuLimit}</Td>
              <Td>
                <span className={`font-medium tabular-nums ${t.healthScore >= 70 ? "text-emerald-700" : t.healthScore >= 50 ? "text-amber-700" : "text-red-700"}`}>
                  {t.healthScore}
                </span>
                <span className="ml-1.5 text-xs text-muted">{t.churnRisk} risk</span>
              </Td>
              <Td className="text-xs text-muted">
                {t.status === "trial" ? `Trial → ${fmtDate(t.billing.trialEndsAt)}` : t.billing.renewalDate ? fmtDate(t.billing.renewalDate) : "—"}
              </Td>
              <Td>
                <Link to={dashPath.adminTenant(t.id)} className="text-xs font-medium text-accent hover:underline">Open →</Link>
              </Td>
            </tr>
          );
        })}
      </Table>
    </>
  );
}
