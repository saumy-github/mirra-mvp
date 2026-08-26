import { useNavigate } from "react-router-dom";
import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { ArrowRight, Check, Ruler } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/misc";
import { GenerationProgress } from "@/features/onboarding/components/generation-progress";
import { SynchronizedState } from "@/features/onboarding/components/synchronized";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { useAccount, useAvatarJob, useAvatarProfile, useGenerateAvatar } from "@/hooks/use-shopper";
import { MirraApiError } from "@/integrations/mirra-api";
import { track } from "@/lib/analytics";
import { MATERIAL_SPRING } from "@/lib/motion-presets";

type Phase =
  "checking" | "decision" | "generating" | "synchronized" | "failed" | "measurements-required";

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
      <main className="grid min-h-dvh place-items-center bg-white px-4 sm:px-6">
        <div className="flex w-full max-w-sm flex-col items-center rounded-[26px] border border-[#d6d3cd] bg-[#faf9f6] p-8 text-center shadow-sm sm:p-9">
          <div className="grid size-12 place-items-center rounded-[14px] border border-line bg-paper text-ink-soft">
            <Ruler aria-hidden size={21} strokeWidth={1.7} />
          </div>
          <p className="mt-4 text-xs font-medium text-ink-soft">Mirra fit profile</p>
          <h1 className="mt-5 text-2xl font-semibold tracking-[-0.035em]">
            Preparing your fitting room
          </h1>
          <p className="mt-3 text-sm leading-6 text-muted">Checking your secure avatar profile…</p>
          <Skeleton className="mt-7 h-1.5 w-full rounded-full bg-[#d6d3cd]" />
        </div>
      </main>
    );
  }

  // ── Decision: a valid avatar already exists ──
  if (phase === "decision" && avatar) {
    return (
      <main className="grid min-h-dvh place-items-center bg-white px-4 py-12 sm:px-6">
        <motion.div
          initial={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.96, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={reduceMotion ? { duration: 0.16 } : MATERIAL_SPRING}
          className="w-full max-w-lg rounded-[26px] border border-[#d6d3cd] bg-[#faf9f6] p-8 shadow-sm sm:p-10"
        >
          <div className="flex items-center justify-between gap-4 border-b border-[#d6d3cd] pb-6">
            <p className="text-[11px] font-medium tracking-wide text-[#686963]">
              Profile / Returning
            </p>
            <p className="rounded-full border border-line bg-surface px-3 py-1.5 text-[10px] font-medium tracking-[0.035em] text-ink-soft">
              Avatar on file
            </p>
          </div>
          <h1 className="mt-9 text-[2.35rem] leading-[1.05] font-semibold tracking-[-0.045em]">
            Welcome back.
          </h1>
          <p className="mt-4 max-w-md text-sm leading-6 text-muted">
            Your saved avatar is ready for this fitting. You can enter the studio now or review its
            measurements first.
          </p>

          <div className="mt-8 grid grid-cols-[auto_1fr] rounded-2xl border border-[#d6d3cd] bg-[#eeece7] p-2">
            <div className="grid min-h-16 w-16 place-items-center rounded-[14px] bg-[#1b1c1a] text-xl font-semibold text-[#f2f0ea]">
              M
            </div>
            <div className="flex flex-col justify-center px-5">
              <p className="text-[13px] font-medium tracking-[-0.01em] text-ink">
                Avatar {avatar.avatarLabel}
              </p>
              <p className="mt-1.5 text-[10px] font-medium tracking-[0.015em] text-muted">
                Updated{" "}
                {new Date(avatar.updatedAt).toLocaleDateString(undefined, {
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                })}
              </p>
            </div>
          </div>

          <div className="mt-9 space-y-3">
            <Button
              className="w-full justify-between"
              size="lg"
              onClick={() => {
                track("saved_avatar_selected", { authenticated: true });
                navigate("/studio");
              }}
            >
              Use my saved avatar
              <span aria-hidden>→</span>
            </Button>
            <Button
              variant="outline"
              className="w-full border-[#cdcac4] bg-transparent"
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
    <main className="grid min-h-dvh place-items-center bg-white px-4 py-10 sm:px-6 sm:py-16">
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
            <section
              className="w-full max-w-3xl overflow-hidden rounded-[26px] border border-line bg-paper shadow-sm"
              aria-labelledby="measurements-required-title"
            >
              <div className="grid md:grid-cols-[minmax(0,1fr)_240px]">
                <div className="p-6 sm:p-8 md:p-10">
                  <div className="flex items-center gap-4">
                    <div className="grid size-12 shrink-0 place-items-center rounded-[14px] border border-line bg-surface text-ink-soft">
                      <Ruler aria-hidden size={22} strokeWidth={1.7} />
                    </div>
                    <div>
                      <p className="text-xs font-medium text-ink">Avatar setup</p>
                      <p className="mt-1 text-xs text-muted">Measurements come first</p>
                    </div>
                  </div>

                  <h1
                    id="measurements-required-title"
                    className="mt-8 max-w-lg text-[clamp(2rem,6vw,2.5rem)] leading-[1.08] font-medium tracking-[-0.035em] text-ink"
                  >
                    Let&apos;s shape your avatar around you.
                  </h1>
                  <p className="mt-4 max-w-lg text-base leading-6 text-muted">
                    Add your body measurements before avatar generation. You can use exact values or
                    comfortable estimates, then update them whenever you like.
                  </p>

                  <ul className="mt-6 grid gap-3 text-sm text-ink-soft">
                    <li className="flex items-center gap-3">
                      <span className="grid size-6 shrink-0 place-items-center rounded-full bg-surface text-ink">
                        <Check aria-hidden size={14} strokeWidth={2} />
                      </span>
                      Review every value before continuing
                    </li>
                    <li className="flex items-center gap-3">
                      <span className="grid size-6 shrink-0 place-items-center rounded-full bg-surface text-ink">
                        <Check aria-hidden size={14} strokeWidth={2} />
                      </span>
                      Refine your fit profile at any time
                    </li>
                  </ul>

                  <Button
                    className="mt-8 w-full justify-between sm:w-auto sm:min-w-56"
                    size="lg"
                    onClick={() => navigate("/measurements?next=/onboarding/avatar")}
                  >
                    Add measurements
                    <ArrowRight aria-hidden size={17} strokeWidth={1.8} />
                  </Button>
                </div>

                <aside
                  className="border-t border-line bg-surface p-6 sm:p-8 md:border-t-0 md:border-l"
                  aria-label="Avatar setup progress"
                >
                  <p className="text-xs font-medium text-muted">Setup progress</p>
                  <ol className="mt-6 grid gap-5">
                    <li className="flex items-start gap-3" aria-current="step">
                      <span className="grid size-8 shrink-0 place-items-center rounded-full bg-ink text-xs font-medium text-white">
                        1
                      </span>
                      <div className="pt-1">
                        <p className="text-sm font-medium text-ink">Measurements</p>
                        <p className="mt-1 text-xs leading-5 text-muted">Ready to add</p>
                      </div>
                    </li>
                    <li className="flex items-start gap-3">
                      <span className="grid size-8 shrink-0 place-items-center rounded-full border border-line bg-paper text-xs font-medium text-muted">
                        2
                      </span>
                      <div className="pt-1">
                        <p className="text-sm font-medium text-ink-soft">Avatar</p>
                        <p className="mt-1 text-xs leading-5 text-muted">Generated next</p>
                      </div>
                    </li>
                  </ol>
                  <p className="mt-8 border-t border-line pt-6 text-xs leading-5 text-muted">
                    Your measurements stay linked to your private fit profile.
                  </p>
                </aside>
              </div>
            </section>
          ) : phase === "failed" ? (
            <div className="flex w-full max-w-md flex-col items-center rounded-[26px] border border-[#d6d3cd] bg-[#faf9f6] p-8 text-center shadow-sm sm:p-9">
              <p className="rounded-full border border-error/30 px-3 py-1.5 text-[10px] font-medium tracking-[0.04em] text-error">
                Generation failed
              </p>
              <h1 className="mt-6 text-[1.85rem] leading-tight font-semibold tracking-[-0.04em]">
                Let&apos;s try that again
              </h1>
              <p className="mt-4 max-w-sm text-sm leading-6 text-muted">
                {job?.failureReason ?? "Your avatar couldn't be generated."}
              </p>
              <Button className="mt-7 min-w-52" onClick={regenerate}>
                Try again
              </Button>
            </div>
          ) : phase === "synchronized" ? (
            <SynchronizedState onContinue={goToMeasurements} />
          ) : job ? (
            <GenerationProgress job={job} />
          ) : (
            <div className="w-full max-w-sm rounded-[26px] border border-[#d6d3cd] bg-[#faf9f6] p-6 shadow-sm">
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
