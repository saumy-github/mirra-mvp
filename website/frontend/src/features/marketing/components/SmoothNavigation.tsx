import Lenis from "lenis";
import { useCallback, useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";

const HEADER_OFFSET = -78;
const AUTH_PATH = /^\/(?:signin-with-chatgpt|signout-with-chatgpt|api)(?:\/|$)/;

function normalizedPath(pathname: string) {
  return pathname.replace(/\/+$/, "") || "/";
}

function targetFromHash(hash: string) {
  if (!hash || hash === "#") return document.documentElement;
  const id = decodeURIComponent(hash.slice(1));
  return document.getElementById(id) ?? document.querySelector<HTMLElement>(`[name="${CSS.escape(id)}"]`);
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

export function SmoothNavigation() {
  const pathname = useLocation().pathname;
  const navigate = useNavigate();
  const lenisRef = useRef<Lenis | null>(null);
  const reducedMotionRef = useRef(false);
  const routeChangeRef = useRef(false);

  const scrollToTarget = useCallback((target: HTMLElement, shouldFocus = true) => {
    const reducedMotion = reducedMotionRef.current;
    const lenis = lenisRef.current;
    const offset = target === document.documentElement ? 0 : HEADER_OFFSET;

    if (reducedMotion || !lenis) {
      const top = target === document.documentElement
        ? 0
        : target.getBoundingClientRect().top + window.scrollY + offset;
      window.scrollTo({ top, behavior: "auto" });
      if (shouldFocus) focusTarget(target);
      return;
    }

    const targetTop = target === document.documentElement
      ? 0
      : target.getBoundingClientRect().top + window.scrollY + offset;
    const distance = Math.abs(targetTop - window.scrollY);
    const duration = Math.min(1.2, Math.max(0.72, distance / 1500));

    lenis.scrollTo(target, {
      offset,
      duration,
      lock: false,
      easing: (time) => Math.min(1, 1.001 - 2 ** (-10 * time)),
      onComplete: () => {
        if (shouldFocus) focusTarget(target);
      },
    });
  }, []);

  const scrollToHash = useCallback((hash: string, shouldFocus = true) => {
    function seekTarget(attempt: number) {
      const target = targetFromHash(hash);
      if (target) {
        scrollToTarget(target, shouldFocus);
        return;
      }

      if (attempt < 24) {
        window.requestAnimationFrame(() => seekTarget(attempt + 1));
      }
    }

    seekTarget(0);
  }, [scrollToTarget]);

  useEffect(() => {
    const reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    reducedMotionRef.current = reducedMotionQuery.matches;

    if (!reducedMotionQuery.matches) {
      const lenis = new Lenis({
        anchors: false,
        autoRaf: true,
        lerp: 0.09,
        smoothWheel: true,
        syncTouch: false,
        wheelMultiplier: 0.9,
      });
      lenisRef.current = lenis;
      lenis.on("scroll", () => window.dispatchEvent(new CustomEvent("mirra:smooth-scroll")));
    }

    const handlePreference = (event: MediaQueryListEvent) => {
      reducedMotionRef.current = event.matches;
      if (event.matches) {
        lenisRef.current?.destroy();
        lenisRef.current = null;
      } else if (!lenisRef.current) {
        lenisRef.current = new Lenis({ anchors: false, autoRaf: true, lerp: 0.09, smoothWheel: true, syncTouch: false, wheelMultiplier: 0.9 });
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
      ) return;

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
      else if (shouldAnimate) scrollToTarget(document.documentElement, false);
    });
  }, [pathname, scrollToHash, scrollToTarget]);

  return null;
}
