import { Link } from "react-router-dom";
import { useDbVersion, getDb } from "../../data/store";
import { timeAgo } from "../../data/util";
import { Badge, Banner, PageHeader, Table, Td } from "../../components/ui";
import { dashPath } from "../../routes";

export default function AdminSyncPage() {
  useDbVersion();
  const db = getDb();
  const runs = db.syncRuns;
  const failing = runs.filter((r) => r.failures.length > 0);

  return (
    <>
      <PageHeader
        title="Sync health"
        subtitle={
          runs.length === 0
            ? "Shopify webhook deliveries and reconciliation jobs across all tenants."
            : failing.length > 0
              ? `${failing.length} of the last ${runs.length} runs had failures. Webhook deliveries and reconciliation jobs across all tenants.`
              : `Last ${runs.length} runs all clean. Webhook deliveries and reconciliation jobs across all tenants.`
        }
      />
      {failing.length > 0 && (
        <div className="mb-5">
          <Banner tone="warn">
            <strong>{failing.length} run{failing.length > 1 ? "s" : ""} with failures.</strong> Failed items retry with backoff; persistent failures need merchant action (bad imagery, deleted variants).
          </Banner>
        </div>
      )}
      <Table caption="Shopify sync runs across all tenants" headers={["Tenant", "Trigger", "Status", "Items", "Failures", "When"]}>
        {runs.map((r) => {
          const tenant = db.tenants.find((t) => t.id === r.tenantId);
          return (
            <tr key={r.id} className="hover:bg-stone-50/60">
              <Td className="font-medium text-ink">
                {tenant ? (
                  <Link to={dashPath.adminTenant(tenant.id)} className="hover:text-accent hover:underline">
                    {tenant.name}
                  </Link>
                ) : "—"}
              </Td>
              <Td className="text-stone-600">{r.trigger}</Td>
              <Td><Badge tone={r.status === "success" ? "success" : r.status === "partial" ? "warn" : r.status === "running" ? "info" : "danger"}>{r.status}</Badge></Td>
              <Td className="tabular-nums text-stone-600">{r.itemsSynced}</Td>
              <Td className="text-xs text-amber-800">
                {r.failures.length === 0 ? <span className="text-muted">—</span> : r.failures.map((f) => `${f.item}: ${f.error}`).join("; ")}
              </Td>
              <Td className="text-xs text-muted">{timeAgo(r.startedAt)}</Td>
            </tr>
          );
        })}
      </Table>
    </>
  );
}
