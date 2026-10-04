import { useEffect, useRef, useState } from "react";
import {
  ArrowUpRight,
  ChevronRight,
  LayoutGrid,
  Menu,
  Ruler,
  ScanFace,
  Shirt,
  SlidersHorizontal,
  UserRound,
  X,
} from "lucide-react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { MirraLogo, MirraMark } from "@/components/ui/logo";
import { useAccount, useAuthMutations } from "@/hooks/use-shopper";
import type { ShopperAccount } from "@/integrations/mirra-api/types";
import Profile from "./Profile";
import "./profile.css";
import "./profile-refresh.css";

const PROFILE_NAV = [
  { href: "/profile", label: "Profile", icon: UserRound },
  { href: "/profile/avatar", label: "Avatar", icon: ScanFace },
  { href: "/profile/measurements", label: "Measurements", icon: Ruler },
  { href: "/profile/signature-looks", label: "My Looks", icon: Shirt },
] as const;

/** Profile navigation stays separate from each route's account data and actions. */
export default function ProfileLayout() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { data: account, isLoading } = useAccount();
  const { logout } = useAuthMutations();
  const mobileDialogRef = useRef<HTMLDialogElement>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    if (!isLoading && !account) {
      navigate(`/auth/login?next=${encodeURIComponent(pathname)}`, { replace: true });
    }
  }, [account, isLoading, navigate, pathname]);

  useEffect(() => {
    const dialog = mobileDialogRef.current;
    if (!dialog) return;
    if (mobileMenuOpen && !dialog.open) dialog.showModal();
    if (!mobileMenuOpen && dialog.open) dialog.close();
  }, [mobileMenuOpen]);

  useEffect(() => {
    const mobileWidth = window.matchMedia("(max-width: 700px)");
    const closeAtDesktopWidth = () => {
      if (!mobileWidth.matches) setMobileMenuOpen(false);
    };
    mobileWidth.addEventListener("change", closeAtDesktopWidth);
    return () => mobileWidth.removeEventListener("change", closeAtDesktopWidth);
  }, []);

  if (isLoading || !account) {
    return <ProfileShellStatus label={isLoading ? "Loading your profile" : "Opening sign in"} />;
  }

  const settingsOpen = pathname === "/profile/privacy";
  const signOut = () => logout.mutate(undefined, { onSuccess: () => navigate("/auth/login") });

  return (
    <main className="profile-shell">
      <div className="profile-frame">
        <header className="profile-mobile-bar">
          <button
            type="button"
            aria-label="Open profile navigation"
            aria-controls="profile-navigation-sheet"
            aria-expanded={mobileMenuOpen}
            onClick={() => setMobileMenuOpen(true)}
          >
            <Menu aria-hidden size={21} strokeWidth={1.5} />
          </button>
          <Link to="/" aria-label="Mirra home" className="profile-mobile-wordmark">
            <MirraLogo alt="Mirra" height={28} />
          </Link>
        </header>

        <ProfileSidebar
          account={account}
          pathname={pathname}
          onSignOut={signOut}
          signOutPending={logout.isPending}
          signOutError={!!logout.error}
        />

        <Link
          to="/studio"
          className="profile-close"
          aria-label="Close profile"
          title="Return to Studio"
        >
          <X aria-hidden size={19} strokeWidth={1.6} />
        </Link>

        <div className="profile-route">{settingsOpen ? <Profile /> : <Outlet />}</div>
      </div>

      <dialog
        id="profile-navigation-sheet"
        ref={mobileDialogRef}
        className="profile-mobile-sheet"
        aria-label="Profile navigation"
        onCancel={(event) => {
          event.preventDefault();
          setMobileMenuOpen(false);
        }}
        onClick={(event) => {
          if (event.target === event.currentTarget) setMobileMenuOpen(false);
        }}
        onClose={() => setMobileMenuOpen(false)}
      >
        <ProfileSidebar
          account={account}
          pathname={pathname}
          onNavigate={() => setMobileMenuOpen(false)}
          onClose={() => setMobileMenuOpen(false)}
          onSignOut={signOut}
          signOutPending={logout.isPending}
          signOutError={!!logout.error}
          sheet
        />
      </dialog>

      {settingsOpen && <Outlet />}
    </main>
  );
}

