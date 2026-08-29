import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";
import { AvatarGlbViewer } from "@/features/profile/components/avatar-glb-viewer";
import { AVATAR_GLB_STALE_KEY } from "@/features/profile/glb-query-keys";
import { Button } from "@/components/ui/button";
import { GenerationProgress } from "@/features/profile/components/generation-progress";
import { SynchronizedState } from "@/features/profile/components/synchronized";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import {
  useAccount,
  useAvatarJob,
  useAvatarProfile,
  useGenerateAvatar,
} from "@/hooks/use-shopper";
import { getRuntimeProvider, MirraApiError } from "@/integrations/mirra-api";
import { track } from "@/lib/analytics";
import { MATERIAL_SPRING } from "@/lib/motion-presets";

type GenerationPhase = "idle" | "generating" | "synchronized" | "failed" | "measurements-required";

// Generation runs directly from saved measurements — no photo-capture step.
// It never starts on mount: a page load must not queue a 90-second CLO job
// (doc 13, D7).
export default function ProfileAvatar() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: account } = useAccount();
  const { data: avatar, isLoading, isError, error, refetch } = useAvatarProfile(!!account);
  const [confirming, setConfirming] = useState(false);
  const [confirmingRegenerate, setConfirmingRegenerate] = useState(false);
  const reduceMotion = useReducedMotion();

  const [phase, setPhase] = useState<GenerationPhase>("idle");
  const [jobId, setJobId] = useState<string | null>(null);
  const generate = useGenerateAvatar();
  const { data: job } = useAvatarJob(jobId);

  // Written into the cache by AvatarGlbViewer when the GLB response lands.
  const { data: isStale } = useQuery<boolean | null>({
    queryKey: AVATAR_GLB_STALE_KEY,
    enabled: false,
    initialData: null,
  });

  const remove = useMutation({
    mutationFn: () => getRuntimeProvider().deleteAvatarProfile(),
    onSuccess: () => {
      qc.setQueryData(["account", "avatar-profile"], null);
      setConfirming(false);
    },
  });

  const startGeneration = useCallback(() => {
    setPhase("generating");
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

  const jobDone = useRef(false);
  useEffect(() => {
    if (!job || jobDone.current) return;
    if (job.state === "ready") {
      jobDone.current = true;
      void qc.invalidateQueries({ queryKey: ["account", "avatar-profile"] });
      void qc.invalidateQueries({ queryKey: ["account", "avatar-glb"] });
      track("avatar_generation_completed", { authenticated: true });
      setPhase("synchronized");
    } else if (job.state === "failed") {
      jobDone.current = true;
      track("avatar_generation_failed", { authenticated: true });
      setPhase("failed");
    }
  }, [job, qc]);

  const goToStudio = useCallback(() => navigate("/studio"), [navigate]);

  function regenerate() {
    jobDone.current = false;
    setJobId(null);
    generate.reset();
    setConfirmingRegenerate(false);
    startGeneration();
  }

  if (isLoading) return null;

  // A failed profile fetch is not "no avatar" — never let it start a run.
  if (isError && phase === "idle") {
    return (
      <div className="flex w-full max-w-md flex-col items-center text-center">
        <p className="mono-tag text-[10px]! tracking-[0.28em]! text-error">COULDN&apos;T LOAD</p>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight">Your avatar didn&apos;t load</h1>
        <p className="mt-4 max-w-sm text-sm leading-relaxed text-muted">
          {error instanceof Error ? error.message : "Something went wrong reaching the server."}
        </p>
        <Button className="mt-8 min-w-52" onClick={() => void refetch()}>
          Try again
        </Button>
      </div>
    );
  }

  if (phase !== "idle") {
    return (
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.div
          key={phase}
          initial={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.98, y: 8 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.98, y: 8 }}
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
              <Button className="mt-8 min-w-52" onClick={() => navigate("/profile/measurements")}>
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
              <div className="mt-8 flex gap-2.5">
                <Button className="min-w-52" onClick={regenerate}>
                  Try again
                </Button>
                <Button variant="outline" onClick={() => setPhase("idle")}>
                  Back
                </Button>
              </div>
            </div>
          ) : phase === "synchronized" ? (
            <SynchronizedState onContinue={goToStudio} />
          ) : (
            <div className="w-full">
              <p className="mb-4 text-center text-[11px] leading-relaxed text-faint">
                This takes about 90 seconds. Leaving this page will lose track of the run.
              </p>
              {job ? (
                <GenerationProgress job={job} />
              ) : (
                <p className="text-center text-sm text-muted">Queueing your run…</p>
              )}
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    );
  }

  // No avatar yet — generation starts from this button and nowhere else.
  if (!avatar) {
    return (
      <div className="flex w-full max-w-sm flex-col items-center text-center">
        <p className="mono-tag text-[9px]! tracking-[0.28em]! text-ink-soft">[ NO AVATAR YET ]</p>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight">Generate your avatar</h1>
        <p className="mt-4 text-sm leading-relaxed text-muted">
          We build a 3D body from the measurements you saved. It takes about 90 seconds.
        </p>
        <Button className="mt-8 min-w-52" onClick={startGeneration} loading={generate.isPending}>
          Generate my avatar
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <AvatarGlbViewer className="h-128" />

      {isStale === true && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-line bg-mist px-5 py-4">
          <p className="text-sm text-ink-soft">
            Your measurements have changed since this avatar was made.
          </p>
          <Button size="sm" onClick={() => setConfirmingRegenerate(true)}>
            Regenerate
          </Button>
        </div>
      )}

      <div>
        <h1 className="text-xl font-semibold tracking-tight">Avatar {avatar.avatarLabel}</h1>
        <dl className="mt-4 space-y-2 text-sm text-ink-soft">
          <div className="flex gap-2">
            <dt className="w-28 text-muted">Version</dt>
            <dd>v{avatar.version}</dd>
          </div>
          <div className="flex gap-2">
            <dt className="w-28 text-muted">Engine</dt>
            <dd className="font-mono text-xs">{avatar.engineVersion}</dd>
          </div>
          <div className="flex gap-2">
            <dt className="w-28 text-muted">Created</dt>
            <dd>{new Date(avatar.createdAt).toLocaleDateString()}</dd>
          </div>
          <div className="flex gap-2">
            <dt className="w-28 text-muted">Last updated</dt>
            <dd>{new Date(avatar.updatedAt).toLocaleDateString()}</dd>
          </div>
        </dl>

        <div className="mt-8 flex flex-wrap gap-2.5 border-t border-line pt-6">
          <Button size="sm" onClick={() => navigate("/studio")}>
            Use my saved avatar
          </Button>
          {confirmingRegenerate ? (
            <>
              <Button variant="outline" size="sm" onClick={() => setConfirmingRegenerate(false)}>
                Keep this one
              </Button>
              <Button size="sm" onClick={regenerate}>
                Replace it
              </Button>
            </>
          ) : (
            <Button variant="outline" size="sm" onClick={() => setConfirmingRegenerate(true)}>
              Regenerate avatar
            </Button>
          )}
        </div>
        {confirmingRegenerate && (
          <p className="mt-3 text-xs leading-relaxed text-muted">
            This runs the pipeline again and replaces your current avatar. It takes about 90 seconds.
          </p>
        )}

        <div className="mt-8 border-t border-line pt-6">
          <h2 className="text-sm font-medium">Delete this avatar</h2>
          <p className="mt-1 text-xs leading-relaxed text-muted">
            Removes the avatar and every measurement estimate. Source photographs were already
            deleted after generation. This can&apos;t be undone.
          </p>
          {confirming ? (
            <div className="mt-3 flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setConfirming(false)}>
                Keep avatar
              </Button>
              <Button
                size="sm"
                className="bg-error!"
                onClick={() => remove.mutate()}
                loading={remove.isPending}
              >
                Delete permanently
              </Button>
            </div>
          ) : (
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              onClick={() => setConfirming(true)}
            >
              Delete avatar…
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
