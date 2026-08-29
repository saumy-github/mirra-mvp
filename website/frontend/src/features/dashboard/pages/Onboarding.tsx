import { Link, Navigate, useNavigate } from "react-router-dom";
import { useDbVersion, getDb } from "../data/store";
import { useSession } from "../data/session";
import {
  AGREEMENT,
  completeOnboardingStepAction,
  reopenOnboardingStepAction,
  signOutAction,
} from "../data/actions";
import { fmtDateTime, money } from "../data/util";
import { MirraLogo } from "../components/shell";
import {
  ActionButton,
  Badge,
  Banner,
  Field,
  NoticeBar,
  Progress,
  SubmitButton,
  ButtonLink,
} from "../components/ui";
import { useAction } from "../components/use-action";
import { inputClass } from "../components/styles";
import { dashPath } from "../routes";
import type { OnboardingState, Tenant } from "../data/types";

interface StepDef {
  key: string;
  title: string;
  done: (o: OnboardingState) => boolean;
}

const STEPS: StepDef[] = [
  { key: "store", title: "Verify your store", done: (o) => o.storeVerified && o.storeUrlConfirmed },
  { key: "shopify", title: "Connect Shopify", done: (o) => o.shopifyConnected },
  { key: "team", title: "Invite your team", done: (o) => o.teamInvited },
  { key: "plan", title: "Choose your plan", done: (o) => o.planChosen },
  { key: "terms", title: "Accept terms", done: (o) => o.termsAccepted },
  { key: "billing", title: "Billing details", done: (o) => o.billingEntered },
  { key: "activate", title: "Activate subscription", done: (o) => o.activated },
  { key: "checklist", title: "Launch checklist", done: (o) => o.checklistReviewed },
];

