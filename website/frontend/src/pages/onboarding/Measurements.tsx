import { useNavigate } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "motion/react";
import { AvatarFigure } from "@/features/studio/components/avatar-figure";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/misc";
import { MeasurementRow } from "@/features/onboarding/components/measurement-row";
import { useAvatarProfile, useAccount } from "@/hooks/use-shopper";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { getRuntimeProvider } from "@/integrations/mirra-api";
import type { MeasurementKey } from "@/integrations/mirra-api/types";
import { track } from "@/lib/analytics";
import type { UnitSystem } from "@/lib/units";

/**
 * Measurement review ("Configure Studio Metrics"). Every engine-supported
 * dimension can be inspected and corrected. Language stays neutral:
 * measurements are reviewed, never "fixed".
 */
export default function OnboardingMeasurements() {
  const navigate = useNavigate();
  const reduceMotion = useReducedMotion();
  const qc = useQueryClient();
  const { data: account, isLoading: accountLoading } = useAccount();
  const { data: avatar, isLoading } = useAvatarProfile(!!account);

  const [draft, setDraft] = useState<Partial<Record<MeasurementKey, number>>>({});
  const [units, setUnits] = useState<UnitSystem>("metric");

  useEffect(() => {
    if (!accountLoading && !account) {
      navigate(`/auth/login?next=${encodeURIComponent("/onboarding/measurements")}`, {
        replace: true,
      });
    }
  }, [account, accountLoading, navigate]);

  useEffect(() => {
    if (avatar) setUnits(avatar.unitsPreference);
  }, [avatar]);

  useEffect(() => {
    track("measurements_reviewed", { authenticated: true });
  }, []);

  const save = useMutation({
    mutationFn: (opts: { continueAfter: boolean; reset?: boolean }) =>
      getRuntimeProvider().updateMeasurements(opts.reset ? {} : draft, {
        resetEstimates: opts.reset,
        unitsPreference: units,
      }),
    onSuccess: (profile, opts) => {
      qc.setQueryData(["account", "avatar-profile"], profile);
      setDraft({});
      if (Object.keys(draft).length > 0 && !opts.reset) {
        track("measurements_updated", { authenticated: true });
      }
      if (opts.continueAfter) navigate("/studio");
    },
  });

  const fields = useMemo(() => {
    if (!avatar) return [];
    return avatar.measurements
      .filter((m) => m.supported) // only what the current engine supports
      .map((m) => ({
        ...m,
        value: draft[m.key] ?? m.value,
        estimated: m.estimated && !(m.key in draft),
      }));
  }, [avatar, draft]);

  if (isLoading || accountLoading) {
    return (
      <main className="grid min-h-dvh place-items-center bg-canvas">
        <Skeleton className="h-64 w-80" />
      </main>
    );
  }

  if (!avatar) {
    return (
      <main className="flex min-h-dvh flex-col items-center justify-center bg-canvas px-6 text-center">
        <p className="eyebrow">No avatar yet</p>
        <p className="mt-5 max-w-sm text-[13px] leading-relaxed text-slate">
          There&apos;s no avatar on this account yet — a quick photo session creates one.
        </p>
        <Button className="mt-8" onClick={() => navigate("/onboarding/avatar")}>
          Create your avatar
        </Button>
      </main>
    );
  }

  return (
    <main className="min-h-dvh bg-vellum lg:grid lg:h-dvh lg:grid-cols-[minmax(0,1.05fr)_minmax(29rem,0.95fr)] lg:overflow-hidden">
      {/* Avatar preview */}
      <div className="border-b border-hairline lg:border-r lg:border-b-0">
        <motion.section
          className="relative flex h-full min-h-[48svh] items-center justify-center overflow-hidden bg-bone"
          initial={reduceMotion ? { opacity: 0 } : { opacity: 0, x: -18, scale: 0.99 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          transition={
            reduceMotion
              ? { duration: 0.16 }
              : { type: "spring", stiffness: 260, damping: 31, mass: 0.95 }
          }
        >
          {/* The room the figure stands in: a ruled bone field, nothing more. */}
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 grid grid-cols-4 grid-rows-6"
          >
            {Array.from({ length: 24 }).map((_, index) => (
              <div key={index} className="border-t border-l border-hairline/70" />
            ))}
          </div>

          <div className="absolute top-5 left-5 z-10 flex items-center gap-2.5 sm:top-7 sm:left-7">
            <span aria-hidden className="size-1.5 rounded-full bg-verdigris" />
            <span className="eyebrow">Profile synchronized</span>
          </div>

          <p className="eyebrow absolute top-5 right-5 z-10 sm:top-7 sm:right-7">Step 3 / 3</p>

          <motion.div
            className="relative z-1"
            initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 14, scale: 0.985 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={
              reduceMotion
                ? { duration: 0.18 }
                : {
                    type: "spring",
                    stiffness: 240,
                    damping: 28,
                    mass: 1,
                    delay: 0.08,
                  }
            }
          >
            <AvatarFigure
              previewAssetUrl={avatar.previewAssetUrl}
              layers={[]}
              className="my-12 h-[42svh] min-h-75 lg:h-[64vh] lg:min-h-110"
              alt="Your generated avatar, wearing base layers only"
            />
          </motion.div>

          <div className="absolute inset-x-5 bottom-5 z-10 flex items-center justify-between gap-4 border-t border-hairline pt-4 sm:inset-x-7 sm:bottom-7">
            <span className="eyebrow">Avatar {avatar.avatarLabel}</span>
            <span className="hidden text-[11px] text-ash sm:inline">
              Adjustments change fit only — not your appearance.
            </span>
            <span className="eyebrow flex items-center gap-2">
              <span aria-hidden className="size-1.5 rounded-full bg-verdigris" />
              Ready
            </span>
          </div>
        </motion.section>
      </div>

      {/* Metrics panel */}
      <motion.section
        className="quiet-scroll flex flex-col px-5 py-10 sm:px-8 lg:overflow-y-auto lg:px-12 lg:py-12"
        initial={reduceMotion ? { opacity: 0 } : { opacity: 0, x: 18 }}
        animate={{ opacity: 1, x: 0 }}
        transition={
          reduceMotion
            ? { duration: 0.16 }
            : {
                type: "spring",
                stiffness: 280,
                damping: 32,
                mass: 0.9,
                delay: 0.04,
              }
        }
      >
        <div className="mx-auto flex w-full max-w-155 flex-1 flex-col">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div className="max-w-md">
              <p className="eyebrow">Configure studio metrics</p>
              <h1 className="mt-5 text-[clamp(1.9rem,3.4vw,2.5rem)] leading-[1.05] font-medium tracking-[-0.035em] text-graphite">
                Make the fit yours.
              </h1>
              <p className="mt-4 text-[13px] leading-relaxed text-slate">
                These are estimates from your photos. Fine-tune anything that looks off—you can
                always reset it later.
              </p>
            </div>

            <div className="relative flex shrink-0 gap-5" role="group" aria-label="Units">
              {(["metric", "imperial"] as const).map((u) => (
                <button
                  key={u}
                  type="button"
                  onClick={() => setUnits(u)}
                  aria-pressed={units === u}
                  className={`relative z-0 min-h-9 text-[10px] tracking-[0.14em] uppercase transition-colors ${
                    units === u ? "text-graphite" : "text-ash hover:text-graphite"
                  }`}
                >
                  {units === u && (
                    <motion.span
                      layoutId="measurement-unit"
                      className="absolute inset-x-0 -bottom-0.5 h-px bg-graphite"
                      transition={{ duration: 0.28, ease: [0.22, 0.8, 0.24, 1] }}
                    />
                  )}
                  {u}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-10 flex-1 border-t border-b border-hairline lg:flex-none">
            <div className="rule-stack">
              {fields.map((field) => (
                <MeasurementRow
                  key={field.key}
                  field={field}
                  units={units}
                  onChange={(value) => setDraft((d) => ({ ...d, [field.key]: value }))}
                />
              ))}
            </div>
          </div>

          {save.error && (
            <p role="alert" className="mt-4 border-b border-error/30 pb-3 text-[12px] text-error">
              {save.error instanceof Error
                ? save.error.message
                : "Saving didn't complete — please retry."}
            </p>
          )}

          <div className="mt-10 space-y-6 pb-[max(0.5rem,env(safe-area-inset-bottom))]">
            <Button
              type="button"
              size="lg"
              className="w-full justify-between px-6!"
              onClick={() => save.mutate({ continueAfter: true })}
              loading={save.isPending}
            >
              <span className="tracking-[0.02em]">Initialize studio engine</span>
              <span aria-hidden>→</span>
            </Button>

            <div className="flex flex-wrap items-center gap-x-7 gap-y-2 text-[10px] tracking-[0.14em] uppercase">
              <button
                type="button"
                className="min-h-9 text-ash transition-colors hover:text-graphite"
                onClick={() => navigate("/onboarding/avatar")}
              >
                Retake photographs
              </button>
              <button
                type="button"
                className="min-h-9 text-ash transition-colors hover:text-graphite"
                onClick={() => save.mutate({ continueAfter: false, reset: true })}
              >
                Reset estimated values
              </button>
              <button
                type="button"
                className="min-h-9 text-graphite underline underline-offset-4 disabled:opacity-40"
                disabled={Object.keys(draft).length === 0 || save.isPending}
                onClick={() => save.mutate({ continueAfter: false })}
              >
                Save for future visits
              </button>
            </div>
          </div>
        </div>
      </motion.section>
    </main>
  );
}
