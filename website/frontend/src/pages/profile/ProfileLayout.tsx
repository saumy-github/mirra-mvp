import { useEffect, useRef } from "react";
import { ArrowUpRight, ChevronDown } from "lucide-react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { MirraLogo } from "@/components/ui/logo";
import { useAccount, useAuthMutations } from "@/hooks/use-shopper";
import "./profile.css";

const NAV = [
  { href: "/profile", label: "Overview" },
  { href: "/profile/avatar", label: "Avatar" },
  { href: "/profile/measurements", label: "Fit Profile" },
  { href: "/profile/signature-looks", label: "Saved Looks" },
  { href: "/profile/privacy", label: "Privacy" },
];

/**
 * Lightweight account profile area. Deliberately not a social space:
 * no feeds, no cross-account products — just the account's own data.
 */
export default function ProfileLayout() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { data: account, isLoading } = useAccount();
  const { logout } = useAuthMutations();
  const activeTabRef = useRef<HTMLAnchorElement>(null);

  useEffect(() => {
    if (!isLoading && !account) {
      navigate(`/auth/login?next=${encodeURIComponent(pathname)}`, { replace: true });
    }
  }, [account, isLoading, navigate, pathname]);

  useEffect(() => {
    activeTabRef.current?.scrollIntoView({ block: "nearest", inline: "center" });
  }, [pathname]);

  if (isLoading || !account) {
    return <ProfileShellStatus label={isLoading ? "Loading your profile" : "Opening sign in"} />;
  }

  const accountInitial = account.displayName.trim().charAt(0).toUpperCase() || "M";

  return (
    <main className="profile-shell">
      <header className="profile-topbar">
        <div className="profile-topbar__brand">
          <Link to="/" aria-label="Mirra home" className="profile-wordmark">
            <MirraLogo alt="" height={38} />
          </Link>
          <span className="profile-topbar__divider" aria-hidden />
          <span className="profile-topbar__title">Your profile</span>
        </div>

        <div className="profile-topbar__actions">
          <Link to="/studio" className="profile-studio-link">
            Open Studio <ArrowUpRight aria-hidden size={16} strokeWidth={1.7} />
          </Link>

          <details className="profile-account">
            <summary>
              <span className="profile-account__initial" aria-hidden>
                {accountInitial}
              </span>
              <span>Account</span>
              <ChevronDown aria-hidden size={15} strokeWidth={1.7} />
            </summary>
            <div className="profile-account__menu">
              <p>{account.displayName}</p>
              {!account.isGuest && <span>{account.email}</span>}
              <button
                type="button"
                disabled={logout.isPending}
                onClick={() =>
                  logout.mutate(undefined, { onSuccess: () => navigate("/auth/login") })
                }
              >
                {logout.isPending ? "Signing out…" : "Sign out"}
              </button>
              {logout.error && (
                <span className="profile-account__error" role="alert">
                  Sign out did not complete. Please try again.
                </span>
              )}
            </div>
          </details>
        </div>
      </header>

      <nav aria-label="Profile sections" className="profile-tabs">
        <div className="profile-tabs__inner">
          {NAV.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                ref={active ? activeTabRef : undefined}
                to={item.href}
                aria-current={active ? "page" : undefined}
                className={active ? "profile-tab profile-tab--active" : "profile-tab"}
              >
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>

      <div className="profile-route">
        <Outlet />
      </div>
    </main>
  );
}

function ProfileShellStatus({ label }: { label: string }) {
  return (
    <main className="profile-shell profile-shell--loading" aria-busy="true">
      <header className="profile-topbar" aria-hidden>
        <span className="profile-loading-block profile-loading-block--brand" />
        <span className="profile-loading-block profile-loading-block--account" />
      </header>
      <nav className="profile-tabs" aria-hidden>
        <div className="profile-tabs__inner profile-tabs__inner--loading">
          {NAV.map((item) => (
            <span className="profile-loading-block profile-loading-block--tab" key={item.href} />
          ))}
        </div>
      </nav>
      <section className="profile-loading-state" role="status" aria-live="polite">
        <span className="profile-loading-state__mark" aria-hidden />
        <p>{label}</p>
        <span>Securely preparing your account details…</span>
      </section>
    </main>
  );
}
