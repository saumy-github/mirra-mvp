import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Link } from "react-router-dom";
import TextReveal from "./TextReveal";

const LaurelBranch = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 100 120"
    fill="currentColor"
    xmlns="http://www.w3.org/2000/svg"
  >
    {/* Curved Stem */}
    <path
      d="M75,105 C55,100 35,85 30,55 C28,30 45,10 60,5"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
    />
    {/* Solid Leaves */}
    <path d="M68,98 C56,100 48,93 46,90 C53,86 63,89 68,98 Z" />
    <path d="M72,102 C62,107 52,103 49,100 C53,94 62,94 72,102 Z" />

    <path d="M54,82 C42,80 36,71 35,68 C42,66 50,71 54,82 Z" />
    <path d="M58,87 C47,89 39,82 36,78 C41,74 50,77 58,87 Z" />

    <path d="M43,64 C33,60 30,50 30,47 C36,47 42,54 43,64 Z" />
    <path d="M48,69 C36,68 30,59 29,55 C34,53 42,58 48,69 Z" />

    <path d="M36,45 C28,39 27,28 28,25 C33,27 37,35 36,45 Z" />
    <path d="M41,50 C30,46 26,36 26,32 C31,32 37,39 41,50 Z" />

    <path d="M35,26 C30,17 32,7 35,3 C39,7 39,17 35,26 Z" />
    <path d="M41,31 C32,25 31,14 32,10 C37,12 40,21 41,31 Z" />
  </svg>
);

const teamTeaserImages = [
  "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=256&h=256&q=80",
  "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=256&h=256&q=80",
  "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=256&h=256&q=80",
  "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=256&h=256&q=80",
  "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?auto=format&fit=crop&w=256&h=256&q=80",
];

const TeamLaurelEmblem = () => (
  <div
    className="relative mx-auto flex h-44 w-full max-w-82.5 items-center justify-center"
    aria-label="Mirra team portraits framed by laurel leaves"
  >
    <motion.div
      className="pointer-events-none absolute top-1/2 left-0 h-36 w-24 -translate-y-1/2 text-ink/80 sm:left-2 sm:h-40 sm:w-28"
      initial={{ opacity: 0, rotate: -10, x: 18 }}
      whileInView={{ opacity: 1, rotate: 0, x: 0 }}
      viewport={{ once: true, amount: 0.5 }}
      transition={{ duration: 0.9, ease: [0.76, 0, 0.24, 1] }}
      aria-hidden="true"
    >
      <LaurelBranch className="h-full w-full" />
    </motion.div>

    <div className="relative z-10 flex items-center justify-center -space-x-3 sm:-space-x-4">
      {teamTeaserImages.map((src, idx) => {
        const sizes = [46, 55, 70, 55, 46];
        return (
          <motion.div
            key={src}
            className="relative shrink-0 overflow-hidden rounded-full border-2 border-bg bg-surface shadow-[0_7px_22px_rgba(31,24,37,0.18)]"
            style={{
              width: sizes[idx],
              height: sizes[idx],
              zIndex: idx === 2 ? 30 : idx === 1 || idx === 3 ? 20 : 10,
            }}
            initial={{ opacity: 0, scale: 0.55, y: 14 }}
            whileInView={{ opacity: 1, scale: 1, y: 0 }}
            viewport={{ once: true, amount: 0.5 }}
            transition={{ duration: 0.62, delay: 0.12 + idx * 0.06, ease: [0.34, 1.56, 0.64, 1] }}
          >
            <img
              src={src}
              alt={"Mirra team member " + (idx + 1)}
              className="h-full w-full object-cover grayscale transition-all duration-700 group-hover:scale-105 group-hover:grayscale-0"
            />
          </motion.div>
        );
      })}
    </div>

    <motion.div
      className="pointer-events-none absolute top-1/2 right-0 h-36 w-24 -translate-y-1/2 -scale-x-100 text-ink/80 sm:right-2 sm:h-40 sm:w-28"
      initial={{ opacity: 0, rotate: 10, x: -18 }}
      whileInView={{ opacity: 1, rotate: 0, x: 0 }}
      viewport={{ once: true, amount: 0.5 }}
      transition={{ duration: 0.9, ease: [0.76, 0, 0.24, 1] }}
      aria-hidden="true"
    >
      <LaurelBranch className="h-full w-full" />
    </motion.div>
  </div>
);

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

export default function Closure() {
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  return (
    <>
      <section className="w-full border-t border-silver bg-bg py-24">
        <div className="mx-auto max-w-260 px-5 sm:px-8">
          {/* 4B: FOUNDERS TEASER (REPLACED WITH MINIMAL OVERLAPPING FORMAT) */}
          <div className="mb-32 flex flex-col items-center">
            <Link
              to="/meet-the-team"
              className="group mx-auto block w-full max-w-105 cursor-pointer rounded-3xl border border-line/40 bg-surface p-6 text-center transition-all duration-300 hover:shadow-md sm:p-8"
            >
              <div className="mb-2 select-none">
                <TextReveal
                  as="h2"
                  variant="chars"
                  className="text-2xl font-semibold tracking-tight whitespace-nowrap text-ink sm:text-3xl"
                >
                  Meet the Team
                </TextReveal>
              </div>

              <TeamLaurelEmblem />
            </Link>
          </div>
        </div>{" "}
        {/* Close max-w container */}
        {/* 4C: FAQ - Editorial Design */}
        <div className="w-full border-t border-line" id="faq">
          <div className="mx-auto max-w-260 px-5 sm:px-8">
            <div className="grid grid-cols-1 md:grid-cols-12">
              {/* Left Column */}
              <div className="pt-4 pb-8 md:col-span-3 md:pr-8">
                <span className="text-sm font-medium tracking-wide text-muted uppercase md:sticky md:top-28">
                  FAQs
                </span>
              </div>

              {/* Right Column */}
              <div className="pt-4 pb-2 md:col-span-9 md:border-l md:border-line md:pl-12">
                <TextReveal
                  as="h2"
                  variant="wipe-right"
                  className="mb-16 max-w-3xl text-4xl leading-[1.1] font-semibold tracking-tight text-ink md:text-5xl lg:text-6xl"
                >
                  Frequently asked questions.
                </TextReveal>

                <div className="flex flex-col border-t border-line">
                  {faqs.map((faq, idx) => (
                    <div
                      key={idx}
                      className={`group ${idx !== faqs.length - 1 ? "border-b border-line" : ""}`}
                    >
                      <button
                        onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                        className="flex w-full items-center justify-between py-6 text-left"
                      >
                        <span className="pr-8 text-lg font-normal tracking-tight text-ink transition-colors group-hover:text-wine md:text-xl">
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
        </div>
        {/* Full width bottom border for last FAQ */}
        <div className="w-full border-t border-line" />
      </section>
    </>
  );
}
