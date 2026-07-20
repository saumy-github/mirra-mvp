import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ChevronDown } from "lucide-react";
import TextReveal, { KineticText } from "./TextReveal";

interface RoiCalculatorProps {
  onBookDemo: () => void;
}

export default function RoiCalculator({ onBookDemo }: RoiCalculatorProps) {
  const [monthlyGMV, setMonthlyGMV] = useState(30000);
  const [returnRate, setReturnRate] = useState(37);
  const [showFormula, setShowFormula] = useState(false);

  // Constants
  const NRF_SIZE_SHARE = 0.53;

  // Efficacy Tier Logic
  let tierDeflectionEfficacy = 0.42;
  if (monthlyGMV < 50000) {
    tierDeflectionEfficacy = 0.38;
  } else if (monthlyGMV >= 250000) {
    tierDeflectionEfficacy = 0.46;
  }

  // Calculations
  const grossReturns = monthlyGMV * (returnRate / 100);
  const topLineCorrosion = grossReturns * NRF_SIZE_SHARE;
  const retainedGrossRevenue = topLineCorrosion * tierDeflectionEfficacy;

  const annualizedLeak = topLineCorrosion * 12;
  const annualizedGrossRevenue = retainedGrossRevenue * 12;

  const formatCurrency = (val: number) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(val);

  return (
    <section id="roi" className="w-full border-t border-silver bg-bg py-24">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="flex flex-col gap-16 lg:flex-row lg:gap-24">
          {/* Left Column */}
          <div className="flex w-full flex-col items-start pt-4 lg:w-4/12">
            <TextReveal
              as="h2"
              variant="wipe-right"
              className="mb-8 text-4xl leading-[1.1] font-medium tracking-tight text-ink md:text-5xl lg:text-6xl"
            >
              {"Put a number\non the problem."}
            </TextReveal>
            <TextReveal
              as="p"
              variant="lift"
              delay={0.18}
              className="mb-12 max-w-sm text-[1.05rem] leading-relaxed text-muted"
            >
              Whether your return rate is an elite 10% or a painful 30%, sizing guesswork drives
              over half of it. Drag the sliders to see what it costs — and what Mirra retains.
            </TextReveal>
            <button
              onClick={onBookDemo}
              className="rounded-full bg-black px-8 py-4 text-sm font-semibold text-white transition-colors hover:bg-black/80"
            >
              <KineticText>Book a Demo</KineticText>
            </button>
          </div>

          {/* Right Column */}
          <div className="w-full pt-4 lg:w-8/12">
            {/* Sliders */}
            <div className="mb-16 flex flex-col gap-14">
              <div>
                <div className="mb-4 flex items-end justify-between">
                  <label className="text-[11px] font-bold tracking-[0.15em] text-muted uppercase">
                    Monthly Store GMV
                  </label>
                  <span className="text-4xl text-ink lg:text-[2.75rem]">
                    {formatCurrency(monthlyGMV)}
                  </span>
                </div>
                <input
                  type="range"
                  min="10000"
                  max="1000000"
                  step="10000"
                  value={monthlyGMV}
                  onChange={(e) => setMonthlyGMV(Number(e.target.value))}
                  className="range-track-sm range-thumb-sm cursor-pointer"
                />
              </div>

              <div>
                <div className="mb-4 flex items-end justify-between">
                  <label className="text-[11px] font-bold tracking-[0.15em] text-muted uppercase">
                    Current Return Rate
                  </label>
                  <span className="text-4xl text-ink lg:text-[2.75rem]">{returnRate}%</span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="50"
                  step="1"
                  value={returnRate}
                  onChange={(e) => setReturnRate(Number(e.target.value))}
                  className="range-track-sm range-thumb-sm cursor-pointer"
                />
              </div>
            </div>

            <div className="mb-16 h-px w-full bg-line" />

            {/* Output */}
            <div className="mb-12 grid grid-cols-1 gap-12 md:grid-cols-2">
              <div>
                <div className="mb-6 text-[11px] font-bold tracking-[0.15em] text-muted uppercase">
                  Revenue Lost to Sizing
                </div>
                <div className="mb-6 text-5xl font-medium tracking-tight text-ink md:text-[3.5rem]">
                  -{formatCurrency(topLineCorrosion)}{" "}
                  <span className="text-2xl font-medium text-ink md:text-3xl">/ mo</span>
                </div>
                <div className="text-[9px] font-bold tracking-widest text-muted uppercase">
                  -{formatCurrency(annualizedLeak)} ANNUALIZED LEAK
                </div>
              </div>

              <div>
                <div className="mb-6 text-[11px] font-bold tracking-[0.15em] text-muted uppercase">
                  Revenue Retained with Mirra
                </div>
                <div className="mb-6 text-5xl font-medium tracking-tight text-ink md:text-[3.5rem]">
                  +{formatCurrency(retainedGrossRevenue)}{" "}
                  <span className="text-2xl font-medium text-ink md:text-3xl">/ mo</span>
                </div>
                <div className="text-[9px] font-bold tracking-widest text-muted uppercase">
                  +{formatCurrency(annualizedGrossRevenue)} ANNUALIZED GROSS REVENUE
                </div>
              </div>
            </div>

            {/* Formula Accordion */}
            <div>
              <button
                onClick={() => setShowFormula(!showFormula)}
                className="mb-6 flex items-center gap-2 text-sm font-semibold text-muted transition-colors hover:text-ink"
              >
                See how we calculate this{" "}
                <ChevronDown
                  size={16}
                  className={`transition-transform duration-300 ${showFormula ? "rotate-180" : ""}`}
                />
              </button>

              <AnimatePresence>
                {showFormula && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="rounded-2xl border border-line bg-surface p-6 text-sm text-muted sm:p-8">
                      <div className="mb-6 overflow-x-auto rounded-xl border border-silver bg-bg p-4 font-mono text-xs whitespace-nowrap text-ink">
                        (Monthly GMV × Return Rate) × 0.53 [Size-Attributed Share] × Tier Deflection
                        Efficacy
                      </div>

                      <div className="space-y-4 leading-relaxed">
                        <p>
                          <strong className="font-semibold text-ink">
                            Monthly GMV × Return Rate
                          </strong>{" "}
                          = the dollar value of merchandise heading backward through the mail each
                          month.
                        </p>
                        <p>
                          <strong className="font-semibold text-ink">
                            0.53 [Size-Attributed Share]
                          </strong>{" "}
                          = the National Retail Federation benchmark: 53% of apparel returns happen
                          strictly because of sizing.
                        </p>
                        <p>
                          <strong className="font-semibold text-ink">
                            Tier Deflection Efficacy
                          </strong>{" "}
                          = the share of those bad size choices Mirra stops before checkout, based
                          on your catalog volume.
                        </p>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
