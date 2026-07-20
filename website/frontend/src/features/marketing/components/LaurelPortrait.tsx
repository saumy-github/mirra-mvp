import React from "react";
import { motion } from "motion/react";

interface LaurelPortraitProps {
  src: string;
  alt: string;
  index?: number;
}

const leaves = [
  { cx: 63, cy: 190, r: -55 },
  { cx: 48, cy: 166, r: -45 },
  { cx: 40, cy: 139, r: -34 },
  { cx: 42, cy: 111, r: -22 },
  { cx: 52, cy: 84, r: -8 },
  { cx: 68, cy: 61, r: 10 },
  { cx: 88, cy: 43, r: 28 },
];

function LaurelSide({ mirrored = false }: { mirrored?: boolean }) {
  return (
    <g transform={mirrored ? "translate(320 0) scale(-1 1)" : undefined}>
      <motion.path
        d="M93 220C47 199 24 163 31 122C36 86 58 51 99 28"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        initial={{ pathLength: 0, opacity: 0 }}
        whileInView={{ pathLength: 1, opacity: 1 }}
        viewport={{ once: true, amount: 0.5 }}
        transition={{ duration: 1.05, ease: [0.76, 0, 0.24, 1] }}
      />
      {leaves.map((leaf, i) => (
        <motion.ellipse
          key={leaf.cx + "-" + leaf.cy}
          cx={leaf.cx}
          cy={leaf.cy}
          rx="7"
          ry="18"
          transform={"rotate(" + leaf.r + " " + leaf.cx + " " + leaf.cy + ")"}
          fill="currentColor"
          initial={{ opacity: 0, scale: 0.35 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.48, delay: 0.2 + i * 0.055, ease: [0.34, 1.56, 0.64, 1] }}
          style={{ transformBox: "fill-box", transformOrigin: "center" }}
        />
      ))}
    </g>
  );
}

export default function LaurelPortrait({ src, alt, index = 0 }: LaurelPortraitProps) {
  return (
    <div className="relative aspect-square w-full overflow-hidden rounded-4xl border border-line/70 bg-surface">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_46%,rgba(248,243,242,0.96)_0%,rgba(238,230,230,0.62)_52%,transparent_78%)]" />
      <svg
        className="absolute inset-[7%] h-[86%] w-[86%] overflow-visible text-ink/72"
        viewBox="0 0 320 250"
        aria-hidden="true"
      >
        <LaurelSide />
        <LaurelSide mirrored />
      </svg>

      <motion.div
        className="absolute top-[48%] left-1/2 h-[51%] w-[51%] -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-full border-[3px] border-bg bg-bg shadow-[0_18px_45px_rgba(31,24,37,0.2)]"
        initial={{ opacity: 0, scale: 0.72 }}
        whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: true, amount: 0.5 }}
        transition={{ duration: 0.72, delay: 0.12 + index * 0.04, ease: [0.34, 1.56, 0.64, 1] }}
      >
        <img
          src={src}
          alt={alt}
          className="h-full w-full object-cover grayscale transition-all duration-700 ease-out group-hover:scale-105 group-hover:grayscale-0"
        />
      </motion.div>

      <div className="absolute bottom-[9%] left-1/2 h-px w-12 -translate-x-1/2 bg-ink/25" />
    </div>
  );
}
