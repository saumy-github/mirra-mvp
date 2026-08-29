import { Link } from "react-router-dom";
import { useDbVersion, getDb } from "../../data/store";
import { timeAgo } from "../../data/util";
import { Badge, Banner, PageHeader, Table, Td } from "../../components/ui";
import { InviteLeadButton, LeadStatusSelect } from "../../components/admin-controls";
import { dashPath } from "../../routes";
import type { LeadRole, MonthlyOrders } from "../../data/types";

const SOURCE_LABELS: Record<string, string> = {
  demo_request: "Demo request",
  early_access: "Early access",
  contact_sales: "Contact sales",
};

const ROLE_LABELS: Record<LeadRole, string> = {
  founder: "Founder",
  ecommerce: "E-commerce",
  product: "Product",
  engineering: "Engineering",
  other: "Other",
};

const ORDER_LABELS: Record<MonthlyOrders, string> = {
  "under-1k": "<1k / mo",
  "1k-10k": "1k–10k / mo",
  "10k-50k": "10k–50k / mo",
  "50k-plus": "50k+ / mo",
};

export default function AdminLeadsPage() {
  useDbVersion();
  const leads = getDb().leads;

  return (
    <>
      <PageHeader
        title="Leads & CRM"
        subtitle="Brands that completed the verification form on the marketing site. Qualify, then invite — inviting creates the tenant workspace and emails the contact an onboarding link."
      />

      {/* Honest about where this data comes from. The public form already
          writes real applications; this console still reads the local demo
          seed until the backend exposes a list endpoint. */}
      <div className="mb-5">
        <Banner tone="warn">
          <strong>Showing demo applications.</strong> The public form at{" "}
          <Link to="/join" className="font-semibold underline">/join</Link> already writes real
          submissions to the <code className="text-xs">join_applications</code> collection, but the
          backend has no endpoint to read them back yet — so sales cannot work real leads from here.
          Adding <code className="text-xs">GET /api/v1/join/applications</code> is what connects
          this screen to the live pipeline.
        </Banner>
      </div>

      <Table caption="Inbound brand applications awaiting qualification" headers={["Company", "Contact", "Store", "Role", "Volume", "Source", "Age", "Status", ""]}>
        {leads.map((l) => (
          <tr key={l.id} className="align-top hover:bg-stone-50/60">
            <Td>
              <div className="font-medium text-ink">{l.company}</div>
              {/* What they wrote in the form is the whole reason sales opens
                  this row — it belongs in the table, not behind a click. */}
              <p className="mt-0.5 max-w-[22rem] text-xs leading-relaxed text-muted">{l.goals}</p>
              {l.notes.length > 0 && (
                <p className="mt-1 max-w-[22rem] truncate text-xs text-stone-500">
                  Note: {l.notes[l.notes.length - 1]}
                </p>
              )}
            </Td>
            <Td className="text-stone-600">
              {l.contactName}
              <div className="text-xs text-muted">{l.email}</div>
            </Td>
            <Td className="text-xs text-stone-600">{l.storeUrl.replace("https://", "")}</Td>
            <Td className="text-stone-600">{ROLE_LABELS[l.role]}</Td>
            <Td className="text-stone-600">{l.monthlyOrders ? ORDER_LABELS[l.monthlyOrders] : "—"}</Td>
            <Td><Badge>{SOURCE_LABELS[l.source]}</Badge></Td>
            <Td className="text-xs text-muted">{timeAgo(l.createdAt)}</Td>
            <Td><LeadStatusSelect leadId={l.id} status={l.status} /></Td>
            <Td>
              {l.tenantId ? (
                <Link to={dashPath.adminTenant(l.tenantId)} className="text-xs font-medium text-accent hover:underline">Workspace →</Link>
              ) : (
                <InviteLeadButton leadId={l.id} disabled={l.status !== "qualified"} />
              )}
            </Td>
          </tr>
        ))}
      </Table>
      <p className="mt-3 text-xs text-muted">
        Leads must be marked <strong>qualified</strong> before they can be invited. Inviting is the
        only way a brand gets a workspace — there is no self-serve merchant signup.
      </p>
    </>
  );
}
