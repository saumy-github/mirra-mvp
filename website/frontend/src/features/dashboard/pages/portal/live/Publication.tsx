import { useState } from "react";
import { Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useSession } from "../../../data/session";
import { liveCan } from "../../../data/live-session";
import { merchantApi, type MerchantGarment } from "../../../data/merchant-api";
import { stageMeta, useLiveGarments } from "../../../data/merchant-queries";
import { Badge, Banner, Card, EmptyState, PageHeader, Table, Td } from "../../../components/ui";
import { buttonClass } from "../../../components/styles";
import { dashPath } from "../../../routes";

const PUBLISHABLE = new Set(["ready", "live", "paused"]);

/** What shoppers can see, for a real workspace. Only QA-approved garments publish. */
export default function LivePublicationPage() {
  const session = useSession();
  const tenantId = session?.tenant?.id ?? "";
  const qc = useQueryClient();
  const garments = useLiveGarments(tenantId);
  const canPublish = liveCan(tenantId, "catalogue.publish");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const rows = garments.data ?? [];
  const publishable = rows.filter((g) => PUBLISHABLE.has(g.stage));
  const waiting = rows.filter((g) => !PUBLISHABLE.has(g.stage));
  const live = rows.filter((g) => g.stage === "live").length;

  const act = async (g: MerchantGarment, fn: () => Promise<MerchantGarment>) => {
    setBusy(g.garmentId);
    setError(null);
    try {
      await fn();
      await qc.invalidateQueries({ queryKey: ["merchant-garments", tenantId] });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      <PageHeader
        title="Publication"
        subtitle={`${live} live of ${rows.length}. A garment reaches shoppers only after Mirra QA approves it and you publish it — and only once its preview has rendered.`}
      />
      {error && (
        <div className="mb-4">
          <Banner tone="danger">{error}</Banner>
        </div>
      )}
      {garments.isLoading ? (
        <p className="text-[13px] text-muted">Loading…</p>
      ) : rows.length === 0 ? (
        <EmptyState
          icon="⇱"
          title="Nothing to publish yet"
          body="Add a garment and take it through QA first."
          action={<Link to={dashPath.garments} className={buttonClass("primary", "sm")}>Go to garments</Link>}
        />
      ) : (
        <div className="flex flex-col gap-5">
          {publishable.length > 0 ? (
            <Table caption="Approved garments" headers={["Garment", "Status", "Try-on", ""]}>
              {publishable.map((g) => {
                const stage = stageMeta(g.stage);
                const pending = busy === g.garmentId;
                return (
                  <tr key={g.garmentId}>
                    <Td>
                      <Link to={dashPath.digitiseGarment(g.garmentId, "review")} className="font-medium hover:text-accent">
                        {g.title}
                      </Link>
                      {g.draftAhead && (
                        <span className="block text-xs text-amber-700">
                          Edited since approval — shoppers still see revision {g.approved?.revision}
                        </span>
                      )}
                    </Td>
                    <Td>
                      <Badge tone={stage.tone}>{stage.label}</Badge>
                    </Td>
                    <Td>
                      <label className="flex items-center gap-2 text-xs">
                        <input
                          type="checkbox"
                          checked={g.publication.tryOnEnabled}
                          disabled={!canPublish || pending}
                          onChange={(e) =>
                            act(g, () =>
                              merchantApi.setPublication(tenantId, g.garmentId, g.publication.published, e.target.checked),
                            )
                          }
                        />
                        Enabled
                      </label>
                    </Td>
                    <Td className="text-right">
                      {canPublish &&
                        (g.stage === "live" ? (
                          <button
                            disabled={pending}
                            onClick={() => act(g, () => merchantApi.setPublication(tenantId, g.garmentId, false))}
                            className={buttonClass("secondary", "sm")}
                          >
                            Pause
                          </button>
                        ) : (
                          <button
                            disabled={pending}
                            onClick={() => act(g, () => merchantApi.setPublication(tenantId, g.garmentId, true))}
                            className={buttonClass("accent", "sm")}
                          >
                            {g.stage === "paused" ? "Resume" : "Publish"}
                          </button>
                        ))}
                    </Td>
                  </tr>
                );
              })}
            </Table>
          ) : (
            <Banner tone="info">No garment has passed QA yet, so nothing can be published.</Banner>
          )}

          {waiting.length > 0 && (
            <Card title="Not yet approved">
              <ul className="divide-y divide-stone-100 text-[13px]">
                {waiting.map((g) => {
                  const stage = stageMeta(g.stage);
                  return (
                    <li key={g.garmentId} className="flex items-center justify-between py-2">
                      <Link to={dashPath.digitiseGarment(g.garmentId)} className="hover:text-accent">
                        {g.title}
                      </Link>
                      <Badge tone={stage.tone}>{stage.label}</Badge>
                    </li>
                  );
                })}
              </ul>
            </Card>
          )}
          {!canPublish && <p className="text-xs text-muted">Only an owner or admin can publish.</p>}
        </div>
      )}
    </>
  );
}
