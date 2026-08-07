import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import TextReveal from "@/features/marketing/components/TextReveal";

const faqs = [
  {
    q: "Does Mirra edit our live Shopify theme code?",
    a: "No. Mirra is designed to use Shopify App Blocks and does not permanently alter your theme code. It is cleanly isolated.",
  },
  {
    q: "Can installing Mirra conflict with our customized storefront?",
    a: "Mirra's styles and scripts are scoped to avoid conflicts with your existing theme customizations.",
  },
  {
    q: "Do our designers have to mail physical garment samples to a studio to be 3D-scanned?",
    a: "We are designed to work with your existing digital assets and standard tech packs, minimizing the need for physical shipping.",
  },
  {
    q: "Does the 3D viewer replace our primary PDP photography carousel?",
    a: 'No, it sits alongside your existing imagery as an additional "Try On" button, allowing shoppers to opt-in.',
  },
  {
    q: "Does a shopper have to download an iOS app or grant camera permissions to test the drape?",
    a: "No apps required. The experience is designed to run entirely in the mobile browser.",
  },
  {
    q: "How long does implementation take?",
    a: "Implementation time varies based on catalog size, but typical rollouts are designed to take weeks, not months.",
  },
  {
    q: "What happens if Mirra fails to load?",
    a: 'Our widget is built to fail silently. If there is a network error, the "Try On" button simply won\'t appear, and your normal PDP functions perfectly.',
  },
  {
    q: "Is there a long-term contract lock-in?",
    a: "We offer flexible terms. Speak with our sales team to find the right pilot structure for your brand.",
  },
];

export default function FAQ() {
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="w-full pt-32 pb-24"
    >
      <div className="mx-auto max-w-260 px-5 sm:px-8">
        {/* Header */}
        <div className="mb-24 flex flex-col items-center text-center">
          <TextReveal
            as="h1"
            variant="wipe-right"
            className="mb-6 text-5xl font-semibold tracking-tight text-ink md:text-6xl lg:text-7xl"
          >
            {"Frequently Asked\nQuestions"}
          </TextReveal>
          <TextReveal
            as="p"
            variant="lift"
            delay={0.24}
            className="mb-10 max-w-2xl text-lg text-muted md:text-xl"
          >
            Everything you need to know about integrating Mirra into your storefront.
          </TextReveal>
        </div>

        {/* FAQ Accordion */}
        <div className="w-full border-t border-line" id="faq">
          <div className="grid grid-cols-1 md:grid-cols-12">
            {/* Left Column */}
            <div className="pt-4 pb-8 md:col-span-3 md:pr-8">
              <span className="text-sm font-medium tracking-wide text-muted uppercase md:sticky md:top-28">
                FAQs
              </span>
            </div>

            {/* Right Column */}
            <div className="pt-4 pb-2 md:col-span-9 md:border-l md:border-line md:pl-12">
              <div className="flex flex-col">
                {faqs.map((faq, idx) => (
                  <div
                    key={idx}
                    className={`group ${idx !== faqs.length - 1 ? "border-b border-line" : ""}`}
                  >
                    <button
                      onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                      className="flex w-full items-center justify-between py-6 text-left"
                    >
                      <span className="pr-8 text-lg font-normal tracking-tight text-ink transition-colors group-hover:text-orange md:text-xl">
                        {faq.q}
                      </span>

                      {/* Custom Smooth Plus/Cross Icon */}
                      <div className="relative flex h-6 w-6 shrink-0 items-center justify-center">
                        {/* Horizontal line */}
                        <div
                          className={`absolute h-[1.5px] w-5 bg-ink transition-transform duration-500 ease-in-out ${openFaq === idx ? "rotate-45" : "rotate-0"}`}
                        />
                        {/* Vertical line */}
                        <div
                          className={`absolute h-[1.5px] w-5 bg-ink transition-transform duration-500 ease-in-out ${openFaq === idx ? "rotate-135" : "rotate-90"}`}
                        />
                      </div>
                    </button>
                    <AnimatePresence initial={false}>
                      {openFaq === idx && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
                          className="overflow-hidden"
                        >
                          <div className="max-w-3xl pt-2 pb-8 text-base leading-relaxed text-muted">
                            {faq.a}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Full width bottom border for last FAQ */}
        <div className="w-full border-t border-line" />
      </div>
    </motion.div>
  );
}
