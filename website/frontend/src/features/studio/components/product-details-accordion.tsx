import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import type { Product } from "../types";

const PANEL_TRANSITION = { duration: 0.3, ease: [0.22, 0.8, 0.24, 1] as const };

interface Section {
  label: string;
  body: string | null;
}

/**
 * Everything the store says about the piece, folded away by default. Each row
 * is a hairline and a label; nothing is invented when a field is empty — the
 * section says so plainly instead.
 */
export function ProductDetailsAccordion({ product }: { product: Product }) {
  const [open, setOpen] = useState<string | null>(null);
  const reduceMotion = useReducedMotion();

  const sections: Section[] = [
    { label: "Product details", body: product.description },
    { label: "Material & care", body: product.materialAndCare },
    { label: "Fit", body: product.fitInfo },
    ...(product.manufacturingInfo ? [{ label: "Made", body: product.manufacturingInfo }] : []),
    { label: "Shipping & returns", body: null },
  ];

  return (
    <div className="border-t border-hairline">
      {sections.map((section) => {
        const expanded = open === section.label;
        return (
          <div key={section.label} className="border-b border-hairline">
            <button
              type="button"
              onClick={() => setOpen(expanded ? null : section.label)}
              aria-expanded={expanded}
              className="flex w-full items-center justify-between gap-4 py-4 text-left transition-colors hover:text-graphite"
            >
              <span className="text-[11px] tracking-[0.14em] text-graphite uppercase">
                {section.label}
              </span>
              <motion.span
                aria-hidden
                className="text-ash"
                animate={{ rotate: expanded ? 90 : 0 }}
                transition={reduceMotion ? { duration: 0.01 } : PANEL_TRANSITION}
              >
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="m9 5 7 7-7 7" />
                </svg>
              </motion.span>
            </button>

            <AnimatePresence initial={false}>
              {expanded && (
                <motion.div
                  className="overflow-hidden"
                  initial={reduceMotion ? false : { height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
                  transition={reduceMotion ? { duration: 0.01 } : PANEL_TRANSITION}
                >
                  <p className="pr-6 pb-5 text-[13px] leading-relaxed text-slate">
                    {section.body ?? "The store hasn't published this yet."}
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </div>
  );
}
