import NumberFlow from "@number-flow/react";
import { Fragment, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, ArrowUpRight, Check, ChevronDown, Minus } from "lucide-react";
import { motion } from "motion/react";
import styles from "./pricing.module.css";

type BillingCycle = "monthly" | "annually";
type PlanId = "startup" | "business" | "enterprise";

type Plan = {
  id: PlanId;
  name: string;
  tagline: string;
  /** USD per month. `null` means custom / contact sales. */
  monthlyPrice: number | null;
  annualPrice: number | null;
  priceNote?: string;
  inheritsFrom?: string;
  highlights: readonly string[];
  ctaLabel: string;
  ctaHref: string;
  recommended?: boolean;
};

// Value metric: active SKUs (garments digitized and live) + monthly try-on sessions.
// Keep these numbers in sync with the comparison table and the FAQ page.
const PLANS: readonly Plan[] = [
  {
    id: "startup",
    name: "Startup",
    tagline: "For early-stage D2C brands launching try-on across their store.",
    monthlyPrice: 90,
    annualPrice: 72,
    highlights: [
      "50 active SKUs",
      "5,000 try-ons / month",
      "Measurement-based shopper avatars",
      "Embeddable try-on widget",
      "Size recommendations",
      "Email support",
    ],
    ctaLabel: "Get started",
    ctaHref: "/join?tier=startup",
  },
  {
    id: "business",
    name: "Business",
    tagline: "For growing e-commerce teams with a full seasonal catalogue.",
    monthlyPrice: 180,
    annualPrice: 144,
    inheritsFrom: "Startup",
    highlights: [
      "240 active SKUs",
      "25,000 try-ons / month",
      "Conversion & return-rate tracking",
      "Custom widget theming",
      "Analytics export",
      "Priority support & Slack channel",
    ],
    ctaLabel: "Get started",
    ctaHref: "/join?tier=business",
    recommended: true,
  },
  {
    id: "enterprise",
    name: "Enterprise",
    tagline: "For retailers and multi-brand catalogues with custom needs.",
    monthlyPrice: null,
    annualPrice: null,
    priceNote: "Tailored to your catalogue and traffic",
    inheritsFrom: "Business",
    highlights: [
      "Unlimited SKUs",
      "Volume try-on pricing",
      "White-glove catalogue digitization",
      "Analytics API & SSO",
      "Dedicated account manager & SLA",
    ],
    ctaLabel: "Contact sales",
    ctaHref: "/join?tier=enterprise",
  },
] as const;

/** `true` = included, `false` = not included, string = included with a limit/qualifier. */
type Cell = boolean | string;

type ComparisonSection = {
  title: string;
  rows: readonly { label: string; values: Record<PlanId, Cell> }[];
};

const COMPARISON: readonly ComparisonSection[] = [
  {
    title: "Usage",
    rows: [
      { label: "Active SKUs", values: { startup: "50", business: "240", enterprise: "Unlimited" } },
      {
        label: "Try-on sessions / month",
        values: { startup: "5,000", business: "25,000", enterprise: "Custom volume" },
      },
      { label: "Storefronts", values: { startup: "1", business: "3", enterprise: "Unlimited" } },
      { label: "Team seats", values: { startup: "5", business: "15", enterprise: "Unlimited" } },
    ],
  },
  {
    title: "Try-on experience",
    rows: [
      {
        label: "Measurement-based shopper avatars",
        values: { startup: true, business: true, enterprise: true },
      },
      {
        label: "Physics-simulated garment fit",
        values: { startup: true, business: true, enterprise: true },
      },
      {
        label: "Embeddable try-on widget",
        values: { startup: true, business: true, enterprise: true },
      },
      {
        label: "Size recommendations",
        values: { startup: true, business: true, enterprise: true },
      },
      {
        label: "Remove Mirra branding",
        values: { startup: false, business: true, enterprise: true },
      },
      {
        label: "Custom widget theming",
        values: { startup: false, business: true, enterprise: true },
      },
    ],
  },
  {
    title: "Catalogue",
    rows: [
      {
        label: "2D image to 3D garment ingestion",
        values: { startup: true, business: true, enterprise: true },
      },
      {
        label: "Swap active SKUs any time",
        values: { startup: true, business: true, enterprise: true },
      },
      {
        label: "Bulk catalogue upload",
        values: { startup: false, business: true, enterprise: true },
      },
      {
        label: "White-glove digitization",
        values: { startup: false, business: false, enterprise: true },
      },
    ],
  },
  {
    title: "Analytics",
    rows: [
      {
        label: "Try-on engagement dashboard",
        values: { startup: true, business: true, enterprise: true },
      },
      {
        label: "Conversion & return-rate tracking",
        values: { startup: false, business: true, enterprise: true },
      },
      { label: "CSV export", values: { startup: false, business: true, enterprise: true } },
      { label: "Analytics API", values: { startup: false, business: false, enterprise: true } },
    ],
  },
  {
    title: "Security & support",
    rows: [
      {
        label: "Shopper-controlled data deletion",
        values: { startup: true, business: true, enterprise: true },
      },
      { label: "SSO (SAML)", values: { startup: false, business: false, enterprise: true } },
      {
        label: "Support",
        values: { startup: "Email", business: "Priority + Slack", enterprise: "Dedicated manager" },
      },
      { label: "Uptime SLA", values: { startup: false, business: false, enterprise: true } },
    ],
  },
] as const;

