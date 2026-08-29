import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  bulkStageAction,
  preflightBulkStage,
  setGarmentStageAction,
  toggleTryOnAction,
} from "../data/actions";
import { STAGE_META, type Requirement } from "../data/ingestion";
import { dashPath } from "../routes";
import type { GarmentStage } from "../data/types";
import {
  ActionButton,
  Badge,
  NoticeBar,
  Pagination,
} from "./ui";
import { useAction } from "./use-action";
import { buttonClass } from "./styles";

export interface GarmentRow {
  id: string;
  title: string;
  emoji: string;
  category: string;
  colour: string;
  skuCount: number;
  productTitle: string;
  productType: string;
  stage: GarmentStage;
  referenceSize?: string;
  tryOnEnabled: boolean;
  completeCount: number;
  requirementCount: number;
  requirements: Requirement[];
  soldOutSizes: string[];
  syncStatus: string;
  updatedAt: string;
  /** What shoppers are actually served, resolved through `publication.ts`. */
  publiclyVisible: boolean;
  publicBlockedReason?: string;
  /** Edits exist that QA hasn't approved — the live surface serves the older one. */
  draftAhead: boolean;
  liveSkus: number;
  scheduledGoLive?: string;
  openQaFindings: number;
}

/**
 * The same rows serve two different jobs, so the table takes a mode rather
 * than being rendered twice with an identical action set:
 *
 * - `catalogue` (Garments) — "what still needs my input?" Completion leads and
 *   the row action continues ingestion.
 * - `publication` (Publication) — "what are shoppers seeing?" Stage leads,
 *   with selection, bulk actions and publish/pause.
 */
export type GarmentTableMode = "catalogue" | "publication";

export function StageBadge({ stage }: { stage: GarmentStage }) {
  const meta = STAGE_META[stage];
  return <Badge tone={meta.tone}>{meta.label}</Badge>;
}

/**
 * "3 / 5 complete" with the breakdown underneath — a merchant can see which
 * chore is outstanding without opening the garment.
 */
export function CompletionCell({ row }: { row: GarmentRow }) {
  const done = row.completeCount === row.requirementCount;
  return (
    <div>
      <div className={`text-xs font-medium ${done ? "text-emerald-700" : "text-amber-800"}`}>
        {row.completeCount} / {row.requirementCount} complete
      </div>
      <ul className="mt-1 flex flex-wrap gap-x-2 gap-y-0.5">
        {row.requirements.map((r) => (
          <li
            key={r.key}
            title={r.detail}
            className={`text-[11px] ${r.complete ? "text-stone-400" : "font-medium text-amber-800"}`}
          >
            {r.complete ? "✓" : "✕"} {r.label}
          </li>
        ))}
      </ul>
    </div>
  );
}

const PAGE_SIZE = 25;

