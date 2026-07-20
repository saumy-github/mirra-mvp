import React, { useRef } from "react";
import { motion, useScroll, useTransform } from "motion/react";
import {
  Plus,
  Minus,
  RotateCcw,
  ChevronDown,
  Info,
  ArrowRight,
  Instagram,
  Linkedin,
  Twitter,
  Facebook,
} from "lucide-react";
import TextReveal, { KineticText } from "./TextReveal";

export default function MirrorCTA({ onBookDemo }: { onBookDemo: () => void }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start end", "end start"],
  });

  const yText = useTransform(scrollYProgress, [0, 1], ["-10%", "10%"]);
  const yCard1 = useTransform(scrollYProgress, [0, 1], ["0%", "-5%"]);
  const yCard2 = useTransform(scrollYProgress, [0, 1], ["5%", "-10%"]);

  return (
    <section
      ref={containerRef}
      className="relative flex min-h-screen w-full flex-col justify-center overflow-hidden border-t border-line bg-bg pt-16 pb-6 md:min-h-0"
    >
      {/* Background massive MIRRA text */}
      <div className="pointer-events-none absolute right-0 bottom-4 left-0 z-0 flex justify-center select-none">
        <motion.div
          style={{ y: yText }}
          className="text-[24vw] leading-[0.75] font-medium tracking-tight whitespace-nowrap text-ink/5"
        >
          Mirra
        </motion.div>
      </div>

      <div className="relative z-10 mx-auto flex w-full max-w-310 flex-col items-center px-5 sm:px-8">
        {/* Header Section */}
        <div className="mx-auto mb-12 max-w-3xl text-center">
          <TextReveal
            as="h2"
            variant="wipe-right"
            className="mb-4 text-4xl leading-[1.05] font-medium tracking-tight text-ink md:text-[56px]"
          >
            A better fit for every storefront
          </TextReveal>
          <TextReveal
            as="p"
            variant="lift"
            delay={0.1}
            className="mx-auto mb-8 max-w-2xl text-sm leading-relaxed font-medium tracking-wide text-muted md:text-base"
          >
            Mirra helps fashion brands reduce returns, improve fit confidence, and turn product
            pages into try-on experiences.
          </TextReveal>

          <motion.button
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2, duration: 0.8 }}
            onClick={onBookDemo}
            className="mx-auto rounded-full bg-ink px-9 py-4 text-sm font-semibold tracking-widest text-bg uppercase shadow-lg transition-colors hover:bg-wine hover:text-white"
          >
            <KineticText>Book a demo</KineticText>
          </motion.button>
        </div>

        {/* Middle Visual Section (Cards & Wavy Line) */}
        <div className="relative mx-auto mb-28 flex h-90 w-full max-w-5xl items-center justify-center md:mb-40 md:h-105">
          {/* Wavy Line SVG */}
          <div className="pointer-events-none absolute inset-0 z-0 flex items-center justify-center">
            <svg
              className="h-full w-full text-[#e6cdad]"
              preserveAspectRatio="none"
              viewBox="0 0 1000 300"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              {/* Smooth bezier curve for the wavy line */}
              <path
                d="M 0 200 C 150 200, 200 130, 300 130 C 450 130, 500 220, 650 220 C 750 220, 800 110, 950 90 C 980 85, 1000 80, 1000 80"
                stroke="currentColor"
                strokeWidth="1.5"
              />

              {/* Points on the line */}
              <circle cx="750" cy="150" r="4" fill="#e6cdad" />
              <circle cx="900" cy="95" r="4" fill="#e6cdad" />
            </svg>
          </div>

          <div className="relative z-10 flex h-full w-full items-center justify-center">
            {/* Main Product Card */}
            <motion.div
              style={{ y: yCard1 }}
              className="absolute top-4 left-[3%] z-20 flex w-75 flex-col rounded-3xl border border-line bg-white p-4 shadow-[0_20px_50px_rgba(31,24,37,0.08)] md:left-[10%] md:w-85 md:p-5 lg:left-[15%]"
            >
              {/* Card Header */}
              <div className="mb-5 flex items-center justify-between px-1">
                <span className="text-xl font-semibold tracking-widest text-ink">MIRRA</span>
                <div className="flex items-center gap-1 rounded-full border border-line px-3 py-1.5 text-[10px] text-muted">
                  Fit: True to size <ChevronDown size={12} />
                </div>
              </div>

              {/* Card Image Area */}
              <div className="relative mb-5 flex h-60 gap-3 overflow-hidden rounded-2xl bg-surface p-3 md:h-70">
                {/* Thumbnails (Scrollable Navbar) */}
                <div
                  className="flex w-12 shrink-0 flex-col gap-2 overflow-y-auto pb-4"
                  style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
                >
                  {/* Item 1 - Active */}
                  <div className="aspect-3/4 w-full shrink-0 overflow-hidden rounded-lg border-2 border-ink bg-silver">
                    <img
                      src="https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?auto=format&fit=crop&w=100&q=80"
                      alt="Red Dress"
                      className="h-full w-full object-cover"
                    />
                  </div>
                  {/* Item 2 */}
                  <div className="aspect-3/4 w-full shrink-0 cursor-pointer overflow-hidden rounded-lg border border-line/50 bg-silver opacity-60 transition-opacity hover:opacity-100">
                    <img
                      src="https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=100&q=80"
                      alt="Outfit 2"
                      className="h-full w-full object-cover"
                    />
                  </div>
                  {/* Item 3 */}
                  <div className="aspect-3/4 w-full shrink-0 cursor-pointer overflow-hidden rounded-lg border border-line/50 bg-silver opacity-60 transition-opacity hover:opacity-100">
                    <img
                      src="https://images.unsplash.com/photo-1539008835657-9e8e9680c956?auto=format&fit=crop&w=100&q=80"
                      alt="Outfit 3"
                      className="h-full w-full object-cover"
                    />
                  </div>
                  {/* Item 4 */}
                  <div className="aspect-3/4 w-full shrink-0 cursor-pointer overflow-hidden rounded-lg border border-line/50 bg-silver opacity-60 transition-opacity hover:opacity-100">
                    <img
                      src="https://images.unsplash.com/photo-1550639525-c97d455acf70?auto=format&fit=crop&w=100&q=80"
                      alt="Outfit 4"
                      className="h-full w-full object-cover"
                    />
                  </div>
                  {/* Item 5 */}
                  <div className="aspect-3/4 w-full shrink-0 cursor-pointer overflow-hidden rounded-lg border border-line/50 bg-silver opacity-60 transition-opacity hover:opacity-100">
                    <img
                      src="https://images.unsplash.com/photo-1572804013427-4d7ca7268217?auto=format&fit=crop&w=100&q=80"
                      alt="Outfit 5"
                      className="h-full w-full object-cover"
                    />
                  </div>
                  {/* Item 6 */}
                  <div className="aspect-3/4 w-full shrink-0 cursor-pointer overflow-hidden rounded-lg border border-line/50 bg-silver opacity-60 transition-opacity hover:opacity-100">
                    <img
                      src="https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?auto=format&fit=crop&w=100&q=80"
                      alt="Outfit 6"
                      className="h-full w-full object-cover grayscale"
                    />
                  </div>
                </div>

                {/* Main Image */}
                <div className="relative flex-1 overflow-hidden rounded-xl bg-silver">
                  <img
                    src="https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?auto=format&fit=crop&w=400&q=80"
                    alt="Model"
                    className="absolute inset-0 h-full w-full object-cover"
                  />

                  {/* Zoom Controls */}
                  <div className="absolute top-1/2 right-3 flex -translate-y-1/2 flex-col gap-2 rounded-full bg-white/90 p-2 shadow-[0_4px_12px_rgba(0,0,0,0.1)] backdrop-blur-md">
                    <button className="rounded-full p-1 text-ink transition-colors hover:bg-surface">
                      <Plus size={14} />
                    </button>
                    <button className="rounded-full p-1 text-ink transition-colors hover:bg-surface">
                      <Minus size={14} />
                    </button>
                    <button className="rounded-full p-1 text-ink transition-colors hover:bg-surface">
                      <RotateCcw size={14} />
                    </button>
                  </div>
                </div>
              </div>

              {/* Card Footer */}
              <div className="flex items-end justify-between px-2">
                <div>
                  <h4 className="mb-1 text-[13px] font-medium text-ink">
                    Relaxed Cashmere Sweater
                  </h4>
                  <p className="text-[11px] text-muted">Ivory • 100% Cashmere</p>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <span className="text-sm font-medium text-ink">$420</span>
                  <button className="rounded-full border border-ink px-5 py-2 text-[11px] font-medium text-ink transition-colors hover:bg-ink hover:text-white">
                    Try on
                  </button>
                </div>
              </div>
            </motion.div>

            {/* Fit Confidence Card */}
            <motion.div
              style={{ y: yCard2 }}
              className="absolute top-[35%] left-[65%] z-10 hidden w-50 rounded-2xl border border-line bg-white p-5 shadow-[0_20px_50px_rgba(31,24,37,0.06)] sm:block md:left-[55%] lg:left-[62%]"
            >
              <div className="mb-3 flex items-center gap-1.5 text-[10px] font-medium tracking-wider text-muted uppercase">
                Fit Confidence <Info size={12} />
              </div>
              <div className="mb-2 text-5xl font-medium text-ink">94%</div>
              <div className="mb-6 pr-4 text-[11px] leading-relaxed text-muted">
                of shoppers feel confident in their size
              </div>
              <button className="flex w-full items-center justify-between border-t border-line pt-4 text-[11px] font-medium text-ink transition-colors hover:text-wine">
                View insights <ArrowRight size={14} />
              </button>
            </motion.div>

            {/* Returns Badge */}
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              whileInView={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.6, duration: 0.5, type: "spring" }}
              className="absolute top-[25%] left-[80%] z-10 hidden items-center gap-1.5 rounded-full bg-[#e6cdad] px-4 py-1.5 text-[11px] font-medium text-ink shadow-sm md:left-[80%] md:flex lg:left-[85%]"
            >
              Returns <span className="text-[10px] font-bold">↓</span>
            </motion.div>
          </div>
        </div>
      </div>

      {/* Bottom Footer Row */}
      <div className="relative z-20 flex w-full flex-col items-end justify-between border-t border-ink/10 px-2 pt-6 pb-2 md:flex-row">
        {/* Logo and Copyright */}
        <div className="flex flex-col items-start gap-3">
          <div className="flex items-center gap-2 text-ink">
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" />
              <path
                d="M12 8V16M8 12H16"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
            <span className="text-xl font-semibold tracking-tight">Mirra</span>
          </div>
          <div className="text-[11px] font-medium text-ink/60">
            <p>&copy; 2026 Mirra Software Inc.</p>
            <p className="mt-0.5">Handcrafted with ❤️ for apparel brands</p>
          </div>
        </div>

        {/* Social Icons */}
        <div className="mt-8 flex items-center gap-5 text-ink/70 md:mt-0">
          <a href="#" className="transition-colors hover:text-ink">
            <Facebook size={18} strokeWidth={1.5} />
          </a>
          <a href="#" className="transition-colors hover:text-ink">
            <Instagram size={18} strokeWidth={1.5} />
          </a>
          <a href="#" className="transition-colors hover:text-ink">
            <Twitter size={18} strokeWidth={1.5} />
          </a>
          <a href="#" className="transition-colors hover:text-ink">
            <Linkedin size={18} strokeWidth={1.5} />
          </a>
        </div>
      </div>
    </section>
  );
}
