import React, { useLayoutEffect, useRef, useState } from "react";
import gsap from "gsap";
import { CustomEase } from "gsap/CustomEase";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";
import "./ProductReveal.css";

gsap.registerPlugin(ScrollTrigger, SplitText, CustomEase);
CustomEase.create("mirra-gap-transition", "0.22, 1, 0.36, 1");

const gapFrames = [
  {
    src: "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=900&q=85",
    alt: "Fashion model in a vibrant editorial street-style look",
    className: "is-street",
  },
  {
    src: "https://images.unsplash.com/photo-1509631179647-0177331693ae?auto=format&fit=crop&w=900&q=85",
    alt: "Fashion model walking in an editorial runway setting",
    className: "is-runway",
  },
  {
    src: "https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=900&q=85",
    alt: "Curated clothing displayed on a fashion retail rail",
    className: "is-rail",
  },
  {
    src: "https://images.unsplash.com/photo-1539109136881-3be0616acf4b?auto=format&fit=crop&w=900&q=85",
    alt: "Fashion portrait featuring a structured tailored outfit",
    className: "is-tailoring",
  },
  {
    src: "https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=900&q=85",
    alt: "Editorial fashion portrait in a contemporary outfit",
    className: "is-editorial",
  },
];

const featureSteps = [
  {
    number: "01",
    text: "Start with the digital assets and tech packs you already have",
    kicker: "Product inputs",
  },
  {
    number: "02",
    text: "Turn flat product media into a realistic 3D garment",
    kicker: "3D garment",
  },
  {
    number: "03",
    text: "Add Try On beside the imagery already on your product page",
    kicker: "Shopify app block",
  },
  {
    number: "04",
    text: "Let shoppers see exactly how the garment sits in-browser",
    kicker: "In-browser try-on",
  },
  {
    number: "05",
    text: "Turn uncertain sizing into a visible fit decision",
    kicker: "Fit decision",
  },
  {
    number: "06",
    text: "Protect retained margin before reverse logistics begins",
    kicker: "Retained margin",
  },
];

const clamp = (value: number, min = 0, max = 1) => Math.min(max, Math.max(min, value));
const lerp = (from: number, to: number, progress: number) => from + (to - from) * progress;

function inverseLerp(value: number, from: number, to: number) {
  if (from === to) return 0;
  return clamp((value - from) / (to - from));
}

