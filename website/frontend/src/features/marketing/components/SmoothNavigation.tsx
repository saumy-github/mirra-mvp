import Lenis from "lenis";
import { useCallback, useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";

const AUTH_PATH = /^\/(?:signin-with-chatgpt|signout-with-chatgpt|api)(?:\/|$)/;
const LENIS_OPTIONS = {
  anchors: false,
  autoRaf: true,
  lerp: 0.075,
  smoothWheel: true,
  syncTouch: false,
  wheelMultiplier: 0.8,
} as const;

function normalizedPath(pathname: string) {
  return pathname.replace(/\/+$/, "") || "/";
}

function targetFromHash(hash: string) {
  if (!hash || hash === "#") return document.documentElement;
  const id = decodeURIComponent(hash.slice(1));
  return (
    document.getElementById(id) ?? document.querySelector<HTMLElement>(`[name="${CSS.escape(id)}"]`)
  );
}

function focusTarget(target: HTMLElement) {
  if (target === document.documentElement) return;
  const hadTabIndex = target.hasAttribute("tabindex");
  if (!hadTabIndex) target.setAttribute("tabindex", "-1");
  target.focus({ preventScroll: true });
  if (!hadTabIndex) {
    target.addEventListener("blur", () => target.removeAttribute("tabindex"), { once: true });
  }
}

function scrollMarginTop(target: HTMLElement) {
  if (target === document.documentElement) return 0;
  return Number.parseFloat(window.getComputedStyle(target).scrollMarginTop) || 0;
}

function targetScrollTop(target: HTMLElement) {
  if (target === document.documentElement) return 0;
  return target.getBoundingClientRect().top + window.scrollY - scrollMarginTop(target);
}

export function SmoothNavigation() {
  const pathname = useLocation().pathname;
  const navigate = useNavigate();
  const lenisRef = useRef<Lenis | null>(null);
  const reducedMotionRef = useRef(false);
  const routeChangeRef = useRef(false);
  const scrollRequestRef = useRef(0);

  const scrollToTarget = useCallback((target: HTMLElement, shouldFocus = true) => {
    const reducedMotion = reducedMotionRef.current;
    const lenis = lenisRef.current;
    const targetTop = targetScrollTop(target);

    if (reducedMotion || !lenis) {
      window.scrollTo({ top: targetTop, behavior: "auto" });
      if (shouldFocus) focusTarget(target);
      return;
    }

    const distance = Math.abs(targetTop - window.scrollY);
    const duration = Math.min(1.65, 0.72 + distance / 2400);

    lenis.scrollTo(targetTop, {
      offset: 0,
      duration,
      lock: false,
      easing: (time) => (1 - Math.cos(Math.PI * time)) / 2,
      onComplete: () => {
        if (shouldFocus) focusTarget(target);
      },
    });
  }, []);

  const scrollToHash = useCallback(
    (hash: string, shouldFocus = true) => {
      const request = ++scrollRequestRef.current;
      const startedAt = window.performance.now();

      function seekTarget() {
        if (request !== scrollRequestRef.current) return;

        const target = targetFromHash(hash);
        if (target) {
          window.requestAnimationFrame(() => {
            window.requestAnimationFrame(() => {
              if (request === scrollRequestRef.current) {
                scrollToTarget(target, shouldFocus);
                window.setTimeout(() => {
                  if (request !== scrollRequestRef.current) return;
                  const settledTarget = targetFromHash(hash);
                  if (!settledTarget) return;
                  const alignmentError =
                    settledTarget.getBoundingClientRect().top - scrollMarginTop(settledTarget);
                  if (Math.abs(alignmentError) > 4) {
                    scrollToTarget(settledTarget, false);
                  }
                }, 1200);
              }
            });
          });
          return;
        }

        if (window.performance.now() - startedAt < 3000) {
          window.requestAnimationFrame(seekTarget);
        }
      }

      void document.fonts.ready.then(() => {
        if (request !== scrollRequestRef.current) return;
        window.requestAnimationFrame(() => window.requestAnimationFrame(seekTarget));
      });
    },
    [scrollToTarget],
  );

  useEffect(() => {
    const reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    reducedMotionRef.current = reducedMotionQuery.matches;
    const notifyScroll = () => window.dispatchEvent(new CustomEvent("mirra:smooth-scroll"));
    const createLenis = () => {
      const lenis = new Lenis(LENIS_OPTIONS);
      lenis.on("scroll", notifyScroll);
      lenisRef.current = lenis;
    };

    if (!reducedMotionQuery.matches) {
      createLenis();
    }

    const handlePreference = (event: MediaQueryListEvent) => {
      reducedMotionRef.current = event.matches;
      if (event.matches) {
        lenisRef.current?.destroy();
        lenisRef.current = null;
      } else if (!lenisRef.current) {
        createLenis();
      }
    };

    const handleMenuState = (event: Event) => {
      const open = (event as CustomEvent<{ open: boolean }>).detail.open;
      if (open) lenisRef.current?.stop();
      else lenisRef.current?.start();
    };

    reducedMotionQuery.addEventListener("change", handlePreference);
    window.addEventListener("mirra:menu-state", handleMenuState);

    return () => {
      scrollRequestRef.current += 1;
      reducedMotionQuery.removeEventListener("change", handlePreference);
      window.removeEventListener("mirra:menu-state", handleMenuState);
      lenisRef.current?.destroy();
      lenisRef.current = null;
    };
  }, []);

  useEffect(() => {
    const handleClick = (event: MouseEvent) => {
      if (
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      )
        return;

      const origin = event.target;
      if (!(origin instanceof Element)) return;
      const anchor = origin.closest<HTMLAnchorElement>("a[href]");
      if (!anchor || anchor.target === "_blank" || anchor.hasAttribute("download")) return;

      const url = new URL(anchor.href, window.location.href);
      if (url.origin !== window.location.origin || AUTH_PATH.test(url.pathname)) return;

      const currentPath = normalizedPath(window.location.pathname);
      const targetPath = normalizedPath(url.pathname);
      const sameDocument = currentPath === targetPath && url.search === window.location.search;

      if (sameDocument) {
        const target = targetFromHash(url.hash);
        if (!target) return;
        event.preventDefault();
        event.stopPropagation();
        scrollRequestRef.current += 1;
        window.dispatchEvent(new Event("mirra:navigation-start"));
        const nextUrl = `${url.pathname}${url.search}${url.hash}`;
        window.history.pushState(null, "", nextUrl);
        window.requestAnimationFrame(() => {
          lenisRef.current?.start();
          scrollToTarget(target);
        });
        return;
      }

      event.preventDefault();
      event.stopPropagation();
      window.dispatchEvent(new Event("mirra:navigation-start"));
      routeChangeRef.current = true;
      navigate(`${url.pathname}${url.search}${url.hash}`);
    };

    const handleHistory = () => scrollToHash(window.location.hash, false);

    document.addEventListener("click", handleClick, true);
    window.addEventListener("popstate", handleHistory);
    window.addEventListener("hashchange", handleHistory);

    return () => {
      document.removeEventListener("click", handleClick, true);
      window.removeEventListener("popstate", handleHistory);
      window.removeEventListener("hashchange", handleHistory);
    };
  }, [navigate, scrollToHash, scrollToTarget]);

  useEffect(() => {
    const shouldAnimate = routeChangeRef.current;
    routeChangeRef.current = false;
    const hash = window.location.hash;

    window.requestAnimationFrame(() => {
      if (hash) scrollToHash(hash, true);
      else {
        scrollRequestRef.current += 1;
        if (shouldAnimate) scrollToTarget(document.documentElement, false);
      }
    });
  }, [pathname, scrollToHash, scrollToTarget]);

  return null;
}
