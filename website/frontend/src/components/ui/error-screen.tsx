import { Link } from "react-router-dom";
import { MirraMark } from "./logo";

/**
 * Intentional full-page state for known failures — never a crash. Laid out
 * on the page grid: the code sits in the margin, the message in the measure.
 */
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
    <main className="flex min-h-dvh flex-col bg-canvas px-6 py-8 lg:px-12 lg:py-10">
      <MirraMark size={24} strokeWidth={1.15} className="text-ink" />

      <div className="page-grid my-auto w-full">
        <div className="col-span-12 border-t border-hairline pt-6 md:col-span-3 md:pt-8">
          <p className="eyebrow">{code.replace(/_/g, " ")}</p>
        </div>

        <div className="col-span-12 border-t border-hairline pt-6 md:col-span-8 md:col-start-4 md:pt-8">
          <h1 className="max-w-2xl text-[clamp(1.75rem,4vw,2.75rem)] leading-[1.08] font-medium tracking-[-0.03em] text-graphite">
            {title}
          </h1>
          <p className="mt-5 max-w-md text-[14px] leading-relaxed text-slate">{body}</p>
          {action && (
            <Link
              to={action.to}
              className="lift-1 mt-8 inline-flex h-12 items-center border-b border-graphite text-[11px] font-medium tracking-[0.14em] text-graphite uppercase"
            >
              {action.label}
            </Link>
          )}
        </div>
      </div>
    </main>
  );
}
