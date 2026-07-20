import React from "react";
import { motion } from "motion/react";
import { Zap, ArrowRight } from "lucide-react";
import LiquidMetal from "./LiquidMetal";
import TextReveal, { KineticText } from "./TextReveal";

interface HeroProps {
  onBookDemo: () => void;
}

const EarlyAccessPill = ({ onClick }: { onClick?: () => void }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, ease: "easeOut" }}
      onClick={onClick}
      className="group mb-12 cursor-pointer"
    >
      <div className="relative inline-flex items-center gap-0 overflow-hidden rounded-full border border-ink/10 bg-white/70 shadow-[0_8px_32px_rgba(0,0,0,0.04)] backdrop-blur-md">
        <div className="relative flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-full border-r border-ink/5 bg-surface">
          <LiquidMetal className="opacity-40 mix-blend-multiply grayscale-30" />
          {/* Pulsing dot overlay */}
          <div className="absolute inset-0 z-10 flex items-center justify-center">
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-ink/40 opacity-60" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-ink shadow-[0_0_8px_rgba(0,0,0,0.2)]" />
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 py-1 pr-5 pl-3">
          <div className="flex flex-col items-start">
            <span className="mb-0.5 text-[8px] leading-none font-black tracking-[0.2em] text-ink/50 uppercase">
              Limited Spots
            </span>
            <span className="text-[11px] leading-none font-bold tracking-[0.12em] text-ink uppercase">
              Early Access
            </span>
          </div>
          <div className="mx-1 h-6 w-px bg-ink/10" />
          <div className="flex items-center gap-1.5">
            <motion.div
              animate={{ scale: [1, 1.25, 1], opacity: [0.5, 1, 0.5] }}
              transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
            >
              <Zap size={11} className="fill-ink/70 text-ink/70" />
            </motion.div>
            <span className="text-[10px] font-semibold tracking-widest text-ink/50 uppercase transition-colors group-hover:text-ink/80">
              Join waitlist
            </span>
            <motion.div
              animate={{ x: [0, 4, 0] }}
              transition={{ repeat: Infinity, duration: 1.6, ease: "easeInOut" }}
            >
              <ArrowRight
                size={10}
                className="text-ink/30 transition-colors group-hover:text-ink/60"
              />
            </motion.div>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default function Hero({ onBookDemo }: HeroProps) {
  return (
    <section className="relative mx-auto flex min-h-screen max-w-7xl flex-col items-center overflow-hidden px-5 pt-32 pb-16 text-center sm:px-8 sm:pt-48 lg:px-12">
      <div className="relative z-10 flex w-full flex-col items-center">
        <EarlyAccessPill onClick={onBookDemo} />

        <TextReveal
          as="h1"
          variant="wipe-right"
          delay={0.16}
          className="w-full max-w-210 text-[clamp(38px,10vw,72px)] leading-[0.95] font-semibold tracking-[-0.075em] wrap-break-word text-ink sm:text-[clamp(42px,5.6vw,72px)]"
        >
          {"Realistic Virtual Try-On\nfor Your Shopify Store"}
        </TextReveal>

        <TextReveal
          as="p"
          variant="lift"
          delay={0.42}
          className="mt-5 max-w-170 text-base leading-[1.35] text-muted sm:text-lg md:text-xl"
        >
          Let customers see how your clothes fit before they buy. Eliminate sizing issues, cut
          return rates, and boost conversions.
        </TextReveal>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.8 }}
          className="mt-10 flex flex-col items-center gap-4 sm:flex-row"
        >
          <button
            onClick={onBookDemo}
            className="rounded-full bg-black px-8 py-3.5 font-medium text-white transition-transform hover:scale-105 hover:bg-ink"
          >
            <KineticText>Book a Demo</KineticText>
          </button>
          <button
            onClick={onBookDemo}
            className="rounded-full border border-silver bg-transparent px-8 py-3.5 font-medium text-ink transition-colors hover:bg-surface"
          >
            <KineticText>Join Waitlist</KineticText>
          </button>
        </motion.div>
      </div>
    </section>
  );
}
