import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useDbVersion, getDb } from "../../data/store";
import { useSession } from "../../data/session";
import {
  resolveQaFindingAction,
  scheduleGoLiveAction,
  setSoldOutPolicyAction,
  setGarmentStageAction,
  submitForMerchantReviewAction,
  updateGarmentAction,
} from "../../data/actions";
import { getEntitlements } from "../../data/entitlements";
import { resolveGarment } from "../../data/publication";
import { assetIsCurrent, revisionNotice, revisionState } from "../../data/revisions";
import { QaPanel } from "../../components/qa-panel";
import {
  MEASUREMENT_FIELDS,
  SIZE_SOURCE_LABELS,
  SOLD_OUT_POLICY_LABELS,
  STAGE_META,
  completionCount,
  inventoryFor,
  soldOutPolicyFor,
} from "../../data/ingestion";
import { can } from "../../data/rbac";
import { fmtDateTime } from "../../data/util";
import {
  ActionButton,
  Badge,
  Banner,
  ButtonLink,
  Card,
  ConfirmAction,
  EmptyState,
  Field,
  KeyValue,
  NoticeBar,
  PageHeader,
  SubmitButton,
} from "../../components/ui";
import { useAction } from "../../components/use-action";
import { buttonClass, inputClass } from "../../components/styles";
import { StageBadge, TryOnToggle } from "../../components/catalogue-table";
import { CopyField } from "../../components/copy-field";
import { CAPTURE_VIEWS } from "../../data/types";
import type { Garment, SoldOutPolicy } from "../../data/types";
import { dashPath, publicUrl } from "../../routes";

/**
 * The garment summary — everything about one garment, read at a glance.
 *
 * Setup work happens in the flow at `/garments/:id/setup`, not here. Mixing
 * the two produced a page that was neither: a summary interrupted by forms,
 * and a form that had lost its sense of progress. This page answers "what is
 * the state of this garment", and hands off to the flow to change it.
 */