export default function DashboardOnboarding() {
  const session = useSession();
  const navigate = useNavigate();
  useDbVersion();

  if (!session) return <Navigate to={dashPath.login} replace />;
  const tenant = session.tenant;
  if (!tenant) return <Navigate to={dashPath.login} replace />;

  const o = tenant.onboarding;
  const doneCount = STEPS.filter((s) => s.done(o)).length;
  const current = STEPS.find((s) => !s.done(o));

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <MirraLogo sub="Onboarding" />
        <div className="flex items-center gap-2">
          {o.activated && <ButtonLink href={dashPath.portal} size="sm">Go to dashboard →</ButtonLink>}
          {/* Both of these were missing, so an account that got stuck here had
              no way to reach help and no way to sign out of it. */}
          <a href={`mailto:onboarding@mirra.com?subject=${encodeURIComponent(`Onboarding help — ${tenant.name}`)}`} className="text-xs font-medium text-accent hover:underline">
            Email onboarding support
          </a>
          <form action={() => navigate(signOutAction())}>
            <button className="cursor-pointer text-xs font-medium text-muted hover:text-ink">
              Sign out
            </button>
          </form>
        </div>
      </div>

      <div className="mt-10">
        <h1 className="text-2xl font-semibold tracking-tight">Welcome, {tenant.name}</h1>
        <p className="mt-2 text-[14px] text-muted">
          {tenant.salesLed
            ? "Your Mirra account manager has prepared this workspace for you. Work through the steps below — we're on hand at every stage."
            : "Set up your try-on workspace in a few guided steps. You can leave and come back anytime."}
        </p>
        <div className="mt-5 flex items-center gap-3">
          <Progress value={doneCount} max={STEPS.length} />
          <span className="whitespace-nowrap text-xs font-medium text-muted">{doneCount} of {STEPS.length}</span>
        </div>
      </div>

      <ol className="mt-8 space-y-3">
        {STEPS.map((step, i) => {
          const done = step.done(o);
          const active = current?.key === step.key;
          return (
            <li
              key={step.key}
              className={`rounded-xl border bg-surface ${active ? "border-accent ring-2 ring-indigo-100" : "border-line"}`}
            >
              <div className="flex items-center gap-3 px-5 py-4">
                <span
                  className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold ${
                    done ? "bg-emerald-100 text-emerald-700" : active ? "bg-accent text-white" : "bg-stone-100 text-muted"
                  }`}
                >
                  {done ? "✓" : i + 1}
                </span>
                <span className={`text-[14px] font-medium ${done ? "text-muted line-through decoration-stone-300" : "text-ink"}`}>
                  {step.title}
                </span>
                {active && <Badge tone="info">Current step</Badge>}
                {/* A wrong store URL used to be unfixable without support. */}
                {done && step.key !== "activate" && (
                  <span className="ml-auto">
                    <ActionButton variant="ghost" onAction={() => reopenOnboardingStepAction(step.key)}>
                      Change
                    </ActionButton>
                  </span>
                )}
              </div>
              {active && (
                <div className="border-t border-line px-5 py-5">
                  <StepBody step={step.key} tenant={tenant} />
                </div>
              )}
            </li>
          );
        })}
      </ol>

      {tenant.agreement && (
        <p className="mt-6 text-center text-xs text-muted">
          Agreement {tenant.agreement.documentVersion} accepted by {tenant.agreement.acceptedByName}{" "}
          on {fmtDateTime(tenant.agreement.acceptedAt)}.
        </p>
      )}

      {o.activated && o.checklistReviewed && (
        <div className="mt-8">
          <Banner tone="success">
            🎉 You&apos;re all set. Your try-on page is provisioned at{" "}
            <strong>{tenant.domain.subdomain}</strong>. Head to your{" "}
            <Link to={dashPath.portal} className="font-semibold underline">dashboard</Link> to publish your first garments.
          </Banner>
        </div>
      )}

      <p className="mt-10 text-center text-xs text-muted">
        Stuck? <Link to={dashPath.support} className="font-medium text-accent hover:underline">Contact support</Link> — onboarding help is free on every plan.
      </p>
    </main>
  );
}

function StepBody({ step, tenant }: { step: string; tenant: Tenant }) {
  const { notice, run, clear } = useAction();
  // Every step reports what happened. Store verification in particular can now
  // fail, and a form that can fail has to be able to say so.
  const action = (formData: FormData) => run(() => completeOnboardingStepAction(step, formData));
  return (
    <>
      <NoticeBar notice={notice} onDismiss={clear} />
      <StepForm step={step} tenant={tenant} action={action} />
    </>
  );
}

function StepForm({
  step,
  tenant,
  action,
}: {
  step: string;
  tenant: Tenant;
  action: (formData: FormData) => void;
}) {
  switch (step) {
    case "store":
      return (
        <form action={action} className="space-y-4">
          <p className="text-[13px] text-muted">
            Confirm the storefront customers will reach from your try-on page. We verify ownership
            via your Shopify connection (or a DNS record for non-standard setups).
          </p>
          <Field label="Store URL">
            <input name="storeUrl" type="url" defaultValue={tenant.storeUrl} required className={inputClass} />
          </Field>
          <SubmitButton>Verify &amp; confirm store</SubmitButton>
        </form>
      );
    case "shopify":
      return (
        <form action={action} className="space-y-4">
          <p className="text-[13px] text-muted">
            Install the Mirra app from the Shopify App Store and authorise product sync. We import
            products, variants, images, and metadata — read-only, revocable anytime.
          </p>
          <div className="rounded-lg border border-line bg-stone-50 px-4 py-3 text-[13px]">
            🛍 <strong>Mirra Try-On</strong> requests: <code className="text-xs">read_products</code>,{" "}
            <code className="text-xs">read_product_listings</code>
          </div>
          <SubmitButton>Connect Shopify &amp; run first sync</SubmitButton>
        </form>
      );
    case "team":
      return (
        <form action={action} className="space-y-4">
          <p className="text-[13px] text-muted">
            Invite the people who&apos;ll manage your catalogue and billing. You can add more later under
            Team &amp; permissions.
          </p>
          {/* These inputs had no `name`, so everything typed was discarded on
              submit while the button said "Send invites". Invitation delivery
              is backend work; until then the step doesn't pretend. */}
          <div className="rounded-lg border border-line bg-stone-50 px-4 py-3 text-[13px] text-stone-700">
            Invitations aren&apos;t available in this environment yet. Your workspace is created
            with you as the owner — we&apos;ll add your merchandising and finance colleagues for
            you, and you can manage seats under Team &amp; permissions once invites ship.
          </div>
          <SubmitButton>Continue</SubmitButton>
        </form>
      );
    case "plan":
      return <PlanStep action={action} tenant={tenant} />;
    case "terms":
      return (
        <form action={action} className="space-y-4">
          {/* An acceptance record has to name the documents and their version,
              or it proves nothing about what was agreed. */}
          <p className="text-[13px] text-muted">
            Version <strong className="text-ink">{AGREEMENT.version}</strong>. Read the full
            documents before accepting:
          </p>
          <ul className="space-y-1">
            {AGREEMENT.documents.map((d) => (
              <li key={d.href}>
                <a
                  href={d.href}
                  target="_blank"
                  rel="noreferrer"
                  className="text-[13px] font-medium text-accent hover:underline"
                >
                  {d.title} ↗
                </a>
              </li>
            ))}
          </ul>
          <div className="max-h-36 overflow-y-auto rounded-lg border border-line bg-stone-50 p-4 text-xs leading-relaxed text-stone-600">
            <strong>Summary — not the agreement itself.</strong> Mirra provides hosted virtual
            try-on services for your product catalogue. You retain all rights to your product data
            and imagery. Mirra processes shopper interactions in aggregate for analytics; no shopper
            biometric data is retained after a session. Fees are billed per your selected plan.
            Either party may terminate per the cancellation terms; your data is preserved for 60
            days after cancellation.
          </div>
          <label className="flex items-start gap-2 text-[13px]">
            <input type="checkbox" required className="mt-1" /> I have read and accept version{" "}
            {AGREEMENT.version} of the Services Agreement and Data Processing Addendum on behalf of{" "}
            {tenant.name}. My name and the time of acceptance will be recorded.
          </label>
          <SubmitButton>Accept &amp; continue</SubmitButton>
        </form>
      );
    case "billing":
      return (
        <form action={action} className="space-y-4">
          {/* Deliberately no card fields. The prototype rendered card number
              and CVC inputs that went nowhere — a form that looks like it
              takes payment details but doesn't is the one kind of mock worth
              refusing to build. Real card entry happens on the provider's
              hosted page, which is where those fields belong. */}
          <p className="text-[13px] text-muted">
            Payment is handled entirely by our payment provider on their own hosted page — Mirra
            never sees or stores card numbers. In this environment no payment is taken and no
            card details are collected.
          </p>
          <div className="rounded-lg border border-line bg-stone-50 px-4 py-3 text-[13px]">
            🔒 You&apos;ll be redirected to our provider to add a payment method when this step
            goes live.
          </div>
          <SubmitButton>Continue without payment (demo)</SubmitButton>
        </form>
      );
    case "activate":
      return (
        <form action={action} className="space-y-4">
          <p className="text-[13px] text-muted">
            Activating starts your {tenant.billing.interval} subscription
            {" "}(trial first where your plan includes one) and provisions your public try-on page:
          </p>
          <div className="rounded-lg border border-line bg-stone-50 px-4 py-3 text-[13px]">
            🌐 <strong>{tenant.domain.subdomain}</strong> — reserved for you
          </div>
          <SubmitButton variant="accent">Activate subscription</SubmitButton>
        </form>
      );
    case "checklist":
      return <ChecklistStep />;
    default:
      return null;
  }
}

function PlanStep({ action, tenant }: { action: (fd: FormData) => void; tenant: Tenant }) {
  const plans = getDb().plans.filter((p) => p.id !== "enterprise");
  return (
    <form action={action} className="space-y-4">
      <div className="grid grid-cols-3 gap-3 max-md:grid-cols-1">
        {plans.map((p) => (
          <label
            key={p.id}
            className="cursor-pointer rounded-xl border border-line p-4 transition-colors hover:border-accent has-checked:border-accent has-checked:ring-2 has-checked:ring-indigo-100"
          >
            <input
              type="radio"
              name="planId"
              value={p.id}
              defaultChecked={p.id === tenant.billing.planId}
              className="sr-only"
            />
            <div className="text-[14px] font-semibold">{p.name}</div>
            <div className="mt-1 text-lg font-semibold">
              {money(p.monthlyUsd)}<span className="text-xs font-normal text-muted">{p.monthlyUsd ? "/mo" : ""}</span>
            </div>
            <div className="mt-1 text-xs text-muted">{p.skuLimit} live SKUs · {p.supportTier} support</div>
          </label>
        ))}
      </div>
      <label className="flex items-center gap-2 text-[13px]">
        <input type="radio" name="interval" value="monthly" defaultChecked /> Monthly
      </label>
      <label className="flex items-center gap-2 text-[13px]">
        <input type="radio" name="interval" value="annual" /> Annual <Badge tone="success">2 months free</Badge>
      </label>
      <p className="text-xs text-muted">
        Need enterprise volume, SSO, or a custom contract?{" "}
        <Link to="/pricing" className="font-medium text-accent">Talk to sales</Link>.
      </p>
      <SubmitButton>Choose plan</SubmitButton>
    </form>
  );
}

/**
 * The last step actually finishes: it marks the checklist reviewed *and*
 * navigates. A button reading "take me to the dashboard" that left you on the
 * onboarding page was the last thing a new merchant saw.
 */
function ChecklistStep() {
  const navigate = useNavigate();
  const { pending, notice, run, clear } = useAction();
  return (
    <div className="space-y-4">
      <NoticeBar notice={notice} onDismiss={clear} />
      <ul className="space-y-2 text-[13px] text-stone-700">
        <li>✓ Subscription active — entitlements applied</li>
        <li>✓ Public subdomain provisioned</li>
        <li>→ Enrich garments with size &amp; fabric data (the dashboard shows what&apos;s missing)</li>
        <li>→ Submit garments to QA, then publish</li>
        <li>→ Preview your page before going live</li>
      </ul>
      <button
        disabled={pending}
        onClick={() =>
          run(
            () => completeOnboardingStepAction("checklist", new FormData()),
            () => navigate(dashPath.portal),
          )
        }
        className="inline-flex cursor-pointer items-center rounded-lg border border-transparent bg-accent px-3.5 py-1.5 text-[13px] font-medium text-white hover:bg-indigo-700 disabled:opacity-40"
      >
        {pending ? "Finishing…" : "Finish — take me to the dashboard"}
      </button>
    </div>
  );
}
