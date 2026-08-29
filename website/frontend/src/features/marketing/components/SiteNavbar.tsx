import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAccount, useAuthMutations } from "@/hooks/use-shopper";
import { MIRRA_HEADER, MIRRA_NAVIGATION } from "../content";
import { MirraBrand } from "./MirraBrand";

const SITE_NAVIGATION = [
  MIRRA_NAVIGATION[0],
  { label: "Why Mirra", href: "/#why-mirra" },
  ...MIRRA_NAVIGATION.slice(1),
] as const;

type MirraViewer = {
  displayName: string;
  email: string;
};

function viewerInitials(viewer: MirraViewer) {
  const source = viewer.displayName.includes("@") ? viewer.email.split("@")[0] : viewer.displayName;
  const words = source
    .trim()
    .split(/[\s._-]+/)
    .filter(Boolean);

  return (
    words
      .slice(0, 2)
      .map((word) => word[0]?.toUpperCase())
      .join("") || "M"
  );
}

function isCurrentDestination(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  if (href.startsWith("/#")) return false;
  return pathname === href;
}

export function SiteNavbar() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const reducedMotion = useReducedMotion();
  const [menuOpen, setMenuOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const scrollState = useRef({ direction: 0 as -1 | 0 | 1, directionStart: 0, lastY: 0 });

  const { continueAsGuest } = useAuthMutations();
  const { data: account } = useAccount();
  const viewer: MirraViewer | null =
    account && !account.isGuest ? { displayName: account.displayName, email: account.email } : null;

  const accountHref = viewer ? "/profile" : MIRRA_HEADER.login.href;
  const accountLabel = viewer
    ? `Signed in as ${viewer.displayName}. Go to your profile`
    : MIRRA_HEADER.login.ariaLabel;

  const handleQuickAccess = async () => {
    try {
      setMenuOpen(false);
      await continueAsGuest.mutateAsync();
      navigate("/studio");
    } catch {
      navigate("/auth/login");
    }
  };

  useEffect(() => {
    const raf = window.requestAnimationFrame(() => {
      const y = Math.max(0, window.scrollY);
      setMenuOpen(false);
      setCollapsed(false);
      scrollState.current = { direction: 0, directionStart: y, lastY: y };
    });

    return () => window.cancelAnimationFrame(raf);
  }, [pathname]);

  useEffect(() => {
    const closeForNavigation = () => {
      setMenuOpen(false);
      setCollapsed(false);
    };

    window.addEventListener("mirra:navigation-start", closeForNavigation);
    return () => window.removeEventListener("mirra:navigation-start", closeForNavigation);
  }, []);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };

    document.body.classList.toggle("menu-open", menuOpen);
    document.body.style.overflow = menuOpen ? "hidden" : previousOverflow;
    document.addEventListener("keydown", closeOnEscape);
    window.dispatchEvent(new CustomEvent("mirra:menu-state", { detail: { open: menuOpen } }));

    return () => {
      document.body.classList.remove("menu-open");
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", closeOnEscape);
      if (menuOpen) {
        window.dispatchEvent(new CustomEvent("mirra:menu-state", { detail: { open: false } }));
      }
    };
  }, [menuOpen]);

  useEffect(() => {
    let raf = 0;

    const update = () => {
      raf = 0;
      const y = Math.max(0, window.scrollY);
      const state = scrollState.current;
      const delta = y - state.lastY;

      if (menuOpen || y < 90) {
        setCollapsed(false);
        state.direction = 0;
        state.directionStart = y;
        state.lastY = y;
        return;
      }

      if (Math.abs(delta) < 1) return;
      const direction: -1 | 1 = delta > 0 ? 1 : -1;
      if (direction !== state.direction) {
        state.direction = direction;
        state.directionStart = state.lastY;
      }

      const intentDistance = Math.abs(y - state.directionStart);
      if (direction === 1 && intentDistance >= 18) setCollapsed(true);
      if (direction === -1 && intentDistance >= 8) setCollapsed(false);
      state.lastY = y;
    };

    const requestUpdate = () => {
      if (!raf) raf = window.requestAnimationFrame(update);
    };

    window.addEventListener("scroll", requestUpdate, { passive: true });
    window.addEventListener("resize", requestUpdate, { passive: true });
    update();

    return () => {
      if (raf) window.cancelAnimationFrame(raf);
      window.removeEventListener("scroll", requestUpdate);
      window.removeEventListener("resize", requestUpdate);
    };
  }, [menuOpen]);

  return (
    <>
      <motion.header
        className={[
          "site-header home-header coast-header",
          pathname === "/join" && "is-join-surface",
          collapsed && "is-collapsed",
        ]
          .filter(Boolean)
          .join(" ")}
        initial={false}
        animate={{ y: collapsed ? -72 : 0 }}
        transition={
          reducedMotion
            ? { duration: 0 }
            : { type: "spring", stiffness: 390, damping: 42, mass: 0.82 }
        }
        onFocusCapture={() => setCollapsed(false)}
      >
        <div className="coast-nav-bar">
          <Link
            className="coast-nav-brand"
            to="/"
            aria-label={MIRRA_HEADER.homeLabel}
            onClick={() => setMenuOpen(false)}
          >
            <MirraBrand />
          </Link>

          <nav className="coast-desktop-nav" aria-label="Main navigation">
            {SITE_NAVIGATION.map((item) => (
              <Link
                to={item.href}
                key={item.label}
                aria-current={isCurrentDestination(pathname, item.href) ? "page" : undefined}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="coast-desktop-actions">
            <Link
              className={viewer ? "coast-account-link is-viewer" : "coast-account-link"}
              to={accountHref}
              aria-label={accountLabel}
            >
              {viewer && (
                <span
                  className="nav-avatar"
                  role="img"
                  aria-label={`${viewer.displayName} profile`}
                >
                  {viewerInitials(viewer)}
                </span>
              )}
              <span>{viewer ? "Profile" : MIRRA_HEADER.login.label}</span>
            </Link>
            <Link className="coast-join-cta" to={MIRRA_HEADER.demo.href}>
              {MIRRA_HEADER.demo.label}
            </Link>
          </div>

          <button
            className={["coast-nav-toggle", menuOpen && "is-open"].filter(Boolean).join(" ")}
            type="button"
            onClick={() => {
              setCollapsed(false);
              setMenuOpen((open) => !open);
            }}
            aria-controls="coast-mobile-navigation"
            aria-expanded={menuOpen}
            aria-label={menuOpen ? "Close navigation" : "Open navigation"}
          >
            <span aria-hidden="true" />
            <span aria-hidden="true" />
            <span aria-hidden="true" />
          </button>
        </div>

        <AnimatePresence initial={false}>
          {menuOpen && (
            <motion.div
              id="coast-mobile-navigation"
              className="coast-mobile-panel"
              initial={reducedMotion ? { opacity: 0 } : { opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reducedMotion ? { opacity: 0 } : { opacity: 0, y: -8 }}
              transition={
                reducedMotion
                  ? { duration: 0 }
                  : { type: "spring", stiffness: 420, damping: 42, mass: 0.82 }
              }
            >
              <nav className="coast-mobile-nav" aria-label="Mobile navigation">
                {SITE_NAVIGATION.map((item) => (
                  <Link
                    to={item.href}
                    key={item.label}
                    aria-current={isCurrentDestination(pathname, item.href) ? "page" : undefined}
                    onClick={() => setMenuOpen(false)}
                  >
                    {item.label}
                  </Link>
                ))}
              </nav>

              {viewer ? (
                <Link
                  className="coast-mobile-account"
                  to={accountHref}
                  aria-label={accountLabel}
                  onClick={() => setMenuOpen(false)}
                >
                  <span
                    className="nav-avatar"
                    role="img"
                    aria-label={`${viewer.displayName} profile`}
                  >
                    {viewerInitials(viewer)}
                  </span>
                  <span>
                    <small>Signed in</small>
                    <strong>{viewer.displayName}</strong>
                  </span>
                </Link>
              ) : (
                <div className="coast-mobile-guest-actions">
                  <button
                    type="button"
                    onClick={handleQuickAccess}
                    disabled={continueAsGuest.isPending}
                  >
                    {continueAsGuest.isPending ? "Opening…" : "Quick access"}
                  </button>
                  <Link
                    to={accountHref}
                    aria-label={accountLabel}
                    onClick={() => setMenuOpen(false)}
                  >
                    {MIRRA_HEADER.login.label}
                  </Link>
                </div>
              )}

              <Link
                className="coast-mobile-join"
                to={MIRRA_HEADER.demo.href}
                onClick={() => setMenuOpen(false)}
              >
                {MIRRA_HEADER.demo.label}
              </Link>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.header>

      <AnimatePresence>
        {menuOpen && (
          <motion.button
            type="button"
            className="coast-nav-veil"
            aria-label="Close navigation"
            onClick={() => setMenuOpen(false)}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={reducedMotion ? { duration: 0 } : { duration: 0.2 }}
          />
        )}
      </AnimatePresence>
    </>
  );
}
