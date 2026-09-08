import { useEffect, useMemo, useState } from "react";
import { motion } from "motion/react";
import QRCode from "qrcode";
import { Link2, LockKeyhole, RefreshCw, Ruler, ScanLine, Smartphone } from "lucide-react";
import { FabricPanel } from "@/components/ui/fabric-panel";
import { MirraMark } from "@/components/ui/logo";
import { Skeleton } from "@/components/ui/misc";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { MATERIAL_SPRING } from "@/lib/motion-presets";

// Measurement intake moved from the standalone /measurements page into the
// profile once /profile/measurements grew its own entry form (doc 13, D7).
const DEFAULT_HANDOFF_PATH = "/profile/measurements";

const HANDOFF_STEPS = [
  {
    icon: ScanLine,
    label: "Scan",
    description: "Scan the QR code with your phone",
  },
  {
    icon: Ruler,
    label: "Measure",
    description: "Add the measurements used to create your fit profile",
  },
  {
    icon: RefreshCw,
    label: "Sync",
    description: "Return to Mirra and generate your avatar from that profile",
  },
] as const;

/**
 * Desktop-to-mobile handoff for the live, measurement-based avatar flow.
 * Photo capture is intentionally not promised here because the capture-session
 * API is no longer part of the active backend.
 */
export default function QrPairing() {
  const reduceMotion = useReducedMotion();
  const targetUrl = useMemo(() => {
    if (typeof window === "undefined") return DEFAULT_HANDOFF_PATH;
    return new URL(DEFAULT_HANDOFF_PATH, window.location.origin).toString();
  }, []);

  return (
    <main className="min-h-dvh bg-[#eceae6] p-1.5 sm:p-2.5">
      <div className="mx-auto grid min-h-[calc(100dvh-0.75rem)] max-w-480 overflow-hidden rounded-[1.35rem] border border-white/90 bg-[#faf9f7] shadow-[0_28px_80px_-50px_rgba(49,44,38,0.48)] lg:min-h-[calc(100dvh-1.25rem)] lg:grid-cols-[minmax(35rem,1.46fr)_minmax(28rem,1fr)]">
        <section className="relative min-h-184 overflow-hidden lg:min-h-0">
          <FabricPanel className="h-full min-h-full">
            <motion.div
              initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={reduceMotion ? { duration: 0.16 } : MATERIAL_SPRING}
              className="flex h-full w-full flex-col items-center px-1 py-6 text-center sm:px-7 sm:py-8"
            >
              <MirraMark size={42} strokeWidth={1.05} className="shrink-0 text-[#302e2a]" />

              <div className="mt-10 flex flex-col items-center sm:mt-12 lg:mt-[clamp(2.5rem,7vh,5.5rem)]">
                <p className="rounded-full border border-[#8c857a]/22 bg-white/26 px-4 py-1.5 text-[10px] font-medium tracking-[0.045em] text-[#6f6a63] shadow-[0_1px_0_rgba(255,255,255,.6)_inset] backdrop-blur-md sm:text-[11px]">
                  02 / 04&nbsp; · &nbsp;MOBILE SETUP
                </p>
                <h1 className="mt-6 max-w-xl text-[2rem] leading-[1.08] font-semibold tracking-[-0.04em] text-balance text-[#201f1c] sm:text-[2.45rem] lg:text-[clamp(2.1rem,2.6vw,2.85rem)]">
                  Scan to continue on your phone
                </h1>
                <p className="mt-4 max-w-md text-[13px] leading-6 text-[#5e5a54] sm:text-[14px]">
                  Use your mobile camera to scan the QR code
                  <br className="hidden sm:block" /> and continue your fit setup.
                </p>
              </div>

              <QrPass targetUrl={targetUrl} />
            </motion.div>
          </FabricPanel>
        </section>

        <StatusPanel reduceMotion={reduceMotion} targetUrl={targetUrl} />
      </div>
    </main>
  );
}

