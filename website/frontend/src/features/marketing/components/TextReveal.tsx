import React from "react";
import { motion, useReducedMotion } from "motion/react";

type RevealTag = "div" | "h1" | "h2" | "h3" | "p" | "span";
type RevealVariant = "wipe-right" | "lift" | "chars";

interface TextRevealProps {
  as?: RevealTag;
  children: string;
  className?: string;
  variant?: RevealVariant;
  delay?: number;
  once?: boolean;
  threshold?: number;
  wipeColor?: "wine" | "ink" | "surface";
}

const ease = [0.76, 0, 0.24, 1] as const;

export default function TextReveal({
  as = "div",
  children,
  className = "",
  variant = "lift",
  delay = 0,
  once = true,
  threshold = 0.22,
  wipeColor = "wine",
}: TextRevealProps) {
  const reduceMotion = useReducedMotion();
  const Tag = as;
  const lines = children.split("\n");

  if (variant === "chars") {
    return (
      <Tag className={className} aria-label={children}>
        <motion.span
          aria-hidden="true"
          className="mirra-char-reveal"
          initial={reduceMotion ? false : "hidden"}
          whileInView={reduceMotion ? undefined : "visible"}
          viewport={{ once, amount: threshold }}
        >
          {Array.from(children).map((char, index) => (
            <span className="mirra-char-reveal__mask" key={char + "-" + index}>
              <motion.span
                className="mirra-char-reveal__char"
                variants={{
                  hidden: { y: "112%", opacity: 0 },
                  visible: {
                    y: "0%",
                    opacity: 1,
                    transition: {
                      duration: 0.62,
                      delay: delay + index * 0.018,
                      ease,
                    },
                  },
                }}
              >
                {char === " " ? "\u00a0" : char}
              </motion.span>
            </span>
          ))}
        </motion.span>
      </Tag>
    );
  }

  return (
    <Tag className={className} aria-label={children.replace(/\n/g, " ")}>
      <motion.span
        aria-hidden="true"
        className={"mirra-text-reveal mirra-text-reveal--" + variant}
        initial={reduceMotion ? false : "hidden"}
        whileInView={reduceMotion ? undefined : "visible"}
        viewport={{ once, amount: threshold }}
      >
        {lines.map((line, index) => {
          const direction = "right";
          const isWipe = variant === "wipe-right";

          return (
            <motion.span
              className="mirra-text-reveal__line"
              key={line + "-" + index}
              variants={{
                hidden: isWipe
                  ? {
                      clipPath: direction === "right" ? "inset(0 100% 0 0)" : "inset(0 0 0 100%)",
                      y: 15,
                    }
                  : { y: "112%", opacity: 0 },
                visible: {
                  ...(isWipe ? { clipPath: "inset(0 0% 0 0%)", y: 0 } : { y: "0%", opacity: 1 }),
                  transition: {
                    duration: isWipe ? 0.9 : 0.76,
                    delay: delay + index * (isWipe ? 0.1 : 0.08),
                    ease,
                  },
                },
              }}
            >
              {line || "\u00a0"}
              {isWipe && !reduceMotion && (
                <motion.span
                  className={"mirra-text-reveal__wipe mirra-text-reveal__wipe--" + wipeColor}
                  variants={{
                    hidden: { scaleX: 1 },
                    visible: {
                      scaleX: 0,
                      transition: {
                        duration: 0.72,
                        delay: delay + 0.18 + index * 0.1,
                        ease,
                      },
                    },
                  }}
                  style={{ transformOrigin: direction }}
                />
              )}
            </motion.span>
          );
        })}
      </motion.span>
    </Tag>
  );
}

interface KineticTextProps {
  children: string;
  className?: string;
}

export function KineticText({ children, className = "" }: KineticTextProps) {
  return (
    <span className={"mirra-kinetic-text " + className} aria-label={children}>
      <span className="mirra-kinetic-text__row" aria-hidden="true">
        {Array.from(children).map((char, index) => (
          <span style={{ "--char-index": index } as React.CSSProperties} key={char + "-a-" + index}>
            {char === " " ? "\u00a0" : char}
          </span>
        ))}
      </span>
      <span className="mirra-kinetic-text__row mirra-kinetic-text__row--clone" aria-hidden="true">
        {Array.from(children).map((char, index) => (
          <span style={{ "--char-index": index } as React.CSSProperties} key={char + "-b-" + index}>
            {char === " " ? "\u00a0" : char}
          </span>
        ))}
      </span>
    </span>
  );
}