const PRICING_FAQS = [
  {
    question: "What counts as a try-on session?",
    answer:
      "A try-on session is one shopper viewing one garment on their avatar. Re-opening the same garment in the same visit doesn't count again, and browsing your store without trying anything on is always free.",
  },
  {
    question: "What is an active SKU?",
    answer:
      "Any product that has been digitized into a 3D garment and is live in your try-on widget. Archived products don't count, and you can swap which products are active whenever your catalogue changes.",
  },
  {
    question: "What happens if we go over our try-on limit?",
    answer:
      "Try-on never switches off mid-month — seasonal spikes and launches are covered. If you consistently run over, we'll reach out to recommend the right plan rather than send a surprise bill.",
  },
  {
    question: "Can we change plans or cancel?",
    answer:
      "Yes. Upgrade at any time and the difference is prorated. Monthly plans can be cancelled before the next billing cycle; annual plans run to the end of their term.",
  },
  {
    question: "Do we need to change our store platform?",
    answer:
      "No. Mirra embeds into the store you already run — there's no replatforming, and your product pages stay where they are.",
  },
  {
    question: "Do shoppers pay anything?",
    answer:
      "No. Creating a digital twin and trying on clothes is always free for your shoppers. Mirra is billed to the brand only.",
  },
] as const;

const PLAN_TONE_CLASS: Record<PlanId, string> = {
  startup: styles.toneStartup,
  business: styles.toneBusiness,
  enterprise: styles.toneEnterprise,
};

function priceSuffix(plan: Plan, annual: boolean) {
  if (plan.priceNote) return plan.priceNote;
  return annual ? "per month, billed yearly" : "per month, billed monthly";
}

function CellValue({ value }: { value: Cell }) {
  if (value === true) {
    return (
      <>
        <span className={styles.cellCheck}>
          <Check size={12} strokeWidth={3} aria-hidden="true" />
        </span>
        <span className={styles.srOnly}>Included</span>
      </>
    );
  }
  if (value === false) {
    return (
      <>
        <Minus size={14} strokeWidth={2} className={styles.cellDash} aria-hidden="true" />
        <span className={styles.srOnly}>Not included</span>
      </>
    );
  }
  return <span className={styles.cellText}>{value}</span>;
}

