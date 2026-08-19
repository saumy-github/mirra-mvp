import { motion, useReducedMotion } from "motion/react";
import { Link } from "react-router-dom";
import type { CSSProperties, MouseEventHandler } from "react";
import { UiIcon } from "./UiIcon";

const MotionLink = motion.create(Link);

type LiquidCTATone = "primary" | "dark" | "light" | "white";

type LiquidCTAProps = {
  children: string;
  className?: string;
  compact?: boolean;
  href: string;
  onClick?: MouseEventHandler<HTMLAnchorElement>;
  tone?: LiquidCTATone;
};

type LiquidButtonProps = Omit<LiquidCTAProps, "href" | "onClick"> & {
  ariaLabel?: string;
  onClick?: MouseEventHandler<HTMLButtonElement>;
  type?: "button" | "submit" | "reset";
};

function AnimatedLabel({ label }: { label: string }) {
  const characters = Array.from(label);

  return (
    <span className="liquid-cta__label" aria-hidden="true">
      <span className="liquid-cta__row liquid-cta__row--current">
        {characters.map((character, index) => (
          <span
            className="liquid-cta__character"
            key={`current-${character}-${index}`}
            style={{ "--character-index": index } as CSSProperties}
          >
            {character === " " ? "\u00a0" : character}
          </span>
        ))}
      </span>
      <span className="liquid-cta__row liquid-cta__row--next">
        {characters.map((character, index) => (
          <span
            className="liquid-cta__character"
            key={`next-${character}-${index}`}
            style={{ "--character-index": index } as CSSProperties}
          >
            {character === " " ? "\u00a0" : character}
          </span>
        ))}
      </span>
    </span>
  );
}

function LiquidCTAContent({ label }: { label: string }) {
  return (
    <>
      <AnimatedLabel label={label} />
      <span className="sr-only">{label}</span>
      <span className="liquid-cta__arrow" aria-hidden="true">
        <span><UiIcon name="arrow-up-right" size={14} /></span>
        <span><UiIcon name="arrow-up-right" size={14} /></span>
      </span>
    </>
  );
}

export function LiquidCTA({
  children,
  className = "",
  compact = false,
  href,
  onClick,
  tone = "primary",
}: LiquidCTAProps) {
  const label = children;
  const reduceMotion = useReducedMotion();
  // In-app targets go through the router; API endpoints and anything external
  // stay plain anchors so the browser performs a real navigation. (The
  // standalone site also excluded its ChatGPT sign-in routes here; those do
  // not exist in this app — auth is /auth/login, which is client-routed.)
  const clientRouted = (href.startsWith("/") || href.startsWith("#"))
    && !/^\/api(?:\/|\?|$)/.test(href);

  const sharedProps = {
    className: `liquid-cta liquid-cta--${tone}${compact ? " liquid-cta--compact" : ""}${className ? ` ${className}` : ""}`,
    onClick,
    whileTap: reduceMotion ? undefined : { scale: 0.97 },
    transition: { type: "spring" as const, stiffness: 200, damping: 25 },
  };

  if (clientRouted) {
    return (
      <MotionLink to={href} {...sharedProps}>
        <LiquidCTAContent label={label} />
      </MotionLink>
    );
  }

  return (
    <motion.a
      href={href}
      {...sharedProps}
    >
      <LiquidCTAContent label={label} />
    </motion.a>
  );
}

export function LiquidButton({
  ariaLabel,
  children,
  className = "",
  compact = false,
  onClick,
  tone = "primary",
  type = "button",
}: LiquidButtonProps) {
  const label = children;
  const reduceMotion = useReducedMotion();

  return (
    <motion.button
      aria-label={ariaLabel ?? label}
      className={`liquid-cta liquid-cta--${tone}${compact ? " liquid-cta--compact" : ""}${className ? ` ${className}` : ""}`}
      onClick={onClick}
      type={type}
      whileTap={reduceMotion ? undefined : { scale: 0.97 }}
      transition={{ type: "spring", stiffness: 200, damping: 25 }}
    >
      <LiquidCTAContent label={label} />
    </motion.button>
  );
}
