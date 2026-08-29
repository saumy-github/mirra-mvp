import { useDbVersion } from "../../data/store";
import { useSession } from "../../data/session";
import { getEntitlements } from "../../data/entitlements";
import { can } from "../../data/rbac";
import { Link } from "react-router-dom";
import {
  archiveBrandChartAction,
  saveBrandChartAction,
  setColourwaySoldOutPolicyAction,
  setStoreSoldOutPolicyAction,
} from "../../data/actions";
import { MEASUREMENT_FIELDS, SOLD_OUT_POLICY_LABELS } from "../../data/ingestion";
import { blankRows, fromCm, toCm, validateChart } from "../../data/size-chart";
import type { BrandSizeChart, GarmentCategory, SizeChartKind, SizeRow } from "../../data/types";
import {
  ActionButton,
  Badge,
  Banner,
  Card,
  Field,
  KeyValue,
  NoticeBar,
  PageHeader,
} from "../../components/ui";
import { useAction } from "../../components/use-action";
import { buttonClass, inputClass } from "../../components/styles";
import { fmtDate } from "../../data/util";
import { useState } from "react";
import { dashPath } from "../../routes";

export default function SettingsPage() {
  const session = useSession();
  const notice = useAction();
  useDbVersion();
  if (!session?.tenant) return null;
  const tenant = session.tenant;

  const ent = getEntitlements(tenant);
  const canManage = can(session.role, "settings.manage");
  const charts = tenant.defaults.brandSizeCharts;

  return (
    <>
      <PageHeader title="Settings" subtitle="Workspace, store, and try-on page appearance." />
      <NoticeBar notice={notice.notice} onDismiss={notice.clear} />
      {!canManage && (
        <div className="mb-5">
          <Banner tone="info">Settings are read-only for your role.</Banner>
        </div>
      )}
      <div className="grid grid-cols-2 gap-4 max-lg:grid-cols-1">
        <Card title="Store">
          <KeyValue
            rows={[
              ["Workspace name", tenant.name],
              ["Store URL", tenant.storeUrl],
              ["Ownership verified", tenant.storeOwnershipVerified ? <Badge key="v" tone="success">Verified</Badge> : <Badge key="v" tone="warn">Pending</Badge>],
              ["Shopify connection", tenant.onboarding.shopifyConnected ? <Badge key="s" tone="success">Connected</Badge> : <Badge key="s" tone="danger">Not connected</Badge>],
            ]}
          />
        </Card>
        {/* Was a form with a Save button that had no action — it claimed
            "changes publish within a minute" while discarding every edit.
            Shown read-only until theming is wired to the merchant API. */}
        <Card title="Try-on page appearance">
          <div className="mb-4">
            <Banner tone="info">
              Read-only for now — editing your try-on page theme needs the merchant API. These are
              the values your page is currently using.
            </Banner>
          </div>
          <KeyValue
            rows={[
              [
                "Brand colour",
                <span key="b" className="flex items-center justify-end gap-2">
                  <span
                    className="h-4 w-4 rounded border border-line"
                    style={{ background: tenant.theme.brandColor }}
                    aria-hidden
                  />
                  <code className="text-xs">{tenant.theme.brandColor}</code>
                </span>,
              ],
              [
                "Accent colour",
                <span key="a" className="flex items-center justify-end gap-2">
                  <span
                    className="h-4 w-4 rounded border border-line"
                    style={{ background: tenant.theme.accentColor }}
                    aria-hidden
                  />
                  <code className="text-xs">{tenant.theme.accentColor}</code>
                </span>,
              ],
              ["Logo text", tenant.theme.logoText],
              ["Welcome headline", tenant.theme.welcomeHeadline],
            ]}
          />
          <p className="mt-3 text-xs text-muted">
            Need a change now?{" "}
            <Link to={dashPath.support} className="font-medium text-accent hover:underline">
              Ask support
            </Link>{" "}
            and we&apos;ll update it for you.
          </p>
        </Card>
        <Card title="Domains">
          <KeyValue
            rows={[
              ["Mirra subdomain", tenant.domain.subdomain],
              ["Custom domain", ent.customDomainAllowed ? (tenant.domain.customDomain ?? "Not configured — contact support to set up") : "Available as an add-on"],
            ]}
          />
        </Card>
        {/* Store-wide ingestion defaults. Per the flow these belong here, not
            repeated on every garment — a garment may override, but the brand
            sets the policy once. */}
        <Card title="When a variant sells out">
          <p className="mb-3 text-[13px] text-muted">
            A generated digital size doesn&apos;t stop existing when stock hits zero — shoppers may
            still want to try it, save it, or wait for a restock. Try-on availability and purchase
            availability are separate decisions.
          </p>
          <div className="space-y-2">
            {(["keep_tryon", "hide_size"] as const).map((policy) => (
              <button
                key={policy}
                disabled={!canManage}
                onClick={() => setStoreSoldOutPolicyAction(policy)}
                aria-pressed={tenant.defaults.soldOutPolicy === policy}
                className={`w-full rounded-xl border px-4 py-3 text-left text-[13px] transition-colors disabled:opacity-60 ${
                  tenant.defaults.soldOutPolicy === policy
                    ? "border-accent bg-accent-soft/40"
                    : "border-line hover:border-accent"
                }`}
              >
                <span className="flex items-center gap-2 font-medium text-ink">
                  {SOLD_OUT_POLICY_LABELS[policy]}
                  {policy === "keep_tryon" && <Badge tone="success">Recommended</Badge>}
                </span>
              </button>
            ))}
          </div>
          {/* The colourway-level rule existed in the model with no control at
              all, so a brand could not express "hide the whole colourway when
              every size of it is gone" — the case that matters most. */}
          <label className="mt-4 flex items-start gap-2 border-t border-line pt-3 text-[13px]">
            <input
              type="checkbox"
              disabled={!canManage}
              checked={tenant.defaults.hideColourwayWhenAllSoldOut}
              onChange={(e) => notice.run(() => setColourwaySoldOutPolicyAction(e.target.checked))}
              className="mt-0.5"
            />
            <span>
              Hide a colourway entirely when every one of its sizes is sold out
              <span className="block text-xs text-muted">
                Otherwise the colourway stays available for try-on with purchase disabled.
              </span>
            </span>
          </label>
          <p className="mt-3 text-xs text-muted">
            Inventory is read from Shopify via webhooks and never edited in Mirra. A garment can
            override the store-wide rule from its own page.
          </p>
        </Card>

        <BrandChartsCard charts={charts} canManage={canManage} />

        <Card title="Data & privacy">
          <ul className="space-y-2 text-[13px] text-stone-700">
            <li>✓ Shopper try-on sessions are processed transiently; no biometric data is stored.</li>
            <li>✓ Analytics are aggregated and never shared across brands.</li>
            <li>✓ You can export or delete your workspace data anytime via support.</li>
            <li>✓ Cancelled workspaces are preserved for 60 days, then permanently erased.</li>
          </ul>
        </Card>
      </div>
    </>
  );
}

