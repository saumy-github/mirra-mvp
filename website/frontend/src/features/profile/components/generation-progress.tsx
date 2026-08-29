import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import type { AvatarJob } from "@/integrations/mirra-api/types";
import { avatarStageLabels, orderedAvatarStages } from "@/lib/state-machines/avatar-job";
import { useAccount } from "@/hooks/use-shopper";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { MATERIAL_SPRING } from "@/lib/motion-presets";

/**
 * The waiting experience. Progress mirrors real backend stages (never fake
 * percentages) — this is the direct answer to the "time issues" problem
 * flagged for avatar/VTO generation. Educational statements rotate quietly
 * and the optional questions are always skippable and never claim to speed
 * things up.
 */

const STATEMENTS = [
  "Your photographs are being prepared securely.",
  "You can review and correct every measurement next.",
  "Your original photographs are never shown to anyone else.",
  "Mirra is learning proportion, not judging appearance.",
  "Your avatar is generated once and reused for every future try-on.",
  "The studio is being tailored around you.",
];

const QUESTIONS: Array<{
  id: string;
  q: string;
  hint: string;
  options: string[];
}> = [
  {
    id: "focus",
    q: "What do you notice first in an outfit?",
    hint: "This can shape what Mirra highlights later.",
    options: ["Fit", "Silhouette", "Styling"],
  },
  {
    id: "fit",
    q: "How do you like clothes to feel?",
    hint: "There is no right answer—choose your usual preference.",
    options: ["Closer", "Regular", "Relaxed"],
  },
  {
    id: "keep",
    q: "Use this avatar on a future visit?",
    hint: "You can change this choice from your profile.",
    options: ["Yes", "Just today"],
  },
];

