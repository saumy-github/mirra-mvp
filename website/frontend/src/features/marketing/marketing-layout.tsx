import { useEffect, useRef, useState } from "react";
import { Outlet } from "react-router-dom";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";
import Header from "./components/Header";
import MirrorCTA from "./components/MirrorCTA";
import { CustomCursor } from "./components/CustomCursor";
import { WaitlistModal } from "./components/WaitlistModal";

gsap.registerPlugin(ScrollTrigger);

export interface MarketingContext {
  onBookDemo: () => void;
}

/** Single smooth-scroll instance, shared by every marketing page. Scoped to
 * this layout only — the app/studio pages have their own scroll containers
 * and would fight with Lenis. */
function useSmoothScroll() {
  useEffect(() => {
    const lenis = new Lenis({
      lerp: 0.08,
      wheelMultiplier: 0.85,
      touchMultiplier: 1.1,
      smoothWheel: true,
    });

    const raf = (time: number) => lenis.raf(time * 1000);
    lenis.on("scroll", ScrollTrigger.update);
    gsap.ticker.add(raf);
    gsap.ticker.lagSmoothing(0);

    return () => {
      gsap.ticker.remove(raf);
      lenis.destroy();
    };
  }, []);
}

/**
 * Wraps the marketing pages (Home, Pricing, Team) ported from
 * Mirra-landing-page — header, footer CTA, custom cursor, waitlist modal,
 * and smooth scroll, all scoped to this route subtree via <Outlet context>.
 * Not used by any /app route.
 */
export default function MarketingLayout() {
  const [isWaitlistOpen, setIsWaitlistOpen] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  useSmoothScroll();

  const toggleSound = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (!audio.paused) {
      audio.pause();
      return;
    }

    audio.volume = 0.42;
    audio.load();
    audio
      .play()
      .then(() => setIsPlaying(true))
      .catch(() => setIsPlaying(false));
  };

  const handleBookDemo = () => {
    setIsWaitlistOpen(true);
  };

  return (
    <div className="min-h-screen overflow-x-clip bg-bg text-ink selection:bg-wine/20">
      <audio
        ref={audioRef}
        src="/leberch-ethereal-cinematic-512569.mp3"
        preload="none"
        loop
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onError={() => setIsPlaying(false)}
      />
      <CustomCursor />
      <WaitlistModal isOpen={isWaitlistOpen} onClose={() => setIsWaitlistOpen(false)} />

      <Header onJoinWaitlist={handleBookDemo} isPlaying={isPlaying} toggleSound={toggleSound} />

      <Outlet context={{ onBookDemo: handleBookDemo } satisfies MarketingContext} />

      <MirrorCTA onBookDemo={handleBookDemo} />
    </div>
  );
}