/**
 * Brand size charts, versioned.
 *
 * Ingestion depends on these — "apply the brand chart" is the single biggest
 * saving once a catalogue passes a hundred products — yet they were a
 * read-only list with no way to create, edit or retire one. Editing publishes
 * a new version and archives the old one, so a garment sized from v2 keeps
 * meaning v2.
 */
function BrandChartsCard({ charts, canManage }: { charts: BrandSizeChart[]; canManage: boolean }) {
  const [editing, setEditing] = useState<BrandSizeChart | "new" | null>(null);
  const active = charts.filter((c) => !c.archived);
  const archived = charts.filter((c) => c.archived);

  return (
    <Card
      title="Brand size charts"
      action={
        canManage && !editing ? (
          <button onClick={() => setEditing("new")} className={buttonClass("secondary", "sm")}>
            + New chart
          </button>
        ) : undefined
      }
    >
      {editing ? (
        <ChartEditor chart={editing === "new" ? undefined : editing} onDone={() => setEditing(null)} />
      ) : active.length === 0 ? (
        <p className="text-[13px] text-muted">
          No brand chart yet. Once you have one, new garments can be sized in a click instead of a
          spreadsheet — the single biggest saving once a catalogue passes ~100 products.
        </p>
      ) : (
        <ul className="divide-y divide-stone-100">
          {active.map((chart) => (
            <li key={chart.id} className="py-2.5 text-[13px]">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium text-ink">
                  {chart.label} <span className="text-xs font-normal text-muted">v{chart.version}</span>
                </span>
                {canManage && (
                  <span className="flex gap-1.5">
                    <button onClick={() => setEditing(chart)} className={buttonClass("secondary", "sm")}>
                      Edit
                    </button>
                    <ActionButton onAction={() => archiveBrandChartAction(chart.id)}>
                      Archive
                    </ActionButton>
                  </span>
                )}
              </div>
              <span className="block text-xs text-muted">
                {chart.sizes.join(" · ")} ·{" "}
                {chart.kind === "body" ? "body measurements" : "finished garment"} ·{" "}
                {chart.rows.length} row{chart.rows.length === 1 ? "" : "s"}
                {chart.gradingRules && " · grades by rule"} · updated {fmtDate(chart.updatedAt)} by{" "}
                {chart.updatedBy}
              </span>
            </li>
          ))}
        </ul>
      )}
      {archived.length > 0 && !editing && (
        <p className="mt-3 text-xs text-muted">
          {archived.length} archived version{archived.length === 1 ? "" : "s"} kept — garments sized
          from them still read the numbers they were given.
        </p>
      )}
    </Card>
  );
}

const CHART_SIZES = ["XXS", "XS", "S", "M", "L", "XL", "XXL"];

