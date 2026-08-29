// Shared class strings for the dashboard primitives. Kept out of `ui.tsx` so
// that file exports components only and stays fast-refresh friendly.

export type Tone = "neutral" | "info" | "success" | "warn" | "danger";

export const TONE_CLASSES: Record<Tone, string> = {
  neutral: "bg-stone-100 text-stone-600 border-stone-200",
  info: "bg-indigo-50 text-indigo-700 border-indigo-200",
  success: "bg-emerald-50 text-emerald-700 border-emerald-200",
  warn: "bg-amber-50 text-amber-800 border-amber-200",
  danger: "bg-red-50 text-red-700 border-red-200",
};

export const BUTTON_VARIANTS = {
  primary: "bg-ink text-white hover:bg-stone-700 border-transparent",
  accent: "bg-accent text-white hover:bg-indigo-700 border-transparent",
  secondary: "bg-surface text-ink hover:bg-stone-50 border-line",
  danger: "bg-surface text-red-700 hover:bg-red-50 border-red-200",
  ghost: "bg-transparent text-muted hover:text-ink border-transparent",
};

export type ButtonVariant = keyof typeof BUTTON_VARIANTS;

export function buttonClass(variant: ButtonVariant = "secondary", size: "sm" | "md" = "md") {
  return `inline-flex items-center justify-center gap-1.5 rounded-lg border font-medium transition-colors disabled:opacity-40 disabled:pointer-events-none cursor-pointer ${
    size === "sm" ? "px-2.5 py-1 text-xs" : "px-3.5 py-1.5 text-[13px]"
  } ${BUTTON_VARIANTS[variant]}`;
}

export const inputClass =
  "w-full rounded-lg border border-line bg-surface px-3 py-2 text-[13px] text-ink placeholder:text-stone-400 focus:border-accent focus:outline-none focus:ring-2 focus:ring-indigo-100";
