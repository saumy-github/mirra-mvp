/* The horizontally scrollable regions below carry an explicit tabIndex so they
 * are keyboard focusable. The standalone site suppressed
 * jsx-a11y/no-noninteractive-tabindex here; this repo does not run jsx-a11y,
 * so the directive is kept as a note rather than a disable comment. */

import { MotionConfig, motion } from "motion/react";
import { useLayoutEffect, useRef, useState } from "react";
import { gsap } from "gsap";
import { Draggable } from "gsap/Draggable";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { LiquidCTA } from "@/features/marketing/components/LiquidCTA";
import {
  MIRRA_APP_CTA,
  MIRRA_COMMERCE_PRINCIPLES,
  MIRRA_FEATURES,
  MIRRA_HERO,
  MIRRA_LATEST_METADATA,
  MIRRA_LEARN,
  MIRRA_STORY_CARDS,
  MIRRA_TRUST,
  type RichText,
} from "@/features/marketing/content";

const HERO_EFFECTS = [
  { num: "045", type: "Scroll, Mouse Move, Infinite" },
  { num: "093", type: "Mouse Move" },
  { num: "062", type: "Mouse Move" },
  { num: "005", type: "Scroll" },
  { num: "026", type: "Scroll, Drag, Infinite" },
  { num: "096", type: "Scroll" },
  { num: "100", type: "Scroll" },
  { num: "099", type: "Scroll, Drag" },
  { num: "097", type: "Scroll" },
  { num: "025", type: "Mouse Move" },
  { num: "054", type: "Scroll" },
  { num: "059", type: "Scroll" },
  { num: "001", type: "Scroll" },
];

const LATEST = [
  { num: "111", date: "4 days ago" },
  { num: "110", date: "1 week ago" },
  { num: "109", date: "2 weeks ago" },
  { num: "108", date: "3 weeks ago" },
  { num: "107", date: "4 weeks ago" },
];

function RichCopy({ content }: { content: RichText }) {
  return (
    <>
      {content.map((segment, index) => (
        <span key={`${segment.text}-${index}`}>
          {segment.emphasis ? <strong>{segment.text}</strong> : segment.text}
          {segment.breakAfter && <br />}
        </span>
      ))}
    </>
  );
}

function PillLink({ children, href = "#latest", tone = "lime", onClick }: {
  children: string;
  href?: string;
  tone?: "lime" | "dark" | "light" | "white";
  onClick?: () => void;
}) {
  const liquidTone = tone === "lime" ? "primary" : tone;

  return (
    <LiquidCTA
      className="pill"
      href={href}
      onClick={onClick}
      tone={liquidTone}
    >
      {children}
    </LiquidCTA>
  );
}

