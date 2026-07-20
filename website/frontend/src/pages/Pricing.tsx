import React, { useState } from "react";
import { motion } from "motion/react";
import { Check } from "lucide-react";
import { useOutletContext } from "react-router-dom";
import type { MarketingContext } from "../features/marketing/marketing-layout";
import TextReveal, { KineticText } from "../features/marketing/components/TextReveal";

export default function Pricing() {
  const { onBookDemo } = useOutletContext<MarketingContext>();
  const [isAnnual, setIsAnnual] = useState(true);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="w-full pt-32 pb-24"
    >
      <div className="mx-auto flex max-w-300 flex-col items-center px-5 sm:px-8">
        <div className="mb-12 text-center">
          <TextReveal
            as="h1"
            variant="wipe-right"
            className="mb-4 text-4xl font-semibold tracking-tight text-ink md:text-5xl lg:text-6xl"
          >
            Simple, transparent pricing.
          </TextReveal>
          <TextReveal as="p" variant="lift" delay={0.16} className="text-lg text-muted">
            Choose the rollout path that fits your store.
          </TextReveal>
          <p className="mt-2 text-sm text-muted opacity-70">
            Final pricing is being locked in with our early access partners.
          </p>
        </div>

        {/* Toggle */}
        <div className="mb-16 flex items-center gap-4">
          <span className={`text-sm font-semibold ${!isAnnual ? "text-ink" : "text-muted"}`}>
            Monthly
          </span>
          <button
            onClick={() => setIsAnnual(!isAnnual)}
            className="flex h-7 w-14 cursor-pointer items-center rounded-full bg-ink px-1 transition-colors"
          >
            <motion.div
              className="h-5 w-5 rounded-full bg-silver-light shadow-sm"
              animate={{ x: isAnnual ? 28 : 0 }}
              transition={{ type: "spring", stiffness: 500, damping: 30 }}
            />
          </button>
          <span className={`text-sm font-semibold ${isAnnual ? "text-ink" : "text-muted"}`}>
            Annually
          </span>
        </div>

        {/* Pricing Cards */}
        <div className="mb-24 grid w-full grid-cols-1 gap-6 md:grid-cols-3 md:gap-8">
          {/* Early Access */}
          <div className="flex flex-col rounded-4xl border border-silver bg-bg p-8 shadow-sm sm:p-10">
            <TextReveal as="h3" variant="chars" className="mb-6 text-2xl font-bold text-ink">
              Early Access
            </TextReveal>
            <div className="mb-2">
              <span className="font-mono text-5xl font-bold tracking-tighter">Custom</span>
            </div>
            <div className="mb-8 min-h-10 text-sm text-muted">
              Pilot program for select Shopify Plus merchants.
            </div>

            <div className="mb-10 flex flex-1 flex-col gap-4">
              {[
                "White-glove onboarding",
                "Up to 50 SKUs digitized",
                "Basic analytics dashboard",
              ].map((feature, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-surface">
                    <Check size={12} className="text-ink" />
                  </div>
                  <span className="text-sm font-medium text-muted">{feature}</span>
                </div>
              ))}
            </div>

            <button
              onClick={onBookDemo}
              className="w-full rounded-full border-2 border-silver py-4 font-bold text-ink transition-colors hover:border-wine"
            >
              <KineticText>Apply for Early Access</KineticText>
            </button>
          </div>

          {/* Growth */}
          <div className="relative flex transform flex-col rounded-4xl border border-ink bg-ink p-8 text-bg shadow-xl sm:p-10 md:-translate-y-4">
            <div className="absolute -top-4 left-1/2 -translate-x-1/2 rounded-full bg-black px-4 py-1 text-xs font-bold tracking-widest text-white uppercase shadow-sm">
              Most Popular
            </div>
            <TextReveal as="h3" variant="chars" className="mb-6 text-2xl font-bold">
              Growth
            </TextReveal>
            <div className="mb-2 flex items-end gap-1">
              <span className="font-mono text-5xl font-bold tracking-tighter">TBA</span>
              <span className="mb-1 text-bg/60">/mo</span>
            </div>
            <div className="mb-8 min-h-10 text-sm text-bg/60">
              {isAnnual ? "Billed annually" : "Billed monthly"} — finalized with early partners
            </div>

            <div className="mb-10 flex flex-1 flex-col gap-4">
              {[
                "Unlimited usage",
                "Up to 200 SKUs digitized",
                "Advanced conversion tracking",
                "Dedicated Slack channel",
              ].map((feature, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-silver/20">
                    <Check size={12} className="text-silver-light" />
                  </div>
                  <span className="text-sm font-medium text-bg/80">{feature}</span>
                </div>
              ))}
            </div>

            <button
              onClick={onBookDemo}
              className="w-full rounded-full bg-silver-light py-4 font-bold text-ink transition-colors hover:bg-silver"
            >
              <KineticText>Talk to Sales</KineticText>
            </button>
          </div>

          {/* Enterprise */}
          <div className="flex flex-col rounded-4xl border border-silver bg-bg p-8 shadow-sm sm:p-10">
            <TextReveal as="h3" variant="chars" className="mb-6 text-2xl font-bold text-ink">
              Enterprise
            </TextReveal>
            <div className="mb-2">
              <span className="font-mono text-5xl font-bold tracking-tighter">Custom</span>
            </div>
            <div className="mb-8 min-h-10 text-sm text-muted">
              For large catalogs and custom integrations.
            </div>

            <div className="mb-10 flex flex-1 flex-col gap-4">
              {[
                "Full catalog digitization",
                "Custom analytics API",
                "Custom SLA & 24/7 support",
                "On-site deployment options",
              ].map((feature, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-surface">
                    <Check size={12} className="text-ink" />
                  </div>
                  <span className="text-sm font-medium text-muted">{feature}</span>
                </div>
              ))}
            </div>

            <button
              onClick={onBookDemo}
              className="w-full rounded-full border-2 border-silver py-4 font-bold text-ink transition-colors hover:border-wine"
            >
              <KineticText>Contact Team</KineticText>
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
