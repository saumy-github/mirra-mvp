import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import QRCode from "qrcode";
import { captureUrl } from "@/config/urls";
import { Skeleton } from "@/components/ui/misc";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { MATERIAL_SPRING } from "@/lib/motion-presets";

/**
 * Frosted QR card floating over the fabric panel. The QR encodes only a
 * one-time, expiring token — never account IDs.
 */
export function QrCard({
  token,
  manualCode,
  dimmed,
  dimmedLabel,
}: {
  token: string;
  manualCode: string;
  dimmed?: boolean;
  dimmedLabel?: string;
}) {
  const reduceMotion = useReducedMotion();
  const [qrImage, setQrImage] = useState<{
    url: string;
    dataUrl: string;
  } | null>(null);
  const url = captureUrl(token);
  const statusLabel = dimmedLabel ?? "CONNECTED";
  const isError = ["EXPIRED", "CANCELLED", "UNAVAILABLE"].includes(statusLabel);
  const isWorking = ["PREPARING", "SYNCING"].includes(statusLabel);

  useEffect(() => {
    let alive = true;
    QRCode.toDataURL(url, {
      margin: 1,
      width: 480,
      color: { dark: "#211f1c", light: "#ffffff" },
    })
      .then((dataUrl) => alive && setQrImage({ url, dataUrl }))
      .catch(() => alive && setQrImage(null));
    return () => {
      alive = false;
    };
  }, [url]);

  return (
    <motion.section
      initial={
        reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.94, y: 18, filter: "blur(12px)" }
      }
      animate={{ opacity: 1, scale: 1, y: 0, filter: "blur(0px)" }}
      transition={reduceMotion ? { duration: 0.18 } : MATERIAL_SPRING}
      className="relative w-full max-w-88 border border-hairline bg-vellum p-6"
      aria-label="Pair your phone"
    >
      <div className="pointer-events-none absolute inset-x-8 top-0 h-px bg-linear-to-r from-transparent via-white to-transparent" />

      <div className="mb-4 flex items-center justify-between gap-3">
        <span className="eyebrow">[ {dimmed ? "SECURE LINK STATUS" : "PAIR YOUR PHONE"} ]</span>
        <span className="flex items-center gap-1.5 text-[10px] font-medium text-ink-soft">
          <svg viewBox="0 0 16 16" className="size-3.5" fill="none" aria-hidden>
            <rect x="3.25" y="7" width="9.5" height="7" rx="2" stroke="currentColor" />
            <path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2" stroke="currentColor" strokeLinecap="round" />
          </svg>
          One-time link
        </span>
      </div>

      <div className="relative mx-auto aspect-square w-full max-w-60 overflow-hidden border border-hairline bg-chalk p-4">
        <motion.div
          className="flex size-full items-center justify-center"
          animate={
            dimmed
              ? { opacity: 0.1, scale: 0.82, filter: "blur(5px)" }
              : { opacity: 1, scale: 1, filter: "blur(0px)" }
          }
          transition={reduceMotion ? { duration: 0.16 } : MATERIAL_SPRING}
        >
          {qrImage?.url === url ? (
            <img
              src={qrImage.dataUrl}
              alt="QR code linking your phone to this fitting session"
              width={208}
              height={208}
              className="size-full"
            />
          ) : (
            <Skeleton className="size-full" />
          )}
        </motion.div>

        <AnimatePresence>
          {dimmed && (
            <motion.div
              key={statusLabel}
              initial={
                reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.72, filter: "blur(8px)" }
              }
              animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
              exit={
                reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.86, filter: "blur(6px)" }
              }
              transition={reduceMotion ? { duration: 0.16 } : MATERIAL_SPRING}
              className="absolute inset-0 flex flex-col items-center justify-center bg-vellum/95 text-center"
              aria-live="polite"
            >
              <span
                className={`flex size-12 items-center justify-center rounded-full border ${
                  isError
                    ? "border-error/25 bg-error/8 text-error"
                    : isWorking
                      ? "border-ink/15 bg-mist text-ink-soft"
                      : "border-ok/25 bg-ok/8 text-ok"
                }`}
              >
                {isError ? (
                  <svg viewBox="0 0 24 24" className="size-6" fill="none" aria-hidden>
                    <path
                      d="M12 7.2v5.3m0 4v.1"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                    />
                    <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.5" />
                  </svg>
                ) : isWorking ? (
                  <motion.svg
                    viewBox="0 0 24 24"
                    className="size-6"
                    fill="none"
                    animate={reduceMotion ? undefined : { rotate: 360 }}
                    transition={
                      reduceMotion ? undefined : { duration: 1.5, repeat: Infinity, ease: "linear" }
                    }
                    aria-hidden
                  >
                    <circle
                      cx="12"
                      cy="12"
                      r="8"
                      stroke="currentColor"
                      strokeOpacity=".24"
                      strokeWidth="1.6"
                    />
                    <path
                      d="M12 4a8 8 0 0 1 8 8"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                    />
                  </motion.svg>
                ) : (
                  <svg viewBox="0 0 24 24" className="size-6" fill="none" aria-hidden>
                    <path
                      d="m7.5 12.5 3 3 6.5-7"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                )}
              </span>
              <span className={`eyebrow mt-5 ${isError ? "text-error!" : "text-graphite!"}`}>
                {statusLabel}
              </span>
              {!isError && (
                <span className="mt-2 text-xs text-muted">
                  {isWorking ? "Keep this window open" : "Continue on your phone"}
                </span>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <p className="mx-auto mt-5 max-w-68 text-center text-[13px] leading-relaxed text-ink-soft">
        Scan with your phone&apos;s Camera to take a few guided photographs. No app is required.
      </p>

      <a
        href={url}
        className="lift-1 mt-5 flex h-12 items-center justify-center rounded-panel-sm bg-graphite px-4 text-[11px] font-medium tracking-[0.14em] text-vellum uppercase lg:hidden"
      >
        Continue on this phone
      </a>

      <div className="mt-6 border-t border-hairline pt-4 text-center">
        <p className="text-[11px] leading-relaxed text-ink-soft">
          Can&apos;t scan? On your phone, open{" "}
          <span className="font-mono">
            {new URL(import.meta.env.VITE_RUNTIME_ORIGIN ?? "http://localhost:3000").host}/capture
          </span>{" "}
          and enter code{" "}
          <span className="mt-2 block text-sm font-medium tracking-[0.3em] text-graphite">
            {manualCode}
          </span>
        </p>
      </div>

      <p className="mt-4 flex items-center justify-center gap-1.5 text-center text-[10px] leading-relaxed text-muted">
        <svg viewBox="0 0 16 16" className="size-3 shrink-0" fill="none" aria-hidden>
          <path
            d="M8 1.75 13 3.6v3.55c0 3.1-1.85 5.7-5 7.1-3.15-1.4-5-4-5-7.1V3.6L8 1.75Z"
            stroke="currentColor"
            strokeLinejoin="round"
          />
          <path d="m5.75 8 1.4 1.4 3.15-3.15" stroke="currentColor" strokeLinecap="round" />
        </svg>
        Encrypted in transit · the pairing link expires automatically
      </p>
    </motion.section>
  );
}