export default function GarmentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const session = useSession();
  const soldOut = useAction();
  useDbVersion();
  if (!session?.tenant) return null;
  const tenant = session.tenant;

  const db = getDb();
  const g = db.garments.find((x) => x.id === id && x.tenantId === tenant.id);
  if (!g) {
    return (
      <EmptyState
        icon="👗"
        title="Garment not found"
        body="It may belong to another workspace, or have been removed."
        action={<ButtonLink href={dashPath.garments} size="sm">Back to garments</ButtonLink>}
      />
    );
  }

  const product = db.products.find((p) => p.id === g.productId);
  const { done, total, reqs } = completionCount(g, product);
  const inventory = inventoryFor(g, product);
  const fields = MEASUREMENT_FIELDS[g.category];
  const canEdit = can(session.role, "catalogue.edit");
  const canPublish = can(session.role, "publication.manage");
  const variants = product?.variants.filter((v) => g.variantIds.includes(v.id)) ?? [];
  const resolved = resolveGarment(g, tenant, product);
  const revNotice = revisionNotice(g);
  const openFindings = g.qaFindings.filter((f) => !f.resolvedAt);
  const ent = getEntitlements(tenant);

  return (
    <>
      <div className="mb-1 text-xs text-muted">
        <Link to={dashPath.garments} className="hover:text-ink">Garments</Link> / {g.title}
      </div>

      <PageHeader
        title={g.title}
        subtitle={
          <span className="flex flex-wrap items-center gap-2">
            <StageBadge stage={g.stage} />
            <span>{STAGE_META[g.stage].help}</span>
            {g.referenceSize && <span>· Reference sample: Size {g.referenceSize}</span>}
            {g.stage === "live" && (
              <span className="flex items-center gap-1.5 text-xs text-muted">
                Try-on{" "}
                {canPublish ? (
                  <TryOnToggle garmentId={g.id} enabled={g.tryOnEnabled} />
                ) : g.tryOnEnabled ? "on" : "off"}
              </span>
            )}
          </span>
        }
        action={
          <div className="flex flex-wrap items-start gap-2">
            {done < total && (
              <ButtonLink href={dashPath.garmentFlow(g.id)} variant="primary" size="sm">
                Continue setup →
              </ButtonLink>
            )}
            {/* `needs_data → merchant_review` is the rung that was missing: a
                complete garment had no route to QA at all. */}
            {canEdit && g.stage === "needs_data" && done === total && (
              <ActionButton variant="primary" onAction={() => submitForMerchantReviewAction(g.id)}>
                I&apos;m ready to review it
              </ActionButton>
            )}
            {canPublish && g.stage === "merchant_review" && (
              <ActionButton variant="primary" onAction={() => setGarmentStageAction(g.id, "in_qa")}>
                Send to Mirra QA
              </ActionButton>
            )}
            {canPublish && g.stage === "ready" && (
              <ActionButton variant="accent" onAction={() => setGarmentStageAction(g.id, "live")}>
                Publish
              </ActionButton>
            )}
            {canPublish && g.stage === "live" && (
              // Pausing removes a product from a live storefront; the click
              // says how many SKUs that is before it happens.
              <ConfirmAction
                label="Pause"
                title={`Hide ${g.title} from shoppers?`}
                impact={
                  <>
                    {resolved.variants.filter((v) => v.tryOnEligible).length} SKU
                    {resolved.variants.filter((v) => v.tryOnEligible).length === 1 ? "" : "s"} stop
                    being try-on eligible immediately. Its QA approval is kept, so resuming is one
                    click and needs no re-review.
                  </>
                }
                onConfirm={() => setGarmentStageAction(g.id, "paused")}
              />
            )}
            {canPublish && g.stage === "paused" && (
              <ActionButton variant="accent" onAction={() => setGarmentStageAction(g.id, "live")}>
                Resume
              </ActionButton>
            )}
          </div>
        }
      />

      {/* What a shopper actually gets, from the same resolver the storefront
          contract uses — not a restatement of the stage. */}
      <div className="mb-5">
        <Banner tone={resolved.visible ? "success" : "neutral"}>
          {resolved.visible ? (
            <>
              <strong>Live to shoppers</strong> — serving approved revision{" "}
              {resolved.servedRevision}, {resolved.variants.filter((v) => v.tryOnEligible).length} of{" "}
              {resolved.variants.length} sizes eligible.
            </>
          ) : (
            <>
              <strong>Not reaching shoppers.</strong> {resolved.blockedDetail}
            </>
          )}
        </Banner>
      </div>

      {revNotice && (
        <div className="mb-5">
          <Banner tone={revNotice.tone}>
            <strong>{revNotice.headline}</strong> {revNotice.detail}
          </Banner>
        </div>
      )}

      {openFindings.length > 0 && (
        <div className="mb-5">
          <Card title={`QA sent this back — ${openFindings.length} to fix`}>
            <ul className="space-y-3">
              {openFindings.map((f) => (
                <li key={f.id} className="text-[13px]">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={f.severity === "blocker" ? "danger" : "warn"}>
                      {f.severity === "blocker" ? "Blocker" : "Advisory"}
                    </Badge>
                    <span className="font-medium text-ink capitalize">{f.area}</span>
                    {f.view && <span className="text-xs text-muted">{f.view} view</span>}
                    {f.measurementKey && <span className="text-xs text-muted">{f.measurementKey}</span>}
                    <span className="text-xs text-muted">· revision {f.revision}</span>
                  </div>
                  <p className="mt-1 text-stone-700">{f.detail}</p>
                  <p className="mt-0.5 text-xs text-muted">
                    <strong className="text-stone-700">What to do:</strong> {f.instruction}
                  </p>
                  {canEdit && (
                    <div className="mt-1.5 flex gap-2">
                      <Link
                        to={dashPath.garmentFlow(
                          g.id,
                          f.area === "capture" ? "capture" : f.area === "material" ? "material" : "sizing",
                        )}
                        className="text-xs font-medium text-accent hover:underline"
                      >
                        Fix it →
                      </Link>
                      <ActionButton
                        variant="ghost"
                        onAction={() => resolveQaFindingAction(g.id, f.id)}
                      >
                        Mark as done
                      </ActionButton>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </Card>
        </div>
      )}

      {done < total && (
        <div className="mb-5">
          <Banner tone="warn">
            <strong>{done} of {total} complete.</strong>{" "}
            {reqs.filter((r) => !r.complete).map((r) => r.label).join(" · ")} outstanding.{" "}
            <Link to={dashPath.garmentFlow(g.id)} className="font-semibold underline">
              Continue setup →
            </Link>
          </Banner>
        </div>
      )}

      {session.isInternal && g.stage === "in_qa" && (
        <div className="mb-5">
          <QaPanel garment={g} />
        </div>
      )}

      <div className="grid grid-cols-3 gap-4 max-lg:grid-cols-1">
        <div className="col-span-2 flex flex-col gap-4 max-lg:col-span-1">
          <Card
            title="Capture set"
            action={
              <Link to={dashPath.garmentFlow(g.id, "capture")} className="text-xs font-medium text-accent hover:underline">
                Manage capture →
              </Link>
            }
          >
            <div className="grid grid-cols-4 gap-3 max-md:grid-cols-2">
              {CAPTURE_VIEWS.map((view) => {
                const has = g.capture.accepted.includes(view);
                const issue = g.capture.issues.find((i) => i.view === view);
                return (
                  <div
                    key={view}
                    className={`flex aspect-[3/4] flex-col items-center justify-center gap-1 rounded-xl border text-center ${
                      has ? "border-line bg-stone-50" : "border-dashed border-amber-300 bg-amber-50/40"
                    }`}
                  >
                    <span className="text-2xl" aria-hidden>{has ? product?.imageEmoji : "＋"}</span>
                    <span className="text-xs font-medium capitalize text-stone-600">{view}</span>
                    <span className="text-[11px] text-muted">{has ? "Accepted" : issue ? "Retake" : "Needed"}</span>
                  </div>
                );
              })}
            </div>
            {g.capture.issues.length > 0 && (
              <p className="mt-3 text-xs text-red-700">{g.capture.issues[0].message}</p>
            )}
            <p className="mt-3 text-xs text-muted">
              Optional details: {g.capture.details.length}
              {g.capture.details.length > 0 && ` · ${g.capture.details.map((d) => d.label).join(", ")}`}
            </p>
          </Card>

          {canEdit ? (
            <GarmentDataForm garment={g} />
          ) : (
            <Card title="Garment data">
              <KeyValue
                rows={[
                  ["Category", <span key="c" className="capitalize">{g.category}</span>],
                  ["Fit notes", g.fitNotes || "—"],
                  ["Fabric", g.fabricComposition.map((f) => `${f.pct}% ${f.material}`).join(", ") || "—"],
                ]}
              />
            </Card>
          )}

          <Card
            title={
              g.sizeChart.length > 0
                ? `Size chart (cm) — ${g.sizeSource ? SIZE_SOURCE_LABELS[g.sizeSource] : "unknown source"}`
                : "Size chart"
            }
            action={
              <Link to={dashPath.garmentFlow(g.id, "sizing")} className="text-xs font-medium text-accent hover:underline">
                {g.sizeChart.length > 0 ? "Edit sizing →" : "Add sizing →"}
              </Link>
            }
          >
            {g.sizeChart.length === 0 ? (
              <p className="text-[13px] text-muted">
                No sizing yet. Import a chart, use your brand chart, or measure the reference sample.
              </p>
            ) : (
              <>
                {g.gradingUnverified && (
                  <div className="mb-3">
                    <Banner tone="warn">
                      <strong>Draft sizes.</strong> Derived from one sample, not measured or supplied.
                    </Banner>
                  </div>
                )}
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-[13px]">
                    <caption className="sr-only">Measurements per size in centimetres</caption>
                    <thead>
                      <tr className="text-xs text-muted">
                        <th scope="col" className="py-1.5 pr-4 font-medium">Size</th>
                        {fields.map((f) => (
                          <th key={f.key} scope="col" className="py-1.5 pr-4 font-medium" title={f.how}>{f.label}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-stone-100">
                      {g.sizeChart.map((r) => (
                        <tr key={r.size}>
                          <td className="py-2 pr-4 font-medium">
                            {r.size}
                            {r.size === g.referenceSize && (
                              <span className="ml-1.5 text-[11px] text-muted">reference</span>
                            )}
                          </td>
                          {fields.map((f) => (
                            <td key={f.key} className="py-2 pr-4 tabular-nums">{r.values[f.key] ?? "—"}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </Card>
        </div>

        <aside className="flex flex-col gap-4">
          <Card title="Progress">
            <div className="mb-2 text-[13px] font-medium text-ink">{done} of {total} complete</div>
            <ul className="space-y-1.5">
              {reqs.map((r) => (
                <li key={r.key} className="flex items-start gap-2 text-xs">
                  <span className={r.complete ? "text-emerald-600" : "text-amber-600"} aria-hidden>
                    {r.complete ? "✓" : "•"}
                  </span>
                  <span>
                    <span className={r.complete ? "text-stone-500" : "font-medium text-ink"}>{r.label}</span>
                    <span className="block text-muted">{r.detail}</span>
                  </span>
                </li>
              ))}
            </ul>
          </Card>

          <Card title="Shopify mapping">
            <p className="mb-2 text-[13px]">
              {variants.length} of {inventory.total || variants.length} variants matched automatically
            </p>
            <ul className="space-y-2">
              {variants.map((v) => (
                <li key={v.id} className="flex items-center justify-between text-[13px]">
                  <span className="font-mono text-xs text-stone-600">{v.sku}</span>
                  <span className="text-muted">
                    {v.size} ·{" "}
                    {v.inventory > 0 ? (
                      <span className="text-stone-600">{v.inventory} available</span>
                    ) : (
                      <span className="text-amber-800">Sold out</span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
            <div className="mt-3 border-t border-line pt-3">
              <p className="text-xs text-muted">
                Inventory synced with Shopify · {inventory.purchasable} of {inventory.total} sizes
                purchasable.
              </p>
              {/* The per-garment override existed as an action nothing called,
                  so Settings' store-wide rule was in practice the only rule. */}
              <label className="mt-2 block">
                <span className="mb-1 block text-xs font-medium text-ink">When a size sells out</span>
                <select
                  disabled={!canPublish}
                  value={g.soldOutPolicy ?? ""}
                  onChange={(e) =>
                    soldOut.run(() =>
                      setSoldOutPolicyAction(g.id, (e.target.value || undefined) as SoldOutPolicy | undefined),
                    )
                  }
                  className={`${inputClass} disabled:opacity-60`}
                >
                  <option value="">
                    Follow the store default — {SOLD_OUT_POLICY_LABELS[tenant.defaults.soldOutPolicy].toLowerCase()}
                  </option>
                  {(["keep_tryon", "hide_size"] as SoldOutPolicy[]).map((p) => (
                    <option key={p} value={p}>{SOLD_OUT_POLICY_LABELS[p]}</option>
                  ))}
                </select>
              </label>
              <p className="mt-1 text-[11px] text-muted">
                In effect: {SOLD_OUT_POLICY_LABELS[soldOutPolicyFor(g, tenant)].toLowerCase()}.
              </p>
              {soldOut.notice && (
                <p
                  role={soldOut.notice.tone === "danger" ? "alert" : "status"}
                  className={`mt-1 text-[11px] ${soldOut.notice.tone === "danger" ? "text-red-700" : "text-emerald-700"}`}
                >
                  {soldOut.notice.message}
                </p>
              )}
            </div>
          </Card>

          <Card title="Shopper link">
            {g.stage === "live" && g.tryOnEnabled ? (
              <CopyField
                label="Unique try-on URL for this garment"
                value={publicUrl.garment(tenant.domain.subdomain, g.id)}
              />
            ) : (
              <p className="text-[13px] text-muted">
                This garment gets its own try-on URL once it is live and try-on is enabled.
              </p>
            )}
          </Card>

          {canPublish && <ScheduleCard garment={g} allowed={ent.scheduledGoLive} />}

          {/* Which revision is which. Without this the difference between what
              a merchant sees and what a shopper sees is invisible. */}
          <Card title="Revisions">
            <KeyValue
              rows={[
                ["Working revision", `#${g.sourceRevision}`],
                [
                  "Generated asset",
                  g.assetRevision === undefined ? (
                    <span key="a" className="text-amber-800">Not generated</span>
                  ) : assetIsCurrent(g) ? (
                    <span key="a">#{g.assetRevision} · current</span>
                  ) : (
                    <span key="a" className="text-amber-800">#{g.assetRevision} · stale</span>
                  ),
                ],
                [
                  "QA approved",
                  g.approved ? (
                    <span key="q">
                      #{g.approved.revision} · {fmtDateTime(g.approved.approvedAt)}
                    </span>
                  ) : (
                    <span key="q" className="text-amber-800">Never</span>
                  ),
                ],
                [
                  "Shoppers see",
                  resolved.servedRevision ? `#${resolved.servedRevision}` : "Nothing yet",
                ],
              ]}
            />
            {revisionState(g) === "draft_ahead" && (
              <p className="mt-2 text-xs text-amber-800">
                Regenerate and resubmit to QA to publish revision {g.sourceRevision}.
              </p>
            )}
          </Card>

          <Card title="Details">
            <KeyValue
              rows={[
                ["Colourway", g.colour],
                ["Reference sample", g.referenceSize ? `Size ${g.referenceSize}` : "—"],
                ["Construction", g.constructionBlocks.length > 1 ? `${g.constructionBlocks.length} blocks` : "Single block"],
                ["Fabric", g.fabricComposition.map((f) => `${f.pct}% ${f.material}`).join(", ") || "—"],
                ["Silhouette", g.silhouette ?? "—"],
                ["Published", g.publishedAt ? fmtDateTime(g.publishedAt) : "—"],
                ["Last updated", `${fmtDateTime(g.updatedAt)} · ${g.updatedBy}`],
              ]}
            />
          </Card>
        </aside>
      </div>
    </>
  );
}

/**
 * The garment's own edit form.
 *
 * Category and behaviour are try-on inputs, so saving them bumps the revision
 * — which is what stops an edit to a live garment quietly changing what
 * shoppers are served. The form says so before it is submitted, rather than
 * after.
 */
function GarmentDataForm({ garment: g }: { garment: Garment }) {
  const { pending, notice, run, clear } = useAction();
  const live = g.stage === "live" || g.stage === "ready" || g.stage === "in_qa";

  return (
    <form
      action={(formData: FormData) => run(() => updateGarmentAction(g.id, formData))}
    >
      <Card
        title="Garment data"
        action={<SubmitButton size="sm" pending={pending}>Save changes</SubmitButton>}
      >
        <NoticeBar notice={notice} onDismiss={clear} />
        {live && (
          <div className="mb-4">
            <Banner tone="warn">
              This garment is {STAGE_META[g.stage].label.toLowerCase()}. Changing its category or
              behaviour creates a new draft revision that has to go back through QA — shoppers keep
              seeing the approved version until it does.
            </Banner>
          </div>
        )}
        <div className="grid grid-cols-2 gap-4 max-md:grid-cols-1">
          <Field
            label="Category"
            hint="Changing this clears the size chart: measurement fields differ per category."
          >
            <select name="category" defaultValue={g.category} className={inputClass}>
              {["dress", "top", "bottom", "outerwear", "knitwear", "swim", "accessory"].map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </Field>
          {/* QA state is deliberately absent — it is Mirra's to set. */}
          {(["stretch", "drape", "opacity", "thickness"] as const).map((attr) => (
            <Field key={attr} label={attr[0].toUpperCase() + attr.slice(1)}>
              <select name={attr} defaultValue={g.attributes[attr]} className={inputClass}>
                {{
                  stretch: ["none", "low", "medium", "high"],
                  drape: ["structured", "moderate", "fluid"],
                  opacity: ["opaque", "semi", "sheer"],
                  thickness: ["light", "mid", "heavy"],
                }[attr].map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
            </Field>
          ))}
        </div>
        <div className="mt-4 space-y-4">
          <Field label="Fit notes" hint="Shown to shoppers and used by the fit engine.">
            <textarea name="fitNotes" defaultValue={g.fitNotes} rows={2} className={inputClass} />
          </Field>
          <Field label="Care notes">
            <textarea name="careNotes" defaultValue={g.careNotes} rows={2} className={inputClass} />
          </Field>
        </div>
      </Card>
    </form>
  );
}

/**
 * Scheduled go-live. Publication has advertised this for a long time with
 * nothing behind it; the control lives on the garment, which is where the page
 * always said it would be.
 */
function ScheduleCard({ garment: g, allowed }: { garment: Garment; allowed: boolean }) {
  const [when, setWhen] = useState(g.scheduledGoLive?.slice(0, 16) ?? "");
  const { pending, notice, run, clear } = useAction();

  if (!allowed) {
    return (
      <Card title="Schedule go-live">
        <p className="text-[13px] text-muted">
          Scheduling a publication time is part of the Atelier plan. On your plan, publish manually
          from this page when you&apos;re ready.
        </p>
      </Card>
    );
  }
  return (
    <Card title="Schedule go-live">
      <NoticeBar notice={notice} onDismiss={clear} />
      {g.scheduledGoLive ? (
        <>
          <p className="text-[13px]">
            Publishing <strong>{fmtDateTime(g.scheduledGoLive)}</strong> in your local timezone.
          </p>
          <div className="mt-2">
            <ActionButton onAction={() => scheduleGoLiveAction(g.id, undefined)}>
              Cancel schedule
            </ActionButton>
          </div>
        </>
      ) : g.stage !== "ready" ? (
        <p className="text-[13px] text-muted">
          A garment can be scheduled once it has passed QA. This one is{" "}
          {STAGE_META[g.stage].label.toLowerCase()}.
        </p>
      ) : (
        <>
          <Field label="Publish at" hint="Your local timezone. It goes live when someone next opens Publication, or by job in production.">
            <input
              type="datetime-local"
              value={when}
              onChange={(e) => setWhen(e.target.value)}
              className={inputClass}
            />
          </Field>
          <button
            disabled={!when || pending}
            onClick={() => run(() => scheduleGoLiveAction(g.id, when ? new Date(when).toISOString() : undefined))}
            className={`${buttonClass("accent", "sm")} mt-2`}
          >
            {pending ? "Scheduling…" : "Schedule"}
          </button>
        </>
      )}
    </Card>
  );
}
