import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useDbVersion } from "../../data/store";
import { useSession } from "../../data/session";
import { getEntitlements } from "../../data/entitlements";
import { liveSkuBreakdown, liveSkuCount } from "../../data/publication";
import { garmentRows } from "../../data/queries";
import { launchImpact, runDueSchedulesAction, setTenantLaunchAction } from "../../data/actions";
import { can } from "../../data/rbac";
import {
  ActionButton,
  Badge,
  Banner,
  ButtonLink,
  Card,
  ConfirmAction,
  NoticeBar,
  PageHeader,
} from "../../components/ui";
import { useAction } from "../../components/use-action";
import { GarmentTable } from "../../components/catalogue-table";
import { CopyField } from "../../components/copy-field";
import { dashPath, publicUrl } from "../../routes";

export default function PublicationPage() {
  const session = useSession();
  useDbVersion();
  const [scheduled, setScheduled] = useState<string[]>([]);
  const notice = useAction();
  const tenantId = session?.tenant?.id;

  // Anything whose scheduled go-live has passed publishes when the merchant
  // opens this page. In production this is a job; the transition, the plan
  // check and the audit entry are identical either way.
  useEffect(() => {
    if (!tenantId) return;
    const published = runDueSchedulesAction(tenantId);
    if (published.length) setScheduled(published);
  }, [tenantId]);

  if (!session?.tenant) return null;
  const tenant = session.tenant;

  const ent = getEntitlements(tenant);
  const rows = garmentRows(tenant.id);
  const canManage = can(session.role, "publication.manage");
  const visible = rows.filter((r) => r.publiclyVisible);
  const usedSkus = liveSkuCount(tenant.id);
  const breakdown = liveSkuBreakdown(tenant.id);
  const impact = launchImpact(tenant.id);
  const staleDrafts = rows.filter((r) => r.draftAhead && r.stage === "live");

  return (
    <>
      <PageHeader
        title="Publication"
        subtitle="What shoppers can see, and why. Everything here resolves through the same rules the try-on page itself uses."
        action={
          <ButtonLink href={dashPath.preview(tenant.slug)} variant="primary" size="sm">
            👁 Preview your page
          </ButtonLink>
        }
      />

      <NoticeBar notice={notice.notice} onDismiss={notice.clear} />
      {scheduled.length > 0 && (
        <div className="mb-5">
          <Banner live tone="success">
            Scheduled go-live ran: <strong>{scheduled.join(", ")}</strong> {scheduled.length === 1 ? "is" : "are"} now live.
          </Banner>
        </div>
      )}

      {/* An edit made after QA does not reach shoppers. Saying so here is the
          difference between a safety property and a silent surprise. */}
      {staleDrafts.length > 0 && (
        <div className="mb-5">
          <Banner tone="warn">
            <strong>
              {staleDrafts.length} live garment{staleDrafts.length === 1 ? " has" : "s have"} edits
              QA hasn&apos;t approved.
            </strong>{" "}
            Shoppers keep seeing the approved version until the new one passes QA —{" "}
            {staleDrafts.slice(0, 3).map((r, i) => (
              <span key={r.id}>
                {i > 0 && ", "}
                <Link to={dashPath.garment(r.id)} className="font-semibold underline">{r.title}</Link>
              </span>
            ))}
            {staleDrafts.length > 3 && ` and ${staleDrafts.length - 3} more`}.
          </Banner>
        </div>
      )}

      <div className="mb-6">
        <Card title="Try-on page">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[15px] font-semibold">{tenant.domain.subdomain}</span>
                {ent.publicSurfaceEnabled ? <Badge tone="success">Serving shoppers</Badge> : <Badge tone="danger">Offline</Badge>}
              </div>
              <p className="mt-1.5 text-[13px] text-muted">
                {visible.length} garment{visible.length === 1 ? "" : "s"} reaching shoppers ·{" "}
                <strong className="text-ink">{usedSkus} of {ent.skuLimit} live SKUs</strong> used.
                {!ent.publicSurfaceEnabled && ` ${ent.publicSurfaceDisabledReason}`}
              </p>
            </div>
            {canManage && tenant.status !== "suspended" && tenant.status !== "cancelled" && (
              <div className="flex gap-2">
                {tenant.launchStatus === "live" ? (
                  // Taking a storefront offline is not a one-click action.
                  <ConfirmAction
                    label="Pause entire page"
                    title="Pause the whole try-on page?"
                    impact={
                      <>
                        {impact.liveGarments} live garment{impact.liveGarments === 1 ? "" : "s"} and{" "}
                        {impact.liveSkus} SKU{impact.liveSkus === 1 ? "" : "s"} stop being reachable
                        immediately. Shoppers on {tenant.domain.subdomain} are redirected to{" "}
                        {tenant.storeUrl}. Nothing is deleted and resuming restores it exactly.
                      </>
                    }
                    confirmWord="PAUSE"
                    onConfirm={() => setTenantLaunchAction("paused")}
                  />
                ) : (
                  <ActionButton
                    variant="accent"
                    onAction={() => setTenantLaunchAction("live")}
                    onDone={(m) => notice.setNotice(m ? { tone: "success", message: m } : null)}
                  >
                    {tenant.launchStatus === "preview" ? "Go live" : "Resume page"}
                  </ActionButton>
                )}
              </div>
            )}
          </div>
          {tenant.launchStatus === "preview" && (
            <div className="mt-4">
              <Banner tone="info">
                Your page is in <strong>preview</strong> — only people with your preview link can see
                it. Go live when you&apos;re ready for shoppers.
              </Banner>
            </div>
          )}

          {/* Both links resolve to a real surface: the tenant page and a
              token-scoped preview that renders the exact same catalogue the
              storefront contract produces, plus what isn't published yet. */}
          <div className="mt-5 grid grid-cols-2 gap-4 border-t border-line pt-5 max-md:grid-cols-1">
            <CopyField label="Your try-on page" value={publicUrl.tenant(tenant.domain.subdomain)} />
            <CopyField
              label="Preview link (includes unpublished content)"
              value={publicUrl.preview(tenant.slug, tenant.previewToken)}
            />
          </div>
          <p className="mt-3 text-xs text-muted">
            The preview link opens the same resolved catalogue as the live page, plus anything
            QA-approved but not yet published, clearly marked. Offline, your public address
            redirects to {tenant.storeUrl}.{" "}
            <Link to={dashPath.settings} className="font-medium text-accent hover:underline">
              Domains and appearance →
            </Link>
          </p>
        </Card>
      </div>

      {/* Plan usage, drilled down. "Live SKUs" is the billable unit, so it has
          to be traceable to the garments consuming it. */}
      {breakdown.length > 0 && (
        <div className="mb-6">
          <Card
            title="What's using your SKU allowance"
            action={
              <Badge tone={usedSkus > ent.skuLimit * 0.9 ? "warn" : "neutral"}>
                {usedSkus} / {ent.skuLimit}
              </Badge>
            }
          >
            <ul className="divide-y divide-stone-100">
              {breakdown.slice(0, 8).map((b) => (
                <li key={b.garmentId} className="flex items-center justify-between gap-3 py-2 text-[13px]">
                  <Link to={dashPath.garment(b.garmentId)} className="font-medium text-ink hover:text-accent">
                    {b.title}
                  </Link>
                  <span className="tabular-nums text-muted">{b.skus} SKUs</span>
                </li>
              ))}
            </ul>
            {breakdown.length > 8 && (
              <p className="mt-2 text-xs text-muted">
                …and {breakdown.length - 8} more garments.
              </p>
            )}
          </Card>
        </div>
      )}

      <h2 className="mb-3 text-[15px] font-semibold">Per-garment publication</h2>
      <GarmentTable rows={rows} mode="publication" canManage={canManage} bulkAllowed={ent.bulkPublishing} />
      <p className="mt-3 text-xs text-muted">
        Publishing requires complete imagery, size chart, fabric data, and a passed QA check.
        {ent.scheduledGoLive
          ? " Schedule a go-live from any QA-passed garment's page."
          : " Scheduled go-lives are available on the Atelier plan."}
      </p>
    </>
  );
}
