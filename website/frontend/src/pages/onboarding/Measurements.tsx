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
      <main className="grid min-h-dvh place-items-center">
        <Skeleton className="h-64 w-80" />
      </main>
    );
  }

  if (!avatar) {
    return (
      <main className="flex min-h-dvh flex-col items-center justify-center px-6 text-center">
        <p className="mono-tag">[ NO AVATAR YET ]</p>
        <p className="mt-4 max-w-sm text-sm text-muted">
          There&apos;s no avatar on this account yet — a quick photo session creates one.
        </p>
        <Button className="mt-8" onClick={() => navigate("/onboarding/avatar")}>
          Create your avatar
        </Button>
      </main>
    );
  }

  return (
    <main className="min-h-dvh bg-canvas lg:grid lg:h-dvh lg:grid-cols-[minmax(0,1.12fr)_minmax(460px,0.88fr)] lg:overflow-hidden">
      {/* Avatar preview */}
      <div className="p-2 lg:p-3 lg:pr-0">
        <motion.section
          className="relative flex h-full min-h-[48svh] items-center justify-center overflow-hidden rounded-[28px] border border-white/80 bg-surface shadow-[0_24px_70px_-44px_rgba(0,0,0,0.28)]"
          initial={reduceMotion ? { opacity: 0 } : { opacity: 0, x: -18, scale: 0.99 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          transition={
            reduceMotion
              ? { duration: 0.16 }
              : { type: "spring", stiffness: 260, damping: 31, mass: 0.95 }
          }
        >
          <div
            aria-hidden
            className="absolute inset-0"
            style={{
              background:
                "radial-gradient(circle at 50% 55%, rgba(226,210,207,0.68), transparent 36%), radial-gradient(circle at 20% 12%, rgba(255,255,255,0.95), transparent 32%), linear-gradient(145deg, #fbfbfc 0%, #f2f2f5 100%)",
            }}
          />
          <div
            aria-hidden
            className="absolute inset-0 opacity-60"
            style={{
              backgroundImage:
                "linear-gradient(to right, rgba(29,29,31,0.035) 1px, transparent 1px), linear-gradient(to bottom, rgba(29,29,31,0.035) 1px, transparent 1px)",
              backgroundSize: "64px 64px",
              maskImage: "radial-gradient(circle at center, black, transparent 74%)",
            }}
          />

          <div className="glass absolute top-4 left-4 z-10 flex items-center gap-2 rounded-full px-3.5 py-2 sm:top-6 sm:left-6">
            <span
              className="flex size-5 items-center justify-center rounded-full bg-ok/12 text-ok"
              aria-hidden
            >
              ✓
            </span>
            <span className="text-xs font-semibold text-ink-soft">Profile synchronized</span>
          </div>

          <div className="absolute top-4 right-4 z-10 rounded-full bg-ink/6 px-3 py-2 text-[11px] font-medium text-muted sm:top-6 sm:right-6">
            Step 3 of 3
          </div>

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
              className="my-12 h-[42svh] min-h-75 lg:h-[68vh] lg:min-h-110"
              alt="Your generated avatar, wearing base layers only"
            />
          </motion.div>

          <div className="glass absolute inset-x-4 bottom-4 z-10 flex items-center justify-between gap-3 rounded-2xl px-4 py-3 text-[11px] text-muted sm:inset-x-6 sm:bottom-6">
            <span className="font-medium text-ink-soft">Avatar {avatar.avatarLabel}</span>
            <span className="hidden sm:inline">
              Adjustments change fit only—not your appearance.
            </span>
            <span className="flex items-center gap-1.5">
              <span className="size-1.5 rounded-full bg-ok" />
              Ready
            </span>
          </div>
        </motion.section>
      </div>

      {/* Metrics panel */}
      <motion.section
        className="rail-scroll flex flex-col px-5 py-8 sm:px-8 lg:overflow-hidden lg:px-10 lg:py-10 xl:px-14"
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
              <p className="mono-tag tracking-widest!">Configure Studio Metrics</p>
              <h1 className="mt-2 text-[clamp(2rem,4vw,2.75rem)] leading-[1.04] font-semibold tracking-[-0.045em]">
                Make the fit yours.
              </h1>
              <p className="mt-3 text-sm leading-relaxed text-muted">
                These are estimates from your photos. Fine-tune anything that looks off—you can
                always reset it later.
              </p>
            </div>

            <div
              className="relative flex rounded-full border border-line bg-paper p-1 shadow-[0_1px_0_rgba(255,255,255,0.8)_inset]"
              role="group"
              aria-label="Units"
            >
              {(["metric", "imperial"] as const).map((u) => (
                <button
                  key={u}
                  type="button"
                  onClick={() => setUnits(u)}
                  aria-pressed={units === u}
                  className={`relative z-0 min-h-9 rounded-full px-3.5 text-xs font-semibold capitalize ${
                    units === u ? "text-white" : "text-muted hover:text-ink"
                  }`}
                >
                  {units === u && (
                    <motion.span
                      layoutId="measurement-unit"
                      className="absolute inset-0 -z-10 rounded-full bg-ink"
                      transition={{
                        type: "spring",
                        stiffness: 500,
                        damping: 38,
                        mass: 0.7,
                      }}
                    />
                  )}
                  {u}
                </button>
              ))}
            </div>
          </div>

          <div className="rail-scroll mt-7 flex-1 rounded-3xl border border-line bg-paper/80 px-5 shadow-[0_16px_44px_-34px_rgba(0,0,0,0.3)] sm:px-6 lg:max-h-[50vh] lg:flex-none lg:overflow-y-auto">
            <div className="divide-y divide-line">
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
            <p role="alert" className="mt-3 rounded-xl bg-error/8 px-4 py-3 text-sm text-error">
              {save.error instanceof Error
                ? save.error.message
                : "Saving didn't complete — please retry."}
            </p>
          )}

          <div className="mt-6 space-y-4 pb-[max(0.5rem,env(safe-area-inset-bottom))]">
            <Button
              type="button"
              size="lg"
              className="w-full justify-between px-5!"
              onClick={() => save.mutate({ continueAfter: true })}
              loading={save.isPending}
            >
              <span>Initialize studio engine</span>
              <span
                className="flex size-7 items-center justify-center rounded-full bg-white/12"
                aria-hidden
              >
                →
              </span>
            </Button>

            <div className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-xs font-medium">
              <button
                type="button"
                className="min-h-9 text-muted hover:text-ink"
                onClick={() => navigate("/onboarding/avatar")}
              >
                Retake photographs
              </button>
              <button
                type="button"
                className="min-h-9 text-muted hover:text-ink"
                onClick={() => save.mutate({ continueAfter: false, reset: true })}
              >
                Reset estimated values
              </button>
              <button
                type="button"
                className="min-h-9 text-blue hover:text-blue-dark disabled:opacity-40"
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
