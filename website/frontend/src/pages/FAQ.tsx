import { MotionConfig, motion, AnimatePresence } from "motion/react";
import { ArrowRight, ArrowUpRight, ChevronDown, Search } from "lucide-react";
import { useId, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import styles from "./faq.module.css";

type FaqCategory = "all" | "integration" | "shopper-experience" | "plans-pricing" | "security" | "general";

type FaqItem = {
  question: string;
  answer: string;
  category: Exclude<FaqCategory, "all">;
};

const CATEGORIES: ReadonlyArray<{ id: FaqCategory; label: string }> = [
  { id: "all", label: "All" },
  { id: "integration", label: "Integration" },
  { id: "shopper-experience", label: "Shopper Experience" },
  { id: "plans-pricing", label: "Plans & Pricing" },
  { id: "security", label: "Security" },
  { id: "general", label: "General" },
];

const FAQS: ReadonlyArray<FaqItem> = [
  // --- General ---
  {
    category: "general",
    question: "What is Mirra?",
    answer:
      "Mirra is an AI-powered virtual try-on experience that helps fashion brands let their customers see how clothing looks on their body, before they buy. It reduces uncertainty, builds confidence, and drives higher conversions while keeping the shopping journey in one place.",
  },
  {
    category: "general",
    question: "How does Mirra work?",
    answer:
      "Mirra turns your existing 2D product photos and tech packs into realistic 3D drape simulations. Shoppers can input basic proportions or upload a photo to generate an avatar and preview realistic fit instantly on your product page.",
  },
  {
    category: "general",
    question: "Who is Mirra for?",
    answer:
      "Mirra is built for high-growth apparel and fashion brands running on Shopify who want to reduce returns, eliminate bracket buying, and give shoppers confidence in sizing.",
  },

  // --- Integration (Preserving all existing website content) ---
  {
    category: "integration",
    question: "Does Mirra edit our live Shopify theme code?",
    answer:
      "No. Mirra is designed to use Shopify App Blocks and does not permanently alter your theme code. It is cleanly isolated.",
  },
  {
    category: "integration",
    question: "Can installing Mirra conflict with our customized storefront?",
    answer:
      "Mirra's styles and scripts are scoped to avoid conflicts with your existing theme customizations.",
  },
  {
    category: "integration",
    question: "Do our designers have to mail physical garment samples to a studio to be 3D-scanned?",
    answer:
      "We are designed to work with your existing digital assets and standard tech packs, minimizing the need for physical shipping.",
  },
  {
    category: "integration",
    question: "Does the 3D viewer replace our primary PDP photography carousel?",
    answer:
      'No, it sits alongside your existing imagery as an additional "Try On" button, allowing shoppers to opt-in.',
  },
  {
    category: "integration",
    question: "How long does implementation take?",
    answer:
      "Implementation time varies based on catalog size, but typical rollouts are designed to take weeks, not months.",
  },
  {
    category: "integration",
    question: "Which platforms does Mirra integrate with?",
    answer:
      "Mirra natively supports Shopify and Shopify Plus storefronts using theme app extensions, with API-driven integrations available for custom headless and enterprise e-commerce platforms.",
  },
  {
    category: "integration",
    question: "How does Shopify integration work?",
    answer:
      "Integration takes minutes via Shopify App Blocks. Simply install the Mirra app, enable the block in your Shopify theme editor, and the Try On experience appears right beside your PDP gallery.",
  },

  // --- Shopper Experience (Preserving existing content) ---
  {
    category: "shopper-experience",
    question: "Does a shopper have to download an iOS app or grant camera permissions to test the drape?",
    answer:
      "No apps required. The experience is designed to run entirely in the mobile browser.",
  },
  {
    category: "shopper-experience",
    question: "What do shoppers need to do?",
    answer:
      "Shoppers simply tap 'Try On' directly on the product page. They can choose standard body proportions or upload a quick photo to see garments draped accurately in seconds in their browser.",
  },
  {
    category: "shopper-experience",
    question: "Do shoppers need an account?",
    answer:
      "No account is required to try on clothes. Shoppers can test fit as guests directly in the storefront, or create a Mirra profile to save measurements across visits.",
  },
  {
    category: "shopper-experience",
    question: "How are avatars created?",
    answer:
      "Shoppers can input basic height and sizing details or upload an optional reference photo. Mirra's geometry engine creates an accurate digital silhouette in seconds.",
  },
  {
    category: "shopper-experience",
    question: "How accurate are the try-ons?",
    answer:
      "Mirra combines garment pattern dimensions, fabric drape physics, and body proportions to render realistic fit tension and drape rather than flat generative image overlays.",
  },
  {
    category: "shopper-experience",
    question: "Can shoppers use Mirra on mobile?",
    answer:
      "Yes. Mirra is optimized specifically for mobile browsers (iOS Safari, Android Chrome), ensuring fast load times and fluid 60fps interaction on any device.",
  },

  // --- Security (Preserving existing content) ---
  {
    category: "security",
    question: "What happens if Mirra fails to load?",
    answer:
      'Our widget is built to fail silently. If there is a network error, the "Try On" button simply won\'t appear, and your normal PDP functions perfectly.',
  },
  {
    category: "security",
    question: "What happens to shopper photos?",
    answer:
      "Shopper photos are processed securely in real-time solely to extract silhouette geometry, never stored permanently without permission, and never used to train public machine learning models.",
  },
  {
    category: "security",
    question: "How does Mirra handle customer data?",
    answer:
      "All customer data is encrypted in transit and at rest with strict SOC 2 and GDPR compliance. Shopper data remains strictly brand-isolated.",
  },
  {
    category: "security",
    question: "Can users delete their avatar?",
    answer:
      "Yes. Shoppers can delete their saved measurements, photos, and avatar profile at any time with one click from their privacy settings.",
  },

  // --- Plans & Pricing (Preserving existing content) ---
  {
    category: "plans-pricing",
    question: "Is there a long-term contract lock-in?",
    answer:
      "We offer flexible terms. Speak with our sales team to find the right pilot structure for your brand.",
  },
  {
    category: "plans-pricing",
    question: "How is Mirra priced?",
    answer:
      "We offer predictable merchant tiers based on monthly order volume, plus a pilot tier for brands launching their first virtual try-on test.",
  },
  {
    category: "plans-pricing",
    question: "Are there usage limits?",
    answer:
      "Each tier includes a generous volume of monthly try-on sessions with automatic scaling to handle seasonal traffic spikes during product launches and holiday sales without interruption.",
  },
] as const;

function AccordionItem({
  answer,
  open,
  question,
  toggle,
}: {
  answer: string;
  open: boolean;
  question: string;
  toggle: () => void;
}) {
  const id = useId();
  const buttonId = `${id}-button`;
  const panelId = `${id}-panel`;

  return (
    <article className={`${styles.item} ${open ? styles.itemOpen : ""}`}>
      <h3>
        <button
          id={buttonId}
          className={styles.question}
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={toggle}
        >
          <span className={styles.questionText}>{question}</span>
          <ChevronDown
            size={18}
            strokeWidth={1.8}
            className={`${styles.chevron} ${open ? styles.chevronOpen : ""}`}
            aria-hidden="true"
          />
        </button>
      </h3>

      <motion.div
        id={panelId}
        className={styles.answerWrap}
        role="region"
        aria-labelledby={buttonId}
        initial={false}
        animate={open ? { height: "auto", opacity: 1 } : { height: 0, opacity: 0 }}
        transition={{
          height: { duration: 0.22, ease: [0.22, 1, 0.36, 1] },
          opacity: { duration: 0.18, ease: "easeOut" },
        }}
      >
        <div className={styles.answerContent}>
          <p>{answer}</p>
        </div>
      </motion.div>
    </article>
  );
}

export default function FAQClient() {
  const [activeCategory, setActiveCategory] = useState<FaqCategory>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [openQuestion, setOpenQuestion] = useState<string | null>(null);

  const filteredFaqs = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return FAQS.filter((item) => {
      const matchesCategory = activeCategory === "all" || item.category === activeCategory;
      if (!matchesCategory) return false;
      if (!query) return true;
      return (
        item.question.toLowerCase().includes(query) || item.answer.toLowerCase().includes(query)
      );
    });
  }, [activeCategory, searchQuery]);

  return (
    <MotionConfig reducedMotion="user">
      <div className={`${styles.site} is-faq-page`} data-header="light" data-nav-label="FAQ">
        <main>
          {/* FAQ Hero */}
          <section className={styles.hero} id="top" aria-labelledby="faq-title">
            <div className={styles.eyebrowPill}>
              <span className={styles.eyebrowDot} aria-hidden="true" />
              <span>FAQ</span>
            </div>
            <h1 className={styles.heroTitle} id="faq-title">
              Frequently Asked
              <br />
              Questions
            </h1>
            <p className={styles.heroSub}>
              Everything you need to know about Mirra, from how it works to integration, security,
              and more.
            </p>
          </section>

          {/* Category Filters (Section 4) */}
          <div className={styles.categoriesWrap}>
            <nav className={styles.categories} aria-label="FAQ categories">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat.id}
                  type="button"
                  className={`${styles.categoryPill} ${
                    activeCategory === cat.id ? styles.activeCategoryPill : ""
                  }`}
                  onClick={() => {
                    setActiveCategory(cat.id);
                    setOpenQuestion(null);
                  }}
                >
                  {cat.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Compact Search Bar (Section 8) */}
          <div className={styles.searchWrap}>
            <div className={styles.searchBar}>
              <Search size={14} strokeWidth={2} className={styles.searchIcon} aria-hidden="true" />
              <input
                type="search"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setOpenQuestion(null);
                }}
                placeholder="Search questions…"
                className={styles.searchInput}
                aria-label="Search frequently asked questions"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery("")}
                  className={styles.searchClear}
                  aria-label="Clear search query"
                >
                  ×
                </button>
              )}
            </div>
          </div>

          {/* FAQ Accordion (Section 5) */}
          <section className={styles.faqSection} aria-label="Frequently asked questions list">
            <AnimatePresence mode="wait">
              <motion.div
                key={`${activeCategory}-${searchQuery ? "search" : "static"}`}
                className={styles.accordion}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.18, ease: "easeOut" }}
              >
                {filteredFaqs.length > 0 ? (
                  filteredFaqs.map((item) => (
                    <AccordionItem
                      key={item.question}
                      question={item.question}
                      answer={item.answer}
                      open={openQuestion === item.question}
                      toggle={() =>
                        setOpenQuestion((current) =>
                          current === item.question ? null : item.question,
                        )
                      }
                    />
                  ))
                ) : (
                  <div className={styles.emptyState}>
                    <p>No questions found matching “{searchQuery}”.</p>
                    <button
                      type="button"
                      onClick={() => {
                        setSearchQuery("");
                        setActiveCategory("all");
                      }}
                    >
                      Browse all questions
                    </button>
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          </section>

          {/* Closing CTA Block (Section 9 - Refined Post-FAQ Conversion Bridge) */}
          <section className={styles.ctaSection} aria-labelledby="faq-closing-title">
            <div className={styles.ctaCard}>
              <svg
                className={styles.ctaContour}
                viewBox="0 0 1200 320"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                preserveAspectRatio="none"
                aria-hidden="true"
              >
                {/* Subtle corner wireframe curves that fade beyond edges without touching text */}
                <path
                  d="M-40 80 C 80 40, 180 15, 260 -20"
                  stroke="rgba(123, 49, 93, 0.10)"
                  strokeWidth="1.2"
                />
                <path
                  d="M 880 -20 C 990 60, 1100 110, 1240 140"
                  stroke="rgba(123, 49, 93, 0.10)"
                  strokeWidth="1.2"
                />
              </svg>

              <div className={styles.ctaLayout}>
                {/* Left Column (~65%) */}
                <div className={styles.ctaLeft}>
                  <p className={styles.ctaEyebrow}>STILL HAVE A QUESTION?</p>
                  <h2 className={styles.ctaHeading} id="faq-closing-title">
                    See how Mirra fits your store.
                  </h2>
                  <p className={styles.ctaSub}>
                    Talk to us about your catalogue, customers and the fit experience you want to
                    create.
                  </p>
                  <p className={styles.ctaMeta}>
                    Shopify ready · No replatforming · Fast implementation
                  </p>
                </div>

                {/* Right Column (~35%) */}
                <div className={styles.ctaRight}>
                  <Link to="/join" className={styles.ctaPrimaryBtn}>
                    <span>Join Mirra</span>
                    <ArrowUpRight
                      size={15}
                      strokeWidth={2.2}
                      className={styles.ctaPrimaryIcon}
                      aria-hidden="true"
                    />
                  </Link>

                  <Link to="/#integration" className={styles.ctaSecondaryLink}>
                    <span>See implementation</span>
                    <ArrowRight
                      size={14}
                      strokeWidth={2}
                      className={styles.ctaSecondaryIcon}
                      aria-hidden="true"
                    />
                  </Link>
                </div>
              </div>
            </div>
          </section>
        </main>
      </div>
    </MotionConfig>
  );
}
