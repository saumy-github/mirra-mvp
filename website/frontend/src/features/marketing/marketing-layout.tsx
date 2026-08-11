import { useEffect, useRef, useState } from "react";
import { Outlet } from "react-router-dom";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";
import Header from "./components/Header";
import MirrorCTA from "./components/MirrorCTA";
// no waitlist modal or custom cursor

gsap.registerPlugin(ScrollTrigger);

/** Single smooth-scroll instance, shared by every marketing page. Scoped to
 * this layout only — the app/studio pages have their own scroll containers
 * and would fight with Lenis. */
function useSmoothScroll() {
  useEffect(() => {
    const lenis = new Lenis({
      lerp: 0.08,
      wheelMultiplier: 0.85,
      touchMultiplier: 1.1,
      smoothWheel: true,
    });

    const raf = (time: number) => lenis.raf(time * 1000);
    lenis.on("scroll", ScrollTrigger.update);
    gsap.ticker.add(raf);
    gsap.ticker.lagSmoothing(0);

    return () => {
      gsap.ticker.remove(raf);
      lenis.destroy();
    };
  }, []);
}

/**
 * Wraps the marketing pages (Home, Pricing, Team) ported from
 * Mirra-landing-page — header, footer CTA, custom cursor, and smooth
 * scroll, all scoped to this route subtree via <Outlet>. Not used by any
 * /app route.
 */
export default function MarketingLayout() {
  useSmoothScroll();

  return (
    <div className="min-h-screen overflow-x-clip bg-bg text-ink selection:bg-orange/20">
      <Header />

      <Outlet />

      <MirrorCTA />
    </div>
  );
}