function QrPass({ targetUrl }: { targetUrl: string }) {
  const [qrImage, setQrImage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    QRCode.toDataURL(targetUrl, {
      width: 520,
      margin: 1,
      errorCorrectionLevel: "H",
      color: { dark: "#171715", light: "#fffdf9" },
    })
      .then((image) => active && setQrImage(image))
      .catch(() => active && setQrImage(null));
    return () => {
      active = false;
    };
  }, [targetUrl]);

  return (
    <section
      aria-label="Mobile setup QR code"
      className="mt-8 w-full max-w-72 rounded-[1.55rem] border border-white/72 bg-[#f8f2e9]/62 p-3 shadow-[0_28px_70px_-38px_rgba(76,64,48,.62),0_1px_0_rgba(255,255,255,.72)_inset] backdrop-blur-xl sm:mt-9 sm:max-w-78"
    >
      <div className="rounded-[1.35rem] border border-white/84 bg-white/58 p-3 shadow-[0_16px_40px_-30px_rgba(45,40,34,.54)] backdrop-blur-lg sm:p-4">
        <div className="aspect-square overflow-hidden rounded-[1.05rem] bg-[#fffdf9] p-3 shadow-[0_1px_0_rgba(255,255,255,.8)_inset] sm:p-4">
          {qrImage ? (
            <img
              src={qrImage}
              alt="QR code to continue avatar setup on your phone"
              width={256}
              height={256}
              className="size-full"
            />
          ) : (
            <Skeleton className="size-full rounded-xl" />
          )}
        </div>
      </div>

      <dl className="mt-3 divide-y divide-[#81786d]/13 px-1 text-left text-[9px] leading-none font-medium tracking-[0.015em] text-[#777168] sm:text-[10px]">
        <InfoRow icon={<Link2 />} label="OPENS" value="Fit setup" />
        <InfoRow
          icon={<span className="size-1.5 rounded-full bg-[#80786f]" />}
          label="STATUS"
          value="Ready"
        />
        <InfoRow icon={<LockKeyhole />} label="ACCOUNT" value="Sign-in required" />
      </dl>
    </section>
  );
}

function InfoRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="grid grid-cols-[1fr_auto] items-center gap-3 py-3">
      <dt className="flex items-center gap-2 font-medium text-[#6e685f]">
        <span className="flex size-3.5 items-center justify-center [&>svg]:size-3">{icon}</span>
        {label}
      </dt>
      <dd className="text-right font-medium tracking-[-0.015em] text-[#514d47]">{value}</dd>
    </div>
  );
}

