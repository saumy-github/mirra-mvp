import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useAccount } from "@/hooks/use-shopper";
import { useEffect, useRef, useState } from "react";
import { MIRRA_HEADER, MIRRA_LATEST_METADATA, MIRRA_NAVIGATION } from "../content";
import { LiquidCTA } from "./LiquidCTA";
import { MirraBrand } from "./MirraBrand";
import { UiIcon } from "./UiIcon";
import { Link, useLocation } from "react-router-dom";

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
  const source = viewer.displayName.includes("@")
    ? viewer.email.split("@")[0]
    : viewer.displayName;
  const words = source.trim().split(/[\s._-]+/).filter(Boolean);
  return words.slice(0, 2).map((word) => word[0]?.toUpperCase()).join("") || "M";
}

function messageForSurface(pathname: string, surface?: HTMLElement) {
  if (pathname === "/faq") return "QUESTIONS, ANSWERED";
  if (pathname === "/pricing") return "PRICING THAT SCALES";
  if (pathname !== "/") return "FIT, WITHOUT FRICTION";
  if (surface?.dataset.navLabel) return surface.dataset.navLabel;
  if (surface?.classList.contains("hero")) return "FIT, WITHOUT FRICTION";
  if (surface?.id === "why-mirra") return "WHY MIRRA";
  if (surface?.id === "outcomes") return "FOUR FIT OUTCOMES";
  if (surface?.id === "product") return "BUILT FOR STOREFRONTS";
  if (surface?.id === MIRRA_LATEST_METADATA.sectionId) return "MIRRA IN MOTION";
  if (surface?.classList.contains("testimonials")) return "TRUSTED IN THE FIT";
  if (surface?.classList.contains("app-banner")) return "SHOPIFY READY";
  if (surface?.tagName === "FOOTER") return "ONE EASIER DECISION";
  return "FIT, WITHOUT FRICTION";
}

