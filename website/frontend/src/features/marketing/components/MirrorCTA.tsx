import { useRef } from "react";
import { motion, useScroll, useTransform } from "motion/react";

/**
 * Site footer: just the parallax MIRRA wordmark. The cards / wavy line /
 * footer nav that used to live here were removed upstream in
 * Mirra-landing-page — this matches that. No CTA button any more, so the
 * component no longer takes onBookDemo.
 */
export default function MirrorCTA() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start end", "end start"],
  });

  const yText = useTransform(scrollYProgress, [0, 1], ["-10%", "10%"]);

  return (
    <section
      ref={containerRef}
      className="relative flex h-[50vh] w-full flex-col justify-center overflow-hidden bg-bg pt-16 pb-6"
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
    </section>
  );
}
