/**
 * The dashboard's analytics charts, composed from the vendored Bklit UI
 * primitives in `../charts`. Both the Overview and the Analytics page render
 * these, so the two surfaces can never drift apart — the previous hand-rolled
 * SVG chart was duplicated between them.
 *
 * Colour rules (see the token block in `dashboard.css` for the validation run):
 * series hues are categorical slots 1 and 2 in fixed order, chrome and every
 * label wear neutral ink, and identity is always carried by a text label next
 * to the swatch rather than by colour alone.
 */
import type { ReactNode } from "react";
import { BarChart } from "../charts/bar-chart";
import { Bar } from "../charts/bar";
import { BarYAxis } from "../charts/bar-y-axis";
import { Grid } from "../charts/grid";
import { Line } from "../charts/line";
import { LineChart } from "../charts/line-chart";
import { ChartTooltip } from "../charts/tooltip";
import { XAxis } from "../charts/x-axis";
import { YAxis } from "../charts/y-axis";
import type { DailyMetric } from "../data/queries";

const SERIES = {
  started: { label: "Sessions started", color: "var(--chart-1)" },
  completed: { label: "Completed", color: "var(--chart-2)" },
} as const;

/**
 * Legend + direct totals. Required whenever two series share a plot, and it
 * doubles as the relief for the contrast rule: every swatch carries a word.
 */
function ChartLegend({ items }: { items: { label: string; color: string; value: ReactNode }[] }) {
  return (
    <ul className="mb-4 flex flex-wrap items-baseline gap-x-6 gap-y-1">
      {items.map((s) => (
        <li key={s.label} className="flex items-baseline gap-2">
          <span
            className="inline-block h-2 w-2 shrink-0 translate-y-[-1px] rounded-full"
            style={{ background: s.color }}
            aria-hidden
          />
          <span className="text-xs text-muted">{s.label}</span>
          <span className="text-[13px] font-semibold tabular-nums text-ink">{s.value}</span>
        </li>
      ))}
    </ul>
  );
}

export function SessionsChart({
  metrics,
  aspectRatio = "3 / 1",
}: {
  metrics: DailyMetric[];
  aspectRatio?: string;
}) {
  const data = metrics.map((m) => ({
    date: m.date,
    started: m.counts.session_start,
    completed: m.counts.session_complete,
  }));
  const sum = (k: "started" | "completed") => data.reduce((n, d) => n + d[k], 0);

  return (
    <div>
      <ChartLegend
        items={[
          { ...SERIES.started, value: sum("started").toLocaleString() },
          { ...SERIES.completed, value: sum("completed").toLocaleString() },
        ]}
      />
      <LineChart data={data} xDataKey="date" aspectRatio={aspectRatio}>
        <Grid />
        <XAxis />
        <YAxis />
        <Line dataKey="started" stroke={SERIES.started.color} />
        <Line dataKey="completed" stroke={SERIES.completed.color} />
        <ChartTooltip />
      </LineChart>
    </div>
  );
}

export function TopGarmentsChart({
  items,
  aspectRatio = "3 / 2",
}: {
  items: { label: string; value: number }[];
  aspectRatio?: string;
}) {
  // One series, one hue. Never a value-ramp across nominal categories — the
  // bar length already encodes magnitude.
  return (
    <BarChart data={items} xDataKey="label" orientation="horizontal" aspectRatio={aspectRatio}>
      <Grid />
      <BarYAxis />
      <Bar dataKey="value" fill="var(--chart-1)" />
      <ChartTooltip />
    </BarChart>
  );
}
