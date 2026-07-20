import React from "react";
import { Play } from "lucide-react";
import TextReveal from "./TextReveal";

export default function DemoPlaceholder() {
  return (
    <section
      id="demo"
      className="mx-auto flex w-full max-w-260 flex-col items-center px-5 py-24 sm:px-8"
    >
      <div className="mb-10 text-center">
        <TextReveal
          as="h3"
          variant="wipe-right"
          className="mb-4 text-3xl font-semibold tracking-tight text-ink md:text-4xl"
        >
          Experience Mirra
        </TextReveal>
        <TextReveal as="p" variant="lift" delay={0.14} className="mx-auto max-w-2xl text-muted">
          A guided walkthrough of Mirra on a live product page — from flat imagery to a confident
          fit decision.
        </TextReveal>
      </div>

      <div className="relative flex aspect-video w-full items-center justify-center overflow-hidden rounded-[28px] border border-silver bg-bg/75 shadow-sm">
        <div className="group flex cursor-pointer flex-col items-center text-center opacity-40 transition-opacity hover:opacity-100">
          <div className="mb-4 flex h-20 w-20 transform items-center justify-center rounded-full bg-surface transition-all group-hover:scale-110 group-hover:bg-wine group-hover:text-bg">
            <Play fill="currentColor" size={32} className="ml-2" />
          </div>
          <p className="text-sm font-semibold tracking-widest uppercase">Demo film — coming soon</p>
        </div>
      </div>
    </section>
  );
}
