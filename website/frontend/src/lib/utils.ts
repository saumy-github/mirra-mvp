import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Tailwind-aware class merge. Required by the vendored Bklit chart components,
 * which import it as `@/lib/utils` per the shadcn registry convention.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
