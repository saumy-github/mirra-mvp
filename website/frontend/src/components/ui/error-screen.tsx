import { Link } from "react-router-dom";
import { MirraMark } from "./logo";

/** Intentional full-page state for known failures — never a crash. */
export function ErrorScreen({
  code,
  title,
  body,
  action,
}: {
  code: string;
  title: string;
  body: string;
  action?: { to: string; label: string } | null;
}) {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center px-6 text-center">
      <MirraMark size={36} className="text-faint" />
      <p className="mono-tag mt-8">[&thinsp;{code}&thinsp;]</p>
      <h1 className="mt-3 text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-3 max-w-sm text-sm leading-relaxed text-muted">{body}</p>
      {action && (
        <Link
          to={action.to}
          className="mt-8 rounded-full border border-line-strong bg-paper px-6 py-2.5 text-sm text-ink transition-colors hover:border-ink"
        >
          {action.label}
        </Link>
      )}
    </main>
  );
}
