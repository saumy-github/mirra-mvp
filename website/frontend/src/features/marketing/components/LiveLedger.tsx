import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ArrowRight, RotateCcw, Box, CheckCircle2, AlertOctagon } from "lucide-react";
import TextReveal from "./TextReveal";

export default function LiveLedger() {
  const [scene, setScene] = useState(0);

  const nextScene = () => {
    if (scene < 5) {
      setScene(scene + 1);
    }
  };

  const reset = () => {
    setScene(0);
  };

  return (
    <section
      id="live-ledger"
      className="relative w-full scroll-mt-28 overflow-hidden border-t border-silver bg-bg pt-10 pb-32"
    >
      {/* Parallax Background */}
      <div
        className="absolute inset-0 z-0"
        style={{
          backgroundImage: "linear-gradient(135deg, #f8f3f2 0%, #f0e3e5 48%, #f8f3f2 100%)",
          backgroundAttachment: "fixed",
          backgroundPosition: "center",
          backgroundSize: "cover",
        }}
      />
      {/* Translucent light overlay */}
      <div className="absolute inset-0 z-0 bg-bg/60 backdrop-blur-[2px]" />

      <div className="relative z-10 mx-auto w-full max-w-7xl px-2">
        {/* Editorial Header */}
        <div className="flex flex-col justify-between gap-8 pb-8 md:flex-row md:items-end">
          <TextReveal
            as="h2"
            variant="wipe-right"
            className="max-w-225 text-5xl leading-none font-medium tracking-tighter text-ink md:text-6xl lg:text-[4.75rem]"
          >
            {"Bracket shopping is a margin killer."}
          </TextReveal>
          <div className="text-left md:max-w-70 md:pb-2 md:text-right">
            <TextReveal
              as="p"
              variant="lift"
              delay={0.2}
              className="text-[0.95rem] leading-snug font-medium text-ink/90"
            >
              Walk through the unit economics of a 'successful' order when sizing doubt enters the
              chat.
            </TextReveal>
          </div>
        </div>
        <div className="relative left-1/2 mb-12 h-px w-screen -translate-x-1/2 bg-silver" />
        <div className="flex min-h-125 flex-col items-stretch gap-12 lg:flex-row">
          {/* Left Side: Visuals */}
          <div className="relative flex flex-1 flex-col items-center justify-center p-8">
            <AnimatePresence mode="wait">
              {scene === 0 && (
                <motion.div
                  key="scene0"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 1.1 }}
                  className="flex flex-col items-center"
                >
                  <div className="relative mb-8 flex h-40 w-40 items-center justify-center rounded-card border border-[#A67E51] bg-[#C69C6D] shadow-[0_28px_70px_rgba(31,24,37,0.2)]">
                    <div className="rotate-[-10deg] rounded border-2 border-ink/20 p-2 font-mono text-sm font-bold text-ink/60 opacity-70">
                      ORDER #9481
                    </div>
                    <div className="absolute top-3 right-3 h-8 w-8">
                      <Box size={32} className="text-ink/15" />
                    </div>
                  </div>
                  <button
                    onClick={nextScene}
                    className="rounded-full bg-black px-8 py-4 text-sm font-bold text-white shadow-xl transition-transform hover:scale-105 hover:bg-black/80"
                  >
                    PRESS TO DISPATCH ORDER
                  </button>
                </motion.div>
              )}

              {scene === 1 && (
                <motion.div
                  key="scene1"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className="flex w-full max-w-sm flex-col items-center"
                >
                  <div className="mb-8 text-sm font-bold tracking-wider text-muted uppercase">
                    The Doubt Tax Begins
                  </div>
                  <div className="mb-8 flex w-full gap-6">
                    <button
                      type="button"
                      className="flex aspect-square flex-1 cursor-pointer flex-col items-center justify-center gap-2 rounded-card border border-silver bg-bg shadow-[0_24px_60px_rgba(31,24,37,0.12)] transition-colors hover:border-wine/50"
                      onClick={nextScene}
                    >
                      <div className="h-16 w-16 rounded-full bg-ink/5" />
                      <div className="font-mono text-lg font-bold text-ink">SIZE: M</div>
                    </button>
                    <button
                      type="button"
                      className="flex aspect-square flex-1 cursor-pointer flex-col items-center justify-center gap-2 rounded-card border border-silver bg-bg shadow-[0_24px_60px_rgba(31,24,37,0.12)] transition-colors hover:border-wine/50"
                      onClick={nextScene}
                    >
                      <div className="h-16 w-16 rounded-full bg-ink/5" />
                      <div className="font-mono text-lg font-bold text-ink">SIZE: L</div>
                    </button>
                  </div>
                  <div className="mb-2 flex items-center justify-center gap-2 text-center text-sm text-muted">
                    <AlertOctagon size={16} className="text-wine" />
                    <span className="font-medium">Inventory held hostage</span>
                  </div>
                  <div
                    className="cursor-pointer text-center text-sm text-muted transition-colors hover:text-ink"
                    onClick={nextScene}
                  >
                    Your shopper isn't sure, so they add two sizes to the cart.
                  </div>
                </motion.div>
              )}

              {scene === 2 && (
                <motion.div
                  key="scene2"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex w-full max-w-sm flex-col items-center"
                >
                  <div className="mb-8 text-sm font-bold tracking-wider text-muted uppercase">
                    The Inevitable Return
                  </div>
                  <div className="relative mb-8 flex w-full gap-6">
                    <div className="flex aspect-square flex-1 flex-col items-center justify-center gap-2 rounded-card border border-silver bg-bg opacity-50 shadow-sm">
                      <div className="h-16 w-16 rounded-full bg-ink/5" />
                      <div className="font-mono text-lg font-bold text-ink">SIZE: M</div>
                    </div>
                    <div className="relative flex aspect-square flex-1 flex-col items-center justify-center gap-2 rounded-card border-2 border-wine/45 bg-bg shadow-[0_24px_60px_rgba(31,24,37,0.12)]">
                      <div className="h-16 w-16 rounded-full bg-ink/5 opacity-50" />
                      <div className="font-mono text-lg font-bold text-wine line-through">
                        SIZE: L
                      </div>

                      <motion.div
                        initial={{ scale: 2, opacity: 0, rotate: -20 }}
                        animate={{ scale: 1, opacity: 1, rotate: -10 }}
                        transition={{ type: "spring", stiffness: 300, damping: 20 }}
                        className="absolute inset-0 m-auto flex h-16 w-32 items-center justify-center rounded-lg border-4 border-wine bg-bg/95 text-xs font-bold tracking-widest text-wine uppercase shadow-[0_22px_60px_rgba(107,31,42,0.24)] backdrop-blur-sm"
                      >
                        DID NOT FIT
                      </motion.div>
                    </div>
                  </div>
                  <div className="mb-8 rounded-lg border border-wine/10 bg-wine/5 p-3 text-center text-sm font-medium text-wine">
                    50% of the order value vanishes instantly.
                  </div>
                  <button
                    onClick={nextScene}
                    className="flex items-center gap-2 rounded-full bg-black px-8 py-4 text-sm font-bold text-white shadow-xl transition-transform hover:scale-105 hover:bg-black/80"
                  >
                    Process Return <ArrowRight size={16} />
                  </button>
                </motion.div>
              )}

              {scene === 3 && (
                <motion.div
                  key="scene3"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex w-full max-w-sm flex-col items-center gap-3"
                >
                  <div className="mb-4 text-sm font-bold tracking-wider text-muted uppercase">
                    The Hidden Margin Drain
                  </div>
                  {[
                    { label: "FedEx Outbound Shipping", cost: "-$14.20" },
                    { label: "FedEx Return Label", cost: "-$14.20" },
                    { label: "3PL Polybag & Inspection", cost: "-$4.50" },
                    { label: "Restocking Labor", cost: "-$6.00" },
                  ].map((item, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.4 }}
                      className="flex w-full items-center justify-between rounded-[14px] border border-wine/25 bg-bg p-5 shadow-[0_16px_36px_rgba(31,24,37,0.1)]"
                    >
                      <span className="text-sm font-medium text-ink">{item.label}</span>
                      <span className="font-mono font-bold text-[#FF3B30]">{item.cost}</span>
                    </motion.div>
                  ))}

                  <motion.button
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 2 }}
                    onClick={nextScene}
                    className="mt-6 flex items-center gap-2 rounded-full bg-black px-8 py-4 text-sm font-bold text-white shadow-xl transition-transform hover:scale-105 hover:bg-black/80"
                  >
                    View Final Ledger <ArrowRight size={16} />
                  </motion.button>
                </motion.div>
              )}

              {scene === 4 && (
                <motion.div
                  key="scene4"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="flex w-full max-w-md flex-col items-center text-center"
                >
                  <div className="relative w-full overflow-hidden rounded-[22px] border border-silver bg-bg p-8 shadow-[0_28px_80px_rgba(31,24,37,0.16)]">
                    <div className="absolute inset-x-0 top-0 h-1 bg-linear-to-r from-transparent via-wine/70 to-transparent" />
                    <div className="mb-6 border-b border-line pb-6 font-mono text-xs tracking-widest text-muted uppercase">
                      Unit Economics Breakdown
                    </div>

                    <div className="flex items-center justify-between py-3 text-sm">
                      <span className="text-muted">Gross Revenue Captured:</span>
                      <span className="font-mono font-semibold text-ink">+$260.00</span>
                    </div>
                    <div className="flex items-center justify-between py-3 text-sm">
                      <span className="text-muted">Refund Issued (Size L):</span>
                      <span className="font-mono font-semibold text-[#FF3B30]">-$130.00</span>
                    </div>
                    <div className="flex items-center justify-between py-3 text-sm">
                      <span className="text-muted">Reverse Logistics Toll:</span>
                      <span className="font-mono font-semibold text-[#FF3B30]">-$38.90</span>
                    </div>
                    <div className="mb-6 flex items-center justify-between border-b border-line py-3 pb-6 text-sm">
                      <span className="text-muted">Customer Acquisition Cost (CAC):</span>
                      <span className="font-mono font-semibold text-[#FF3B30]">-$65.00</span>
                    </div>

                    <div className="flex items-center justify-between text-lg font-bold">
                      <span className="text-ink">Net Order Profit:</span>
                      <span className="font-mono text-2xl text-[#19C37D]">$26.10</span>
                    </div>
                  </div>

                  <div className="relative mt-8 overflow-hidden rounded-2xl border border-wine/20 bg-wine/5 p-6 text-left text-sm text-ink/80 shadow-lg">
                    <div className="absolute top-0 bottom-0 left-0 w-1 bg-wine" />
                    <strong className="mb-1 block text-wine">
                      The Silent Killer of Apparel Brands
                    </strong>
                    After CAC, fulfillment, and reverse logistics, your "profitable" $260 order just
                    yielded a 10% margin. This is why brands are bleeding cash.
                  </div>

                  <div className="mt-8 flex flex-col items-center gap-5 sm:flex-row">
                    <button
                      onClick={nextScene}
                      className="flex items-center gap-2 rounded-full bg-black px-7 py-3 text-sm font-bold text-white transition-colors hover:bg-black/80"
                    >
                      See Mirra Intervention <ArrowRight size={16} />
                    </button>
                    <button
                      onClick={reset}
                      className="flex items-center gap-2 text-sm font-bold text-ink transition-colors hover:text-black"
                    >
                      <RotateCcw size={16} /> REPLAY SIMULATOR
                    </button>
                  </div>
                </motion.div>
              )}

              {scene === 5 && (
                <motion.div
                  key="scene5"
                  initial={{ opacity: 0, y: 30, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -20, scale: 0.95 }}
                  transition={{ type: "spring", stiffness: 80, damping: 20 }}
                  className="flex w-full max-w-lg flex-col items-center text-center"
                >
                  <div className="mb-4 flex w-full flex-col">
                    <div className="mb-2 flex items-center justify-center pb-6">
                      <span className="text-sm font-bold tracking-[0.2em] text-ink uppercase">
                        Stop margin leakage before checkout
                      </span>
                    </div>
                    <div className="flex flex-col items-center gap-10 sm:flex-row">
                      <div className="relative h-56 w-48 shrink-0 overflow-hidden rounded-card border-4 border-surface shadow-[0_20px_40px_rgba(31,24,37,0.15)]">
                        <img
                          src="https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=600&q=80"
                          alt="White T-Shirt"
                          className="h-full w-full scale-[1.15] object-cover"
                        />
                      </div>
                      <div className="flex flex-col gap-5 text-left">
                        {[
                          "Fit shown before checkout",
                          "Backup size avoided",
                          "Return loop avoided",
                        ].map((item) => (
                          <div key={item} className="flex items-center gap-4">
                            <CheckCircle2 size={24} className="shrink-0 text-[#19C37D]" />
                            <span className="text-lg font-medium tracking-tight text-ink/90">
                              {item}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  <p className="mt-7 max-w-md text-sm leading-relaxed text-ink/78">
                    Mirra ensures shoppers buy their true size the first time, keeping your revenue
                    out of the reverse logistics trap.
                  </p>

                  <button
                    onClick={reset}
                    className="mt-8 flex items-center gap-2 text-sm font-bold text-ink transition-colors hover:text-black"
                  >
                    <RotateCcw size={16} /> REPLAY SIMULATOR
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Right Side: Ledger Tracker */}
          <motion.div
            layout
            className="relative z-20 flex w-full shrink-0 flex-col self-center overflow-hidden rounded-[22px] border border-silver bg-bg/92 p-8 shadow-[0_30px_90px_rgba(31,24,37,0.16)] backdrop-blur-2xl lg:w-100"
          >
            <motion.div
              layout
              className="mb-8 border-b border-line pb-4 text-xs font-bold tracking-widest text-muted uppercase"
            >
              P&L DASHBOARD
            </motion.div>

            <motion.div layout className="flex flex-1 flex-col">
              <motion.div layout className="flex flex-col gap-2">
                <span className="text-sm font-medium text-muted">Gross Revenue</span>
                <motion.span className="font-mono text-4xl font-bold tracking-tight text-[#19C37D]">
                  $260.00
                </motion.span>
              </motion.div>

              <AnimatePresence>
                {scene >= 2 && scene < 5 && (
                  <motion.div
                    layout
                    initial={{ opacity: 0, height: 0, y: -10 }}
                    animate={{
                      opacity: 1,
                      height: "auto",
                      y: 0,
                      transition: { duration: 0.4, ease: "easeOut" },
                    }}
                    exit={{
                      opacity: 0,
                      height: 0,
                      y: -10,
                      transition: { duration: 0.3, ease: "easeIn" },
                    }}
                    className="overflow-hidden"
                  >
                    <div className="pt-8">
                      <div className="relative flex items-center justify-between border-b border-line pb-8">
                        <span className="text-sm font-semibold text-muted">
                          Refund (Did not fit)
                        </span>
                        <span className="font-mono text-2xl font-bold tracking-tight text-[#FF3B30]">
                          -$130.00
                        </span>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              <AnimatePresence>
                {scene >= 3 && scene < 5 && (
                  <motion.div
                    layout
                    initial={{ opacity: 0, height: 0, y: -10 }}
                    animate={{
                      opacity: 1,
                      height: "auto",
                      y: 0,
                      transition: { duration: 0.4, ease: "easeOut" },
                    }}
                    exit={{
                      opacity: 0,
                      height: 0,
                      y: -10,
                      transition: { duration: 0.3, ease: "easeIn" },
                    }}
                    className="overflow-hidden"
                  >
                    <div className="pt-8">
                      <div className="relative flex items-center justify-between border-b border-line pb-8">
                        <span className="text-sm font-semibold text-muted">
                          Reverse Logistics Toll
                        </span>
                        <span className="font-mono text-xl font-bold tracking-tight text-[#FF3B30]">
                          -$38.90
                        </span>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              <AnimatePresence>
                {scene >= 4 && scene < 5 && (
                  <motion.div
                    layout
                    initial={{ opacity: 0, height: 0, y: -10 }}
                    animate={{
                      opacity: 1,
                      height: "auto",
                      y: 0,
                      transition: { duration: 0.4, ease: "easeOut" },
                    }}
                    exit={{
                      opacity: 0,
                      height: 0,
                      y: -10,
                      transition: { duration: 0.3, ease: "easeIn" },
                    }}
                    className="overflow-hidden"
                  >
                    <div className="pt-8">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-semibold text-muted">Marketing CAC</span>
                        <span className="font-mono text-xl font-bold tracking-tight text-[#FF3B30]">
                          -$65.00
                        </span>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>

            <AnimatePresence>
              {scene === 4 && (
                <motion.div
                  layout
                  initial={{ opacity: 0, height: 0, y: -10 }}
                  animate={{
                    opacity: 1,
                    height: "auto",
                    y: 0,
                    transition: { duration: 0.5, ease: "easeOut", delay: 0.2 },
                  }}
                  exit={{
                    opacity: 0,
                    height: 0,
                    y: -10,
                    transition: { duration: 0.3, ease: "easeIn" },
                  }}
                  className="overflow-hidden"
                >
                  <div className="pt-12">
                    <div className="border-t-2 border-ink pt-8">
                      <div className="mb-2 text-sm font-bold tracking-wider text-ink uppercase">
                        Net Transaction Profit
                      </div>
                      <div className="font-mono text-4xl font-bold tracking-tight text-[#19C37D]">
                        $26.10
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <AnimatePresence>
              {scene === 5 && (
                <motion.div
                  layout
                  initial={{ opacity: 0, height: 0, y: -10 }}
                  animate={{
                    opacity: 1,
                    height: "auto",
                    y: 0,
                    transition: { duration: 0.45, ease: "easeOut" },
                  }}
                  exit={{
                    opacity: 0,
                    height: 0,
                    y: -10,
                    transition: { duration: 0.3, ease: "easeIn" },
                  }}
                  className="overflow-hidden"
                >
                  <div className="space-y-7 pt-8">
                    <div className="flex flex-col gap-2 border-t border-line pt-8">
                      <span className="text-sm font-medium text-muted">Backup Size Avoided</span>
                      <span className="font-mono text-2xl font-bold tracking-tight text-[#19C37D]">
                        $130.00 retained
                      </span>
                    </div>
                    <div className="flex flex-col gap-2 border-t border-line pt-7">
                      <span className="text-sm font-medium text-muted">Return Loop Avoided</span>
                      <span className="font-mono text-2xl font-bold tracking-tight text-[#19C37D]">
                        $38.90 protected
                      </span>
                    </div>
                    <div className="border-t-2 border-ink pt-7">
                      <div className="mb-2 text-sm font-bold tracking-wider text-ink uppercase">
                        Fit Confidence
                      </div>
                      <div className="text-sm leading-relaxed text-muted">
                        Resolved before dispatch.
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