export function SiteNavbar() {
  const pathname = useLocation().pathname;
  const reducedMotion = useReducedMotion();
  const [menuOpen, setMenuOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [message, setMessage] = useState(() => messageForSurface(pathname));
  const scrollState = useRef({ direction: 0 as -1 | 0 | 1, directionStart: 0, lastY: 0 });

  // The standalone site read a ChatGPT-hosted session off /api/auth/me. Here
  // the real account comes from the shared react-query cache that the rest of
  // the app already uses, so the navbar stays in step with login/logout
  // elsewhere instead of holding its own copy.
  //
  // Guests are deliberately treated as signed out: they have a session but no
  // profile to link to, so the useful affordance for them is still "Login".
  const { data: account } = useAccount();
  const viewer: MirraViewer | null =
    account && !account.isGuest
      ? { displayName: account.displayName, email: account.email }
      : null;

  useEffect(() => {
    const raf = window.requestAnimationFrame(() => {
      setMenuOpen(false);
      setCollapsed(false);
      setMessage(messageForSurface(pathname));
      scrollState.current = {
        direction: 0,
        directionStart: Math.max(0, window.scrollY),
        lastY: Math.max(0, window.scrollY),
      };
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
      if (menuOpen) window.dispatchEvent(new CustomEvent("mirra:menu-state", { detail: { open: false } }));
    };
  }, [menuOpen]);

  useEffect(() => {
    let raf = 0;

    const update = () => {
      raf = 0;
      const y = Math.max(0, window.scrollY);
      const state = scrollState.current;
      const delta = y - state.lastY;
      const surface = Array.from(document.querySelectorAll<HTMLElement>("[data-header], [data-nav-label]"))
        .filter((candidate) => {
          const bounds = candidate.getBoundingClientRect();
          return bounds.top <= 35 && bounds.bottom > 35;
        })
        .at(-1);

      const nextMessage = messageForSurface(pathname, surface);
      setMessage((current) => current === nextMessage ? current : nextMessage);

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
  }, [menuOpen, pathname]);

  // Signed in, the account chip goes to the profile rather than signing out —
  // sign-out lives in the profile UI, and a one-click logout sitting in the
  // marketing header is too easy to hit by accident.
  const accountHref = viewer ? "/profile" : MIRRA_HEADER.login.href;
  const accountLabel = viewer
    ? `Signed in as ${viewer.displayName}. Go to your profile`
    : MIRRA_HEADER.login.ariaLabel;

  return (
    <>
      <motion.header
        className={`site-header home-header${collapsed ? " is-collapsed" : ""}`}
        initial={false}
        animate={{ y: collapsed ? -86 : 0 }}
        transition={reducedMotion ? { duration: 0 } : { type: "spring", stiffness: 390, damping: 42, mass: 0.82 }}
        onFocusCapture={() => setCollapsed(false)}
      >
        <motion.div
          className="lama-nav-shell"
          layout
          transition={{ layout: reducedMotion ? { duration: 0 } : { duration: 0.38, ease: [0.9, 0, 0.1, 1] } }}
        >
          <span className="lama-nav-surface" aria-hidden="true" />
          <div className="lama-nav-bar">
            <Link className="lama-nav-brand" to="/" aria-label={MIRRA_HEADER.homeLabel} onClick={() => setMenuOpen(false)}>
              <MirraBrand />
            </Link>
            <span className="lama-nav-message" data-nav-message>{message}</span>
            <button
              className={`lama-nav-toggle${menuOpen ? " is-open" : ""}`}
              type="button"
              onClick={() => {
                setCollapsed(false);
                setMenuOpen((open) => !open);
              }}
              aria-controls="site-lama-navigation"
              aria-expanded={menuOpen}
              aria-label={menuOpen ? "Close navigation" : "Open navigation"}
            >
              <span aria-hidden="true" />
              <span aria-hidden="true" />
              <span aria-hidden="true" />
            </button>
          </div>

          <motion.div
            id="site-lama-navigation"
            className={`lama-nav-panel${menuOpen ? " is-open" : ""}`}
            aria-hidden={!menuOpen}
            inert={!menuOpen}
            initial={false}
            animate={menuOpen ? { height: "auto", opacity: 1 } : { height: 0, opacity: 0 }}
            transition={reducedMotion ? { duration: 0 } : { duration: 0.38, ease: [0.9, 0, 0.1, 1] }}
          >
            <nav className="lama-nav-list" aria-label="Main navigation">
              {SITE_NAVIGATION.map((item) => {
                const current = item.href === "/"
                  ? pathname === "/"
                  : item.href === "/faq" || item.href === "/pricing"
                    ? pathname === item.href
                    : false;

                return (
                  <Link
                    className="lama-nav-item"
                    to={item.href}
                    key={item.label}
                    aria-current={current ? "page" : undefined}
                    onClick={() => setMenuOpen(false)}
                  >
                    <span>{item.label}</span>
                    <UiIcon name="arrow-up-right" size={11} strokeWidth={1.2} />
                  </Link>
                );
              })}
            </nav>

            <div className="lama-nav-account-wrap">
              {viewer ? (
                <Link className="lama-nav-account" to={accountHref} aria-label={accountLabel} onClick={() => setMenuOpen(false)}>
                  <span className="nav-avatar" role="img" aria-label={`${viewer.displayName} profile`}>{viewerInitials(viewer)}</span>
                  <span className="lama-nav-account-copy">
                    <small>Signed in</small>
                    <strong>{viewer.displayName}</strong>
                  </span>
                  <UiIcon name="arrow-up-right" size={12} strokeWidth={1.2} />
                </Link>
              ) : (
                <Link className="lama-nav-account lama-nav-account--login" to={accountHref} aria-label={accountLabel} onClick={() => setMenuOpen(false)}>
                  <span>Login</span>
                  <UiIcon name="arrow-up-right" size={12} strokeWidth={1.2} />
                </Link>
              )}
            </div>

            <div className="lama-nav-panel-actions">
              <LiquidCTA href="/#product" tone="white" onClick={() => setMenuOpen(false)}>Product</LiquidCTA>
              <LiquidCTA href={MIRRA_HEADER.demo.href} tone="white" onClick={() => setMenuOpen(false)}>{MIRRA_HEADER.demo.label}</LiquidCTA>
            </div>
          </motion.div>
        </motion.div>

        <div className="lama-join-card">
          <LiquidCTA href={MIRRA_HEADER.demo.href} tone="white">{MIRRA_HEADER.demo.label}</LiquidCTA>
        </div>
      </motion.header>

      <AnimatePresence>
        {menuOpen && (
          <motion.button
            type="button"
            className="lama-nav-veil"
            aria-label="Close navigation"
            onClick={() => setMenuOpen(false)}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={reducedMotion ? { duration: 0 } : { duration: 0.32, ease: [0.9, 0, 0.1, 1] }}
          />
        )}
      </AnimatePresence>
    </>
  );
}