export default function Home() {
  const pageRef = useRef<HTMLDivElement>(null);
  const heroRef = useRef<HTMLElement>(null);
  const heroViewportRef = useRef<HTMLDivElement>(null);
  const heroTrackRef = useRef<HTMLDivElement>(null);
  const featureViewportRef = useRef<HTMLDivElement>(null);
  const featureTrackRef = useRef<HTMLDivElement>(null);
  const latestViewportRef = useRef<HTMLDivElement>(null);
  const latestTrackRef = useRef<HTMLDivElement>(null);
  const testimonialViewportRef = useRef<HTMLDivElement>(null);
  const testimonialTrackRef = useRef<HTMLDivElement>(null);
  const outcomesRef = useRef<HTMLElement>(null);
  const featuresRef = useRef<HTMLElement>(null);
  const [heroIndex, setHeroIndex] = useState(6);
  const [latestIndex, setLatestIndex] = useState(0);

  useLayoutEffect(() => {
    if (!pageRef.current) return;

    gsap.registerPlugin(ScrollTrigger, Draggable);
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const desktop = window.matchMedia("(min-width: 901px)").matches;
    const draggables: Draggable[] = [];
    let autoHero = 0;
    let heroStart = 0;
    let heroResize: (() => void) | null = null;
    let mobileScrollCleanup: (() => void) | null = null;

    const context = gsap.context(() => {
      if (reducedMotion) {
        pageRef.current?.querySelectorAll("video").forEach((video) => {
          video.autoplay = false;
          video.pause();
        });
      } else {
        gsap.from(".hero-support, .hero-drag-hint, .hero-current", {
          autoAlpha: 0,
          y: 8,
          duration: 0.5,
          stagger: 0.04,
          ease: "power3.out",
        });

        gsap.utils.toArray<HTMLElement>(".section-reveal").forEach((element) => {
          gsap.from(element, {
            y: 55,
            autoAlpha: 0,
            duration: 1,
            ease: "power3.out",
            scrollTrigger: { trigger: element, start: "top 84%" },
          });
        });

        gsap.from(".learn-screen", {
          yPercent: 22,
          scale: 0.94,
          scrollTrigger: { trigger: ".learn-visual", start: "top 90%", end: "top 42%", scrub: 1 },
        });
        gsap.to(".logo-marquee-track", {
          xPercent: -50,
          duration: 30,
          repeat: -1,
          ease: "none",
        });

        const outcomePanels = gsap.utils.toArray<HTMLElement>(".outcome-panel");
        const outcomeCopies = gsap.utils.toArray<HTMLElement>(".outcome-panel-copy");
        const outcomeImages = gsap.utils.toArray<HTMLElement>(".outcome-panel-media video, .outcome-panel-media img");
        if (desktop && outcomesRef.current && outcomePanels.length && outcomeImages.length) {
          gsap.set(outcomePanels.slice(1), { clipPath: "inset(100% 0 0 0)" });
          gsap.set(outcomeCopies.slice(1), { autoAlpha: 0, y: 28 });
          gsap.set(outcomeImages, { scale: 1.055, yPercent: 3 });

          const outcomesTimeline = gsap.timeline({
            defaults: { ease: "none" },
            scrollTrigger: {
              trigger: outcomesRef.current,
              start: "top top",
              end: "bottom bottom",
              scrub: 0.65,
            },
          });

          // Give the first outcome a short moving breath before the normal
          // one-card-per-beat cadence begins. The image keeps drifting, so the
          // scroll never feels paused or locked.
          const openingBreath = 0.22;
          outcomesTimeline.to(outcomeImages[0], {
            scale: 1.045,
            yPercent: 2,
            duration: openingBreath,
          }, 0);

          outcomePanels.slice(1).forEach((panel, index) => {
            const transitionStart = index + 0.1 + openingBreath;
            outcomesTimeline
              .to(panel, { clipPath: "inset(0% 0 0 0)", duration: 0.72 }, transitionStart)
              .to(outcomeCopies[index], { autoAlpha: 0, y: -22, duration: 0.18 }, transitionStart + 0.03)
              .to(outcomeImages[index], { scale: 1.015, yPercent: -2, duration: 0.72 }, transitionStart)
              .to(outcomeCopies[index + 1], { autoAlpha: 1, y: 0, duration: 0.22 }, transitionStart + 0.43);
          });

          outcomesTimeline.to(outcomeImages.at(-1) ?? outcomeImages[0], {
            scale: 1,
            yPercent: -3,
            duration: 0.4,
          });
        }

        const featureCards = gsap.utils.toArray<HTMLElement>(".feature-card");
        if (featuresRef.current && featureCards.length) {
          featureCards.forEach((card, index) => {
            const rowOffset = ((index % 3) + 1) * (desktop ? 40 : 15);
            gsap.set(card, { autoAlpha: 0, yPercent: rowOffset });
            gsap.set(card.querySelector(".feature-media"), { clipPath: "inset(0 0 100% 0)" });
          });

          gsap.timeline({
            scrollTrigger: {
              trigger: featuresRef.current,
              start: "top 82%",
              once: true,
            },
          })
            .to(featureCards, {
              autoAlpha: 1,
              yPercent: 0,
              duration: 1.15,
              stagger: 0.08,
              ease: "power4.out",
            })
            .to(featureCards.map((card) => card.querySelector(".feature-media")), {
              clipPath: "inset(0 0 0% 0)",
              duration: 1.05,
              stagger: 0.08,
              ease: "power4.inOut",
            }, 0.08);
        }

      }

      if (!reducedMotion && desktop) {
        const makeHorizontalDrag = (
          track: HTMLDivElement | null,
          viewport: HTMLDivElement | null,
          onChange?: (index: number) => void,
        ) => {
          if (!track || !viewport) return;
          const minX = Math.min(0, viewport.clientWidth - track.scrollWidth);
          const instance = Draggable.create(track, {
            type: "x",
            bounds: { minX, maxX: 0 },
            edgeResistance: 0.86,
            dragResistance: 0.035,
            onDragEnd() {
              if (!onChange) return;
              const children = Array.from(track.children) as HTMLElement[];
              const center = viewport.clientWidth / 2;
              let closest = 0;
              let closestDistance = Infinity;
              children.forEach((child, index) => {
                const childCenter = child.offsetLeft + this.x + child.offsetWidth / 2;
                const delta = Math.abs(center - childCenter);
                if (delta < closestDistance) {
                  closest = index;
                  closestDistance = delta;
                }
              });
              onChange(closest);
            },
          })[0];
          draggables.push(instance);
          return instance;
        };
        makeHorizontalDrag(featureTrackRef.current, featureViewportRef.current);
        if (featureTrackRef.current) {
          const cards = Array.from(featureTrackRef.current.children) as HTMLElement[];
          cards.forEach((card) => {
            const rotateX = gsap.quickTo(card, "rotationX", { duration: 0.5, ease: "power3.out" });
            const rotateY = gsap.quickTo(card, "rotationY", { duration: 0.5, ease: "power3.out" });
            const onPointerMove = (event: PointerEvent) => {
              const bounds = card.getBoundingClientRect();
              const x = (event.clientX - bounds.left) / bounds.width - 0.5;
              const y = (event.clientY - bounds.top) / bounds.height - 0.5;
              rotateX(y * -5);
              rotateY(x * 5);
            };
            const resetTilt = () => {
              rotateX(0);
              rotateY(0);
            };
            card.addEventListener("pointermove", onPointerMove);
            card.addEventListener("pointerleave", resetTilt);
            draggables.push({
              kill: () => {
                card.removeEventListener("pointermove", onPointerMove);
                card.removeEventListener("pointerleave", resetTilt);
              },
            } as Draggable);
          });
        }
        const latestDraggable = makeHorizontalDrag(latestTrackRef.current, latestViewportRef.current, setLatestIndex);
        const testimonialDraggable = makeHorizontalDrag(testimonialTrackRef.current, testimonialViewportRef.current);

        // Auto-scroll for latest carousel (step by step delay)
        if (latestTrackRef.current && latestViewportRef.current) {
          const track = latestTrackRef.current;
          const viewport = latestViewportRef.current;
          const items = Array.from(track.children) as HTMLElement[];
          let currentIndex = 0;

          const autoScrollLatest = () => {
            if (draggables.some(d => d.isDragging || d.isPressed)) {
              gsap.delayedCall(5, autoScrollLatest);
              return;
            }
            currentIndex = (currentIndex + 1) % items.length;
            const item = items[currentIndex];
            const center = viewport.clientWidth / 2;
            let targetX = center - item.offsetLeft - item.offsetWidth / 2;
            const minX = Math.min(0, viewport.clientWidth - track.scrollWidth);
            targetX = Math.max(minX, Math.min(0, targetX));

            gsap.to(track, {
              x: targetX,
              duration: 1.2,
              ease: "power2.inOut",
              onUpdate: () => { latestDraggable?.update(); },
              onComplete: () => {
                setLatestIndex(currentIndex);
                gsap.delayedCall(5, autoScrollLatest);
              }
            });
          };
          gsap.delayedCall(5, autoScrollLatest);
        }

        // Continuous slow scroll for testimonials
        if (testimonialTrackRef.current && testimonialViewportRef.current) {
          const track = testimonialTrackRef.current;
          const viewport = testimonialViewportRef.current;
          const minX = Math.min(0, viewport.clientWidth - track.scrollWidth);

          const autoScrollTestimonials = () => {
            if (draggables.some(d => d.isDragging || d.isPressed)) {
              gsap.delayedCall(2, autoScrollTestimonials);
              return;
            }
            const currentX = gsap.getProperty(track, "x") as number;
            const distanceLeft = Math.abs(currentX - minX);
            const duration = distanceLeft / 50; // pixels per second

            gsap.to(track, {
              x: minX,
              duration: duration,
              ease: "none",
              onUpdate: () => { testimonialDraggable?.update(); },
              onComplete: () => {
                // Return to start and repeat
                gsap.to(track, {
                  x: 0,
                  duration: 2,
                  ease: "power2.inOut",
                  onComplete: () => { gsap.delayedCall(1, autoScrollTestimonials); }
                });
              }
            });
          };
          gsap.delayedCall(1, autoScrollTestimonials);
        }
      }

      if (!reducedMotion && !desktop) {
        const latestViewport = latestViewportRef.current;
        const latestTrack = latestTrackRef.current;
        if (latestViewport && latestTrack) {
          let frame = 0;
          const syncLatestIndex = () => {
            window.cancelAnimationFrame(frame);
            frame = window.requestAnimationFrame(() => {
              const items = Array.from(latestTrack.children) as HTMLElement[];
              const center = latestViewport.scrollLeft + latestViewport.clientWidth / 2;
              let closest = 0;
              let distance = Infinity;
              items.forEach((item, index) => {
                const delta = Math.abs(center - item.offsetLeft - item.offsetWidth / 2);
                if (delta < distance) {
                  closest = index;
                  distance = delta;
                }
              });
              setLatestIndex(closest);
            });
          };
          latestViewport.addEventListener("scroll", syncLatestIndex, { passive: true });
          mobileScrollCleanup = () => {
            window.cancelAnimationFrame(frame);
            latestViewport.removeEventListener("scroll", syncLatestIndex);
          };
        }
      }

      if (reducedMotion && desktop && heroViewportRef.current && heroTrackRef.current) {
        const viewport = heroViewportRef.current;
        const track = heroTrackRef.current;
        const items = Array.from(track.children) as HTMLElement[];
        const current = 6;
        const row = (items[0]?.offsetHeight || viewport.clientWidth * 0.5625) + 5;
        const trackY = viewport.clientHeight / 2 - row / 2 - current * row + 5;
        const activeCenter = items[current].offsetTop + items[current].offsetHeight / 2;
        const viewportCenter = viewport.clientHeight / 2;
        gsap.set(track, { y: trackY });
        items.forEach((item, index) => {
          const distance = Math.abs(index - current);
          const itemCenter = item.offsetTop + item.offsetHeight / 2;
          const naturalCenter = viewportCenter + itemCenter - activeCenter;
          const direction = index < current ? -1 : 1;
          const edgeCenter = index < current
            ? -item.offsetHeight / 2 + 40
            : viewport.clientHeight + item.offsetHeight / 2 - 40;
          const collapsedY = index === current
            ? 0
            : edgeCenter - naturalCenter + (distance > 1 ? direction * viewportCenter : 0);
          gsap.set(item, {
            y: collapsedY,
            scale: 1,
            autoAlpha: distance <= 1 ? 1 : 0,
          });
        });
      }

      if (!reducedMotion && desktop && heroViewportRef.current && heroTrackRef.current) {
        const viewport = heroViewportRef.current;
        const track = heroTrackRef.current;
        const items = Array.from(track.children) as HTMLElement[];
        let current = 6;
        let row = (items[0]?.offsetHeight || viewport.clientWidth * 0.5625) + 5;
        const positionFor = (index: number) => viewport.clientHeight / 2 - row / 2 - index * row + 5;

        const goTo = (next: number, animate = true) => {
          current = gsap.utils.clamp(0, items.length - 1, next);
          setHeroIndex(current);
          const duration = animate ? 0.8 : 0;
          const activeCenter = items[current].offsetTop + items[current].offsetHeight / 2;
          const viewportCenter = viewport.clientHeight / 2;
          gsap.to(track, { y: positionFor(current), duration, ease: "expo.inOut" });
          items.forEach((item, index) => {
            const distance = Math.abs(index - current);
            const itemCenter = item.offsetTop + item.offsetHeight / 2;
            const naturalCenter = viewportCenter + itemCenter - activeCenter;
            const direction = index < current ? -1 : 1;
            const edgeCenter = index < current
              ? -item.offsetHeight / 2 + 40
              : viewport.clientHeight + item.offsetHeight / 2 - 40;
            const collapsedY = index === current
              ? 0
              : edgeCenter - naturalCenter + (distance > 1 ? direction * viewportCenter : 0);
            gsap.to(item, {
              y: collapsedY,
              scale: 1,
              autoAlpha: distance <= 1 ? 1 : 0,
              duration,
              ease: "expo.inOut",
            });
            const video = item as HTMLVideoElement;
            if (distance <= 1) video.play().catch(() => undefined);
            else video.pause();
          });
        };
        const startAuto = (delay = 3300) => {
          window.clearTimeout(autoHero);
          autoHero = window.setTimeout(() => {
            goTo((current + 1) % items.length);
            startAuto(3300);
          }, delay);
        };
        goTo(6, false);
        const heroDrag = Draggable.create(track, {
          type: "y",
          bounds: { minY: positionFor(items.length - 1), maxY: positionFor(0) },
          edgeResistance: 0.85,
          dragResistance: 0.025,
          onPress: () => {
            window.clearTimeout(autoHero);
            window.clearTimeout(heroStart);
            heroRef.current?.classList.add("is-dragging");
            gsap.to(items, { y: 0, scale: 1, autoAlpha: 1, duration: 0.4, ease: "expo.inOut" });
            gsap.to(".hero-title, .hero-current", { autoAlpha: 0, duration: 0.3, ease: "expo.inOut" });
            gsap.to(".hero-meta", { autoAlpha: 1, duration: 0.3, delay: 0.1, ease: "expo.inOut" });
          },
          onDrag() {
            const index = gsap.utils.clamp(0, items.length - 1, Math.round((viewport.clientHeight / 2 - row / 2 - this.y) / row));
            if (index !== current) {
              current = index;
              setHeroIndex(index);
            }
          },
          onRelease() {
            const next = Math.round((viewport.clientHeight / 2 - row / 2 - this.y) / row);
            goTo(next);
            heroRef.current?.classList.remove("is-dragging");
            gsap.to(".hero-meta", { autoAlpha: 0, duration: 0.3, ease: "expo.inOut" });
            gsap.to(".hero-title, .hero-current", { autoAlpha: 1, duration: 0.3, delay: 0.1, ease: "expo.inOut" });
            startAuto();
          },
        })[0];
        draggables.push(heroDrag);
        heroStart = window.setTimeout(() => {
          goTo((current + 1) % items.length);
          startAuto();
        }, 4200);

        heroResize = () => {
          row = (items[0]?.offsetHeight || viewport.clientWidth * 0.5625) + 5;
          goTo(current, false);
          heroDrag.applyBounds({ minY: positionFor(items.length - 1), maxY: positionFor(0) });
        };
        window.addEventListener("resize", heroResize);
      }

      if (!reducedMotion) {
        const appBanner = pageRef.current?.querySelector<HTMLElement>(".app-banner");
        if (appBanner) {
          gsap.fromTo(appBanner, {
            y: 72,
            scale: 0.975,
            clipPath: "inset(14% 0 0 0 round 20px)",
          }, {
            y: 0,
            scale: 1,
            clipPath: "inset(0% 0 0 0 round 20px)",
            ease: "none",
            scrollTrigger: {
              trigger: appBanner,
              start: "top 90%",
              end: "top 42%",
              scrub: 0.8,
            },
          });
          gsap.fromTo(appBanner.querySelector("img"), { x: 28, scale: 1.045 }, {
            x: 0,
            scale: 1,
            ease: "none",
            scrollTrigger: {
              trigger: appBanner,
              start: "top 90%",
              end: "top 42%",
              scrub: 0.8,
            },
          });
        }
      }

      ScrollTrigger.refresh();
    }, pageRef);

    return () => {
      window.clearTimeout(autoHero);
      window.clearTimeout(heroStart);
      if (heroResize) window.removeEventListener("resize", heroResize);
      mobileScrollCleanup?.();
      draggables.forEach((instance) => instance.kill());
      context.revert();
    };
  }, []);

  const currentHero = HERO_EFFECTS[heroIndex];

  return (
    <MotionConfig reducedMotion="user">
    <div className="site" ref={pageRef}>
      <main>
        <section className="hero light-section" id="top" ref={heroRef} data-header="dark">
          <h1 className="sr-only">{MIRRA_HERO.accessibleTitle}</h1>
          <div className="hero-title" aria-hidden="true">
            {MIRRA_HERO.titleLines.map((line, index) => (
              <div data-side={index === 0 ? "left" : "right"} key={line}>{line.split(" ").map((word) => <span className="hero-word" key={word}>{word} </span>)}</div>
            ))}
          </div>
          <div className="hero-meta label">
            <span>#{currentHero.num}</span>
            <span>{currentHero.type}</span>
            <span>#VTO</span>
          </div>
          <div className="hero-current label">#{currentHero.num}</div>
          <div className="hero-reel-viewport" ref={heroViewportRef}>
            <div className="hero-reel-track" ref={heroTrackRef}>
              {HERO_EFFECTS.map((effect) => (
                <video
                  className="hero-video"
                  key={effect.num}
                  src={`/mwg/video-effect-${effect.num}.mp4`}
                  poster={`/mwg/thumb-${effect.num}.webp`}
                  muted
                  loop
                  playsInline
                  preload="metadata"
                  aria-label={`Effect ${effect.num}: ${effect.type}`}
                />
              ))}
            </div>
          </div>
          <p className="hero-support body-copy">
            {MIRRA_HERO.supportLines.map((line, index) => (
              <span key={index}>
                {line}
                {index < MIRRA_HERO.supportLines.length - 1 && <br />}
              </span>
            ))}
          </p>
          <p className="hero-drag-hint label">Drag to explore Mirra</p>
          <div className="hero-mobile-cta"><PillLink href={`#${MIRRA_LATEST_METADATA.sectionId}`} tone="dark">See Mirra in action</PillLink></div>
        </section>

        <section className="learn dark-section" id="why-mirra" data-header="light">
          <p className="eyebrow section-reveal">{MIRRA_LEARN.eyebrow}</p>
          <h2 className="section-title section-reveal"><RichCopy content={MIRRA_LEARN.title} /></h2>
          <p className="learn-copy body-copy section-reveal">{MIRRA_LEARN.body}</p>
          <div className="learn-visual section-reveal">
            <img className="learn-screen" src="/mwg/screen.png" alt="Mirra virtual try-on interface preview" />
            <p>Designed for Shopify storefronts</p>
          </div>
        </section>

        <section className="trust dark-section" data-header="light">
          <div className="people-row">
            {MIRRA_TRUST.peopleImages.map((image) => <img key={image} src={image} alt="" />)}
          </div>
          <p className="label"><strong>{MIRRA_TRUST.peopleLabel}</strong><br />&amp; {MIRRA_TRUST.brandsLabel}</p>
          <div className="logo-marquee" aria-label={MIRRA_TRUST.brandLogosAriaLabel}>
            <div className="logo-marquee-track">
              {[...MIRRA_TRUST.brandLogos, ...MIRRA_TRUST.brandLogos].map((logo, index) => (
                <img key={`${logo}-${index}`} src={logo} alt="" />
              ))}
            </div>
          </div>
        </section>

        <section className="cards-story dark-section" id="outcomes" data-header="light" ref={outcomesRef}>
          <h2 className="sr-only">Four commercial outcomes</h2>
          <div className="cards-story-inner">
            {MIRRA_STORY_CARDS.map((card, index) => (
              <article className={`outcome-panel outcome-panel--${card.color}`} key={card.number}>
                <div className="outcome-panel-media" aria-hidden={card.media ? undefined : true}>
                  {card.media ? (
                    <img src={card.media.src} alt={card.media.alt} />
                  ) : (
                    <video
                      src={`/mwg/video-effect-${LATEST[index].num}.mp4`}
                      poster={`/mwg/thumb-${LATEST[index].num}.webp`}
                      muted
                      loop
                      playsInline
                      autoPlay
                      preload="metadata"
                    />
                  )}
                </div>
                <div className="outcome-panel-shade" aria-hidden="true" />
                <div className="outcome-panel-copy">
                  <div className="outcome-panel-meta">
                    <span className="label">0{card.number}</span>
                    <span className="outcome-chip label">Mirra outcome</span>
                  </div>
                  <span className="outcome-rule" aria-hidden="true" />
                  <div className="outcome-panel-content">
                    <p className="label">Fit confidence</p>
                    <div>
                      <h3>{card.titleLines.map((line) => <span key={line}>{line}</span>)}</h3>
                      <p className="outcome-panel-body"><RichCopy content={card.body} /></p>
                      <PillLink href="#product" tone="white">See how it works</PillLink>
                    </div>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="features dark-section" id="product" data-header="light" ref={featuresRef}>
          <h2 className="section-title section-reveal">Meet the Mirra features that keep the <em>fit decision</em> in your store</h2>
          <div className="horizontal-viewport" ref={featureViewportRef} role="region" tabIndex={0} aria-label="Mirra product features">
            <div className="feature-track drag-track" ref={featureTrackRef}>
              {MIRRA_FEATURES.map((feature) => (
                <article className={`feature-card feature-card--tone-${(Number(feature.number) - 1) % 4}${feature.featured ? " feature-card--featured" : ""}`} key={feature.number}>
                  <div className="feature-card-top">
                    <div>
                      <p className="feature-kicker label">{feature.label}</p>
                      <h3>{feature.titleLines.map((line) => <span key={line}>{line}</span>)}</h3>
                    </div>
                    <span className="feature-number label">{feature.number}</span>
                  </div>
                  <div className="feature-media">
                    <video
                      src={feature.media.video}
                      poster={feature.media.poster}
                      muted
                      loop
                      playsInline
                      autoPlay
                      preload="metadata"
                      aria-label={feature.media.alt}
                    />
                    {feature.featured && (
                      <motion.span
                        className="fit-scan"
                        aria-hidden="true"
                        animate={{ x: ["-110%", "210%"] }}
                        transition={{ duration: 3.4, ease: "easeInOut", repeat: Infinity, repeatDelay: 0.5 }}
                      />
                    )}
                  </div>
                  <div className="feature-card-bottom">
                    <p className="feature-body"><RichCopy content={feature.body} /></p>
                    {feature.supporting && <p className="feature-support"><RichCopy content={feature.supporting} /></p>}
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="latest light-panel" id={MIRRA_LATEST_METADATA.sectionId} data-header="dark">
          <h2 className="display-title section-reveal"><span>{MIRRA_LATEST_METADATA.heading.primary}</span><br /><em>{MIRRA_LATEST_METADATA.heading.secondary}</em></h2>
          <div className="horizontal-viewport latest-viewport" ref={latestViewportRef} role="region" tabIndex={0} aria-label="Mirra try-on examples">
            <div className="latest-track drag-track" ref={latestTrackRef}>
              {LATEST.map((effect) => (
                <article className="latest-card" key={effect.num}>
                  <video src={`/mwg/video-effect-${effect.num}.mp4`} poster={`/mwg/thumb-${effect.num}.webp`} muted loop playsInline autoPlay preload="metadata" />
                </article>
              ))}
            </div>
          </div>
          <div className="latest-data" data-active-index={latestIndex}>
            <span className="latest-brand-button">{MIRRA_LATEST_METADATA.brandLabel}</span>
            <LiquidCTA className="latest-try-on" href={`#${MIRRA_APP_CTA.sectionId}`} compact tone="dark">
              {MIRRA_LATEST_METADATA.tryOnLabel}
            </LiquidCTA>
          </div>

        </section>

        <section className="testimonials dark-section" data-header="light">
          <p className="eyebrow">Commerce principles / 07</p>
          <h2 className="community-title section-reveal">Designed around the realities of fashion retail</h2>
          <div className="horizontal-viewport testimonial-viewport" ref={testimonialViewportRef} role="region" tabIndex={0} aria-label="Mirra commerce principles">
            <div className="testimonial-track drag-track" ref={testimonialTrackRef}>
              {MIRRA_COMMERCE_PRINCIPLES.map((principle) => (
                <article className="testimonial" key={principle.title}>
                  <p>{principle.body}</p>
                  <div className="testimonial-person">
                    <span className="label">{principle.title}</span>
                  </div>
                  <i aria-hidden="true" />
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="app-banner dark-section" id={MIRRA_APP_CTA.sectionId} data-header="light">
          <div className="app-copy">
            <p className="eyebrow">{MIRRA_APP_CTA.eyebrow}</p>
            <h2>
              <span>Add </span>Mirra<span> to the store</span><br />
              <span>you already </span>run.
            </h2>
            <PillLink href={MIRRA_APP_CTA.action.href} tone="white">{MIRRA_APP_CTA.action.label}</PillLink>
            <p className="app-note label">{MIRRA_APP_CTA.note}</p>
          </div>
          <img src={MIRRA_APP_CTA.media.src} alt={MIRRA_APP_CTA.media.alt} />
        </section>

      </main>

    </div>
    </MotionConfig>
  );
}
