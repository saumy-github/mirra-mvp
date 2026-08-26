import { useNavigate } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "motion/react";
import { Check, ChevronRight, LockKeyhole } from "lucide-react";
import { AvatarFigure } from "@/features/studio/components/avatar-figure";
import { Button } from "@/components/ui/button";
import { FabricPanel } from "@/components/ui/fabric-panel";
import { MirraLogo, MirraMark } from "@/components/ui/logo";
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
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

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
    onMutate: () => setStatusMessage(null),
    onSuccess: (profile, opts) => {
      qc.setQueryData(["account", "avatar-profile"], profile);
      setDraft({});
      if (Object.keys(draft).length > 0 && !opts.reset) {
        track("measurements_updated", { authenticated: true });
      }
      if (opts.continueAfter) {
        navigate("/studio");
      } else {
        setStatusMessage(
          opts.reset ? "Estimated measurements restored." : "Your measurements are saved.",
        );
      }
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

  const hasChanges =
    Object.keys(draft).length > 0 || (avatar ? units !== avatar.unitsPreference : false);
  const hasAvatarPreview = Boolean(avatar?.previewAssetUrl);

  if (isLoading || accountLoading) {
    return (
      <main className="grid min-h-dvh place-items-center bg-canvas px-5">
        <div className="w-full max-w-sm rounded-[26px] border border-white/85 bg-paper/80 p-8 text-center shadow-[0_22px_64px_-38px_rgba(0,0,0,0.32)] backdrop-blur-2xl">
          <MirraMark size={34} className="mx-auto text-ink" />
          <p className="mt-4 text-sm font-medium text-ink-soft">Preparing your fit profile</p>
          <Skeleton className="mt-6 h-1.5 w-full rounded-full" />
        </div>
      </main>
    );
  }

  if (!avatar) {
    return (
      <main className="grid min-h-dvh place-items-center bg-canvas px-5 py-12">
        <section className="w-full max-w-md rounded-[26px] border border-line bg-paper p-7 text-center shadow-[0_22px_64px_-38px_rgba(0,0,0,0.32)] sm:p-10">
          <div className="mx-auto grid size-12 place-items-center rounded-2xl bg-mist text-ink">
            <MirraMark size={28} />
          </div>
          <h1 className="mt-6 text-[2rem] leading-tight font-medium tracking-[-0.035em] text-ink">
            Create your avatar first
          </h1>
          <p className="mx-auto mt-3 max-w-sm text-sm leading-6 text-muted">
            Your avatar gives these measurements a visual fit preview. It only takes a moment to
            create one.
          </p>
          <Button
            className="mt-7 w-full sm:w-auto sm:min-w-52"
            onClick={() => navigate("/onboarding/avatar")}
          >
            Create your avatar
            <ChevronRight aria-hidden size={17} />
          </Button>
        </section>
      </main>
    );
  }

  return (
    <main className="safe-screen min-h-dvh bg-canvas lg:grid lg:h-dvh lg:grid-cols-[minmax(0,1.04fr)_minmax(500px,0.96fr)] lg:overflow-hidden">
      <motion.aside
        className="hidden h-dvh p-3 lg:block"
        initial={reduceMotion ? { opacity: 0 } : { opacity: 0, x: -18, scale: 0.99 }}
        animate={{ opacity: 1, x: 0, scale: 1 }}
        transition={
          reduceMotion
            ? { duration: 0.16 }
            : { type: "spring", stiffness: 240, damping: 30, mass: 1 }
        }
        aria-label="Avatar preview"
      >
        <div className="h-full overflow-hidden rounded-[28px] shadow-[0_28px_80px_-44px_rgba(62,52,43,0.42)]">
          <FabricPanel className="min-h-0">
            <div className="relative flex h-full w-full items-center justify-center">
              <div className="glass absolute top-0 left-0 z-10 flex items-center gap-2.5 rounded-full px-3.5 py-2.5">
                <span
                  className="grid size-5 place-items-center rounded-full bg-ink text-white"
                  aria-hidden
                >
                  <Check size={12} strokeWidth={2.4} />
                </span>
                <span className="text-xs font-medium text-ink-soft">Profile synchronized</span>
              </div>

              <motion.div
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
                {hasAvatarPreview ? (
                  <AvatarFigure
                    previewAssetUrl={avatar.previewAssetUrl}
                    layers={[]}
                    className="h-[68vh] max-h-170 min-h-110"
                    alt="Your generated avatar, wearing base layers only"
                  />
                ) : (
                  <div
                    className="flex max-w-72 flex-col items-center text-center"
                    role="img"
                    aria-label="Your fit profile is ready; the avatar preview is still being prepared"
                  >
                    <div className="glass grid size-36 place-items-center rounded-[36px] text-ink sm:size-40">
                      <MirraMark size={72} strokeWidth={1.05} />
                    </div>
                    <p className="mt-7 text-lg font-medium tracking-[-0.02em] text-ink">
                      Fit profile ready
                    </p>
                    <p className="mt-2 text-sm leading-6 text-muted">
                      Your avatar preview will appear here when generation is complete.
                    </p>
                  </div>
                )}
              </motion.div>

              <div className="glass absolute inset-x-0 bottom-0 z-10 flex items-center justify-between gap-5 rounded-[18px] px-4 py-3.5 text-xs text-muted">
                <div>
                  <p className="font-medium text-ink">
                    {hasAvatarPreview ? `Avatar ${avatar.avatarLabel}` : "Fit profile"}
                  </p>
                  <p className="mt-0.5 text-[11px]">
                    {hasAvatarPreview ? "Fit preview" : "Preview pending"}
                  </p>
                </div>
                <p className="max-w-55 text-right leading-5">
                  Adjustments change fit only, not your appearance.
                </p>
              </div>
            </div>
          </FabricPanel>
        </div>
      </motion.aside>

      <motion.section
        className="rail-scroll relative min-h-dvh overflow-x-clip lg:h-dvh lg:min-h-0 lg:overflow-y-auto"
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
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-[radial-gradient(circle_at_50%_-20%,rgba(255,255,255,0.95),transparent_68%)] lg:hidden"
        />

        <div className="relative mx-auto flex min-h-dvh w-full max-w-180 flex-col px-5 pt-24 pb-6 sm:px-8 lg:min-h-full lg:max-w-none lg:px-12 lg:pt-18 lg:pb-5 xl:px-15">
          <div className="absolute inset-x-0 top-7 flex items-center justify-center lg:top-6">
            <MirraLogo height={36} />
          </div>

          <div className="my-auto w-full max-w-145 self-center">
            <div className="text-center">
              <span className="inline-flex min-h-7 items-center rounded-full border border-line bg-paper/80 px-3.5 py-1 text-xs font-medium text-ink-soft shadow-[0_1px_0_rgba(255,255,255,0.9)_inset]">
                Fit setup · Step 2 of 2
              </span>
              <h1 className="mt-4 text-[clamp(2rem,5vw,2.6rem)] leading-[1.08] font-medium tracking-[-0.035em] text-ink lg:mt-3">
                Make the fit yours
              </h1>
              <p className="mx-auto mt-3 max-w-lg text-[15px] leading-6 text-muted lg:mt-2">
                Review the estimates from your profile and adjust anything that doesn&apos;t feel
                right. You can change these later.
              </p>
            </div>

            <div className="mt-7 flex items-center gap-3 rounded-[18px] border border-line bg-paper p-3.5 shadow-[0_1px_0_rgba(255,255,255,0.8)_inset] lg:hidden">
              <span className="grid size-9 shrink-0 place-items-center rounded-full bg-mist text-ink">
                <Check aria-hidden size={16} strokeWidth={2.2} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-ink">Profile synchronized</p>
                <p className="truncate text-xs text-muted">
                  {hasAvatarPreview
                    ? `Avatar ${avatar.avatarLabel} is ready`
                    : "Measurements ready to review"}
                </p>
              </div>
            </div>

            <section
              className="mt-7 overflow-hidden rounded-[22px] border border-line bg-paper shadow-[0_18px_52px_-38px_rgba(0,0,0,0.34)] lg:mt-5"
              aria-labelledby="measurement-list-title"
            >
              <div className="flex flex-col gap-4 border-b border-line px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
                <div>
                  <h2 id="measurement-list-title" className="text-sm font-medium text-ink">
                    Your measurements
                  </h2>
                  <p className="mt-0.5 text-xs text-muted">
                    {fields.length} fit {fields.length === 1 ? "point" : "points"} · Stored
                    privately
                  </p>
                </div>

                <div
                  className="relative grid w-full grid-cols-2 rounded-xl bg-mist p-1 sm:w-auto"
                  role="group"
                  aria-label="Measurement unit system"
                >
                  {(["metric", "imperial"] as const).map((unit) => {
                    const selected = units === unit;
                    return (
                      <button
                        key={unit}
                        type="button"
                        onClick={() => setUnits(unit)}
                        aria-pressed={selected}
                        className={`relative z-0 min-h-9 rounded-[9px] px-4 text-xs font-medium transition-colors ${
                          selected ? "text-ink" : "text-muted hover:text-ink"
                        }`}
                      >
                        {selected && (
                          <motion.span
                            layoutId="measurement-unit"
                            className="absolute inset-0 -z-10 rounded-[9px] border border-line bg-paper shadow-sm"
                            transition={
                              reduceMotion
                                ? { duration: 0 }
                                : { type: "spring", stiffness: 500, damping: 38, mass: 0.7 }
                            }
                          />
                        )}
                        {unit === "metric" ? "Metric" : "Imperial"}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="rail-scroll divide-y divide-line px-5 sm:px-6 lg:max-h-[min(34vh,360px)] lg:overflow-y-auto">
                {fields.map((field) => (
                  <MeasurementRow
                    key={field.key}
                    field={field}
                    units={units}
                    onChange={(value) => {
                      setStatusMessage(null);
                      setDraft((current) => ({ ...current, [field.key]: value }));
                    }}
                  />
                ))}
              </div>
            </section>

            <div className="mt-3 min-h-6" aria-live="polite">
              {save.error ? (
                <p
                  role="alert"
                  className="rounded-xl border border-error/20 bg-error/8 px-4 py-3 text-sm text-error"
                >
                  {save.error instanceof Error
                    ? save.error.message
                    : "Saving didn't complete — please retry."}
                </p>
              ) : statusMessage ? (
                <p role="status" className="flex items-center gap-2 px-1 text-sm text-ok">
                  <Check aria-hidden size={15} strokeWidth={2.2} />
                  {statusMessage}
                </p>
              ) : null}
            </div>

            <div className="mt-4 space-y-3 pb-[max(0.5rem,env(safe-area-inset-bottom))]">
              <Button
                type="button"
                size="lg"
                className="w-full justify-between"
                onClick={() => save.mutate({ continueAfter: true })}
                loading={save.isPending}
              >
                <span>Continue to studio</span>
                <ChevronRight aria-hidden size={18} strokeWidth={1.9} />
              </Button>

              <div className="flex flex-wrap items-center justify-center gap-x-5 gap-y-1 text-xs font-medium">
                <button
                  type="button"
                  className="min-h-10 rounded-lg px-2 text-muted transition-colors hover:bg-mist hover:text-ink disabled:opacity-40"
                  onClick={() => navigate("/onboarding/avatar")}
                  disabled={save.isPending}
                >
                  Regenerate avatar
                </button>
                <button
                  type="button"
                  className="min-h-10 rounded-lg px-2 text-muted transition-colors hover:bg-mist hover:text-ink disabled:opacity-40"
                  onClick={() => save.mutate({ continueAfter: false, reset: true })}
                  disabled={save.isPending}
                >
                  Reset estimates
                </button>
                <button
                  type="button"
                  className="min-h-10 rounded-lg px-2 text-blue transition-colors hover:bg-blue/6 hover:text-blue-dark disabled:opacity-40"
                  disabled={!hasChanges || save.isPending}
                  onClick={() => save.mutate({ continueAfter: false })}
                >
                  Save changes
                </button>
              </div>
            </div>
          </div>

          <p className="mt-6 flex shrink-0 items-center justify-center gap-2 text-center text-[11px] text-faint lg:mt-4">
            <LockKeyhole aria-hidden size={13} strokeWidth={1.7} />
            Your measurements are private and only used to improve fit
          </p>
        </div>
      </motion.section>
    </main>
  );
}