export default function ProductReveal() {
  const gapRef = useRef<HTMLElement>(null);
  const introRef = useRef<HTMLElement>(null);
  const featureRef = useRef<HTMLElement>(null);
  const innerRef = useRef<HTMLDivElement>(null);
  const counterRef = useRef<HTMLDivElement>(null);
  const scrollItemsRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLOListElement>(null);
  const visualRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<Array<HTMLLIElement | null>>([]);
  const copyRefs = useRef<Array<HTMLParagraphElement | null>>([]);
  const activeStepRef = useRef(0);
  const [activeStep, setActiveStep] = useState(0);

  useLayoutEffect(() => {
    const section = gapRef.current;
    if (!section) return;

    const headings = Array.from(section.querySelectorAll(".mirra-gap__heading")) as HTMLElement[];
    const cover = section.querySelector<HTMLElement>(".mirra-gap__cards-entry");
    const images = Array.from(section.querySelectorAll(".mirra-gap__card")) as HTMLElement[];
    const sticky = section.querySelector<HTMLElement>(".mirra-gap__sticky");
    if (!cover || !sticky || headings.length !== 2 || images.length === 0) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const splits: SplitText[] = [];
    let activeImage = 0;
    let intervalId: number | undefined;

    const context = gsap.context(() => {
      gsap.set(headings[0], { x: "-30vw" });
      gsap.set(headings[1], { x: "30vw" });
      gsap.set(cover, {
        clipPath: reduceMotion
          ? "inset(0% 0% 0% 0% round 0.25rem)"
          : "inset(50% 50% 50% 50% round 0.25rem)",
      });
      gsap.set(images, { opacity: (index: number) => (index === 0 ? 1 : 0) });

      if (reduceMotion) {
        gsap.set(headings, { x: 0 });
        return;
      }

      const switchImage = () => {
        gsap.set(images[activeImage], { opacity: 0 });
        activeImage = (activeImage + 1) % images.length;
        gsap.set(images[activeImage], { opacity: 1 });
      };

      const startCycling = () => {
        if (intervalId !== undefined || images.length <= 1) return;
        intervalId = window.setInterval(switchImage, 800);
      };

      const stopCycling = () => {
        if (intervalId === undefined) return;
        window.clearInterval(intervalId);
        intervalId = undefined;
      };

      ScrollTrigger.create({
        trigger: section,
        start: "top bottom",
        end: "bottom top",
        onEnter: startCycling,
        onLeave: stopCycling,
        onEnterBack: startCycling,
        onLeaveBack: stopCycling,
      });

      gsap
        .timeline({
          scrollTrigger: {
            trigger: section,
            start: "top 50%",
            end: "bottom top",
            scrub: true,
            invalidateOnRefresh: true,
          },
        })
        .to(headings, {
          x: "0vw",
          duration: 1.075,
          ease: "mirra-gap-transition",
        })
        .fromTo(
          cover,
          { clipPath: "inset(50% 50% 50% 50% round 0.25rem)" },
          {
            clipPath: "inset(0% 0% 0% 0% round 0.25rem)",
            duration: 1.075,
            ease: "mirra-gap-transition",
          },
          "<",
        );

      headings.forEach((heading) => {
        const isLeft = heading.classList.contains("is-left");
        const split = new SplitText(heading, {
          type: "chars",
          charsClass: "mirra-gap__char",
        });
        splits.push(split);

        gsap.set(split.chars, {
          display: "inline-block",
          x: isLeft ? -80 : 80,
          scaleY: 0.95,
          opacity: 0,
        });

        gsap.to(split.chars, {
          keyframes: {
            "40%": { opacity: 1 },
            "90%": { x: 0, scaleY: 1 },
            "100%": {},
          },
          duration: 1,
          ease: "expo.out",
          stagger: {
            each: 0.022,
            from: isLeft ? "end" : "start",
          },
          scrollTrigger: {
            trigger: sticky,
            start: "top 50%",
            end: "bottom top",
            scrub: 0.5,
            invalidateOnRefresh: true,
          },
        });
      });

      ScrollTrigger.refresh();
    }, section);

    return () => {
      if (intervalId !== undefined) window.clearInterval(intervalId);
      splits.forEach((split) => split.revert());
      context.revert();
    };
  }, []);

  useLayoutEffect(() => {
    const section = introRef.current;
    const highlightedCopy = section?.querySelector<HTMLElement>("strong");
    if (!section || !highlightedCopy) return;

    let split: SplitText | undefined;
    const context = gsap.context(() => {
      split = new SplitText(highlightedCopy, {
        type: "words,chars",
        wordsClass: "mirra-intro__word",
        charsClass: "mirra-intro__char",
      });

      const chars = (split.chars as HTMLElement[]).filter((char) => char.textContent?.trim());
      const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

      if (reduceMotion) {
        gsap.set(chars, { color: "#1f1825" });
        return;
      }

      gsap
        .timeline({
          scrollTrigger: {
            trigger: section,
            start: "top 40%",
          },
        })
        .to(
          chars,
          {
            color: "#a9364a",
            duration: 0.4,
            stagger: 0.05,
            ease: "power2.inOut",
          },
          0,
        )
        .to(
          chars,
          {
            color: "#1f1825",
            duration: 0.5,
            stagger: 0.05,
            ease: "power2.inOut",
          },
          0.25,
        );
    }, section);

    return () => {
      context.revert();
      split?.revert();
    };
  }, []);

  useLayoutEffect(() => {
    const section = featureRef.current;
    const inner = innerRef.current;
    const counter = counterRef.current;
    const scrollItems = scrollItemsRef.current;
    const list = listRef.current;
    const visual = visualRef.current;

    if (!section || !inner || !counter || !scrollItems || !list || !visual) return;

    const splits: SplitText[] = [];
    const characterGroups: HTMLElement[][] = [];
    const mediaQuery = gsap.matchMedia();
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let metrics: Array<{ y: number; height: number }> = [];
    let refreshFrame = 0;

    const commitActiveStep = (nextStep: number) => {
      const safeStep = clamp(nextStep, 0, featureSteps.length - 1);
      if (safeStep === activeStepRef.current) return;
      activeStepRef.current = safeStep;
      setActiveStep(safeStep);
    };

    const setCharacterProgress = (totalProgress: number) => {
      characterGroups.forEach((chars, itemIndex) => {
        const itemProgress = clamp(totalProgress - itemIndex);
        const visibleCharacters = itemProgress * chars.length;

        chars.forEach((char, charIndex) => {
          char.classList.toggle("is-revealed", visibleCharacters > charIndex);
        });
      });
    };

    const measure = () => {
      metrics = itemRefs.current.map((item) => ({
        y: item?.offsetTop ?? 0,
        height: item?.offsetHeight ?? 0,
      }));
    };

    const context = gsap.context(() => {
      copyRefs.current.forEach((copy) => {
        if (!copy) return;

        const split = new SplitText(copy, {
          type: "words,chars",
          wordsClass: "mirra-features__word",
          charsClass: "mirra-features__char",
        });
        const chars = (split.chars as HTMLElement[]).filter((char) => char.textContent?.trim());

        chars.forEach((char, charIndex) => {
          char.style.setProperty("--mirra-char-delay", `${Math.round(charIndex * 1.4) / 100}s`);
        });

        splits.push(split);
        characterGroups.push(chars);
      });

      measure();
      visual.style.setProperty("--mirra-notch-y", "30%");

      if (reduceMotion) {
        setCharacterProgress(featureSteps.length);
      }

      mediaQuery.add("(min-width: 1024px)", () => {
        const headerEase = gsap.parseEase("power2.out");
        gsap.set(counter, { y: "-10rem" });

        ScrollTrigger.create({
          trigger: inner,
          start: "top bottom",
          end: "top 15%",
          invalidateOnRefresh: true,
          onUpdate: ({ progress }) => {
            gsap.set(counter, { y: `${lerp(-10, 0, headerEase(progress))}rem` });
          },
        });

        ScrollTrigger.create({
          trigger: inner,
          start: "top bottom",
          end: "top 30%",
          scrub: 0,
          invalidateOnRefresh: true,
          onUpdate: ({ progress }) => {
            if (!reduceMotion && progress < 1) setCharacterProgress(progress);
          },
        });

        ScrollTrigger.create({
          trigger: scrollItems,
          start: "top 50%",
          end: "bottom 50%",
          scrub: 0,
          invalidateOnRefresh: true,
          onRefresh: measure,
          onUpdate: ({ progress }) => {
            if (metrics.length === 0) return;

            const listPosition = progress * list.offsetHeight;
            let activeIndex = metrics.findIndex((item) => item.y > listPosition + 25);
            activeIndex = activeIndex === -1 ? metrics.length - 1 : Math.max(0, activeIndex - 1);
            commitActiveStep(activeIndex);

            visual.style.setProperty("--mirra-notch-y", `${lerp(30, 70, progress)}%`);

            if (reduceMotion) return;

            let revealIndex = metrics.findIndex((item) => item.y > listPosition + 50);
            revealIndex = revealIndex === -1 ? metrics.length - 1 : Math.max(0, revealIndex - 1);

            if (revealIndex < 1) {
              setCharacterProgress(1);
              return;
            }

            const activeMetric = metrics[revealIndex];
            const itemProgress = inverseLerp(
              listPosition,
              activeMetric.y - 50,
              activeMetric.y + activeMetric.height - 50,
            );
            setCharacterProgress(revealIndex + itemProgress);
          },
        });

        return () => {
          gsap.set(counter, { clearProps: "transform" });
        };
      });

      mediaQuery.add("(max-width: 1023px)", () => {
        const updateMobileStep = () => {
          const items = itemRefs.current.filter((item): item is HTMLLIElement => Boolean(item));
          if (items.length === 0) return;

          const padding = Number.parseFloat(window.getComputedStyle(list).paddingLeft) || 0;
          const nextStep = items.reduce((closestIndex, item, itemIndex) => {
            const currentDistance = Math.abs(
              items[closestIndex].offsetLeft - list.scrollLeft - padding,
            );
            const candidateDistance = Math.abs(item.offsetLeft - list.scrollLeft - padding);
            return candidateDistance < currentDistance ? itemIndex : closestIndex;
          }, 0);

          commitActiveStep(nextStep);
        };

        characterGroups.forEach((chars) => {
          chars.forEach((char) => char.classList.remove("is-revealed"));
        });
        list.addEventListener("scroll", updateMobileStep, { passive: true });
        updateMobileStep();

        return () => list.removeEventListener("scroll", updateMobileStep);
      });

      ScrollTrigger.addEventListener("refreshInit", measure);
      refreshFrame = window.requestAnimationFrame(() => ScrollTrigger.refresh());
    }, section);

    return () => {
      window.cancelAnimationFrame(refreshFrame);
      ScrollTrigger.removeEventListener("refreshInit", measure);
      mediaQuery.revert();
      context.revert();
      splits.forEach((split) => split.revert());
    };
  }, []);

  const moveMobileStep = (direction: -1 | 1) => {
    const list = listRef.current;
    if (!list) return;

    const nextStep = clamp(activeStepRef.current + direction, 0, featureSteps.length - 1);
    const target = itemRefs.current[nextStep];
    if (!target) return;

    const padding = Number.parseFloat(window.getComputedStyle(list).paddingLeft) || 0;
    list.scrollTo({ left: target.offsetLeft - padding, behavior: "smooth" });
  };

  return (
    <>
      <section ref={gapRef} className="mirra-gap" aria-label="We close that gap">
        <div className="mirra-gap__sticky">
          <div className="mirra-gap__stage">
            <div className="mirra-gap__headline" aria-label="We close that gap">
              <h2 className="mirra-gap__heading is-left" aria-label="We close">
                We close&lrm;&lrm;&lrm;&lrm;&lrm;&lrm;{" "}
              </h2>
              <h2 className="mirra-gap__heading is-right" aria-label="that gap">
                that gap
              </h2>
            </div>

            <div className="mirra-gap__cards-anchor" aria-hidden="true">
              <div className="mirra-gap__cards-entry">
                <div className="mirra-gap__cards">
                  {gapFrames.map((frame) => (
                    <figure
                      className={`mirra-gap__card ${frame.className}`}
                      key={`${frame.src}-${frame.className}`}
                    >
                      <img src={frame.src} alt={frame.alt} />
                    </figure>
                  ))}
                </div>
              </div>
            </div>

            <div className="mirra-gap__copy-anchor">
              <div className="mirra-gap__copy">
                <p>
                  The gap between liking a garment and trusting how it will fit is where confident
                  purchases disappear. Mirra brings that decision into view, before uncertainty
                  turns into an abandoned cart or a return.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section
        ref={introRef}
        className="mirra-intro"
        aria-label="Imagine Mirra on every product page"
      >
        <h2>
          Imagine every product page <strong>as a fitting room shoppers can trust.</strong>
        </h2>
      </section>

      <section
        ref={featureRef}
        id="mirra-method"
        className="mirra-features"
        aria-label="What is Mirra"
      >
        <div ref={innerRef} className="mirra-features__inner">
          <div className="mirra-features__content">
            <div ref={counterRef} className="mirra-features__counter-wrap" aria-hidden="true">
              <MirraOdometer value={activeStep + 1} />
            </div>

            <div className="mirra-features__mobile-counters" aria-hidden="true">
              {featureSteps.map((step, index) => (
                <span className={index === activeStep ? "is-active" : ""} key={step.number}>
                  {step.number}
                </span>
              ))}
            </div>

            <div ref={scrollItemsRef} className="mirra-features__scroll-items">
              <ol ref={listRef} className="mirra-features__list">
                {featureSteps.map((step, index) => (
                  <li
                    ref={(item) => {
                      itemRefs.current[index] = item;
                    }}
                    className={`mirra-features__item ${index === activeStep ? "is-active" : ""}`}
                    style={{ "--mirra-item-index": index } as React.CSSProperties}
                    key={step.number}
                  >
                    <span className="mirra-features__mobile-kicker">{step.kicker}</span>
                    <p
                      ref={(copy) => {
                        copyRefs.current[index] = copy;
                      }}
                      aria-label={step.text}
                    >
                      {step.text}
                    </p>
                  </li>
                ))}
              </ol>

              <div className="mirra-features__mobile-progress" aria-hidden="true">
                <span style={{ transform: `translateX(${activeStep * 100}%)` }} />
              </div>
            </div>
          </div>

          <div ref={visualRef} className="mirra-features__visual">
            <div className="mirra-features__media-stack">
              {featureSteps.map((step, index) => (
                <MirraVisualScene
                  active={index === activeStep}
                  visible={index <= activeStep}
                  index={index}
                  key={step.number}
                />
              ))}
            </div>

            <div className="mirra-features__mobile-buttons">
              <button
                type="button"
                aria-label="Previous Mirra feature"
                disabled={activeStep === 0}
                onClick={() => moveMobileStep(-1)}
              >
                <span aria-hidden="true">&#8592;</span>
              </button>
              <button
                type="button"
                aria-label="Next Mirra feature"
                disabled={activeStep === featureSteps.length - 1}
                onClick={() => moveMobileStep(1)}
              >
                <span aria-hidden="true">&#8594;</span>
              </button>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

function MirraOdometer({ value }: { value: number }) {
  return (
    <span className="mirra-odometer" aria-label={`Feature ${value} of ${featureSteps.length}`}>
      <span className="mirra-odometer__digit">0</span>
      <span className="mirra-odometer__window">
        <span
          className="mirra-odometer__stack"
          style={{ transform: `translate3d(0, -${value}em, 0)` }}
        >
          {Array.from({ length: 10 }, (_, digit) => (
            <span key={digit}>{digit}</span>
          ))}
        </span>
      </span>
    </span>
  );
}

function MirraVisualScene({
  active,
  visible,
  index,
}: {
  active: boolean;
  visible: boolean;
  index: number;
  key?: React.Key;
}) {
  return (
    <figure
      className={`mirra-scene mirra-scene--${index + 1} ${visible ? "is-visible" : ""} ${active ? "is-current" : ""}`}
      aria-hidden={!active}
    >
      <div className="mirra-scene__technical-grid" />
      <figcaption className="mirra-scene__topline">
        <span>MIRRA / FIT SYSTEM</span>
        <span>{featureSteps[index].number}</span>
      </figcaption>

      {index === 0 && <ProductInputsScene />}
      {index === 1 && <GarmentScene />}
      {index === 2 && <ProductPageScene />}
      {index === 3 && <TryOnScene />}
      {index === 4 && <FitDecisionScene />}
      {index === 5 && <RetainedMarginScene />}
    </figure>
  );
}

function GarmentShape({ className = "" }: { className?: string }) {
  return (
    <span className={`mirra-garment ${className}`} aria-hidden="true">
      <i />
      <i />
      <i />
    </span>
  );
}

function BodyShape({ className = "" }: { className?: string }) {
  return <span className={`mirra-body ${className}`} aria-hidden="true" />;
}

function ProductInputsScene() {
  const labels = ["FRONT", "BACK", "DETAIL", "FABRIC", "TECH", "COLOR"];
  return (
    <div className="mirra-scene__content mirra-inputs">
      <div className="mirra-inputs__tiles">
        {labels.map((label, index) => (
          <span className={`mirra-inputs__tile tone-${index + 1}`} key={label}>
            <i />
            <b>{label}</b>
          </span>
        ))}
      </div>
      <span className="mirra-inputs__path" />
      <div className="mirra-inputs__target">
        <GarmentShape />
        <small>ASSETS INGESTED</small>
      </div>
    </div>
  );
}

function GarmentScene() {
  return (
    <div className="mirra-scene__content mirra-garment-stage">
      <span className="mirra-garment-stage__orbit orbit-one" />
      <span className="mirra-garment-stage__orbit orbit-two" />
      <GarmentShape className="mirra-garment--hero" />
      <span className="mirra-garment-stage__axis axis-x" />
      <span className="mirra-garment-stage__axis axis-y" />
      <span className="mirra-garment-stage__label label-mesh">MESH / 19.5K</span>
      <span className="mirra-garment-stage__label label-drape">DRAPE / READY</span>
    </div>
  );
}

function ProductPageScene() {
  return (
    <div className="mirra-scene__content mirra-pdp">
      <div className="mirra-pdp__browser">
        <div className="mirra-pdp__browser-bar">
          <i />
          <i />
          <i />
          <span>yourstore.com/products/everyday-tee</span>
        </div>
        <div className="mirra-pdp__page">
          <div className="mirra-pdp__gallery">
            <GarmentShape />
          </div>
          <div className="mirra-pdp__details">
            <small>NEW COLLECTION</small>
            <strong>Everyday Form Tee</strong>
            <span className="mirra-pdp__price">$130</span>
            <span className="mirra-pdp__line" />
            <span className="mirra-pdp__line is-short" />
            <button type="button" tabIndex={-1}>
              TRY IT ON
            </button>
            <span className="mirra-pdp__add">ADD TO BAG</span>
          </div>
        </div>
      </div>
      <span className="mirra-pdp__isolation">ISOLATED APP BLOCK</span>
    </div>
  );
}

function TryOnScene() {
  return (
    <div className="mirra-scene__content mirra-tryon">
      <div className="mirra-tryon__phone">
        <div className="mirra-tryon__phone-bar">
          <span />
          <b>TRY ON</b>
          <i />
        </div>
        <div className="mirra-tryon__viewport">
          <BodyShape />
          <GarmentShape className="mirra-garment--worn" />
          <span className="mirra-tryon__scan" />
          <small>RENDER COMPLETE</small>
        </div>
      </div>
      <div className="mirra-tryon__status">
        <span>
          <i /> IN BROWSER
        </span>
        <span>
          <i /> NO APP DOWNLOAD
        </span>
        <span>
          <i /> SHOPPER READY
        </span>
      </div>
    </div>
  );
}

function FitDecisionScene() {
  return (
    <div className="mirra-scene__content mirra-fit">
      <div className="mirra-fit__figure">
        <BodyShape />
        <GarmentShape className="mirra-garment--fit" />
        <span className="mirra-fit__measure measure-shoulder">
          <i>SHOULDER</i>
        </span>
        <span className="mirra-fit__measure measure-chest">
          <i>CHEST</i>
        </span>
        <span className="mirra-fit__measure measure-length">
          <i>LENGTH</i>
        </span>
      </div>
      <div className="mirra-fit__choice">
        <small>RECOMMENDED SIZE</small>
        <div>
          <span>M</span>
          <span className="is-selected">L</span>
          <span>XL</span>
        </div>
        <strong>94% FIT CONFIDENCE</strong>
      </div>
    </div>
  );
}

function RetainedMarginScene() {
  const checks = ["Fit shown before checkout", "Backup size avoided", "Return loop avoided"];
  return (
    <div className="mirra-scene__content mirra-margin">
      <div className="mirra-margin__card">
        <small>RETAINED MARGIN</small>
        <strong>$168.90</strong>
        <span>protected on this order</span>
        <i />
        <div>
          {checks.map((check) => (
            <p key={check}>
              <b>&#10003;</b>
              {check}
            </p>
          ))}
        </div>
      </div>
      <div className="mirra-margin__ledger">
        <span>
          <i>GROSS REVENUE</i>
          <b>$260.00</b>
        </span>
        <span>
          <i>REFUND</i>
          <b>$0.00</b>
        </span>
        <span>
          <i>REVERSE LOGISTICS</i>
          <b>$0.00</b>
        </span>
      </div>
    </div>
  );
}
