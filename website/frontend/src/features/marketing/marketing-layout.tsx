import { AnimatePresence, MotionConfig, motion } from "motion/react";
import { Outlet, useLocation } from "react-router-dom";
import { SiteFooter } from "./components/SiteFooter";
import { SiteNavbar } from "./components/SiteNavbar";
import { SmoothNavigation } from "./components/SmoothNavigation";

// Landing design system. Every rule is scoped to `.mirra-landing` so it cannot
// reach the app routes, which are light-themed and share styles/globals.css.
// Imported here rather than in main.tsx so it ships in the marketing chunk.
import "./marketing.css";

/**
 * Chrome for the marketing site — navbar, footer, smooth scroll and route
 * transitions — scoped to this route subtree via <Outlet>. Not used by any
 * app route.
 *
 * Ported from the standalone landing site's SiteChrome. Smooth scrolling now
 * lives entirely in <SmoothNavigation>, which owns its own Lenis instance
 * (anchor handling, menu lock, teardown on unmount). The layout must not
 * create a second one — two instances fight over the scroll position, and the
 * studio has its own scroll containers that Lenis must never touch.
 *
 * The `mirra-landing` class is what activates the landing stylesheet. Without
 * it every rule in marketing.css is inert, which is exactly the property that
 * keeps the app routes safe.
 */
export default function MarketingLayout() {
  const { pathname } = useLocation();

  return (
    <MotionConfig reducedMotion="user">
      <div className="mirra-landing">
        <SmoothNavigation />
        <SiteNavbar />
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            className="site-route"
            key={pathname}
            initial={{ opacity: 0.72, y: 8, filter: "blur(4px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0.82, y: -4, filter: "blur(3px)" }}
            transition={{ duration: 0.34, ease: [0.22, 1, 0.36, 1] }}
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
        <SiteFooter />
      </div>
    </MotionConfig>
  );
}
