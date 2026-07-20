import React, { useState, useEffect, useRef } from "react";
import { motion, useScroll, useTransform, AnimatePresence } from "motion/react";
import { X } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";

interface HeaderProps {
  onJoinWaitlist: () => void;
  isPlaying: boolean;
  toggleSound: () => void;
}

export default function Header({ onJoinWaitlist, isPlaying, toggleSound }: HeaderProps) {
  const { scrollY } = useScroll();
  const [isSticky, setIsSticky] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const pillRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let lastScrollY = scrollY.get();

    const unsub = scrollY.on("change", (v) => {
      setIsSticky(v >= 100);

      // Auto-collapse the pill menu on scroll
      if (isMenuOpen) {
        if (Math.abs(v - lastScrollY) > 20) {
          setIsMenuOpen(false);
          lastScrollY = v;
        }
      } else {
        lastScrollY = v;
      }
    });
    return unsub;
  }, [scrollY, isMenuOpen]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (pillRef.current && !pillRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    };
    if (isMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isMenuOpen]);

  const navBg = useTransform(
    scrollY,
    [0, 50],
    ["rgba(248, 243, 242, 0)", "rgba(248, 243, 242, 0.88)"],
  );
  const navBorder = useTransform(
    scrollY,
    [0, 50],
    ["rgba(196, 198, 204, 0)", "rgba(196, 198, 204, 0.72)"],
  );
  const navBlur = useTransform(scrollY, [0, 50], ["blur(0px)", "blur(12px)"]);

  const handleHomeClick = (e: React.MouseEvent) => {
    if (location.pathname === "/") {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
    setIsMenuOpen(false);
  };

  const scrollToProduct = () => {
    const productEl = document.getElementById("mirra-method") || document.getElementById("demo");
    if (productEl) {
      productEl.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const handleProductClick = (e: React.MouseEvent) => {
    e.preventDefault();
    if (location.pathname !== "/") {
      navigate("/");
      window.setTimeout(scrollToProduct, 120);
    } else {
      scrollToProduct();
    }
    setIsMenuOpen(false);
  };

  const navItems = [
    { label: "Home", to: "/", onClick: handleHomeClick },
    { label: "Product", to: "/#mirra-method", onClick: handleProductClick },
    { label: "Meet the Team", to: "/meet-the-team", onClick: () => setIsMenuOpen(false) },
    { label: "Pricing", to: "/pricing", onClick: () => setIsMenuOpen(false) },
  ];

  return (
    <>
      {/* Standard top bar (visible when not sticky) */}
      <motion.div
        animate={
          isSticky
            ? { opacity: 0, y: -20, pointerEvents: "none" }
            : { opacity: 1, y: 0, pointerEvents: "auto" }
        }
        transition={{ duration: 0.5, ease: [0.075, 0.82, 0.165, 1] }}
        style={{
          backgroundColor: navBg,
          borderBottomColor: navBorder,
          backdropFilter: navBlur,
          WebkitBackdropFilter: navBlur,
        }}
        className="fixed top-0 right-0 left-0 z-50 flex items-center justify-between border-b border-transparent px-6 py-4 sm:px-12"
      >
        <Link
          to="/"
          onClick={handleHomeClick}
          className="cursor-pointer font-display text-xl font-bold tracking-[0.3em] transition-opacity hover:opacity-70"
        >
          MIRRA
        </Link>

        {/* Desktop Center Nav */}
        <div className="hidden items-center gap-8 md:flex">
          {navItems.map((item) => (
            <Link
              key={item.label}
              to={item.to}
              onClick={item.onClick}
              className="text-sm font-medium transition-colors hover:text-wine"
            >
              {item.label}
            </Link>
          ))}
        </div>

        {/* Desktop Right Actions */}
        <div className="hidden items-center gap-6 md:flex">
          <button
            onClick={toggleSound}
            className="group relative flex items-center gap-2 px-2 py-1 text-[10px] font-bold tracking-widest uppercase opacity-60 transition-all hover:opacity-100"
          >
            <span>{isPlaying ? "sound on" : "sound off"}</span>
            <div className="flex h-3 items-end gap-0.5">
              {[1, 2, 3, 4].map((i) => (
                <motion.div
                  key={i}
                  animate={isPlaying ? { height: ["20%", "100%", "20%"] } : { height: "20%" }}
                  transition={
                    isPlaying ? { repeat: Infinity, duration: 0.5 + i * 0.1, delay: i * 0.1 } : {}
                  }
                  className="w-0.5 rounded-full bg-wine"
                />
              ))}
            </div>
          </button>

          <button
            onClick={onJoinWaitlist}
            className="group relative overflow-hidden rounded-full bg-black px-5 py-2 text-[11px] font-bold tracking-wider text-white uppercase transition-transform duration-300 hover:scale-105 hover:bg-black/80"
          >
            <span className="relative z-10">Book a Demo</span>
          </button>
        </div>

        {/* Mobile Menu Toggle (When not sticky) */}
        <div className="md:hidden">
          <button onClick={() => setIsMenuOpen(!isMenuOpen)} className="p-2">
            <div className="mb-1.5 h-px w-5 bg-ink" />
            <div className="h-px w-5 bg-ink" />
          </button>
        </div>
      </motion.div>

      {/* Sticky Pill Nav (morphs in on scroll) */}
      <motion.div
        ref={pillRef}
        initial={{ x: "-50%", opacity: 0, y: -30, scale: 0.92 }}
        animate={
          isSticky
            ? { opacity: 1, y: 0, scale: 1, x: "-50%", pointerEvents: "auto" }
            : { opacity: 0, y: -30, scale: 0.92, x: "-50%", pointerEvents: "none" }
        }
        transition={{ duration: 0.6, ease: [0.075, 0.82, 0.165, 1] }}
        className="fixed top-5 left-1/2 z-50 flex transform-gpu items-center justify-center"
      >
        <div
          className="relative flex items-center overflow-hidden"
          style={{
            height: "56px",
            borderRadius: "200px",
            background: "rgba(248,243,242,0.9)",
            border: "1px solid rgba(196,198,204,0.85)",
            backdropFilter: "blur(24px)",
            WebkitBackdropFilter: "blur(24px)",
            boxShadow: "0 8px 32px rgba(31,24,37,0.12)",
          }}
        >
          <AnimatePresence mode="wait">
            {!isMenuOpen ? (
              <motion.div
                key="collapsed"
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.4, ease: [0.075, 0.82, 0.165, 1] }}
                className="flex items-center overflow-hidden px-2 whitespace-nowrap"
              >
                <button
                  onClick={() => setIsMenuOpen(true)}
                  className="ml-1 flex h-10 w-10 shrink-0 flex-col items-center justify-center gap-1.5 rounded-full transition-colors hover:bg-black/10"
                >
                  <div className="h-px w-4 bg-ink" />
                  <div className="h-px w-4 bg-ink" />
                </button>

                <div className="mx-2 h-6 w-px shrink-0 bg-silver" />

                <Link
                  to="/"
                  onClick={handleHomeClick}
                  className="mx-2 shrink-0 font-display text-sm font-bold tracking-[0.2em] transition-opacity hover:opacity-70"
                >
                  MIRRA
                </Link>

                <div className="mx-2 h-6 w-px shrink-0 bg-silver" />

                <button
                  onClick={toggleSound}
                  className="group flex h-10 w-10 shrink-0 items-center justify-center rounded-full transition-colors hover:bg-black/10"
                >
                  <div className="flex h-3 items-end gap-0.5 opacity-60 transition-opacity group-hover:opacity-100">
                    {[1, 2, 3, 4].map((i) => (
                      <motion.div
                        key={i}
                        animate={isPlaying ? { height: ["20%", "100%", "20%"] } : { height: "20%" }}
                        transition={
                          isPlaying
                            ? { repeat: Infinity, duration: 0.5 + i * 0.1, delay: i * 0.1 }
                            : {}
                        }
                        className="w-0.5 rounded-full bg-wine"
                      />
                    ))}
                  </div>
                </button>

                <button
                  onClick={() => {
                    onJoinWaitlist();
                    setIsMenuOpen(false);
                  }}
                  className="relative mr-1 ml-2 shrink-0 overflow-hidden rounded-full bg-black px-5 py-2.5 text-[10px] font-bold tracking-wider text-white uppercase"
                >
                  Book a Demo
                </button>
              </motion.div>
            ) : (
              <motion.div
                key="expanded"
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.5, ease: [0.075, 0.82, 0.165, 1] }}
                className="flex items-center overflow-hidden px-2 whitespace-nowrap"
              >
                {navItems.map((item, i) => (
                  <motion.div
                    key={item.label}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 + i * 0.05, duration: 0.3 }}
                    className="shrink-0"
                  >
                    <Link
                      to={item.to}
                      onClick={item.onClick}
                      className="px-4 py-2 text-sm font-medium whitespace-nowrap transition-colors hover:text-wine"
                    >
                      {item.label}
                    </Link>
                  </motion.div>
                ))}

                <div className="mx-1 h-6 w-px shrink-0 bg-silver" />

                <motion.button
                  initial={{ opacity: 0, scale: 0.7 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.48, duration: 0.35 }}
                  onClick={() => {
                    onJoinWaitlist();
                    setIsMenuOpen(false);
                  }}
                  className="relative mx-2 shrink-0 overflow-hidden rounded-full bg-black px-5 py-2.5 text-[10px] font-bold tracking-wider whitespace-nowrap text-white uppercase"
                >
                  Book a Demo
                </motion.button>

                <motion.button
                  initial={{ opacity: 0, scale: 0.7 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.55, duration: 0.3 }}
                  onClick={() => setIsMenuOpen(false)}
                  className="mr-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-ink/45 transition-all hover:bg-black/10 hover:text-ink"
                >
                  <X size={14} />
                </motion.button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>

      {/* Mobile Drawer */}
      <AnimatePresence>
        {isMenuOpen && !isSticky && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed inset-0 z-40 flex flex-col bg-bg px-6 pt-24 md:hidden"
          >
            <div className="flex flex-col gap-6 text-2xl font-medium">
              {navItems.map((item) => (
                <Link key={item.label} to={item.to} onClick={item.onClick}>
                  {item.label}
                </Link>
              ))}
            </div>
            <div className="mt-12">
              <button
                onClick={() => {
                  onJoinWaitlist();
                  setIsMenuOpen(false);
                }}
                className="w-full rounded-full bg-black py-4 font-semibold text-white"
              >
                Book a Demo
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
