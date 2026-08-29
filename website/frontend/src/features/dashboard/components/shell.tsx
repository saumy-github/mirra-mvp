import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { MirraLogo as MirraBrandLockup } from "@/components/ui/logo";
import type { SessionContext } from "../data/session";
import { ROLE_LABELS } from "../data/rbac";
import { TENANT_STATUS_META } from "../data/lifecycle";
import { signOutAction, stopViewAsAction } from "../data/actions";
import { Badge } from "./ui";
import { buttonClass } from "./styles";

/** The shell only needs to render a link; capability filtering happens above. */
export interface ShellNavItem {
  href: string;
  label: string;
  icon: string;
  end?: boolean;
}

function NavList({ items, onNavigate }: { items: ShellNavItem[]; onNavigate?: () => void }) {
  return (
    <nav className="flex flex-col gap-0.5 px-3">
      {items.map((item) => (
        <NavLink
          key={item.href}
          to={item.href}
          end={item.end}
          onClick={onNavigate}
          className={({ isActive }) =>
            `flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors ${
              isActive ? "bg-accent-soft text-accent" : "text-stone-600 hover:bg-stone-100 hover:text-ink"
            }`
          }
        >
          <span className="w-4 text-center text-sm opacity-70" aria-hidden>{item.icon}</span>
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}

/** Identity, role and the way out. Repeated in the sidebar and the mobile sheet. */
function AccountBlock({ session, onNavigate }: { session: SessionContext; onNavigate?: () => void }) {
  const navigate = useNavigate();
  const role = session.isInternal ? session.user.internalRole! : session.role;
  return (
    <div className="border-t border-line px-5 py-4">
      <div className="text-[13px] font-medium text-ink">{session.user.name}</div>
      <div className="mt-0.5 text-xs text-muted">{role ? ROLE_LABELS[role] : "—"}</div>
      <form
        action={() => {
          onNavigate?.();
          navigate(signOutAction());
        }}
      >
        <button className="mt-2 cursor-pointer text-xs font-medium text-muted hover:text-ink">
          Sign out
        </button>
      </form>
    </div>
  );
}

export function AppShell({
  session,
  nav,
  brand,
  children,
}: {
  session: SessionContext;
  nav: ShellNavItem[];
  brand: ReactNode;
  children: ReactNode;
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const closeRef = useRef<HTMLButtonElement>(null);

  // A route change closes the sheet; without it the menu stays over the page
  // it just navigated to.
  useEffect(() => setMenuOpen(false), [location.pathname]);

  // Escape closes, and focus moves into the sheet so a keyboard user isn't
  // left tabbing through the page behind it.
  useEffect(() => {
    if (!menuOpen) return;
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  const current = nav.find((n) => (n.end ? location.pathname === n.href : location.pathname.startsWith(n.href)));

  return (
    <div className="flex min-h-screen">
      <aside className="fixed inset-y-0 flex w-60 flex-col border-r border-line bg-surface max-md:hidden">
        <div className="px-6 py-5">{brand}</div>
        <div className="flex-1 overflow-y-auto pb-4">
          <NavList items={nav} />
        </div>
        <AccountBlock session={session} />
      </aside>

      <div className="flex-1 md:pl-60">
        {/* Below `md` the sidebar is hidden, so this bar carries everything it
            held: where you are, who you are, and the way out. Without it a
            merchant on a phone — the device the capture flow is designed
            around — could not navigate or sign out at all. */}
        <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-line bg-surface px-4 py-2.5 md:hidden">
          <button
            type="button"
            onClick={() => setMenuOpen(true)}
            aria-expanded={menuOpen}
            aria-controls="dashboard-mobile-nav"
            className={buttonClass("secondary", "sm")}
          >
            <span aria-hidden>☰</span> Menu
          </button>
          <span className="truncate text-[13px] font-medium text-ink">{current?.label ?? "Dashboard"}</span>
          <span className="shrink-0 text-xs text-muted">{session.user.name.split(" ")[0]}</span>
        </header>

        {menuOpen && (
          <div className="fixed inset-0 z-40 md:hidden">
            <button
              type="button"
              aria-label="Close menu"
              tabIndex={-1}
              onClick={() => setMenuOpen(false)}
              className="absolute inset-0 bg-ink/30"
            />
            <div
              id="dashboard-mobile-nav"
              role="dialog"
              aria-modal="true"
              aria-label="Dashboard navigation"
              className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col border-r border-line bg-surface"
            >
              <div className="flex items-start justify-between gap-3 px-5 py-4">
                {brand}
                <button
                  ref={closeRef}
                  type="button"
                  onClick={() => setMenuOpen(false)}
                  className={buttonClass("ghost", "sm")}
                >
                  Close
                </button>
              </div>
              {session.impersonating && session.tenant && (
                <p className="mx-3 mb-2 rounded-lg bg-amber-100 px-3 py-2 text-xs text-amber-900">
                  Viewing {session.tenant.name} as Mirra staff
                  {session.viewAs?.mode === "read_only" ? " (read-only)" : ""}.
                </p>
              )}
              <div className="flex-1 overflow-y-auto pb-4">
                <NavList items={nav} onNavigate={() => setMenuOpen(false)} />
              </div>
              <AccountBlock session={session} onNavigate={() => setMenuOpen(false)} />
            </div>
          </div>
        )}

        {session.impersonating && session.tenant && (
          <div
            role="status"
            className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-3 bg-amber-100 px-6 py-2 text-[13px] text-amber-900 max-md:px-4"
          >
            <span>
              👁 Viewing <strong>{session.tenant.name}</strong> as Mirra staff —{" "}
              <strong>{session.viewAs?.mode === "write" ? "write access" : "read-only"}</strong>.
              {session.viewAs && (
                <>
                  {" "}Reason: {session.viewAs.reason}. Ends{" "}
                  {new Date(session.viewAs.expiresAt).toLocaleTimeString("en-US", {
                    hour: "numeric",
                    minute: "2-digit",
                  })}
                  .
                </>
              )}{" "}
              Every read and write is recorded in the brand&apos;s audit log.
            </span>
            <form action={() => navigate(stopViewAsAction())}>
              <button className="cursor-pointer rounded-md border border-amber-300 bg-white px-2.5 py-1 text-xs font-medium hover:bg-amber-50">
                Exit view-as
              </button>
            </form>
          </div>
        )}
        <main className="mx-auto max-w-6xl px-6 py-8 max-md:px-4">{children}</main>
      </div>
    </div>
  );
}

export function TenantStatusBadge({ status }: { status: keyof typeof TENANT_STATUS_META }) {
  const meta = TENANT_STATUS_META[status];
  return <Badge tone={meta.tone}>{meta.label}</Badge>;
}

/**
 * The real brand asset, not a third hand-set wordmark. The prototype drew its
 * own "mirra." in text because it had no access to the brand files; this repo
 * ships them, and `pages/profile/ProfileLayout.tsx` already uses this exact
 * component.
 */
export function MirraLogo({ sub }: { sub?: string }) {
  return (
    <Link to="/" className="flex items-baseline gap-2" aria-label={sub ? `Mirra ${sub}` : "Mirra"}>
      <MirraBrandLockup alt="" height={26} />
      {sub && <span className="text-xs font-medium tracking-wide text-muted uppercase">{sub}</span>}
    </Link>
  );
}
