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

/**
 * One button, five weights, no elevation. Every variant is a rectangle with
 * a 10px radius: either filled with ink or drawn with a hairline. Emphasis
 * comes from contrast and size, never from a shadow or a gradient.
 */
const base =
  "inline-flex touch-manipulation items-center justify-center gap-2 font-medium select-none " +
  "transition-colors duration-200 will-change-transform disabled:cursor-not-allowed disabled:opacity-40";

const variants: Record<Variant, string> = {
  primary: "rounded-(--radius-control) bg-graphite text-vellum hover:bg-black",
  outline:
    "rounded-(--radius-control) border border-hairline-strong text-graphite hover:border-graphite",
  ghost: "rounded-(--radius-control) text-slate hover:text-graphite",
  studio:
    "rounded-(--radius-compact) border border-hairline-strong text-graphite uppercase tracking-[0.14em] text-[11px] hover:border-graphite",
  "studio-dark":
    "rounded-(--radius-compact) bg-graphite text-vellum uppercase tracking-[0.14em] text-[11px] hover:bg-black",
};

const sizes: Record<Size, string> = {
  sm: "h-10 px-4 text-[12px]",
  md: "h-12 px-5 text-[13px]",
  lg: "h-14 px-7 text-[13px]",
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
      transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
      {...rest}
    >
      {loading && <Spinner className="size-4" />}
      {children}
    </motion.button>
  );
});
