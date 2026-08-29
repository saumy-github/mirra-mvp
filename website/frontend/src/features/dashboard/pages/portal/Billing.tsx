import { useDbVersion, getDb } from "../../data/store";
import { useSession } from "../../data/session";
import { getEntitlements, getPlan } from "../../data/entitlements";
import { cancellationImpact, requestCancellationAction, reactivateAction } from "../../data/actions";
import { can } from "../../data/rbac";
import { fmtDate, fmtDateTime, money } from "../../data/util";
import {
  ActionButton,
  Badge,
  Banner,
  Card,
  Field,
  KeyValue,
  NoticeBar,
  PageHeader,
  SubmitButton,
} from "../../components/ui";
import { useAction } from "../../components/use-action";
import { inputClass } from "../../components/styles";

const ADD_ON_LABELS: Record<string, string> = {
  extra_sku_pack: "Extra SKU capacity (+100)",
  premium_support: "Premium support",
  custom_domain: "Custom domain",
  analytics_plus: "Analytics+",
};

export default function BillingPage() {
  const session = useSession();
  const notice = useAction();
  useDbVersion();
  if (!session?.tenant) return null;
  const tenant = session.tenant;

  if (!can(session.role, "billing.view")) {
    return (
      <>
        <PageHeader title="Billing" />
        <Banner tone="info">Your role doesn&apos;t include billing access. Ask your account owner if you need invoices or plan details.</Banner>
      </>
    );
  }
  const db = getDb();
  const plan = getPlan(tenant);
  const ent = getEntitlements(tenant);
  const events = db.billingEvents.filter((e) => e.tenantId === tenant.id).slice(0, 8);
  const canManage = can(session.role, "billing.manage");
  const cancelled = tenant.status === "cancelled";
  const suspended = tenant.status === "suspended";
  const impact = cancellationImpact(tenant.id);

  return (
    <>
      <PageHeader title="Billing" subtitle="Your plan, payment status, invoices, and renewal — all in one place." />
      <NoticeBar notice={notice.notice} onDismiss={notice.clear} />

      {suspended && (
        <div className="mb-5">
          <Banner tone="danger">
            <strong>Payment past due — your try-on page is suspended.</strong> Update your payment method to restore
            it instantly. Your catalogue and settings are untouched.
          </Banner>
        </div>
      )}
      {cancelled && (
        <div className="mb-5">
          <Banner tone="warn">
            <strong>Subscription cancelled.</strong> Your data is preserved until {fmtDate(tenant.graceUntil)}.
            Reactivate anytime before then to restore your page exactly as it was.
          </Banner>
        </div>
      )}

      <div className="grid grid-cols-3 gap-4 max-lg:grid-cols-1">
        <Card title="Current plan" className="col-span-2 max-lg:col-span-1">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-semibold">{plan.name}</span>
                <Badge tone={tenant.billing.paymentStatus === "paid" ? "success" : tenant.billing.paymentStatus === "trialing" ? "info" : tenant.billing.paymentStatus === "past_due" ? "danger" : "neutral"}>
                  {tenant.billing.paymentStatus.replace("_", " ")}
                </Badge>
              </div>
              <p className="mt-1 text-[13px] text-muted">
                {money(tenant.billing.interval === "annual" ? plan.annualUsd : plan.monthlyUsd)}
                /{tenant.billing.interval === "annual" ? "yr" : "mo"} · {ent.skuLimit} live SKUs · {ent.seatLimit} seats · {ent.supportTier} support
              </p>
            </div>
            {/* This was a link to a paragraph on the same page dressed up as
                an external portal. Until the provider is connected there is no
                portal to open, so it doesn't pretend to be a button. */}
            {canManage && !cancelled && (
              <span className="text-right text-xs text-muted">
                Payment methods and invoices
                <span className="block">open in the provider&apos;s portal once billing is connected.</span>
              </span>
            )}
          </div>
          <div className="mt-4">
            <KeyValue
              rows={[
                ["Billing interval", tenant.billing.interval === "annual" ? "Annual" : "Monthly"],
                tenant.billing.trialEndsAt && tenant.status === "trial"
                  ? ["Trial ends", fmtDate(tenant.billing.trialEndsAt)]
                  : ["Next renewal", fmtDate(tenant.billing.renewalDate)],
                ["Add-ons", tenant.billing.addOns.length === 0 ? "None" : tenant.billing.addOns.map((a) => ADD_ON_LABELS[a]).join(", ")],
                ...(cancelled
                  ? ([["Cancelled on", fmtDate(tenant.billing.cancellationDate)], ["Reason", tenant.billing.cancellationReason ?? "—"]] as [string, string][])
                  : []),
              ]}
            />
          </div>
          <p id="billing-portal" className="mt-4 text-xs text-muted">
            Invoices, payment methods, and tax details open in the secure billing portal (Stripe) — Mirra never stores card numbers.
          </p>
        </Card>

        <div className="flex flex-col gap-4">
          {canManage && (cancelled || suspended) && (
            <Card title="Reactivate">
              <p className="mb-3 text-[13px] text-muted">
                Restore your subscription and bring your try-on page back online immediately.
              </p>
              <ActionButton
                variant="accent"
                size="md"
                onAction={reactivateAction}
                onDone={(m) => notice.setNotice(m ? { tone: "success", message: m } : null)}
              >
                Reactivate subscription
              </ActionButton>
              <p className="mt-2 text-xs text-muted">
                Your page comes back immediately. Billing stays &quot;past due&quot; until the
                payment provider confirms a successful charge — Mirra never marks an account paid on
                its own.
              </p>
            </Card>
          )}
          {canManage && !cancelled && <CancelCard impact={impact} />}
        </div>
      </div>

      <div className="mt-6">
        <Card title="Billing history">
          <ul className="space-y-2.5">
            {events.map((e) => (
              <li key={e.id} className="flex items-center justify-between gap-3 text-[13px]">
                <span className="text-stone-700">
                  <span className="font-medium text-ink">{e.type.replace(/_/g, " ")}</span> — {e.detail}
                </span>
                <span className="whitespace-nowrap text-xs text-muted">{fmtDateTime(e.at)}</span>
              </li>
            ))}
            {events.length === 0 && <li className="text-[13px] text-muted">No billing events yet.</li>}
          </ul>
        </Card>
      </div>
    </>
  );
}