function ProfileSidebar({
  account,
  pathname,
  onNavigate,
  onClose,
  onSignOut,
  signOutPending,
  signOutError,
  sheet = false,
}: {
  account: ShopperAccount;
  pathname: string;
  onNavigate?: () => void;
  onClose?: () => void;
  onSignOut: () => void;
  signOutPending: boolean;
  signOutError: boolean;
  sheet?: boolean;
}) {
  const accountInitial = account.displayName.trim().charAt(0).toUpperCase() || "M";
  const settingsActive = pathname === "/profile/privacy";

  return (
    <aside className={sheet ? "profile-sidebar profile-sidebar--sheet" : "profile-sidebar"}>
      <Link to="/" aria-label="Mirra home" className="profile-wordmark" onClick={onNavigate}>
        <MirraLogo alt="Mirra" height={32} className="profile-wordmark__full" />
        <MirraMark alt="Mirra" size={32} className="profile-wordmark__compact" />
      </Link>
      {sheet && (
        <button
          type="button"
          className="profile-sheet-close"
          aria-label="Close navigation"
          onClick={onClose}
        >
          <X aria-hidden size={20} strokeWidth={1.5} />
        </button>
      )}

      <Link
        to="/studio"
        className="profile-sidebar__studio"
        aria-label="Open Studio"
        title="Open Studio"
        onClick={onNavigate}
      >
        <span>Open Studio</span>
        <ArrowUpRight
          className="profile-sidebar__studio-arrow"
          aria-hidden
          size={18}
          strokeWidth={1.5}
        />
        <LayoutGrid
          className="profile-sidebar__studio-rail-icon"
          aria-hidden
          size={20}
          strokeWidth={1.5}
        />
      </Link>

      <nav aria-label="Profile sections" className="profile-tabs">
        <div className="profile-tabs__inner">
          {PROFILE_NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                to={href}
                aria-label={label}
                title={label}
                aria-current={active ? "page" : undefined}
                className={active ? "profile-tab profile-tab--active" : "profile-tab"}
                onClick={onNavigate}
              >
                <Icon aria-hidden size={19} strokeWidth={1.5} />
                <span>{label}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      <div className="profile-sidebar__bottom">
        <nav aria-label="Account utilities">
          <Link
            to="/profile/privacy"
            aria-label="Settings"
            title="Settings"
            aria-current={settingsActive ? "page" : undefined}
            className={settingsActive ? "profile-tab profile-tab--active" : "profile-tab"}
            onClick={onNavigate}
          >
            <SlidersHorizontal aria-hidden size={19} strokeWidth={1.5} />
            <span>Settings</span>
          </Link>
        </nav>
        <details className="profile-account">
          <summary title={`${account.displayName}${account.isGuest ? "" : ` · ${account.email}`}`}>
            <span className="profile-account__initial" aria-hidden>
              {accountInitial}
            </span>
            <span className="profile-account__identity">
              <strong>{account.displayName}</strong>
              <small>{account.isGuest ? "Guest account" : account.email}</small>
            </span>
            <ChevronRight aria-hidden size={15} strokeWidth={1.5} />
          </summary>
          <div className="profile-account__menu">
            <Link to="/profile/privacy" onClick={onNavigate}>
              Account settings
            </Link>
            <button type="button" disabled={signOutPending} onClick={onSignOut}>
              {signOutPending ? "Signing out…" : "Sign out"}
            </button>
            {signOutError && (
              <span className="profile-account__error" role="alert">
                Sign out did not complete. Please try again.
              </span>
            )}
          </div>
        </details>
      </div>
    </aside>
  );
}

function ProfileShellStatus({ label }: { label: string }) {
  return (
    <main className="profile-shell profile-shell--loading" aria-busy="true">
      <div className="profile-frame">
        <aside className="profile-sidebar" aria-hidden>
          <span className="profile-loading-block profile-loading-block--brand" />
          <div className="profile-tabs__inner profile-tabs__inner--loading">
            {PROFILE_NAV.map((item) => (
              <span className="profile-loading-block profile-loading-block--tab" key={item.href} />
            ))}
          </div>
        </aside>
        <section className="profile-loading-state" role="status" aria-live="polite">
          <span className="profile-loading-state__mark" aria-hidden />
          <p>{label}</p>
          <span>Securely preparing your account details…</span>
        </section>
      </div>
    </main>
  );
}
