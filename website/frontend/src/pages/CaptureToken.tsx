import { useParams } from "react-router-dom";
import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { getRuntimeProvider, MirraApiError, userMessage } from "@/integrations/mirra-api";
import type { CaptureSession } from "@/integrations/mirra-api/types";
import { Button } from "@/components/ui/button";
import { MirraMark, MirraWordmark } from "@/components/ui/logo";
import { DemoModeNotice, Spinner } from "@/components/ui/misc";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { CameraCapture, type CapturedImage } from "@/features/capture/components/camera-capture";

/**
 * The mobile capture route opened from the QR code. Consent before camera,
 * silhouette-guided capture per configured step, retake, upload fallback,
 * and a clear hand-back to the desktop.
 */
export default function CaptureToken() {
  const { token = "" } = useParams<{ token: string }>();
  const reduceMotion = useReducedMotion();
  const api = useMemo(() => getRuntimeProvider(), []);
  const [session, setSession] = useState<CaptureSession | null>(null);
  const [fatal, setFatal] = useState<string | null>(null);
  const [stepIdx, setStepIdx] = useState(0);

  // Resolve + pair exactly once (one-time token semantics).
  const paired = useRef(false);
  const initial = useQuery({
    queryKey: ["capture-token", token],
    queryFn: () => getRuntimeProvider().getCaptureSessionByToken(token),
    retry: false,
    staleTime: Infinity,
  });

  useEffect(() => {
    if (!initial.data || paired.current) return;
    paired.current = true;
    const s = initial.data;
    if (s.state === "qr_ready") {
      api
        .pairCaptureSession(token)
        .then(setSession)
        .catch((e: unknown) =>
          setFatal(e instanceof MirraApiError ? userMessage(e.code) : "Pairing didn't complete."),
        );
    } else {
      setSession(s);
    }
  }, [initial.data, api, token]);

  useEffect(() => {
    if (initial.error) {
      const e = initial.error;
      setFatal(e instanceof MirraApiError ? userMessage(e.code) : "This pairing link isn't valid.");
    }
  }, [initial.error]);

  const consent = useMutation({
    mutationFn: () => api.giveCaptureConsent(token),
    onSuccess: setSession,
  });

  const upload = useMutation({
    mutationFn: ({ stepId, img }: { stepId: string; img: CapturedImage }) =>
      api.submitCaptureAsset(token, stepId, img),
    onSuccess: (s) => {
      setSession(s);
      setStepIdx((i) => i + 1);
    },
  });

  const {
    mutate: startComplete,
    isPending: completePending,
    isSuccess: completeSucceeded,
  } = useMutation({
    mutationFn: () => api.completeCapture(token),
    onSuccess: setSession,
  });

  // Auto-start generation once every step is handled.
  const steps = session?.steps ?? [];
  const allHandled = session?.state === "uploaded" && stepIdx >= steps.length;
  useEffect(() => {
    if (allHandled && !completePending && !completeSucceeded) startComplete();
  }, [allHandled, completePending, completeSucceeded, startComplete]);

  const shell = (children: React.ReactNode) => (
    <main className="safe-screen relative flex min-h-dvh flex-col items-center overflow-x-hidden bg-canvas px-5 pt-[max(1.25rem,env(safe-area-inset-top))] pb-[max(1.5rem,env(safe-area-inset-bottom))]">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-[46vh] bg-[radial-gradient(circle_at_50%_0%,rgba(255,255,255,0.98),transparent_72%)]"
      />
      <header className="relative z-10 flex w-full max-w-sm items-center justify-between">
        <div className="flex items-center gap-2">
          <MirraMark size={25} className="text-ink" />
          <MirraWordmark className="text-[10px]! tracking-[0.26em]! text-ink-soft" />
        </div>
        <span className="flex items-center gap-1.5 rounded-full border border-line bg-paper/75 px-3 py-1.5 text-[10px] font-semibold text-muted">
          <span className="size-1.5 rounded-full bg-ok" />
          Private session
        </span>
      </header>
      <motion.div
        className="relative z-1 mt-6 flex w-full max-w-sm flex-1 flex-col"
        initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={
          reduceMotion
            ? { duration: 0.14 }
            : { type: "spring", stiffness: 300, damping: 32, mass: 0.85 }
        }
      >
        {children}
      </motion.div>
      {(import.meta.env.VITE_AVATAR_ENGINE_MODE ?? "demo") === "demo" && (
        <div className="relative z-1 mt-8 w-full max-w-sm">
          <DemoModeNotice subject="photo capture" />
        </div>
      )}
    </main>
  );

  if (fatal) {
    return shell(
      <div className="flex flex-1 flex-col items-center justify-center text-center">
        <p className="mono-tag tracking-[0.28em]! text-error">LINK UNAVAILABLE</p>
        <p className="mt-4 text-sm leading-relaxed text-muted">{fatal}</p>
        <p className="mt-4 text-xs leading-relaxed text-faint">
          Return to your computer and generate a fresh QR code, then scan it again.
        </p>
      </div>,
    );
  }

  if (!session) {
    return shell(
      <div className="flex flex-1 items-center justify-center">
        <Spinner className="size-6 text-muted" />
      </div>,
    );
  }

  // ── Consent, before any camera access ──
  if (session.state === "consent_pending") {
    return shell(
      <div className="flex flex-1 flex-col justify-center py-4">
        <div className="mb-6 flex size-14 items-center justify-center rounded-card bg-ink text-white shadow-[0_12px_28px_-16px_rgba(0,0,0,0.55)]">
          <svg
            width="27"
            height="27"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            aria-hidden
          >
            <path d="M4 8.5A2.5 2.5 0 0 1 6.5 6h1.2l1-1.5h6.6l1 1.5h1.2A2.5 2.5 0 0 1 20 8.5v8A2.5 2.5 0 0 1 17.5 19h-11A2.5 2.5 0 0 1 4 16.5v-8Z" />
            <circle cx="12" cy="12.5" r="3.5" />
          </svg>
        </div>
        <p className="text-xs font-semibold text-ok">Connected to your computer</p>
        <h1 className="mt-2 text-[34px] leading-[1.06] font-semibold tracking-[-0.045em]">
          A few photos,
          <br />
          always on your terms.
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-muted">
          We&apos;ll guide you through each angle. Review every photo before it leaves your phone.
        </p>

        <div className="mt-6 space-y-2.5">
          <PrivacyPoint
            icon="01"
            title={`${steps.filter((s) => s.required).length} required views`}
            body="Front and side, with one optional back view."
          />
          <PrivacyPoint
            icon="02"
            title="Only for your avatar"
            body="Never shown to anyone else and never used to train models."
          />
          <PrivacyPoint
            icon="03"
            title="Source photos are deleted"
            body="They’re removed after generation; your avatar remains yours to delete."
          />
        </div>
        <div className="mt-8 space-y-2.5">
          <Button
            size="lg"
            className="w-full"
            onClick={() => consent.mutate()}
            loading={consent.isPending}
          >
            Continue to camera
          </Button>
          <p className="text-center text-xs text-faint">
            Your browser asks for permission next. Uploading existing photos is always available.
          </p>
        </div>
      </div>,
    );
  }

  // ── Capture steps ──
  if ((session.state === "capturing" || session.state === "uploading") && stepIdx < steps.length) {
    const step = steps[stepIdx];
    if (session.uploadedStepIds.includes(step.id)) {
      // Already uploaded (e.g. reload) — move along.
      setStepIdx((i) => i + 1);
      return null;
    }
    return shell(
      <div className="flex flex-1 flex-col">
        <div className="mb-4 flex items-center justify-between">
          <p className="text-xs font-semibold text-ink-soft">
            Photo {stepIdx + 1} of {steps.length}
          </p>
          <div className="flex gap-1.5" aria-hidden>
            {steps.map((captureStep, index) => (
              <span
                key={captureStep.id}
                className={`h-1.5 rounded-full transition-[width,background-color] ${
                  index === stepIdx
                    ? "w-6 bg-ink"
                    : index < stepIdx
                      ? "w-1.5 bg-ok"
                      : "w-1.5 bg-line-strong"
                }`}
              />
            ))}
          </div>
        </div>
        <CameraCapture
          step={step}
          busy={upload.isPending}
          onConfirm={(img) => upload.mutate({ stepId: step.id, img })}
          onSkip={!step.required ? () => setStepIdx((i) => i + 1) : undefined}
        />
        {upload.error && (
          <p role="alert" className="mt-3 text-center text-sm text-error">
            {upload.error instanceof MirraApiError
              ? upload.error.message
              : "Upload failed — please retry."}
          </p>
        )}
      </div>,
    );
  }

  // ── Optional steps remain but required set is done ──
  if (session.state === "uploaded" && stepIdx < steps.length) {
    const step = steps[stepIdx];
    return shell(
      <div className="flex flex-1 flex-col">
        <p className="mono-tag mb-4 text-center">[ OPTIONAL VIEW ]</p>
        <CameraCapture
          step={step}
          busy={upload.isPending}
          onConfirm={(img) => upload.mutate({ stepId: step.id, img })}
          onSkip={() => setStepIdx((i) => i + 1)}
        />
      </div>,
    );
  }

  // ── Done: desktop takes over ──
  if (session.state === "processing" || session.state === "completed" || allHandled) {
    return shell(
      <div className="flex flex-1 flex-col items-center justify-center text-center">
        <motion.div
          className="relative flex size-24 items-center justify-center rounded-full bg-paper shadow-[0_18px_50px_-26px_rgba(0,0,0,0.35)]"
          initial={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.76 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={
            reduceMotion
              ? { duration: 0.14 }
              : { type: "spring", stiffness: 300, damping: 24, mass: 0.8 }
          }
        >
          <svg viewBox="0 0 48 48" className="size-14" fill="none" aria-hidden>
            <circle cx="24" cy="24" r="21" stroke="var(--color-ok)" strokeWidth="1.6" />
            <motion.path
              d="M15 25 21 31 33 17"
              stroke="var(--color-ok)"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              initial={reduceMotion ? undefined : { pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.45, delay: 0.1, ease: "easeOut" }}
            />
          </svg>
        </motion.div>
        <h1 className="mt-7 text-3xl font-semibold tracking-[-0.04em]">Photos received</h1>
        <p className="mt-3 text-sm leading-relaxed text-muted">
          Your computer has been notified and is building your avatar now. You can close this tab —
          everything continues on the bigger screen.
        </p>
        <p className="mt-6 rounded-[14px] border border-line bg-paper/75 px-4 py-3 text-xs leading-relaxed text-faint">
          If the desktop screen doesn&apos;t move on within a minute, refresh it — your photos are
          safe and won&apos;t need retaking.
        </p>
      </div>,
    );
  }

  if (session.state === "cancelled" || session.state === "failed") {
    return shell(
      <div className="flex flex-1 flex-col items-center justify-center text-center">
        <p className="mono-tag tracking-[0.28em]! text-error">SESSION CLOSED</p>
        <p className="mt-4 text-sm text-muted">
          This capture session ended. Generate a fresh QR code on your computer to start again.
        </p>
      </div>,
    );
  }

  return shell(
    <div className="flex flex-1 items-center justify-center">
      <Spinner className="size-6 text-muted" />
    </div>,
  );
}

function PrivacyPoint({ icon, title, body }: { icon: string; title: string; body: string }) {
  return (
    <div className="flex gap-3 rounded-2xl border border-line bg-paper/78 p-3.5 shadow-[0_10px_28px_-24px_rgba(0,0,0,0.28)]">
      <span className="flex size-8 shrink-0 items-center justify-center rounded-field bg-mist text-[10px] font-bold text-muted tabular-nums">
        {icon}
      </span>
      <div>
        <p className="text-[13px] font-semibold text-ink">{title}</p>
        <p className="mt-0.5 text-xs leading-relaxed text-muted">{body}</p>
      </div>
    </div>
  );
}
