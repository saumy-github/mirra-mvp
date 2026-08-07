import { useNavigate } from "react-router-dom";
import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { FabricPanel } from "@/components/ui/fabric-panel";
import { Button } from "@/components/ui/button";
import { DemoModeNotice, Skeleton } from "@/components/ui/misc";
import { QrCard } from "@/features/onboarding/components/qr-card";
import { SyncStatus } from "@/features/onboarding/components/sync-status";
import { GenerationProgress } from "@/features/onboarding/components/generation-progress";
import { SynchronizedState } from "@/features/onboarding/components/synchronized";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { useAvatarProfile, useAccount } from "@/hooks/use-shopper";
import {
  useAvatarJob,
  useCancelCaptureSession,
  useCaptureSession,
  useCreateCaptureSession,
} from "@/hooks/use-capture";
import { track } from "@/lib/analytics";
import { MATERIAL_SPRING } from "@/lib/motion-presets";

type Phase = "checking" | "decision" | "qr";

/**
 * Existing-avatar decision, desktop QR pairing, live capture status, and
 * the avatar-generation waiting experience.
 */
export default function OnboardingAvatar() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: account, isLoading: accountLoading } = useAccount();
  const { data: avatar, isLoading: avatarLoading } = useAvatarProfile(!!account);
  const reduceMotion = useReducedMotion();

  const [phase, setPhase] = useState<Phase>("checking");
  const create = useCreateCaptureSession();
  const cancel = useCancelCaptureSession();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const { data: session } = useCaptureSession(sessionId);
  const { data: job } = useAvatarJob(session?.avatarJobId ?? null);

  // Auth guard
  useEffect(() => {
    if (!accountLoading && !account) {
      navigate(`/auth/login?next=${encodeURIComponent("/onboarding/avatar")}`, { replace: true });
    }
  }, [account, accountLoading, navigate]);

  // Existing-avatar decision
  useEffect(() => {
    if (phase !== "checking" || avatarLoading || !account) return;
    setPhase(avatar ? "decision" : "qr");
  }, [phase, avatar, avatarLoading, account]);

  const startPairing = useCallback(() => {
    setPhase("qr");
    create.mutate(undefined, {
      onSuccess: (s) => {
        setSessionId(s.captureSessionId);
        track("qr_session_created", {
          sessionId: s.captureSessionId,
          authenticated: true,
        });
      },
    });
  }, [create]);

  useEffect(() => {
    if (phase === "qr" && !sessionId && !create.isPending) startPairing();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  // Analytics on capture-state transitions
  const prevState = useRef<string | null>(null);
  useEffect(() => {
    if (!session || session.state === prevState.current) return;
    const ctx = {
      sessionId: session.captureSessionId,
      authenticated: true,
    };
    if (session.state === "paired" || session.state === "consent_pending") track("qr_scanned", ctx);
    if (session.state === "capturing" && prevState.current === "consent_pending") {
      track("capture_consent_given", ctx);
      track("capture_started", ctx);
    }
    if (session.state === "uploaded") track("capture_completed", ctx);
    if (session.state === "processing") track("avatar_generation_started", ctx);
    prevState.current = session.state;
  }, [session]);

  const jobDone = useRef(false);
  useEffect(() => {
    if (!job || jobDone.current) return;
    if (job.state === "ready") {
      jobDone.current = true;
      // The freshly generated profile replaces the cached (possibly null) one.
      void qc.invalidateQueries({ queryKey: ["account", "avatar-profile"] });
      track("avatar_generation_completed", { authenticated: true });
    } else if (job.state === "failed") {
      jobDone.current = true;
      track("avatar_generation_failed", { authenticated: true });
    }
  }, [job, qc]);

  const goToMeasurements = useCallback(() => navigate("/onboarding/measurements"), [navigate]);

  function restart() {
    jobDone.current = false;
    prevState.current = null;
    setSessionId(null);
    create.reset();
    startPairing();
  }

  if (accountLoading || phase === "checking") {
    return (
      <main className="relative grid min-h-dvh place-items-center overflow-hidden bg-canvas px-6">
        <motion.div
          initial={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.94, y: 14 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={reduceMotion ? { duration: 0.16 } : MATERIAL_SPRING}
          className="relative flex w-full max-w-sm flex-col items-center text-center"
        >
          <div className="relative flex size-10 items-center justify-center border border-hairline">
            <motion.span
              className="size-1.5 rounded-full bg-graphite"
              animate={
                reduceMotion ? undefined : { scale: [0.75, 1, 0.75], opacity: [0.4, 1, 0.4] }
              }
              transition={
                reduceMotion ? undefined : { duration: 1.4, repeat: Infinity, ease: "easeInOut" }
              }
              aria-hidden
            />
          </div>
          <p className="eyebrow mt-7">Mirra fit profile</p>
          <h1 className="mt-4 text-xl font-medium tracking-[-0.03em] text-graphite">
            Preparing your fitting room
          </h1>
          <p className="mt-3 text-[13px] leading-relaxed text-slate">
            Checking your secure avatar profile…
          </p>
          <div className="mt-8 grid w-full grid-cols-[1fr_3fr] gap-3" aria-hidden>
            <Skeleton className="h-12" />
            <Skeleton className="h-12" />
          </div>
        </motion.div>
      </main>
    );
  }

  // ── Decision: a valid avatar already exists ──
  if (phase === "decision" && avatar) {
    return (
      <main className="grid min-h-dvh grid-cols-1 bg-vellum lg:grid-cols-[1.05fr_1fr]">
        <div className="relative hidden h-dvh border-r border-hairline lg:sticky lg:top-0 lg:block">
          <FabricPanel
            footer={`MIRRA_PROFILE // AVATAR: ${avatar.avatarLabel.toUpperCase()} // READY`}
          >
            <motion.div
              initial={
                reduceMotion
                  ? { opacity: 0 }
                  : { opacity: 0, scale: 0.9, y: 20, filter: "blur(12px)" }
              }
              animate={{ opacity: 1, scale: 1, y: 0, filter: "blur(0px)" }}
              transition={reduceMotion ? { duration: 0.18 } : MATERIAL_SPRING}
              className="flex h-full w-full flex-col"
            >
              <div className="flex items-center justify-between">
                <p className="eyebrow">Mirra / Fit profile</p>
                <span className="eyebrow">Ready to wear</span>
              </div>
              <div className="flex flex-1 items-center justify-center py-8">
                <div className="h-[min(60vh,31rem)] w-[min(40vw,22rem)] overflow-hidden border border-hairline bg-vellum">
                  <img
                    src={avatar.previewAssetUrl}
                    alt="Your saved avatar"
                    className="size-full object-contain"
                  />
                </div>
              </div>
              <p className="eyebrow text-center">Profile {avatar.avatarLabel} · Synchronized</p>
            </motion.div>
          </FabricPanel>
        </div>

        <section className="relative flex min-h-dvh items-center bg-vellum px-6 py-20 sm:px-10 lg:px-14 xl:px-20">
          <div className="absolute inset-x-0 top-0 flex items-center justify-between px-6 py-6 sm:px-10 lg:px-14 xl:px-20">
            <p className="text-[11px] tracking-[0.34em] text-graphite uppercase">Mirra</p>
            <span className="eyebrow">Avatar setup</span>
          </div>

          <motion.div
            initial={reduceMotion ? { opacity: 0 } : { opacity: 0, x: 24, filter: "blur(10px)" }}
            animate={{ opacity: 1, x: 0, filter: "blur(0px)" }}
            transition={reduceMotion ? { duration: 0.18 } : MATERIAL_SPRING}
            className="mx-auto w-full max-w-md"
          >
            <div className="mb-7 flex justify-center lg:hidden">
              <div className="relative h-48 w-36 overflow-hidden border border-hairline bg-bone">
                <img
                  src={avatar.previewAssetUrl}
                  alt="Your saved avatar"
                  className="size-full object-contain"
                />
                <span className="absolute top-2.5 right-2.5 flex size-5 items-center justify-center rounded-full bg-verdigris text-vellum">
                  <svg viewBox="0 0 16 16" className="size-3.5" fill="none" aria-hidden>
                    <path
                      d="m4 8.2 2.4 2.3L12 5"
                      stroke="currentColor"
                      strokeWidth="1.6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
              </div>
            </div>

            <p className="eyebrow">Avatar on file</p>
            <h1 className="mt-5 text-[clamp(2.1rem,4vw,2.9rem)] leading-[1.03] font-medium tracking-[-0.035em] text-graphite">
              Welcome back
            </h1>
            <p className="mt-5 max-w-md text-[14px] leading-relaxed text-slate">
              Your saved avatar is ready for this fitting. You can enter the studio now or review
              its measurements first.
            </p>

            <div className="mt-8 flex items-center gap-4 border-t border-b border-hairline py-4">
              <span className="flex size-8 items-center justify-center text-ash">
                <svg viewBox="0 0 18 18" className="size-4" fill="none" aria-hidden>
                  <circle cx="9" cy="9" r="6.5" stroke="currentColor" />
                  <path d="M9 5.8v3.7l2.3 1.5" stroke="currentColor" strokeLinecap="round" />
                </svg>
              </span>
              <div>
                <p className="eyebrow">Avatar {avatar.avatarLabel}</p>
                <p className="mt-1.5 text-[12px] text-slate">
                  Updated{" "}
                  {new Date(avatar.updatedAt).toLocaleDateString(undefined, {
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                  })}
                </p>
              </div>
            </div>

            <div className="mt-10 space-y-3">
              <Button
                className="w-full"
                size="lg"
                onClick={() => {
                  track("saved_avatar_selected", {
                    authenticated: true,
                  });
                  navigate("/studio");
                }}
              >
                Use my saved avatar
                <svg viewBox="0 0 18 18" className="size-4" fill="none" aria-hidden>
                  <path
                    d="M4 9h10m-4-4 4 4-4 4"
                    stroke="currentColor"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </Button>
              <Button variant="outline" className="w-full" size="lg" onClick={goToMeasurements}>
                Review measurements
              </Button>
              <Button variant="ghost" className="w-full" onClick={startPairing}>
                Create a new avatar
              </Button>
            </div>

            <p className="mt-8 flex items-start gap-2.5 border-t border-hairline pt-6 text-[11px] leading-relaxed text-ash">
              <svg viewBox="0 0 16 16" className="mt-0.5 size-3.5 shrink-0" fill="none" aria-hidden>
                <path
                  d="M8 1.75 13 3.6v3.55c0 3.1-1.85 5.7-5 7.1-3.15-1.4-5-4-5-7.1V3.6L8 1.75Z"
                  stroke="currentColor"
                  strokeLinejoin="round"
                />
              </svg>
              Your avatar remains in your Mirra profile and is never exposed to anyone else.
            </p>
          </motion.div>
        </section>
      </main>
    );
  }

  // ── QR pairing + generation ──
  const generating =
    session?.state === "processing" && job && job.state !== "ready" && job.state !== "failed";
  const synchronized = session?.state === "completed" || job?.state === "ready";
  const generationFailed = job?.state === "failed" || session?.state === "failed";
  const qrStatusLabel =
    session?.state === "created"
      ? "PREPARING"
      : session?.state === "expired"
        ? "EXPIRED"
        : session?.state === "cancelled"
          ? "CANCELLED"
          : session?.state === "failed"
            ? "UNAVAILABLE"
            : session?.state === "processing"
              ? "SYNCING"
              : "CONNECTED";
  const contentKey = generationFailed
    ? "generation-failed"
    : synchronized
      ? "synchronized"
      : generating
        ? "generating"
        : "capture";

  return (
    <main className="grid min-h-dvh grid-cols-1 bg-vellum lg:grid-cols-[minmax(28rem,1.05fr)_minmax(31rem,1fr)]">
      <div className="relative hidden h-dvh border-r border-hairline lg:sticky lg:top-0 lg:block">
        <FabricPanel
          footer={`MIRRA_RUNTIME // SESSION: ${
            session?.captureSessionId.slice(-6).toUpperCase() ?? "——"
          }`}
        >
          <div className="flex h-full w-full flex-col">
            <div className="flex items-center justify-between gap-4">
              <p className="eyebrow">Mirra / Private capture</p>
              <span className="eyebrow flex items-center gap-2">
                <span className="size-1.5 rounded-full bg-verdigris" aria-hidden />
                Secure session
              </span>
            </div>
            <div className="flex flex-1 items-center justify-center py-8">
              <AnimatePresence mode="popLayout" initial={false}>
                {session && !synchronized ? (
                  <motion.div
                    key="qr"
                    layout
                    transition={MATERIAL_SPRING}
                    className="w-full max-w-88"
                  >
                    <QrCard
                      token={session.oneTimeToken}
                      manualCode={session.manualCode}
                      dimmed={session.state !== "qr_ready"}
                      dimmedLabel={qrStatusLabel}
                    />
                  </motion.div>
                ) : !session ? (
                  <motion.div key="qr-loading" className="w-full max-w-88">
                    <Skeleton className="h-136 w-full" />
                  </motion.div>
                ) : (
                  <motion.div
                    key="qr-complete"
                    initial={
                      reduceMotion
                        ? { opacity: 0 }
                        : { opacity: 0, scale: 0.82, filter: "blur(10px)" }
                    }
                    animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
                    transition={reduceMotion ? { duration: 0.16 } : MATERIAL_SPRING}
                    className="flex w-full max-w-xs flex-col items-center border-t border-b border-hairline py-10 text-center"
                  >
                    <span className="flex size-12 items-center justify-center rounded-full border border-verdigris/40 text-verdigris">
                      <svg viewBox="0 0 24 24" className="size-7" fill="none" aria-hidden>
                        <path
                          d="m6.5 12.5 3.5 3.4 7.5-8"
                          stroke="currentColor"
                          strokeWidth="1.7"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </span>
                    <p className="eyebrow mt-6">Capture secured</p>
                    <p className="mt-3 text-[13px] leading-relaxed text-slate">
                      Your phone and this fitting room are synchronized.
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
            <p className="pb-2 text-center text-[11px] leading-relaxed text-ash">
              One-time pairing · encrypted transfer · automatic expiry
            </p>
          </div>
        </FabricPanel>
      </div>

      <section className="relative flex min-h-dvh flex-col bg-vellum">
        <header className="sticky top-0 z-20 flex items-center justify-between border-b border-hairline bg-vellum px-5 py-5 sm:px-8 lg:px-10">
          <div>
            <p className="text-[11px] tracking-[0.34em] text-graphite uppercase">Mirra</p>
            <p className="mt-1.5 text-[11px] text-ash">Personal avatar setup</p>
          </div>
          <span className="eyebrow flex items-center gap-2">
            <svg viewBox="0 0 16 16" className="size-3" fill="none" aria-hidden>
              <rect x="3.25" y="7" width="9.5" height="7" rx="2" stroke="currentColor" />
              <path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2" stroke="currentColor" strokeLinecap="round" />
            </svg>
            Private session
          </span>
        </header>

        <div className="flex flex-1 flex-col items-center px-5 py-9 sm:px-8 sm:py-12 lg:justify-center lg:px-10 lg:py-16">
          {/* On phones the same one-time link can open capture directly. */}
          <AnimatePresence initial={false}>
            {session?.state === "qr_ready" && !synchronized && !generationFailed && (
              <motion.div
                key="mobile-qr"
                initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 16, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 16, scale: 0.97 }}
                transition={reduceMotion ? { duration: 0.16 } : MATERIAL_SPRING}
                className="mb-9 w-full max-w-sm lg:hidden"
              >
                <QrCard
                  token={session.oneTimeToken}
                  manualCode={session.manualCode}
                  dimmed={false}
                />
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence mode="popLayout" initial={false}>
            <motion.div
              key={contentKey}
              initial={
                reduceMotion
                  ? { opacity: 0 }
                  : { opacity: 0, scale: 0.975, y: 12, filter: "blur(8px)" }
              }
              animate={{ opacity: 1, scale: 1, y: 0, filter: "blur(0px)" }}
              exit={
                reduceMotion
                  ? { opacity: 0 }
                  : { opacity: 0, scale: 0.975, y: 12, filter: "blur(8px)" }
              }
              transition={reduceMotion ? { duration: 0.16 } : MATERIAL_SPRING}
              className="flex w-full justify-center"
            >
              {generationFailed ? (
                <div className="flex w-full max-w-md flex-col items-center text-center">
                  <span className="flex size-14 items-center justify-center border border-error/30 text-error">
                    <svg viewBox="0 0 24 24" className="size-7" fill="none" aria-hidden>
                      <path
                        d="M12 7.2v5.3m0 4v.1"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                      />
                      <path
                        d="M10.3 3.8 3.2 16.1A2 2 0 0 0 4.9 19h14.2a2 2 0 0 0 1.7-2.9L13.7 3.8a2 2 0 0 0-3.4 0Z"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </span>
                  <p className="eyebrow mt-7 text-error!">Generation failed</p>
                  <h1 className="mt-5 text-[clamp(1.75rem,3.4vw,2.25rem)] leading-[1.05] font-medium tracking-[-0.035em] text-graphite">
                    Let&apos;s try that again
                  </h1>
                  <p className="mt-5 max-w-sm text-[13px] leading-relaxed text-slate">
                    {job?.failureReason ?? "The photographs couldn't be processed."} Retaking them
                    in brighter, even light usually solves it.
                  </p>
                  <Button className="mt-10 min-w-52" onClick={restart}>
                    Retake photographs
                  </Button>
                  <p className="mt-6 text-[11px] text-ash">
                    The unsuccessful capture is not shown to anyone else.
                  </p>
                </div>
              ) : synchronized ? (
                <SynchronizedState onContinue={goToMeasurements} />
              ) : generating && job ? (
                <GenerationProgress job={job} />
              ) : session ? (
                <SyncStatus
                  session={session}
                  onRestart={restart}
                  onCancel={() => sessionId && cancel.mutate(sessionId)}
                />
              ) : (
                <div className="w-full max-w-sm">
                  <Skeleton className="h-7 w-40" />
                  <Skeleton className="mt-4 h-4 w-full" />
                  <Skeleton className="mt-2 h-4 w-4/5" />
                  <Skeleton className="mt-7 h-28 w-full" />
                </div>
              )}
            </motion.div>
          </AnimatePresence>

          {(import.meta.env.VITE_AVATAR_ENGINE_MODE ?? "demo") === "demo" && (
            <div className="mt-10 w-full max-w-sm">
              <DemoModeNotice subject="avatar generation" />
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