export default function PricingClient() {
  const [billingCycle, setBillingCycle] = useState<BillingCycle>("annually");
  const [mobilePlan, setMobilePlan] = useState<PlanId>("business");
  const annual = billingCycle === "annually";

  return (
    <div className={`${styles.site} is-pricing-page`} data-header="light" data-nav-label="Pricing">
      <main className={styles.main}>
        {/* Hero */}
        <section className={styles.hero} aria-labelledby="pricing-title">
          <p className={styles.eyebrow}>
            <span className={styles.eyebrowDot} aria-hidden="true" />
            Pricing
          </p>
          <h1 className={styles.heroTitle} id="pricing-title">
            Plans that grow with your catalogue
          </h1>
          <p className={styles.heroSub}>
            Pay for the products you put on try-on — never for the shoppers who use it. Every plan
            includes measurement-based avatars and physics-simulated fit.
          </p>

          <div className={styles.billingToggle} role="group" aria-label="Billing cycle">
            <button
              type="button"
              className={`${styles.toggleLabel} ${!annual ? styles.activeLabel : ""}`}
              onClick={() => setBillingCycle("monthly")}
              aria-pressed={!annual}
            >
              Monthly
            </button>

            <button
              type="button"
              className={styles.switchTrack}
              onClick={() => setBillingCycle((current) => (current === "monthly" ? "annually" : "monthly"))}
              aria-label={annual ? "Switch to yearly billing" : "Switch to monthly billing"}
              role="switch"
              aria-checked={annual}
            >
              <motion.span
                className={styles.switchThumb}
                animate={{ x: annual ? 18 : 0 }}
                transition={{ type: "spring", stiffness: 450, damping: 32 }}
                aria-hidden="true"
              />
            </button>

            <button
              type="button"
              className={`${styles.toggleLabel} ${annual ? styles.activeLabel : ""}`}
              onClick={() => setBillingCycle("annually")}
              aria-pressed={annual}
            >
              Yearly
            </button>

            <span className={styles.discountBadge}>Save 20%</span>
          </div>
        </section>

        {/* Plan cards */}
        <section className={styles.planGrid} aria-label="Plans">
          {PLANS.map((plan) => {
            const price = annual ? plan.annualPrice : plan.monthlyPrice;

            return (
              <article
                key={plan.id}
                className={`${styles.planCard} ${PLAN_TONE_CLASS[plan.id]} ${
                  plan.recommended ? styles.planRecommended : ""
                }`}
                aria-labelledby={`plan-${plan.id}`}
              >
                <header className={styles.planHeader}>
                  <h2 className={styles.planName} id={`plan-${plan.id}`}>
                    <span className={styles.planSwatch} aria-hidden="true" />
                    {plan.name}
                  </h2>
                  {plan.recommended && <span className={styles.recommendedTag}>Most popular</span>}
                </header>

                <p className={styles.planTagline}>{plan.tagline}</p>

                <div className={styles.priceBlock}>
                  <span className={styles.priceFigure}>
                    {price === null ? (
                      <span className={styles.priceAmount}>Custom</span>
                    ) : (
                      <NumberFlow
                        className={styles.priceAmount}
                        value={price}
                        format={{ style: "currency", currency: "USD", maximumFractionDigits: 0 }}
                      />
                    )}
                  </span>
                  <span className={styles.priceSuffix}>{priceSuffix(plan, annual)}</span>
                </div>

                <Link to={plan.ctaHref} className={`${styles.button} ${styles.planButton}`}>
                  {plan.ctaLabel}
                  <ArrowRight size={15} strokeWidth={2} aria-hidden="true" />
                </Link>

                <div className={styles.planFeatures}>
                  <p className={styles.inherits}>
                    {plan.inheritsFrom ? `Everything in ${plan.inheritsFrom}, plus:` : "Includes:"}
                  </p>
                  <ul className={styles.featureList}>
                    {plan.highlights.map((feature) => (
                      <li key={feature} className={styles.featureItem}>
                        <span className={styles.featureCheck}>
                          <Check size={11} strokeWidth={3} aria-hidden="true" />
                        </span>
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </article>
            );
          })}
        </section>

        <p className={styles.gridFootnote}>
          Shoppers never pay to create an avatar or try clothes on. Prices in USD, excluding
          applicable taxes.
        </p>

        {/* Comparison table */}
        <section className={styles.compare} aria-labelledby="compare-title">
          <h2 className={styles.sectionTitle} id="compare-title">
            Compare plans
          </h2>

          <div className={styles.mobilePlanPicker} role="radiogroup" aria-label="Plan to compare">
            {PLANS.map((plan) => (
              <button
                key={plan.id}
                type="button"
                role="radio"
                aria-checked={mobilePlan === plan.id}
                className={`${styles.toggleOption} ${mobilePlan === plan.id ? styles.toggleActive : ""}`}
                onClick={() => setMobilePlan(plan.id)}
              >
                {plan.name}
              </button>
            ))}
          </div>

          <table className={styles.compareTable} data-mobile-plan={mobilePlan}>
            <thead>
              <tr>
                <th scope="col" className={styles.compareCorner}>
                  <span className={styles.srOnly}>Feature</span>
                </th>
                {PLANS.map((plan) => {
                  const price = annual ? plan.annualPrice : plan.monthlyPrice;
                  return (
                    <th
                      key={plan.id}
                      scope="col"
                      className={`${styles.comparePlanHead} ${PLAN_TONE_CLASS[plan.id]}`}
                      data-plan={plan.id}
                    >
                      <div className={styles.comparePlanInner}>
                        <span className={styles.comparePlanName}>
                          <span className={styles.planSwatch} aria-hidden="true" />
                          {plan.name}
                        </span>
                        <span className={styles.comparePlanPrice}>
                          {price === null ? "Custom pricing" : `$${price} / month`}
                        </span>
                        <Link
                          to={plan.ctaHref}
                          className={`${styles.button} ${styles.buttonSmall} ${styles.planButton}`}
                        >
                          {plan.ctaLabel}
                        </Link>
                      </div>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {COMPARISON.map((section) => (
                <Fragment key={section.title}>
                  <tr className={styles.compareSectionRow}>
                    <th scope="colgroup">{section.title}</th>
                    {PLANS.map((plan) => (
                      <td key={plan.id} data-plan={plan.id} className={PLAN_TONE_CLASS[plan.id]} />
                    ))}
                  </tr>
                  {section.rows.map((row) => (
                    <tr key={row.label} className={styles.compareRow}>
                      <th scope="row" className={styles.compareLabel}>
                        {row.label}
                      </th>
                      {PLANS.map((plan) => (
                        <td key={plan.id} data-plan={plan.id} className={PLAN_TONE_CLASS[plan.id]}>
                          <CellValue value={row.values[plan.id]} />
                        </td>
                      ))}
                    </tr>
                  ))}
                </Fragment>
              ))}
            </tbody>
          </table>
        </section>

        {/* FAQ */}
        <section className={styles.faq} aria-labelledby="faq-title">
          <div className={styles.faqIntro}>
            <h2 className={styles.sectionTitle} id="faq-title">
              Questions &amp; answers
            </h2>
            <p className={styles.faqIntroText}>
              Can&apos;t find what you need?{" "}
              <Link to="/faq" className={styles.inlineLink}>
                Read the full FAQ
              </Link>
              .
            </p>
          </div>
          <div className={styles.faqList}>
            {PRICING_FAQS.map((item) => (
              <details key={item.question} className={styles.faqItem}>
                <summary className={styles.faqQuestion}>
                  <span>{item.question}</span>
                  <ChevronDown
                    size={18}
                    strokeWidth={1.8}
                    className={styles.faqIcon}
                    aria-hidden="true"
                  />
                </summary>
                <p className={styles.faqAnswer}>{item.answer}</p>
              </details>
            ))}
          </div>
        </section>

        {/* Closing CTA */}
        <section className={styles.closing} aria-labelledby="closing-title">
          <div className={styles.closingCopy}>
            <p className={styles.closingEyebrow}>Ready when you are</p>
            <h2 className={styles.closingTitle} id="closing-title">
              See the fit before it ships.
            </h2>
            <p className={styles.closingSub}>
              Put virtual try-on on your product pages and give shoppers the confidence to buy the
              right size.
            </p>
            <p className={styles.closingMeta}>
              Shopify ready · No replatforming · Fast implementation
            </p>
          </div>
          <div className={styles.closingActions}>
            <Link to="/join?tier=business" className={`${styles.button} ${styles.buttonPlum}`}>
              Get started
              <ArrowUpRight size={15} strokeWidth={2} aria-hidden="true" />
            </Link>
            <Link to="/join?tier=enterprise" className={styles.textLink}>
              Talk to sales
              <ArrowRight size={14} strokeWidth={2} aria-hidden="true" />
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}