function ChartEditor({ chart, onDone }: { chart?: BrandSizeChart; onDone: () => void }) {
  const [label, setLabel] = useState(chart?.label ?? "");
  const [category, setCategory] = useState<GarmentCategory | "all">(chart?.category ?? "all");
  const [kind, setKind] = useState<SizeChartKind>(chart?.kind ?? "garment");
  const [sizes, setSizes] = useState<string[]>(chart?.sizes.length ? chart.sizes : ["XS", "S", "M", "L"]);
  const [rows, setRows] = useState<SizeRow[]>(chart?.rows ?? []);
  const { pending, notice, run, clear } = useAction();

  // "all" has no single field set, so the editor grades against `top` — the
  // most common shape — and says so rather than silently picking one.
  const fieldCategory: GarmentCategory = category === "all" ? "top" : category;
  const fields = MEASUREMENT_FIELDS[fieldCategory];
  const working = rows.length ? rows : blankRows(sizes, fieldCategory);
  const validation = validateChart(working, fieldCategory, sizes);

  const setCell = (size: string, key: string, raw: string) =>
    setRows(
      working.map((r) =>
        r.size !== size ? r : { ...r, values: { ...r.values, [key]: raw.trim() === "" ? undefined : toCm(Number(raw), "cm") } },
      ),
    );

  return (
    <div className="flex flex-col gap-3">
      <NoticeBar notice={notice} onDismiss={clear} />
      <Field label="Name">
        <input value={label} onChange={(e) => setLabel(e.target.value)} className={inputClass} placeholder="Womenswear standard" />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Applies to">
          <select
            value={category}
            onChange={(e) => { setCategory(e.target.value as GarmentCategory | "all"); setRows([]); }}
            className={inputClass}
          >
            <option value="all">All categories</option>
            {(Object.keys(MEASUREMENT_FIELDS) as GarmentCategory[]).map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </Field>
        <Field label="These numbers are">
          <select value={kind} onChange={(e) => setKind(e.target.value as SizeChartKind)} className={inputClass}>
            <option value="garment">Finished garment</option>
            <option value="body">Body measurements</option>
          </select>
        </Field>
      </div>
      <Field label="Sizes">
        <div className="flex flex-wrap gap-1.5">
          {CHART_SIZES.map((sz) => (
            <button
              key={sz}
              type="button"
              aria-pressed={sizes.includes(sz)}
              onClick={() => {
                setSizes((prev) => (prev.includes(sz) ? prev.filter((x) => x !== sz) : [...CHART_SIZES].filter((c) => prev.includes(c) || c === sz)));
                setRows([]);
              }}
              className={`rounded-lg border px-2 py-1 text-xs font-medium ${
                sizes.includes(sz) ? "border-accent bg-accent-soft text-accent" : "border-line text-muted"
              }`}
            >
              {sz}
            </button>
          ))}
        </div>
      </Field>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-[13px]">
          <caption className="sr-only">Brand chart measurements per size, in centimetres</caption>
          <thead>
            <tr className="text-xs text-muted">
              <th scope="col" className="py-1.5 pr-3 font-medium">Size</th>
              {fields.map((f) => (
                <th key={f.key} scope="col" className="py-1.5 pr-3 font-medium" title={f.how}>{f.label}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {working.map((r) => (
              <tr key={r.size}>
                <th scope="row" className="py-1.5 pr-3 text-left font-medium">{r.size}</th>
                {fields.map((f) => (
                  <td key={f.key} className="py-1.5 pr-3">
                    <input
                      type="number"
                      step="0.1"
                      aria-label={`${f.label} for size ${r.size}`}
                      value={typeof r.values[f.key] === "number" ? String(fromCm(r.values[f.key] as number, "cm")) : ""}
                      onChange={(e) => setCell(r.size, f.key, e.target.value)}
                      className="w-20 rounded-md border border-line bg-surface px-2 py-1 text-[13px] tabular-nums focus:border-accent focus:outline-none"
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {category === "all" && (
        <p className="text-xs text-muted">
          A chart for all categories is stored against the top/knitwear field set. Category-specific
          charts are more accurate where a category needs different measurements.
        </p>
      )}
      {!validation.valid && (
        <p className="text-xs text-amber-800">
          {validation.issues.length} measurement{validation.issues.length === 1 ? "" : "s"} still to
          fill in before this can be saved.
        </p>
      )}
      <div className="flex gap-2">
        <button
          disabled={!label.trim() || !validation.valid || pending}
          onClick={() =>
            run(
              () => saveBrandChartAction({ id: chart?.id, label, category, kind, rows: working }),
              onDone,
            )
          }
          className={buttonClass("accent", "sm")}
        >
          {pending ? "Saving…" : chart ? `Publish version ${chart.version + 1}` : "Create chart"}
        </button>
        <button onClick={onDone} className={buttonClass("ghost", "sm")}>Cancel</button>
      </div>
      {chart && (
        <p className="text-xs text-muted">
          Saving publishes a new version and archives v{chart.version}. Garments already sized from
          v{chart.version} keep those numbers.
        </p>
      )}
    </div>
  );
}