export function GenerationProgress({ job }: { job: AvatarJob }) {
  const reduceMotion = useReducedMotion();
  const { data: account } = useAccount();
  const [statementIdx, setStatementIdx] = useState(0);
  const [questionIdx, setQuestionIdx] = useState(0);
  const answers = useRef<Record<string, string>>({});

  useEffect(() => {
    if (reduceMotion) return;
    const t = setInterval(() => setStatementIdx((i) => (i + 1) % STATEMENTS.length), 4200);
    return () => clearInterval(t);
  }, [reduceMotion]);

  function answer(id: string, value: string | null) {
    if (value !== null) {
      answers.current[id] = value;
      // Preference answers are kept only with explicit consent, and only for
      // this tab's session.
      if (account?.consents.preferenceStorage) {
        sessionStorage.setItem("mirra.preferences", JSON.stringify(answers.current));
      }
    }
    setQuestionIdx((i) => i + 1);
  }

  const stages = orderedAvatarStages.slice(0, 5);
  const reachedIdx = Math.max(stages.indexOf(job.state), 0);
  const question = QUESTIONS[questionIdx];

  return (
    <section className="flex w-full max-w-lg flex-col items-center text-center">
      <div
        className="relative flex size-36 items-center justify-center"
        role="status"
        aria-live="polite"
        aria-label={job.stageLabel}
      >
        <motion.span
          className="absolute inset-0 rounded-[2.6rem] border border-white bg-white/48 shadow-[0_25px_70px_-45px_rgba(33,31,28,.65)] backdrop-blur-2xl"
          animate={reduceMotion ? undefined : { rotate: [0, 1.5, 0] }}
          transition={
            reduceMotion ? undefined : { duration: 5.4, repeat: Infinity, ease: "easeInOut" }
          }
        />
        <span className="absolute inset-3 rounded-[2.15rem] border border-line/80 bg-linear-to-br from-white/80 to-mist/45" />

        {!reduceMotion && (
          <>
            <motion.span
              className="absolute inset-[1.35rem] rounded-full border border-line-strong/80 border-t-ink"
              animate={{ rotate: 360 }}
              transition={{ repeat: Infinity, duration: 4.8, ease: "linear" }}
            />
            <motion.span
              className="absolute inset-[2.15rem] rounded-full border border-line border-b-ink-soft"
              animate={{ rotate: -360 }}
              transition={{ repeat: Infinity, duration: 6.4, ease: "linear" }}
            />
          </>
        )}

        <motion.svg
          viewBox="0 0 48 64"
          className="relative h-16 w-12 text-ink"
          fill="none"
          initial={false}
          animate={
            reduceMotion ? { opacity: 1 } : { opacity: [0.58, 1, 0.58], scale: [0.98, 1, 0.98] }
          }
          transition={
            reduceMotion ? undefined : { duration: 2.8, repeat: Infinity, ease: "easeInOut" }
          }
          aria-hidden
        >
          <circle cx="24" cy="10.5" r="7" stroke="currentColor" strokeWidth="1.3" />
          <path
            d="M15.5 25.5c1-5 4-8 8.5-8s7.5 3 8.5 8l2.5 15H13l2.5-15Z"
            stroke="currentColor"
            strokeWidth="1.3"
            strokeLinejoin="round"
          />
          <path
            d="m18 41-2 17m14-17 2 17M14 29 8 43m26-14 6 14"
            stroke="currentColor"
            strokeWidth="1.3"
            strokeLinecap="round"
          />
        </motion.svg>
      </div>

      <p className="mono-tag mt-7 text-[9px]! tracking-[0.25em]! text-ink-soft">
        [ BUILDING YOUR AVATAR ]
      </p>
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.h1
          key={job.state}
          initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 8, filter: "blur(6px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 8, filter: "blur(6px)" }}
          transition={reduceMotion ? { duration: 0.16 } : MATERIAL_SPRING}
          className="mt-3 text-[1.75rem] leading-[1.08] font-semibold tracking-[-0.035em] text-balance text-ink sm:text-[2rem]"
        >
          {avatarStageLabels[job.state]}
        </motion.h1>
      </AnimatePresence>
      <p className="mt-3 max-w-sm text-sm leading-relaxed text-muted">
        Keep this page open. Progress below comes directly from the avatar engine.
      </p>

      {/* Real stages: each segment fills only after the backend reaches it. */}
      <ol className="mt-7 grid w-full grid-cols-5 gap-1.5" aria-label="Avatar generation stages">
        {stages.map((stage, i) => {
          const done = reachedIdx > i || job.state === "ready";
          const current = reachedIdx === i && job.state !== "ready";
          return (
            <li key={stage} className="min-w-0">
              <motion.span
                initial={false}
                animate={{
                  backgroundColor: done || current ? "var(--color-ink)" : "var(--color-line)",
                  opacity: current ? 0.62 : 1,
                }}
                transition={reduceMotion ? { duration: 0.16 } : MATERIAL_SPRING}
                className="block h-1.5 rounded-full"
                aria-hidden
              />
              <span className="sr-only">
                {avatarStageLabels[stage]}:{" "}
                {done ? "complete" : current ? "in progress" : "upcoming"}
              </span>
            </li>
          );
        })}
      </ol>

      {/* Rotating reassurance */}
      <div
        className="mt-5 flex min-h-10 w-full items-center justify-center overflow-hidden"
        aria-live="off"
      >
        <AnimatePresence mode="wait">
          <motion.p
            key={statementIdx}
            initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 8, filter: "blur(4px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -8, filter: "blur(4px)" }}
            transition={reduceMotion ? { duration: 0.16 } : MATERIAL_SPRING}
            className="text-[13px] leading-relaxed text-muted"
          >
            {STATEMENTS[statementIdx]}
          </motion.p>
        </AnimatePresence>
      </div>

      {/* Optional, skippable questions — answering changes nothing about processing */}
      <div className="mt-4 w-full">
        <AnimatePresence mode="popLayout" initial={false}>
          {question ? (
            <motion.div
              key={question.id}
              initial={
                reduceMotion
                  ? { opacity: 0 }
                  : { opacity: 0, x: 18, scale: 0.98, filter: "blur(7px)" }
              }
              animate={{ opacity: 1, x: 0, scale: 1, filter: "blur(0px)" }}
              exit={
                reduceMotion
                  ? { opacity: 0 }
                  : { opacity: 0, x: -18, scale: 0.98, filter: "blur(7px)" }
              }
              transition={reduceMotion ? { duration: 0.16 } : MATERIAL_SPRING}
              className="w-full rounded-[1.6rem] border border-white/80 bg-white/58 p-5 text-left shadow-[0_22px_60px_-46px_rgba(33,31,28,.55)] backdrop-blur-xl sm:p-6"
            >
              <div className="flex items-center justify-between gap-3">
                <p className="mono-tag text-[9px]! tracking-[0.2em]! text-ink-soft">
                  OPTIONAL PREFERENCE
                </p>
                <p className="font-mono text-[10px] text-faint">
                  {questionIdx + 1} / {QUESTIONS.length}
                </p>
              </div>
              <h2 className="mt-3 text-lg font-semibold tracking-[-0.02em] text-ink">
                {question.q}
              </h2>
              <p className="mt-1.5 text-xs leading-relaxed text-muted">{question.hint}</p>

              <div className="mt-5 grid grid-cols-1 gap-2 sm:grid-cols-3">
                {question.options.map((opt) => (
                  <motion.button
                    key={opt}
                    type="button"
                    onClick={() => answer(question.id, opt)}
                    whileTap={reduceMotion ? undefined : { scale: 0.97 }}
                    transition={MATERIAL_SPRING}
                    className="min-h-11 rounded-xl border border-line-strong bg-white/65 px-4 py-2 text-sm font-medium text-ink-soft shadow-sm hover:border-ink hover:text-ink"
                  >
                    {opt}
                  </motion.button>
                ))}
              </div>
              <button
                type="button"
                onClick={() => answer(question.id, null)}
                className="mt-4 min-h-9 w-full px-3 text-[11px] font-medium text-muted hover:text-ink"
              >
                Skip — this never affects processing
              </button>
            </motion.div>
          ) : (
            <motion.div
              key="questions-complete"
              initial={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={reduceMotion ? { duration: 0.16 } : MATERIAL_SPRING}
              className="flex items-center justify-center gap-2 rounded-2xl border border-line/70 bg-white/45 px-4 py-3 text-xs text-muted backdrop-blur-lg"
            >
              <svg viewBox="0 0 18 18" className="size-4 text-ok" fill="none" aria-hidden>
                <circle cx="9" cy="9" r="7" stroke="currentColor" />
                <path
                  d="m5.8 9.2 2 2 4.4-4.5"
                  stroke="currentColor"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              You&apos;re all caught up. Your avatar is still building.
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <p className="mt-4 max-w-sm text-[10px] leading-relaxed text-faint">
        Preferences are optional and stay in this session unless you have already allowed preference
        storage.
      </p>
    </section>
  );
}
