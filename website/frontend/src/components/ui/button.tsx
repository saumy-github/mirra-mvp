import { forwardRef, type ReactNode } from "react";
import { motion, type HTMLMotionProps } from "motion/react";
import { Spinner } from "./misc";

type Variant = "primary" | "outline" | "ghost" | "studio" | "studio-dark";
type Size = "md" | "lg" | "sm";

export interface ButtonProps extends Omit<HTMLMotionProps<"button">, "ref" | "children"> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  children?: ReactNode;
}

const base =
  "inline-flex touch-manipulation items-center justify-center gap-2 font-semibold select-none " +
  "will-change-transform disabled:cursor-not-allowed disabled:opacity-45";

const variants: Record<Variant, string> = {
  primary:
    "rounded-(--radius-control) bg-ink text-white shadow-[0_8px_24px_-12px_rgba(0,0,0,0.55)] hover:bg-black",
  outline:
    "rounded-(--radius-control) border border-line-strong bg-paper/80 text-ink shadow-[0_1px_0_rgba(255,255,255,0.8)_inset] hover:border-ink/50 hover:bg-paper",
  ghost: "rounded-(--radius-control) text-ink-soft hover:bg-mist/80 hover:text-ink",
  studio:
    "rounded-(--radius-compact) border border-ink/80 bg-paper/90 text-ink uppercase tracking-widest text-xs hover:bg-mist",
  "studio-dark":
    "rounded-(--radius-compact) bg-ink text-white uppercase tracking-widest text-xs shadow-[0_8px_22px_-14px_rgba(0,0,0,0.8)] hover:bg-black",
};

const sizes: Record<Size, string> = {
  sm: "h-10 px-4 text-[13px]",
  md: "h-11 px-5 text-sm",
  lg: "h-12.5 px-6 text-[15px]",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading, className = "", children, disabled, ...rest },
  ref,
) {
  return (
    <motion.button
      ref={ref}
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      whileHover={disabled || loading ? undefined : { y: -1 }}
      whileTap={disabled || loading ? undefined : { scale: 0.97 }}
      transition={{ type: "spring", stiffness: 520, damping: 34, mass: 0.65 }}
      {...rest}
    >
      {loading && <Spinner className="size-4" />}
      {children}
    </motion.button>
  );
});