export function GarmentTable({
  rows,
  canManage,
  bulkAllowed,
  mode = "publication",
}: {
  rows: GarmentRow[];
  canManage: boolean;
  bulkAllowed: boolean;
  mode?: GarmentTableMode;
}) {
  const [query, setQuery] = useState("");
  const [stageFilter, setStageFilter] = useState<string>("all");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [page, setPage] = useState(0);
  const { notice, setNotice, clear } = useAction();

  const isPublication = mode === "publication";
  const showControls = isPublication && canManage;

  const filtered = useMemo(
    () =>
      rows.filter((r) => {
        if (stageFilter === "incomplete") return r.completeCount < r.requirementCount && matches(r, query);
        if (stageFilter === "offline") return !r.publiclyVisible && matches(r, query);
        if (stageFilter !== "all" && r.stage !== stageFilter) return false;
        return matches(r, query);
      }),
    [rows, query, stageFilter],
  );

  // Selection is scoped to what is on screen. Keeping hidden rows selected
  // meant a bulk action could mutate garments the merchant had filtered away
  // and could no longer see.
  const visibleIds = useMemo(() => new Set(filtered.map((r) => r.id)), [filtered]);
  const activeSelection = useMemo(
    () => [...selected].filter((id) => visibleIds.has(id)),
    [selected, visibleIds],
  );
  const hiddenSelected = selected.size - activeSelection.length;

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount - 1);
  const pageRows = filtered.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE);

  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const runBulk = (to: GarmentStage) => {
    const res = bulkStageAction(activeSelection, to);
    setNotice({
      tone: res.skipped.length === 0 ? "success" : "danger",
      message:
        res.skipped.length === 0
          ? `Updated ${res.applied} garment${res.applied === 1 ? "" : "s"}.`
          : `Updated ${res.applied}. Skipped ${res.skipped.length}: ${res.skipped
              .slice(0, 3)
              .map((x) => `${x.title} — ${x.reason}`)
              .join("; ")}${res.skipped.length > 3 ? ` and ${res.skipped.length - 3} more` : ""}.`,
    });
    setSelected(new Set());
  };

  // Bulk buttons are enabled only when the selection can actually take them,
  // and say how many of the selected rows would move.
  const preflight = (to: GarmentStage) =>
    activeSelection.length > 0 ? preflightBulkStage(activeSelection, to) : { eligible: [], skipped: [] };
  const bulkOptions: { to: GarmentStage; label: string; variant: "secondary" | "accent" }[] = [
    { to: "in_qa", label: "Submit to QA", variant: "secondary" },
    { to: "live", label: "Publish", variant: "accent" },
    { to: "paused", label: "Pause", variant: "secondary" },
  ];

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <label className="sr-only" htmlFor="garment-search">Search garments</label>
        <input
          id="garment-search"
          type="search"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setPage(0); }}
          placeholder="Search garments…"
          className="w-56 rounded-lg border border-line bg-surface px-3 py-1.5 text-[13px] focus:border-accent focus:outline-none"
        />
        <label className="sr-only" htmlFor="garment-filter">Filter garments</label>
        <select
          id="garment-filter"
          value={stageFilter}
          onChange={(e) => { setStageFilter(e.target.value); setPage(0); }}
          className="rounded-lg border border-line bg-surface px-2.5 py-1.5 text-[13px]"
        >
          <option value="all">All garments</option>
          {!isPublication && <option value="incomplete">Needs my input</option>}
          {isPublication && <option value="offline">Not reaching shoppers</option>}
          {(["draft", "processing", "needs_data", "merchant_review", "in_qa", "ready", "live", "paused"] as GarmentStage[]).map(
            (s) => (
              <option key={s} value={s}>{STAGE_META[s].label}</option>
            ),
          )}
        </select>
        <span className="text-xs text-muted" aria-live="polite">{filtered.length} of {rows.length}</span>
        {showControls && activeSelection.length > 0 && (
          <div className="ml-auto flex flex-wrap items-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5">
            <span className="text-xs font-medium text-indigo-700">
              {activeSelection.length} selected
              {hiddenSelected > 0 && ` (${hiddenSelected} hidden by the filter, not included)`}
            </span>
            {bulkAllowed ? (
              bulkOptions.map((opt) => {
                const p = preflight(opt.to);
                return (
                  <button
                    key={opt.to}
                    disabled={p.eligible.length === 0}
                    title={
                      p.eligible.length === 0
                        ? `None of the selected garments can be ${STAGE_META[opt.to].label.toLowerCase()}`
                        : `${p.eligible.length} of ${activeSelection.length} will change`
                    }
                    onClick={() => runBulk(opt.to)}
                    className={buttonClass(opt.variant, "sm")}
                  >
                    {opt.label} ({p.eligible.length})
                  </button>
                );
              })
            ) : (
              <span className="text-xs text-indigo-700">Bulk publishing available on Boutique and above</span>
            )}
          </div>
        )}
      </div>
      <NoticeBar notice={notice} onDismiss={clear} />
      <div className="overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full text-left text-[13px]">
          <caption className="sr-only">
            {isPublication ? "Garments and what shoppers can currently see" : "Garments and the data each still needs"}
          </caption>
          <thead>
            <tr className="border-b border-line text-xs text-muted">
              {showControls && <th scope="col" className="w-8 px-3 py-2.5"><span className="sr-only">Select</span></th>}
              <th scope="col" className="px-3 py-2.5 font-medium">Garment</th>
              <th scope="col" className="px-3 py-2.5 font-medium">Category</th>
              <th scope="col" className="px-3 py-2.5 font-medium">SKUs</th>
              {isPublication ? (
                <>
                  <th scope="col" className="px-3 py-2.5 font-medium">Stage</th>
                  <th scope="col" className="px-3 py-2.5 font-medium">Shoppers see</th>
                </>
              ) : (
                <>
                  <th scope="col" className="px-3 py-2.5 font-medium">Data</th>
                  <th scope="col" className="px-3 py-2.5 font-medium">Stage</th>
                </>
              )}
              {showControls && <th scope="col" className="px-3 py-2.5 font-medium">Actions</th>}
              {!isPublication && <th scope="col" className="px-3 py-2.5 font-medium"><span className="sr-only">Continue</span></th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {pageRows.map((r) => (
              <tr key={r.id} className="align-top hover:bg-stone-50/60">
                {showControls && (
                  <td className="px-3 py-3">
                    <input
                      type="checkbox"
                      checked={selected.has(r.id)}
                      onChange={() => toggle(r.id)}
                      aria-label={`Select ${r.title}`}
                    />
                  </td>
                )}
                <td className="px-3 py-3">
                  <Link to={dashPath.garment(r.id)} className="group flex items-center gap-2.5">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-stone-100 text-base" aria-hidden>{r.emoji}</span>
                    <span>
                      <span className="block font-medium text-ink group-hover:text-accent">{r.title}</span>
                      <span className="block text-xs text-muted">
                        {r.productType}
                        {/* Which physical sample this was built from — without
                            it nobody can audit the sizes six months later. */}
                        {r.referenceSize ? ` · sample ${r.referenceSize}` : " · no sample yet"}
                        {r.syncStatus === "error" && " · sync error"}
                      </span>
                    </span>
                  </Link>
                </td>
                <td className="px-3 py-3 capitalize text-stone-600">{r.category}</td>
                <td className="px-3 py-3 text-stone-600">
                  <span className="tabular-nums">{r.skuCount}</span>
                  {r.soldOutSizes.length > 0 && (
                    <span className="block text-[11px] text-muted">{r.soldOutSizes.length} sold out</span>
                  )}
                </td>
                {isPublication ? (
                  <>
                    <td className="px-3 py-3">
                      <StageBadge stage={r.stage} />
                      {r.draftAhead && (
                        <span className="mt-1 block text-[11px] font-medium text-amber-800">
                          Draft ahead of QA
                        </span>
                      )}
                      {r.scheduledGoLive && (
                        <span className="mt-1 block text-[11px] text-muted">
                          Scheduled {new Date(r.scheduledGoLive).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}
                        </span>
                      )}
                    </td>
                    {/* Not the stage a second time: what the publication
                        resolver says a shopper actually gets right now. */}
                    <td className="px-3 py-3">
                      {r.publiclyVisible ? (
                        <>
                          <Badge tone="success">Live to shoppers</Badge>
                          <span className="mt-1 block text-[11px] text-muted">{r.liveSkus} SKUs served</span>
                        </>
                      ) : (
                        <>
                          <Badge tone="neutral">Not visible</Badge>
                          <span className="mt-1 block text-[11px] text-muted">{r.publicBlockedReason}</span>
                        </>
                      )}
                    </td>
                  </>
                ) : (
                  <>
                    <td className="px-3 py-3"><CompletionCell row={r} /></td>
                    <td className="px-3 py-3">
                      <StageBadge stage={r.stage} />
                      {r.openQaFindings > 0 && (
                        <span className="mt-1 block text-[11px] font-medium text-red-700">
                          {r.openQaFindings} QA finding{r.openQaFindings === 1 ? "" : "s"}
                        </span>
                      )}
                    </td>
                  </>
                )}
                {showControls && (
                  <td className="px-3 py-3">
                    <div className="flex flex-wrap gap-1.5">
                      {r.stage === "merchant_review" && (
                        <ActionButton onAction={() => setGarmentStageAction(r.id, "in_qa")}>
                          Submit to QA
                        </ActionButton>
                      )}
                      {r.stage === "ready" && (
                        <ActionButton variant="accent" onAction={() => setGarmentStageAction(r.id, "live")}>
                          Publish
                        </ActionButton>
                      )}
                      {r.stage === "live" && (
                        <ActionButton onAction={() => setGarmentStageAction(r.id, "paused")}>
                          Pause
                        </ActionButton>
                      )}
                      {r.stage === "paused" && (
                        <ActionButton variant="accent" onAction={() => setGarmentStageAction(r.id, "live")}>
                          Resume
                        </ActionButton>
                      )}
                      {r.stage === "in_qa" && <span className="text-xs text-muted">With Mirra QA</span>}
                    </div>
                  </td>
                )}
                {!isPublication && (
                  <td className="px-3 py-3">
                    <Link to={nextStop(r)} className="text-xs font-medium text-accent hover:underline">
                      {r.completeCount === r.requirementCount ? "Review →" : "Continue setup →"}
                    </Link>
                  </td>
                )}
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-10 text-center text-muted">
                  {query.trim() || stageFilter !== "all" ? (
                    <>
                      No garments match this filter.{" "}
                      <button
                        onClick={() => { setQuery(""); setStageFilter("all"); }}
                        className="font-medium text-accent underline"
                      >
                        Clear it
                      </button>
                    </>
                  ) : (
                    "No garments yet."
                  )}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <Pagination
        page={currentPage}
        pageSize={PAGE_SIZE}
        total={filtered.length}
        onPage={setPage}
        label="Garment pages"
      />
    </div>
  );
}

/**
 * Deep-link to whatever this garment actually needs next, rather than always
 * dropping the merchant at capture and making them find it.
 */
function nextStop(r: GarmentRow): string {
  // Finished garments go to their summary; unfinished ones resume the flow at
  // whichever step is still outstanding.
  return r.completeCount === r.requirementCount
    ? dashPath.garment(r.id)
    : dashPath.garmentFlow(r.id);
}

function matches(r: GarmentRow, query: string): boolean {
  const q = query.trim().toLowerCase();
  return !q || r.title.toLowerCase().includes(q) || r.productType.toLowerCase().includes(q);
}

export function TryOnToggle({ garmentId, enabled }: { garmentId: string; enabled: boolean }) {
  const { run } = useAction();
  return (
    <button
      onClick={() => run(() => toggleTryOnAction(garmentId, !enabled))}
      role="switch"
      aria-checked={enabled}
      className={`relative h-5 w-9 cursor-pointer rounded-full transition-colors ${enabled ? "bg-accent" : "bg-stone-300"}`}
    >
      <span className="sr-only">Try-on {enabled ? "enabled" : "disabled"}</span>
      <span
        className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${enabled ? "translate-x-4.5 left-0" : "left-0.5"}`}
      />
    </button>
  );
}
