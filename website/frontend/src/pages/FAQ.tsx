import { MotionConfig, motion } from "motion/react";
import { useId, useState } from "react";
import { LiquidCTA } from "@/features/marketing/components/LiquidCTA";
import styles from "./faq.module.css";

const FAQS = [
  {
    question: "Does Mirra edit our live Shopify theme code?",
    answer:
      "No. Mirra is designed to use Shopify App Blocks and does not permanently alter your theme code. It is cleanly isolated.",
  },
  {
    question: "Can installing Mirra conflict with our customized storefront?",
    answer:
      "Mirra's styles and scripts are scoped to avoid conflicts with your existing theme customizations.",
  },
  {
    question: "Do our designers have to mail physical garment samples to a studio to be 3D-scanned?",
    answer:
      "We are designed to work with your existing digital assets and standard tech packs, minimizing the need for physical shipping.",
  },
  {
    question: "Does the 3D viewer replace our primary PDP photography carousel?",
    answer:
      'No, it sits alongside your existing imagery as an additional "Try On" button, allowing shoppers to opt-in.',
  },
  {
    question: "Does a shopper have to download an iOS app or grant camera permissions to test the drape?",
    answer:
      "No apps required. The experience is designed to run entirely in the mobile browser.",
  },
  {
    question: "How long does implementation take?",
    answer:
      "Implementation time varies based on catalog size, but typical rollouts are designed to take weeks, not months.",
  },
  {
    question: "What happens if Mirra fails to load?",
    answer:
      'Our widget is built to fail silently. If there is a network error, the "Try On" button simply won\'t appear, and your normal PDP functions perfectly.',
  },
  {
    question: "Is there a long-term contract lock-in?",
    answer:
      "We offer flexible terms. Speak with our sales team to find the right pilot structure for your brand.",
  },
] as const;

const FAQ_GROUPS = [
  {
    id: "integration",
    label: "Integration",
    navLabel: "Integration",
    questions: FAQS.slice(0, 4),
  },
  {
    id: "shopper-experience",
    label: "Shopper experience",
    navLabel: "Shopper",
    questions: FAQS.slice(4, 7),
  },
  {
    id: "plans-and-terms",
    label: "Plans & terms",
    navLabel: "Plans & terms",
    questions: FAQS.slice(7),
  },
] as const;

function GlassLink({ children, href }: { children: string; href: string }) {
  return (
    <LiquidCTA
      className={styles.glassCta}
      href={href}
    >
      {children}
    </LiquidCTA>
  );
}

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
    <motion.article
      className={`${styles.item}${open ? ` ${styles.itemOpen}` : ""}`}
      layout
      transition={{ layout: { duration: 0.38, ease: [0.22, 1, 0.36, 1] } }}
    >
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
          <span className={styles.toggle} aria-hidden="true"><i /><i /></span>
        </button>
      </h3>

      <motion.div
        id={panelId}
        className={styles.answerWrap}
        role="region"
        aria-labelledby={buttonId}
        aria-hidden={!open}
        initial={false}
        animate={open ? { height: "auto", opacity: 1 } : { height: 0, opacity: 0 }}
        transition={{ height: { duration: 0.36, ease: [0.22, 1, 0.36, 1] }, opacity: { duration: 0.2 } }}
      >
        <p>{answer}</p>
      </motion.div>
    </motion.article>
  );
}

export default function FAQClient() {
  const [openQuestion, setOpenQuestion] = useState<string | null>(null);

  return (
    <MotionConfig reducedMotion="user">
    <div className={styles.site}>
      <main>
        <section className={styles.hero} id="top" aria-labelledby="faq-title">
          <h1 id="faq-title">Frequently Asked Questions</h1>
          <p className={styles.subheading}>Everything you need to know about integrating Mirra into your storefront.</p>
        </section>

        <div className={styles.categoryBar}>
          <nav className={styles.categoryNav} aria-label="FAQ sections">
            {FAQ_GROUPS.map((group) => (
              <a href={`#${group.id}`} key={group.id}>
                <span className={styles.categoryLabel}>
                  <span>{group.navLabel}</span>
                  <span aria-hidden="true">{group.navLabel}</span>
                </span>
              </a>
            ))}
          </nav>
        </div>

        <section className={styles.faqSection} aria-label="Mirra frequently asked questions">
          {FAQ_GROUPS.map((group) => (
            <section className={styles.faqGroup} id={group.id} key={group.id} aria-labelledby={`${group.id}-title`}>
              <h2 className={styles.groupTitle} id={`${group.id}-title`}>{group.label}</h2>
              <div className={styles.accordion}>
                {group.questions.map((item) => (
                  <AccordionItem
                    {...item}
                    key={item.question}
                    open={openQuestion === item.question}
                    toggle={() => setOpenQuestion((current) => current === item.question ? null : item.question)}
                  />
                ))}
              </div>
            </section>
          ))}
        </section>

        <section className={styles.demo} aria-labelledby="faq-demo-title">
          <p>Still have a question?</p>
          <h2 id="faq-demo-title">See how Mirra fits your store.</h2>
          <GlassLink href="/#book-a-demo">Book a Demo</GlassLink>
        </section>
      </main>
    </div>
    </MotionConfig>
  );
}
