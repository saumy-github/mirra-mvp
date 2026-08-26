import { AnimatePresence, MotionConfig, motion } from "motion/react";
import { useState } from "react";
import { LiquidCTA } from "@/features/marketing/components/LiquidCTA";
import styles from "./pricing.module.css";

type BillingCycle = "monthly" | "annually";

type PricingTier = {
  name: string;
  monthlyPrice: string;
  annualPrice: string;
  idealFor: string;
  features: readonly string[];
  cta: string;
  featured?: boolean;
};

const PRICING_TIERS: readonly PricingTier[] = [
  {
    name: "Startup",
    monthlyPrice: "$80",
    annualPrice: "$72",
    idealFor: "Early-stage brands & startups.",
    features: [
      "Up to 50 Products",
      "Basic analytics dashboard",
      "Self-serve onboarding",
      "Standard email support",
    ],
    cta: "Join",
  },
  {
    name: "Custom",
    monthlyPrice: "Custom",
    annualPrice: "Custom",
    idealFor: "Enterprise retailers & global fashion brands.",
    features: [
      "Custom Product Catalog",
      "White-glove onboarding",
      "Custom analytics API",
      "Custom SLA & 24/7 support",
      "Dedicated Account Manager",
    ],
    cta: "Join",
    featured: true,
  },
  {
    name: "Business",
    monthlyPrice: "$160",
    annualPrice: "$144",
    idealFor: "Growing D2C & e-commerce brands.",
    features: [
      "Up to 240 Products",
      "Advanced conversion tracking",
      "Priority email support",
      "Dedicated Slack channel",
      "Early access to new features",
    ],
    cta: "Join",
  },
] as const;

function LiquidLink({
  children,
  href,
  compact = false,
  onClick,
}: {
  children: string;
  href: string;
  compact?: boolean;
  onClick?: () => void;
}) {
  return (
    <LiquidCTA
      className={`${styles.liquidButton}${compact ? ` ${styles.compactButton}` : ""}`}
      compact={compact}
      href={href}
      onClick={onClick}
    >
      {children}
    </LiquidCTA>
  );
}
export default function PricingClient() {
  const [billingCycle, setBillingCycle] = useState<BillingCycle>("annually");
  const annual = billingCycle === "annually";

  return (
    <MotionConfig reducedMotion="user">
    <div className="site">
      <main className={styles.page}>
        <section className={styles.pricingSection} id="top" aria-labelledby="pricing-title">
          <div className={styles.intro}>
            <p className={styles.eyebrow}>Pricing</p>
            <h1 id="pricing-title">
              <span className={styles.srOnly}>Simple, transparent pricing.</span>
              <span className={styles.visualLine} aria-hidden="true">Simple, transparent</span>
              <span className={styles.visualLine} aria-hidden="true">pricing.</span>
            </h1>
            <p className={styles.subheading}>Choose the rollout path that fits your store.</p>
            <p className={styles.note}>Final pricing is being locked in with our early access partners.</p>

            <div className={styles.billingToggle} role="group" aria-label="Billing cycle">
              <button
                type="button"
                className={!annual ? styles.activeToggle : ""}
                onClick={() => setBillingCycle("monthly")}
                aria-pressed={!annual}
              >
                Monthly
              </button>
              <button
                type="button"
                className={styles.cycleSwitch}
                onClick={() => setBillingCycle((current) => current === "monthly" ? "annually" : "monthly")}
                aria-label={annual ? "Switch to monthly billing" : "Switch to annual billing"}
              >
                <motion.span
                  animate={{ x: annual ? 18 : 0 }}
                  transition={{ type: "spring", stiffness: 420, damping: 34 }}
                  aria-hidden="true"
                />
              </button>
              <button
                type="button"
                className={annual ? styles.activeToggle : ""}
                onClick={() => setBillingCycle("annually")}
                aria-pressed={annual}
              >
                Annually
              </button>
            </div>
          </div>

          <div className={styles.tierGrid}>
            {PRICING_TIERS.map((tier, index) => {
              const price = annual ? tier.annualPrice : tier.monthlyPrice;
              const custom = price === "Custom";

              return (
                <article
                  className={`${styles.tierCard}${tier.featured ? ` ${styles.featuredCard}` : ""}`}
                  key={tier.name}
                >
                  <div className={styles.cardTopline}>
                    <span>{String(index + 1).padStart(2, "0")}</span>
                    {tier.featured && <span className={styles.partnerBadge}>For larger teams</span>}
                  </div>
                  <h2>{tier.name}</h2>
                  <div className={`${styles.price}${custom ? ` ${styles.customPrice}` : ""}`} aria-live="polite">
                    <AnimatePresence mode="wait" initial={false}>
                      <motion.div
                        key={`${tier.name}-${billingCycle}`}
                        initial={{ opacity: 0, y: 12, filter: "blur(5px)" }}
                        animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                        exit={{ opacity: 0, y: -12, filter: "blur(5px)" }}
                        transition={{ duration: 0.24 }}
                      >
                        <strong>{price}</strong>
                        {!custom && <span>/mo</span>}
                      </motion.div>
                    </AnimatePresence>
                  </div>
                  <p className={styles.billingDetail}>
                    {custom ? "Built around your rollout." : annual ? "Billed annually." : "Billed monthly."}
                  </p>
                  <p className={styles.idealFor}><span>Ideal For:</span> {tier.idealFor}</p>
                  <ul className={styles.featureList}>
                    {tier.features.map((feature) => (
                      <li key={feature}><span aria-hidden="true">✓</span>{feature}</li>
                    ))}
                  </ul>
                  <LiquidLink href="/join">{tier.cta}</LiquidLink>
                </article>
              );
            })}
          </div>

          <div className={styles.faqPrompt}>
            <p>You may have some questions.</p>
            <LiquidCTA className={styles.faqButton} href="/faq" tone="white" compact>
              Read our FAQ
            </LiquidCTA>
          </div>
        </section>
      </main>
    </div>
    </MotionConfig>
  );
}