function StatusPanel({ reduceMotion, targetUrl }: { reduceMotion: boolean; targetUrl: string }) {
  return (
    <section className="relative flex min-h-168 flex-col bg-[radial-gradient(circle_at_55%_25%,rgba(255,255,255,.98),rgba(249,248,246,.88)_44%,rgba(245,244,242,.96)_100%)] px-7 py-10 sm:px-12 lg:min-h-0 lg:px-[clamp(2.5rem,5vw,5.75rem)] lg:py-[clamp(3rem,7vh,6rem)]">
      <motion.div
        initial={reduceMotion ? { opacity: 0 } : { opacity: 0, x: 18 }}
        animate={{ opacity: 1, x: 0 }}
        transition={reduceMotion ? { duration: 0.16 } : { ...MATERIAL_SPRING, delay: 0.08 }}
        className="mx-auto flex w-full max-w-lg flex-1 flex-col items-center"
      >
        <PhoneOrbit reduceMotion={reduceMotion} />

        <div className="mt-7 text-center sm:mt-9">
          <h2
            className="text-[1.75rem] leading-tight font-semibold tracking-[-0.04em] text-[#201f1c] sm:text-[2.05rem]"
            aria-live="polite"
          >
            Continue on your phone
          </h2>
          <p className="mt-2.5 text-sm leading-6 text-[#68645f]">
            Scan the QR code to open the next setup step.
          </p>
        </div>

        <div className="mt-10 flex w-full items-center gap-4 text-[#79746d] sm:mt-11">
          <span className="h-px flex-1 bg-[#6f6a64]/22" />
          <p className="shrink-0 text-[10px] font-medium tracking-[0.045em] sm:text-[11px]">
            WHAT HAPPENS NEXT
          </p>
          <span className="h-px flex-1 bg-[#6f6a64]/22" />
        </div>

        <ol className="mt-8 w-full space-y-6 sm:space-y-7">
          {HANDOFF_STEPS.map((step, index) => {
            const Icon = step.icon;
            return (
              <li
                key={step.label}
                className="relative grid grid-cols-[3.35rem_1fr] gap-5 sm:grid-cols-[3.75rem_1fr] sm:gap-6"
              >
                {index < HANDOFF_STEPS.length - 1 && (
                  <span
                    aria-hidden
                    className="absolute top-[3.65rem] left-[1.65rem] h-6 border-l border-dashed border-[#817b73]/35 sm:left-[1.85rem]"
                  />
                )}
                <span className="flex size-13.5 items-center justify-center rounded-full border border-[#756f67]/18 bg-white/76 text-[#302e2a] shadow-[0_8px_24px_-18px_rgba(43,39,35,.72)] sm:size-15">
                  <Icon size={23} strokeWidth={1.35} aria-hidden />
                </span>
                <div className="pt-1.5">
                  <div className="flex items-baseline gap-3.5">
                    <span className="text-[11px] font-medium text-[#504c47]">{index + 1}</span>
                    <h3 className="text-[14px] font-semibold tracking-[-0.015em] text-[#302e2a] sm:text-[15px]">
                      {step.label}
                    </h3>
                  </div>
                  <p className="mt-1.5 pl-7 text-[12px] leading-5 text-[#74706a] sm:text-[13px]">
                    {step.description}
                  </p>
                </div>
              </li>
            );
          })}
        </ol>

        <a
          href={targetUrl}
          className="mt-9 inline-flex min-h-11 items-center justify-center rounded-full border border-[#746f68]/18 bg-white/72 px-5 text-xs font-medium text-[#4d4944] shadow-sm transition-colors hover:bg-white lg:hidden"
        >
          Continue on this device
        </a>
      </motion.div>

      <p className="mx-auto mt-9 flex items-center justify-center gap-2 text-center text-[10px] leading-relaxed text-[#77736d] sm:text-[11px] lg:mt-6">
        <LockKeyhole size={13} strokeWidth={1.5} aria-hidden />
        The QR code opens the same Mirra setup page on your phone.
      </p>
    </section>
  );
}

function PhoneOrbit({ reduceMotion }: { reduceMotion: boolean }) {
  return (
    <div className="relative flex size-32 items-center justify-center sm:size-36" aria-hidden>
      <motion.span
        className="absolute inset-1 rounded-full border border-[#3c3935]/45"
        animate={reduceMotion ? undefined : { rotate: 360 }}
        transition={reduceMotion ? undefined : { duration: 16, repeat: Infinity, ease: "linear" }}
      >
        <span className="absolute top-0 left-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#242321] shadow-[0_2px_7px_rgba(0,0,0,.28)]" />
        <span className="absolute top-1/2 right-0 size-1.5 translate-x-1/2 -translate-y-1/2 rounded-full bg-[#d0b588]" />
      </motion.span>
      <span className="absolute inset-5 rounded-full bg-white/82 shadow-[0_10px_40px_-24px_rgba(45,40,36,.6)]" />
      <Smartphone className="relative text-[#292724]" size={35} strokeWidth={1.4} />
      <motion.span
        className="absolute left-[21%] size-1 rounded-full bg-[#3a3834]"
        animate={reduceMotion ? undefined : { opacity: [0.25, 1, 0.25] }}
        transition={reduceMotion ? undefined : { duration: 2, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.span
        className="absolute right-[20%] size-1 rounded-full bg-[#b99b70]"
        animate={reduceMotion ? undefined : { opacity: [1, 0.25, 1] }}
        transition={reduceMotion ? undefined : { duration: 2, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
}
