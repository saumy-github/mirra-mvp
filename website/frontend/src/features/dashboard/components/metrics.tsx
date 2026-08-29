/**
 * Metric display primitives, following the post-login UI brief in
 * `website/ZANDER_WHITEHURST_UI_UX_RESEARCH.md`:
 *
 * - Hierarchy is three-layer — one hero value, a supporting row, then detail.
 *   A grid of equally-weighted tiles says everything matters equally, which
 *   means nothing does.
 * - Grouping comes from one surface plus selective separators, not from N
 *   bordered boxes ("stop adding containers", "stop adding borders").
 * - Status is a dot *and* a word. Never colour alone.
 */
import type { ReactNode } from "react";
import { Badge } from "./ui";
import type { Tone } from "./styles";

export interface StatItem {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: Tone;
}

/**
 * The supporting layer: one surface, hairline separators between cells.
 * Replaces the previous row of individually bordered tiles.
 */
export function StatRow({ items }: { items: StatItem[] }) {
  return (
    <dl className="grid grid-cols-4 divide-x divide-line overflow-hidden rounded-xl border border-line bg-surface max-lg:grid-cols-2 max-lg:divide-y max-md:grid-cols-1 max-md:divide-x-0">
      {items.map((item) => (
        <div key={item.label} className="px-5 py-4">
          <dt className="text-xs font-medium text-muted">{item.label}</dt>
          <dd className="mt-1 text-2xl font-semibold tracking-tight text-ink">{item.value}</dd>
          {item.hint && (
            <div className="mt-1.5 text-xs text-muted">
              {item.tone ? <Badge tone={item.tone}>{item.hint}</Badge> : item.hint}
            </div>
          )}
        </div>
      ))}
    </dl>
  );
}

/**
 * The hero layer: the single number this screen exists to answer, the words
 * that say what it means, and what to do about it.
 *
 * Per the brief's own caveat, a hero is only a hero when it is the most useful
 * signal for the immediate task — don't promote a metric for visual balance.
 */
export function HeroMetric({
  label,
  value,
  status,
  caption,
  action,
}: {
  label: string;
  value: ReactNode;
  status?: { tone: Tone; label: string };
  caption?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-x-8 gap-y-3">
      <div>
        <div className="text-xs font-medium text-muted">{label}</div>
        <div className="mt-1 flex items-center gap-3">
          <span className="text-[2.75rem] leading-none font-semibold tracking-tight text-ink tabular-nums">
            {value}
          </span>
          {status && <Badge tone={status.tone}>{status.label}</Badge>}
        </div>
        {caption && <p className="mt-2 max-w-md text-[13px] text-muted">{caption}</p>}
      </div>
      {action}
    </div>
  );
}
