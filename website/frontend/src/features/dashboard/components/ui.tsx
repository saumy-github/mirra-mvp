// Dashboard-local primitives. Deliberately NOT merged into `@/components/ui`:
// the merchant surface has its own visual language (indigo accent, dense
// tables, 13px type) and keeping it self-contained means the shopper-facing
// components can evolve without regressing this one.
import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import type { ActionResult } from "../data/actions";
import { useAction, type Notice } from "./use-action";
import { buttonClass, TONE_CLASSES, type ButtonVariant, type Tone } from "./styles";

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap ${TONE_CLASSES[tone]}`}
    >
      {children}
    </span>
  );
}

export function Card({
  title,
  action,
  children,
  className = "",
}: {
  title?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-xl border border-line bg-surface shadow-[0_1px_2px_rgba(0,0,0,0.03)] ${className}`}>
      {(title || action) && (
        <header className="flex items-center justify-between gap-3 border-b border-line px-5 py-3.5">
          <h2 className="text-[13px] font-semibold tracking-wide text-ink">{title}</h2>
          {action}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function StatTile({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: Tone;
}) {
  return (
    <div className="rounded-xl border border-line bg-surface px-5 py-4">
      <div className="text-xs font-medium text-muted">{label}</div>
      <div className="mt-1 text-2xl font-semibold tracking-tight text-ink">{value}</div>
      {hint && <div className="mt-1 text-xs text-muted">{tone ? <Badge tone={tone}>{hint}</Badge> : hint}</div>}
    </div>
  );
}

export function EmptyState({
  icon = "◌",
  title,
  body,
  action,
}: {
  icon?: string;
  title: string;
  body?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-line bg-surface px-6 py-14 text-center">
      <div className="text-3xl opacity-40" aria-hidden>{icon}</div>
      <div className="text-sm font-semibold text-ink">{title}</div>
      {body && <p className="max-w-sm text-[13px] text-muted">{body}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

/**
 * `live` gives the banner an ARIA role so a change announced only visually is
 * also announced to a screen reader. Static page furniture stays silent —
 * marking every banner as an alert is the same as marking none.
 */
export function Banner({
  tone = "info",
  live,
  children,
}: {
  tone?: Tone;
  live?: boolean;
  children: ReactNode;
}) {
  return (
    <div
      role={live ? (tone === "danger" ? "alert" : "status") : undefined}
      aria-live={live && tone !== "danger" ? "polite" : undefined}
      className={`rounded-lg border px-4 py-3 text-[13px] ${TONE_CLASSES[tone]}`}
    >
      {children}
    </div>
  );
}

export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-ink">{title}</h1>
        {subtitle && <p className="mt-1 max-w-2xl text-[13px] text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

/**
 * `caption` is required rather than optional: a screen-reader user landing on
 * one of these dense tables needs to know what it lists before reading rows.
 * It is visually hidden — the surrounding PageHeader already says it on screen.
 *
 * Columns are ruled only at the header and between rows. No vertical rules:
 * alignment does that job, and a full grid makes a table read as a spreadsheet
 * (see "stop adding borders" in the UI brief).
 */
export function Table({
  caption,
  headers,
  children,
}: {
  caption: string;
  headers: string[];
  children: ReactNode;
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-line bg-surface">
      <table className="w-full text-left text-[13px]">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr className="border-b border-line text-xs text-muted">
            {headers.map((h, i) => (
              <th key={h || `col-${i}`} scope="col" className="px-4 py-2.5 font-medium">
                {h || <span className="sr-only">Actions</span>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-stone-100">{children}</tbody>
      </table>
    </div>
  );
}

export function Td({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <td className={`px-4 py-3 align-middle ${className}`}>{children}</td>;
}

export function Progress({ value, max }: { value: number; max: number }) {
  const pct = max === 0 ? 0 : Math.min(100, Math.round((value / max) * 100));
  return (
    <div className="h-1.5 w-full rounded-full bg-stone-100" role="progressbar" aria-valuenow={value} aria-valuemax={max}>
      <div className="h-1.5 rounded-full bg-accent transition-all" style={{ width: `${pct}%` }} />
    </div>
  );
}

export function ButtonLink({
  href,
  variant = "secondary",
  size = "md",
  children,
}: {
  href: string;
  variant?: ButtonVariant;
  size?: "sm" | "md";
  children: ReactNode;
}) {
  return (
    <Link to={href} className={buttonClass(variant, size)}>
      {children}
    </Link>
  );
}

export function SubmitButton({
  variant = "primary",
  size = "md",
  pending,
  children,
}: {
  variant?: ButtonVariant;
  size?: "sm" | "md";
  pending?: boolean;
  children: ReactNode;
}) {
  return (
    <button type="submit" disabled={pending} aria-busy={pending} className={buttonClass(variant, size)}>
      {pending ? "Working…" : children}
    </button>
  );
}

/** Renders whatever `useAction` last produced. */
export function NoticeBar({ notice, onDismiss }: { notice: Notice | null; onDismiss?: () => void }) {
  if (!notice) return null;
  return (
    <div className="mb-3">
      <Banner live tone={notice.tone === "success" ? "success" : "danger"}>
        {notice.message}
        {onDismiss && (
          <button onClick={onDismiss} className="ml-2 cursor-pointer font-medium underline">
            Dismiss
          </button>
        )}
      </Banner>
    </div>
  );
}

/** A button wired to an action: pending state, result, no double submit. */
export function ActionButton({
  onAction,
  variant = "secondary",
  size = "sm",
  disabled,
  onDone,
  children,
}: {
  onAction: () => ActionResult;
  variant?: ButtonVariant;
  size?: "sm" | "md";
  disabled?: boolean;
  onDone?: (message?: string) => void;
  children: ReactNode;
}) {
  const { pending, notice, run, clear } = useAction();
  return (
    <span className="inline-flex flex-col items-start gap-1">
      <button
        type="button"
        disabled={disabled || pending}
        aria-busy={pending}
        onClick={() => run(onAction, onDone)}
        className={buttonClass(variant, size)}
      >
        {pending ? "Working…" : children}
      </button>
      {notice && (
        <span
          role={notice.tone === "danger" ? "alert" : "status"}
          className={`text-[11px] leading-tight ${notice.tone === "danger" ? "text-red-700" : "text-emerald-700"}`}
        >
          {notice.message}
          <button onClick={clear} className="ml-1.5 cursor-pointer underline">dismiss</button>
        </span>
      )}
    </span>
  );
}

/**
 * A destructive or outward-facing action, gated behind the thing it is about
 * to do. `impact` is not decoration — it is the count of shoppers-facing items
 * the click affects, and `confirmWord` forces the operator to read it.
 */
export function ConfirmAction({
  label,
  title,
  impact,
  confirmWord,
  variant = "danger",
  size = "sm",
  disabled,
  onConfirm,
}: {
  label: string;
  title: string;
  impact: ReactNode;
  confirmWord?: string;
  variant?: ButtonVariant;
  size?: "sm" | "md";
  disabled?: boolean;
  onConfirm: () => ActionResult;
}) {
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState("");
  const { pending, notice, run, clear } = useAction();

  if (!open) {
    return (
      <button
        type="button"
        disabled={disabled}
        onClick={() => { setOpen(true); clear(); }}
        className={buttonClass(variant, size)}
      >
        {label}
      </button>
    );
  }
  const ready = !confirmWord || typed.trim().toUpperCase() === confirmWord.toUpperCase();
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-[13px]">
      <div className="font-semibold text-red-800">{title}</div>
      <div className="mt-1 text-xs text-red-900">{impact}</div>
      {confirmWord && (
        <label className="mt-2.5 block">
          <span className="mb-1 block text-xs font-medium text-red-900">
            Type {confirmWord} to confirm
          </span>
          <input
            autoFocus
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            className="w-44 rounded-md border border-red-200 bg-white px-2 py-1 text-xs focus:outline-none"
          />
        </label>
      )}
      {notice && (
        <p role="alert" className="mt-2 text-xs font-medium text-red-800">{notice.message}</p>
      )}
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          disabled={!ready || pending}
          aria-busy={pending}
          onClick={() => run(onConfirm, () => setOpen(false))}
          className={buttonClass("danger", "sm")}
        >
          {pending ? "Working…" : label}
        </button>
        <button type="button" onClick={() => setOpen(false)} className={buttonClass("ghost", "sm")}>
          Keep things as they are
        </button>
      </div>
    </div>
  );
}

/**
 * Page-at-a-time for the catalogue and audit tables. Rendering every row of a
 * real brand's catalogue in one pass is the difference between a page that
 * opens and one that doesn't.
 */
export function Pagination({
  page,
  pageSize,
  total,
  onPage,
  label,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPage: (p: number) => void;
  label: string;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (total <= pageSize) return null;
  const from = page * pageSize + 1;
  const to = Math.min(total, (page + 1) * pageSize);
  return (
    <nav aria-label={label} className="mt-3 flex items-center justify-between gap-3 text-xs text-muted">
      <span aria-live="polite">
        Showing {from}–{to} of {total}
      </span>
      <span className="flex items-center gap-2">
        <button
          type="button"
          disabled={page === 0}
          onClick={() => onPage(page - 1)}
          className={buttonClass("secondary", "sm")}
        >
          ← Previous
        </button>
        <span>
          Page {page + 1} of {pages}
        </span>
        <button
          type="button"
          disabled={page + 1 >= pages}
          onClick={() => onPage(page + 1)}
          className={buttonClass("secondary", "sm")}
        >
          Next →
        </button>
      </span>
    </nav>
  );
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-ink">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-muted">{hint}</span>}
    </label>
  );
}

export function KeyValue({ rows }: { rows: [string, ReactNode][] }) {
  return (
    <dl className="divide-y divide-stone-100">
      {rows.map(([k, v]) => (
        <div key={k} className="flex items-center justify-between gap-4 py-2.5">
          <dt className="text-[13px] text-muted">{k}</dt>
          <dd className="text-[13px] font-medium text-ink text-right">{v}</dd>
        </div>
      ))}
    </dl>
  );
}
