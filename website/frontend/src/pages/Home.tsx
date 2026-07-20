import React from "react";
import { motion } from "motion/react";
import { useOutletContext } from "react-router-dom";
import type { MarketingContext } from "../features/marketing/marketing-layout";
import Hero from "../features/marketing/components/Hero";
import ProblemTeardown from "../features/marketing/components/ProblemTeardown";
import ProductReveal from "../features/marketing/components/ProductReveal";
import LiveLedger from "../features/marketing/components/LiveLedger";
import DemoPlaceholder from "../features/marketing/components/DemoPlaceholder";
import RoiCalculator from "../features/marketing/components/RoiCalculator";
import Closure from "../features/marketing/components/Closure";

export default function Home() {
  const { onBookDemo } = useOutletContext<MarketingContext>();
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="w-full"
    >
      <main>
        {/* Zone 1 — The First Impression */}
        <Hero onBookDemo={onBookDemo} />

        {/* Zone 2A — Problem Teardown Story */}
        <ProblemTeardown onBookDemo={onBookDemo} />

        {/* Zone 2B — Mirra Product Reveal */}
        <ProductReveal />

        {/* Zone 2C — Live Ledger Teardown */}
        <LiveLedger />

        {/* Zone 2D — Product Demo Video */}
        <DemoPlaceholder />

        {/* Zone 3B — ROI Calculator */}
        <RoiCalculator onBookDemo={onBookDemo} />

        {/* Home Page Finale (Team Teaser & FAQ) */}
        <Closure />
      </main>
    </motion.div>
  );
}
