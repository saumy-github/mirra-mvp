import { useNavigate } from "react-router-dom";
import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/misc";
import { GenerationProgress } from "@/features/onboarding/components/generation-progress";
import { SynchronizedState } from "@/features/onboarding/components/synchronized";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import {
  useAccount,
  useAvatarJob,
  useAvatarProfile,
  useGenerateAvatar,
} from "@/hooks/use-shopper";
import { MirraApiError } from "@/integrations/mirra-api";
import { track } from "@/lib/analytics";
import { MATERIAL_SPRING } from "@/lib/motion-presets";

type Phase =
  | "checking"
  | "decision"
  | "generating"
  | "synchronized"
  | "failed"
  | "measurements-required";

/**
 * Existing-avatar decision, then avatar generation from already-saved
 * measurements. No photo capture involved — generation is triggered
 * directly against POST /avatars/generate (capture_sessions was removed;
 * see .agent/website-launch execution logs).
 */
export default function OnboardingAvatar() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: account, isLoading: accountLoading } = useAccount();
  const { data: avatar, isLoading: avatarLoading } = useAvatarProfile(!!account);
  const reduceMotion = useReducedMotion();

  const [phase, setPhase] = useState<Phase>("checking");
  const [jobId, setJobId] = useState<string | null>(null);
  const generate = useGenerateAvatar();
  const { data: job } = useAvatarJob(jobId);

  // Auth guard
  useEffect(() => {
    if (!accountLoading && !account) {
      navigate(`/auth/login?next=${encodeURIComponent("/onboarding/avatar")}`, { replace: true });
    }
  }, [account, accountLoading, navigate]);

  // Existing-avatar decision
  useEffect(() => {
    if (phase !== "checking" || avatarLoading || !account) return;
    setPhase(avatar ? "decision" : "generating");
  }, [phase, avatar, avatarLoading, account]);

  const startGeneration = useCallback(() => {
    generate.mutate(undefined, {
      onSuccess: (j) => {
        setJobId(j.jobId);
        track("avatar_generation_started", { authenticated: true });
      },
      onError: (err: unknown) => {
        if (err instanceof MirraApiError && err.status === 404) {
          setPhase("measurements-required");
        } else {
          setPhase("failed");
        }
      },
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (phase === "generating" && !jobId && !generate.isPending && !generate.isError) {
      startGeneration();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, jobId]);

  const jobDone = useRef(false);
  useEffect(() => {
    if (!job || jobDone.current) return;
    if (job.state === "ready") {
      jobDone.current = true;
      void qc.invalidateQueries({ queryKey: ["account", "avatar-profile"] });
      track("avatar_generation_completed", { authenticated: true });
      setPhase("synchronized");
    } else if (job.state === "failed") {
      jobDone.current = true;
      track("avatar_generation_failed", { authenticated: true });
      setPhase("failed");
    }
  }, [job, qc]);

  const goToMeasurements = useCallback(() => navigate("/onboarding/measurements"), [navigate]);

  function regenerate() {
    jobDone.current = false;
    setJobId(null);
    generate.reset();
    setPhase("generating");
    startGeneration();
  }

  if (accountLoading || phase === "checking") {
    return (
      <main className="grid min-h-dvh place-items-center bg-canvas px-6">
        <div className="flex w-full max-w-sm flex-col items-center rounded-4xl border border-line bg-paper p-8 text-center shadow-sm">
          <p className="mono-tag text-[9px]! tracking-[0.24em]!">MIRRA FIT PROFILE</p>
          <h1 className="mt-2 text-xl font-semibold tracking-tight">Preparing your fitting room</h1>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            Checking your secure avatar profile…
          </p>
          <Skeleton className="mt-6 h-12 w-full rounded-xl" />
        </div>
      </main>
    );
  }

  // ── Decision: a valid avatar already exists ──
  if (phase === "decision" && avatar) {
    return (
      <main className="grid min-h-dvh place-items-center bg-canvas px-6">
        <motion.div
          initial={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.96, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={reduceMotion ? { duration: 0.16 } : MATERIAL_SPRING}
          className="w-full max-w-md rounded-4xl border border-line bg-paper p-8"
        >
          <p className="mono-tag text-[9px]! tracking-[0.24em]! text-ok">[ AVATAR ON FILE ]</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight">Welcome back</h1>
          <p className="mt-4 text-sm leading-relaxed text-muted">
            Your saved avatar is ready for this fitting. You can enter the studio now or review
            its measurements first.
          </p>

          <div className="mt-6 flex items-center gap-3 rounded-2xl border border-line bg-surface p-3.5">
            <div>
              <p className="text-xs font-semibold text-ink">Avatar {avatar.avatarLabel}</p>
              <p className="mt-0.5 text-[11px] text-muted">
                Updated{" "}
                {new Date(avatar.updatedAt).toLocaleDateString(undefined, {
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                })}
              </p>
            </div>
          </div>

          <div className="mt-8 space-y-2.5">
            <Button
              className="w-full"
              size="lg"
              onClick={() => {
                track("saved_avatar_selected", { authenticated: true });
                navigate("/studio");
              }}
            >
              Use my saved avatar
            </Button>
            <Button
              variant="outline"
              className="w-full"
              size="lg"
              onClick={goToMeasurements}
            >
              Review measurements
            </Button>
            <Button variant="ghost" className="w-full" onClick={regenerate}>
              Regenerate avatar
            </Button>
          </div>
        </motion.div>
      </main>
    );
  }

  // ── Generation from saved measurements (no photo capture) ──
  return (
    <main className="grid min-h-dvh place-items-center bg-canvas px-6 py-16">
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.div
          key={phase}
          initial={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.975, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.975, y: 12 }}
          transition={reduceMotion ? { duration: 0.16 } : MATERIAL_SPRING}
          className="flex w-full justify-center"
        >
          {phase === "measurements-required" ? (
            <div className="flex w-full max-w-sm flex-col items-center text-center">
              <p className="mono-tag text-[9px]! tracking-[0.28em]! text-ink-soft">
                [ MEASUREMENTS NEEDED ]
              </p>
              <h1 className="mt-3 text-2xl font-semibold tracking-tight">
                Save your measurements first
              </h1>
              <p className="mt-4 text-sm leading-relaxed text-muted">
                Your avatar is built from your body measurements — add those before generating one.
              </p>
              <Button
                className="mt-8 min-w-52"
                onClick={() => navigate("/measurements?next=/onboarding/avatar")}
              >
                Add measurements
              </Button>
            </div>
          ) : phase === "failed" ? (
            <div className="flex w-full max-w-md flex-col items-center text-center">
              <p className="mono-tag text-[10px]! tracking-[0.28em]! text-error">
                GENERATION FAILED
              </p>
              <h1 className="mt-3 text-2xl font-semibold tracking-tight">Let&apos;s try that again</h1>
              <p className="mt-4 max-w-sm text-sm leading-relaxed text-muted">
                {job?.failureReason ?? "Your avatar couldn't be generated."}
              </p>
              <Button className="mt-8 min-w-52" onClick={regenerate}>
                Try again
              </Button>
            </div>
          ) : phase === "synchronized" ? (
            <SynchronizedState onContinue={goToMeasurements} />
          ) : job ? (
            <GenerationProgress job={job} />
          ) : (
            <div className="w-full max-w-sm rounded-[1.6rem] border border-line bg-paper p-6">
              <Skeleton className="h-7 w-40 rounded-lg" />
              <Skeleton className="mt-4 h-4 w-full rounded-lg" />
              <Skeleton className="mt-2 h-4 w-4/5 rounded-lg" />
              <Skeleton className="mt-7 h-28 w-full rounded-2xl" />
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </main>
  );
}
