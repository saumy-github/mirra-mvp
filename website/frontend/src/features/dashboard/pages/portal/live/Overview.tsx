import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "../../../data/session";
import { liveCan } from "../../../data/live-session";
import { merchantApi } from "../../../data/merchant-api";
import { useLiveGarments, useLiveProducts } from "../../../data/merchant-queries";
import { Banner, ButtonLink, Card, KeyValue, PageHeader, StatTile } from "../../../components/ui";
import { dashPath } from "../../../routes";

/** Overview for a real workspace — every number here comes from the merchant API. */
export default function LiveOverviewPage() {
  const session = useSession();
  const tenantId = session?.tenant?.id ?? "";
  const garments = useLiveGarments(tenantId);
  const products = useLiveProducts(tenantId);
  const workspace = useQuery({
    queryKey: ["merchant-workspace", tenantId],
    queryFn: () => merchantApi.getWorkspace(tenantId),
  });

  const rows = garments.data ?? [];
  const count = (...stages: string[]) => rows.filter((g) => stages.includes(g.stage)).length;
  const needsData = count("needs_data");
  const changes = count("qa_changes");
  const inQa = count("in_qa");
  const toPublish = count("ready", "paused");
  const live = count("live");
  const canEdit = liveCan(tenantId, "catalogue.edit");
  const canQa = liveCan(tenantId, "qa.review");

  const todo: { label: string; href: string }[] = [];
  if (changes) todo.push({ label: `QA asked for changes on ${changes} garment${changes > 1 ? "s" : ""}`, href: dashPath.garments });
  if (needsData) todo.push({ label: `${needsData} garment${needsData > 1 ? "s need" : " needs"} data`, href: dashPath.garments });
  if (inQa && canQa) todo.push({ label: `${inQa} garment${inQa > 1 ? "s" : ""} waiting for QA`, href: dashPath.garments });
  if (toPublish) todo.push({ label: `${toPublish} approved garment${toPublish > 1 ? "s" : ""} not live`, href: dashPath.publication });
  const shopify = workspace.data?.shopify;
  if (workspace.data && !shopify?.connected)
    todo.push({ label: "Connect your Shopify store", href: dashPath.settings });

  return (
    <>
      <PageHeader
        title="Overview"
        subtitle={`${session?.tenant?.name ?? "Your workspace"} at a glance.`}
        action={
          canEdit ? (
            <ButtonLink href={dashPath.digitise} variant="primary" size="sm">
              + Add garment
            </ButtonLink>
          ) : undefined
        }
      />
      {garments.isError && (
        <div className="mb-4">
          <Banner tone="danger">Could not reach Mirra: {(garments.error as Error).message}</Banner>
        </div>
      )}
      <div className="mb-5 grid grid-cols-4 gap-4 max-lg:grid-cols-2">
        <StatTile label="Products" value={String(products.data?.length ?? "—")} />
        <StatTile label="Garments" value={String(garments.data ? rows.length : "—")} />
        <StatTile label="With QA" value={String(garments.data ? inQa : "—")} />
        <StatTile label="Live" value={String(garments.data ? live : "—")} />
      </div>
      <div className="grid grid-cols-2 gap-5 max-lg:grid-cols-1">
        <Card title="Next up">
          {todo.length === 0 ? (
            <p className="text-[13px] text-muted">
              {rows.length === 0 ? (
                <>
                  Nothing yet. <Link to={dashPath.digitise} className="text-accent hover:underline">Add your first garment</Link>.
                </>
              ) : (
                "Nothing needs you right now."
              )}
            </p>
          ) : (
            <ul className="space-y-2 text-[13px]">
              {todo.map((t) => (
                <li key={t.label}>
                  <Link to={t.href} className="font-medium text-accent hover:underline">
                    {t.label} →
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Store">
          <KeyValue
            rows={[
              ["Shopify", shopify ? (shopify.connected ? shopify.storeDomain : "Not connected") : "—"],
              ["Last sync", shopify?.lastSyncAt ? new Date(shopify.lastSyncAt).toLocaleString() : "—"],
              ["Workspace status", workspace.data?.status ?? "—"],
            ]}
          />
        </Card>
      </div>
    </>
  );
}
