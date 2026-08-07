import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import type { SizeChartRow } from "@/integrations/mirra-api/types";
import type { SizeOption } from "../types";

/**
 * Size as a row of plain rectangles. Selected is solid ink; sold out is a
 * struck-through outline that stays legible — availability is information,
 * not an error.
 */
export function SizeSelector({
  options,
  activeSize,
  sizeChart,
  onChange,
}: {
  options: SizeOption[];
  activeSize: string | null;
  sizeChart: SizeChartRow[] | null;
  onChange: (size: string) => void;
}) {
  const [chartOpen, setChartOpen] = useState(false);
  const reduceMotion = useReducedMotion();

  if (options.length === 0) return null;

  return (
    <fieldset>
      <div className="flex items-baseline justify-between gap-3">
        <legend className="eyebrow">Select size</legend>
        {sizeChart && (
          <button
            type="button"
            onClick={() => setChartOpen((open) => !open)}
            aria-expanded={chartOpen}
            className="text-[10px] tracking-[0.12em] text-ash uppercase transition-colors hover:text-graphite"
          >
            {chartOpen ? "Hide chart" : "Size chart"}
          </button>
        )}
      </div>

      <div className="mt-3.5 flex flex-wrap gap-2">
        {options.map(({ size, variant, inStock }) => {
          const selected = size === activeSize;
          return (
            <button
              key={variant.publicVariantId}
              type="button"
              disabled={!inStock}
              onClick={() => onChange(size)}
              aria-pressed={selected}
              aria-label={`Size ${size}${inStock ? "" : " — out of stock"}`}
              className={`h-11 min-w-13 rounded-panel-sm border px-3 text-[13px] font-medium transition-colors duration-200 ${
                selected
                  ? "border-graphite bg-graphite text-vellum"
                  : inStock
                    ? "border-hairline-strong text-graphite hover:border-graphite"
                    : "border-hairline text-ash line-through"
              }`}
            >
              {size}
            </button>
          );
        })}
      </div>

      <AnimatePresence initial={false}>
        {chartOpen && sizeChart && (
          <motion.div
            className="overflow-hidden"
            initial={reduceMotion ? false : { height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
            transition={
              reduceMotion ? { duration: 0.01 } : { duration: 0.28, ease: [0.22, 0.8, 0.24, 1] }
            }
          >
            <div className="quiet-scroll mt-4 overflow-x-auto border border-hairline">
              <table className="w-full text-left text-[11px]">
                <thead>
                  <tr className="border-b border-hairline">
                    <th className="px-3 py-2.5 font-medium tracking-[0.1em] text-ash uppercase">
                      Size
                    </th>
                    {Object.keys(sizeChart[0].measurements).map((key) => (
                      <th
                        key={key}
                        className="px-3 py-2.5 font-medium tracking-[0.1em] text-ash uppercase"
                      >
                        {key}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sizeChart.map((row) => (
                    <tr key={row.size} className="border-b border-hairline last:border-b-0">
                      <td className="px-3 py-2.5 font-medium text-graphite">{row.size}</td>
                      {Object.values(row.measurements).map((value, index) => (
                        <td key={index} className="px-3 py-2.5 text-slate">
                          {value}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </fieldset>
  );
}