/**
 * Cancellation, with the friction the action deserves.
 *
 * It takes a storefront offline and starts a deletion clock, so it states the
 * count of SKUs affected and the date data is erased, requires a reason, and
 * requires the word CANCEL to be typed. None of that is decoration: a single
 * misplaced click here used to do all of it.
 */
function CancelCard({ impact }: { impact: ReturnType<typeof cancellationImpact> }) {
  const { pending, notice, run, clear } = useAction();
  return (
    <Card title="Cancel subscription">
      <NoticeBar notice={notice} onDismiss={clear} />
      <form action={(formData: FormData) => run(() => requestCancellationAction(formData))} className="space-y-3">
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
          <strong className="block text-[13px]">What cancelling does, immediately:</strong>
          <ul className="mt-1 space-y-0.5">
            <li>
              · {impact.liveGarments} live garment{impact.liveGarments === 1 ? "" : "s"} and{" "}
              {impact.liveSkus} SKU{impact.liveSkus === 1 ? "" : "s"} stop being reachable by shoppers
            </li>
            <li>· {impact.seats} team seat{impact.seats === 1 ? "" : "s"} lose access</li>
            <li>
              · {impact.totalGarments} garment{impact.totalGarments === 1 ? "" : "s"} of ingestion
              work is kept until {fmtDate(impact.dataDeletedAfter)}, then permanently erased
            </li>
          </ul>
          <span className="mt-1.5 block">Reactivating before that date restores everything exactly.</span>
        </div>
        <Field label="Why are you leaving? (required)">
          <select name="reason" required className={inputClass}>
            <option value="">Choose a reason…</option>
            <option>Not enough shopper adoption</option>
            <option>Too expensive for current stage</option>
            <option>Missing features we need</option>
            <option>Switching provider</option>
            <option>Store is closing / rebranding</option>
            <option>Other</option>
          </select>
        </Field>
        <Field label="Type CANCEL to confirm">
          <input name="confirmation" required placeholder="CANCEL" className={`${inputClass} w-40`} />
        </Field>
        <SubmitButton variant="danger" pending={pending}>Cancel subscription</SubmitButton>
      </form>
    </Card>
  );
}
