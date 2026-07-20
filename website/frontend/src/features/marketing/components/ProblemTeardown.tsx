import React, { useEffect } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import TextReveal from "./TextReveal";
import "./ProblemTeardown.css";

gsap.registerPlugin(ScrollTrigger);

const steps = [
  {
    number: "01",
    title: (
      <>
        The Buy Two,
        <br />
        Return One Habit.
      </>
    ),
    leftTag: "Fit confidence gap",
    rightTag: "Multi-size ordering",
    leftCopy: (
      <>
        <span className="text-black/60">Customers reading your size chart are left imagining </span>
        <span className="font-medium text-black">how the garment actually fits them.</span>
      </>
    ),
    rightCopy: (
      <>
        <span className="text-black/60">These customers eventually end up </span>
        <span className="font-medium text-black">ordering 2 sizes</span>
        <span className="text-black/60"> of the same garment to be sure.</span>
      </>
    ),
    className: "step-one",
  },
  {
    number: "02",
    title: "The Cost of Bracket Shopping.",
    leftTag: "Guaranteed return cost",
    rightTag: "Shipping + restocking loss",
    leftCopy: (
      <>
        <span className="text-black/60">
          Shipping out a backup size purely for home try-ons leaves you footing the bill for a{" "}
        </span>
        <span className="font-medium text-black">guaranteed return.</span>
      </>
    ),
    rightCopy: (
      <>
        <span className="text-black/60">
          Once you absorb shipping costs and warehouse restocking,{" "}
        </span>
        <span className="font-medium text-black">your profit on that sale is gone.</span>
      </>
    ),
    className: "step-two",
  },
  {
    number: "03",
    title: "The Display-to-Drape Deficit.",
    leftTag: "Static images miss real fit",
    rightTag: "Visual expectation gap",
    leftCopy: (
      <>
        <span className="text-black/60">Because static imagery captures </span>
        <span className="font-medium text-black">aesthetics rather than physics</span>
        <span className="text-black/60">, 2D photos fail to prove how a garment </span>
        <span className="font-medium text-black">actually sits across a 3D body.</span>
      </>
    ),
    rightCopy: (
      <>
        <span className="text-black/60">
          The gap between what shoppers see and how it truly fits{" "}
        </span>
        <span className="font-medium text-black">turns quiet doubt</span>
        <span className="text-black/60"> into </span>
        <span className="font-medium text-black">another return in the mail.</span>
      </>
    ),
    className: "step-three",
  },
];

function splitWords(text: string) {
  return text.split(/(\s+)/).map((part, index) =>
    part.trim() ? (
      <span className="flash-word" key={`${part}-${index}`}>
        {part}
      </span>
    ) : (
      part
    ),
  );
}

function FlashText({
  as: Tag = "span",
  children,
  className = "",
  muted = false,
}: {
  as?: React.ElementType;
  children: React.ReactNode;
  className?: string;
  muted?: boolean;
}) {
  const content = typeof children === "string" ? splitWords(children) : children;
  return <Tag className={`flash-text ${muted ? "is-muted" : ""} ${className}`}>{content}</Tag>;
}

function PlaceholderTile({
  tone = "hero-a",
  className = "",
}: {
  tone?: string;
  className?: string;
}) {
  return <div className={`placeholder-tile ${tone} ${className}`} />;
}

function StepArt({ label }: { label: string }) {
  return (
    <div className={`step-art step-art-${label.replace(/\s+/g, "-")}`} aria-hidden="true">
      <div className="step-art__topbar">
        <i />
        <i />
        <i />
      </div>
      <div className="step-art__figure">
        <span className="step-art__body" />
        <span className="step-art__garment" />
        <span className="step-art__measure step-art__measure--one" />
        <span className="step-art__measure step-art__measure--two" />
        <span className="step-art__measure step-art__measure--three" />
      </div>
      <div className="step-art__grid">
        {Array.from({ length: 8 }, (_, index) => (
          <PlaceholderTile key={index} tone={`art-${index + 1}`} />
        ))}
      </div>
    </div>
  );
}

interface ProblemTeardownProps {
  onBookDemo: () => void;
}

export default function ProblemTeardown({ onBookDemo }: ProblemTeardownProps) {
  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.utils.toArray<Element>(".step-slide").forEach((slide, index, slides) => {
        if (index === slides.length - 1) return;

        const pin = slide.querySelector(".step-pin");
        const card = slide.querySelector(".step-card");

        gsap.to(card, {
          rotationZ: index % 2 ? -4 : 4,
          scale: 0.72,
          rotationX: 38,
          transformOrigin: "50% 0%",
          ease: "power1.in",
          scrollTrigger: {
            trigger: slide,
            pin,
            start: "top top",
            end: () => `+=${window.innerHeight}`,
            scrub: true,
          },
        });

        gsap.to(card, {
          autoAlpha: 0,
          ease: "power1.in",
          scrollTrigger: {
            trigger: slide,
            start: "top -80%",
            end: () => `+=${window.innerHeight * 0.5}`,
            scrub: true,
          },
        });
      });
    });

    return () => ctx.revert();
  }, []);

  return (
    <section className="list-section" id="list">
      <div className="list-title section-border">
        <TextReveal as="h2" variant="wipe-right">
          {"The hidden cost\nof uncertain fit."}
        </TextReveal>
        <p>Before a return becomes logistics, it starts as uncertainty on the product page.</p>
      </div>

      <div className="steps-wrap">
        {steps.map((step) => (
          <section className="step-slide" key={step.number}>
            <div className="step-pin">
              <article className={`step-card ${step.className}`}>
                <div className="step-card__top">
                  <span className="absolute top-12 left-1/2 -translate-x-1/2 text-xs tracking-widest text-ink/40 uppercase">
                    ( The Problem )
                  </span>
                  <div className="step-card__title">
                    <FlashText as="h3" className="step-flash">
                      {step.title}
                    </FlashText>
                    <span className="step-number">{step.number}</span>
                  </div>

                  <div className="step-info">
                    <div className="step-info__left">
                      <span>
                        <i />
                        {step.leftTag}
                      </span>
                      <p>{step.leftCopy}</p>
                    </div>
                    <div className="step-info__right">
                      <span>
                        <i />
                        {step.rightTag}
                      </span>
                      <p>{step.rightCopy}</p>
                    </div>
                  </div>

                  <button className="primary-button step-button" type="button" onClick={onBookDemo}>
                    Book a Demo
                  </button>
                </div>

                <div className="step-card__bottom">
                  <StepArt label={step.number} />
                  <div className="step-gradient" />
                </div>
              </article>
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}
