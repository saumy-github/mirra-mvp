import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useDbVersion, getDb } from "../../data/store";
import { useSession } from "../../data/session";
import { canInternal } from "../../data/rbac";
import { VIEW_AS_TTL_MINUTES } from "../../data/session";
import { getEntitlements } from "../../data/entitlements";
import { TENANT_TRANSITIONS } from "../../data/lifecycle";
import { addAccountNoteAction, startViewAsAction } from "../../data/actions";
import { fmtDate, fmtDateTime, timeAgo } from "../../data/util";
import { Badge, Banner, ButtonLink, Card, EmptyState, KeyValue, PageHeader, SubmitButton } from "../../components/ui";
import { buttonClass, inputClass } from "../../components/styles";
import { TenantStatusBadge } from "../../components/shell";
import { TenantOverrideButton } from "../../components/admin-controls";
import { dashPath } from "../../routes";

export default function AdminTenantDetail() {
  const { id } = useParams<{ id: string }>();
  const session = useSession();
  useDbVersion();
  if (!session) return null;

  const db = getDb();
  const t = db.tenants.find((x) => x.id === id);
  if (!t) {
    return (
      <EmptyState
        icon="▦"
        title="Tenant not found"
        body="This workspace may have been archived or the link is stale."
        action={<ButtonLink href={dashPath.admin} size="sm">Back to tenants</ButtonLink>}
      />
    );
  }

  const ent = getEntitlements(t);
  const isAdmin = session.user.internalRole === "mirra_admin";

  const timeline = [
    ...db.auditEvents.filter((e) => e.tenantId === t.id).map((e) => ({ at: e.at, label: `${e.actorName}: ${e.action} — ${e.target}`, detail: e.detail })),
    ...db.billingEvents.filter((e) => e.tenantId === t.id).map((e) => ({ at: e.at, label: `Billing: ${e.type.replace(/_/g, " ")}`, detail: e.detail })),
  ].sort((a, b) => b.at.localeCompare(a.at)).slice(0, 20);

  const onboardingSteps = Object.entries(t.onboarding);
  const onboardingDone = onboardingSteps.filter(([, v]) => v).length;
  const tickets = db.tickets.filter((x) => x.tenantId === t.id && x.status !== "resolved");
  const overrideTargets = TENANT_TRANSITIONS[t.status];

  return (
    <>
      <div className="mb-1 text-xs text-muted">
        <Link to={dashPath.admin} className="hover:text-ink">Tenants</Link> / {t.name}
      </div>
      <PageHeader
        title={t.name}
        subtitle={
          <span className="flex items-center gap-2">
            <TenantStatusBadge status={t.status} />
            <span className="capitalize">{t.billing.planId} · {t.billing.interval}</span>
            <span>· {t.domain.subdomain}</span>
          </span>
        }
        action={<ViewAsButton tenantId={t.id} tenantName={t.name} />}
      />

      {tickets.some((x) => x.status === "escalated") && (
        <div className="mb-5">
          <Banner tone="danger"><strong>Escalated production ticket open.</strong> Check the support queue.</Banner>
        </div>
      )}

      <div className="grid grid-cols-3 gap-4 max-lg:grid-cols-1">
        <div className="col-span-2 flex flex-col gap-4 max-lg:col-span-1">
          <Card title="Account timeline">
            <ul className="space-y-3">
              {timeline.map((e, i) => (
                <li key={i} className="flex gap-3 text-[13px]">
                  <span className="w-24 shrink-0 text-xs text-muted">{timeAgo(e.at)}</span>
                  <span>
                    <span className="text-stone-800">{e.label}</span>
                    {e.detail && <span className="block text-xs text-muted">{e.detail}</span>}
                  </span>
                </li>
              ))}
              {timeline.length === 0 && <li className="text-[13px] text-muted">No events yet.</li>}
            </ul>
          </Card>

          <Card title="Account notes">
            <form action={(formData: FormData) => void addAccountNoteAction(t.id, formData)} className="mb-4 flex gap-2">
              <input name="note" required placeholder="Add a note for the team…" className={inputClass} />
              <SubmitButton size="sm">Add</SubmitButton>
            </form>
            <ul className="space-y-3">
              {t.accountNotes.map((n, i) => (
                <li key={i} className="text-[13px]">
                  <span className="text-stone-800">{n.note}</span>
                  <span className="block text-xs text-muted">{n.by} · {fmtDateTime(n.at)}</span>
                </li>
              ))}
            </ul>
          </Card>
        </div>

        <div className="flex flex-col gap-4">
          <Card title="Health & risk">
            <KeyValue
              rows={[
                ["Health score", <span key="h" className={t.healthScore >= 70 ? "text-emerald-700" : t.healthScore >= 50 ? "text-amber-700" : "text-red-700"}>{t.healthScore} / 100</span>],
                ["Churn risk", <Badge key="c" tone={t.churnRisk === "low" ? "success" : t.churnRisk === "medium" ? "warn" : "danger"}>{t.churnRisk}</Badge>],
                ["Open tickets", String(tickets.length)],
                ["Onboarding", `${onboardingDone}/${onboardingSteps.length} steps`],
                ["Sales-led", t.salesLed ? "Yes" : "Self-serve"],
              ]}
            />
          </Card>
          <Card title="Provisioning & domain">
            <KeyValue
              rows={[
                ["Public surface", <Badge key="p" tone={ent.publicSurfaceEnabled ? "success" : "danger"}>{ent.publicSurfaceEnabled ? "Serving" : "Offline"}</Badge>],
                ["Launch status", <span key="l" className="capitalize">{t.launchStatus.replace("_", " ")}</span>],
                ["Subdomain", t.domain.subdomain],
                ["Ownership verified", t.storeOwnershipVerified ? "Yes" : "No"],
                ["Preview token", <code key="t" className="text-xs">{t.previewToken}</code>],
                ...(t.graceUntil ? ([["Data grace until", fmtDate(t.graceUntil)]] as [string, string][]) : []),
              ]}
            />
          </Card>
          <Card title="Billing">
            <KeyValue
              rows={[
                ["Payment", t.billing.paymentStatus.replace("_", " ")],
                ["Renewal", fmtDate(t.billing.renewalDate)],
                ["Add-ons", t.billing.addOns.join(", ") || "None"],
                ...(t.billing.cancellationReason ? ([["Cancel reason", t.billing.cancellationReason]] as [string, string][]) : []),
              ]}
            />
          </Card>
          {isAdmin && overrideTargets.length > 0 && (
            <Card title="⚠ Manual overrides">
              <p className="mb-3 text-xs text-amber-800">
                These bypass billing-driven automation and take effect immediately on the public surface.
                Every override requires a reason and is audit-logged.
              </p>
              <div className="flex flex-wrap gap-2">
                {overrideTargets.map((to) => (
                  <TenantOverrideButton
                    key={to}
                    tenantId={t.id}
                    to={to}
                    label={
                      { lead: "→ Lead", onboarding: "→ Onboarding", trial: "→ Trial", active: "Force activate", past_due: "Mark past due", suspended: "Suspend", cancelled: "Cancel", archived: "Archive" }[to]
                    }
                    danger={to === "suspended" || to === "cancelled" || to === "archived"}
                  />
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}

/**
 * Entering a customer's workspace.
 *
 * Read-only is the default and the only mode most console roles can use; write
 * access is Admin-only, and even then it maps to a Merchandiser seat rather
 * than an Owner one — nobody impersonating a customer needs to change their
 * billing or remove their team. A reason is mandatory and lands in the brand's
 * own audit log, and the grant expires on its own.
 */
function ViewAsButton({ tenantId, tenantName }: { tenantId: string; tenantName: string }) {
  const session = useSession();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [mode, setMode] = useState<"read_only" | "write">("read_only");
  const [error, setError] = useState<string | null>(null);

  const role = session?.user.internalRole;
  if (!canInternal(role, "viewas.start")) return null;
  const canElevate = canInternal(role, "viewas.elevate");

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className={buttonClass("secondary", "sm")}>
        👁 View as tenant
      </button>
    );
  }
  return (
    <div className="w-80 rounded-xl border border-amber-200 bg-amber-50 p-3 text-[13px]">
      <div className="font-semibold text-amber-900">Enter {tenantName}&apos;s workspace</div>
      <p className="mt-1 text-xs text-amber-900">
        This is recorded in the brand&apos;s audit log with your name and reason, and ends
        automatically after {VIEW_AS_TTL_MINUTES} minutes.
      </p>
      <label className="mt-2 block">
        <span className="mb-1 block text-xs font-medium text-amber-900">Reason (required)</span>
        <input
          autoFocus
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Ticket #tk_1 — sync error on Sable Trench"
          className="w-full rounded-md border border-amber-200 bg-white px-2 py-1 text-xs focus:outline-none"
        />
      </label>
      <fieldset className="mt-2">
        <legend className="text-xs font-medium text-amber-900">Access</legend>
        <label className="mt-1 flex items-center gap-2 text-xs">
          <input type="radio" checked={mode === "read_only"} onChange={() => setMode("read_only")} />
          Read-only (recommended)
        </label>
        <label className="mt-0.5 flex items-center gap-2 text-xs">
          <input
            type="radio"
            disabled={!canElevate}
            checked={mode === "write"}
            onChange={() => setMode("write")}
          />
          Write access — Merchandiser seat
          {!canElevate && <span className="text-amber-800">(Admin only)</span>}
        </label>
      </fieldset>
      {error && <p role="alert" className="mt-2 text-xs font-medium text-red-700">{error}</p>}
      <div className="mt-3 flex gap-2">
        <button
          disabled={reason.trim().length < 4}
          onClick={() => {
            const res = startViewAsAction(tenantId, reason, mode);
            if ("error" in res) setError(res.error);
            else navigate(res.path);
          }}
          className={buttonClass("accent", "sm")}
        >
          Enter workspace
        </button>
        <button onClick={() => setOpen(false)} className={buttonClass("ghost", "sm")}>
          Cancel
        </button>
      </div>
    </div>
  );
}
