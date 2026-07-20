import { motion } from "motion/react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useState } from "react";
import { Spinner } from "@/components/ui/misc";
import { useAuthMutations } from "@/hooks/use-shopper";
import { track } from "@/lib/analytics";
import { demoAccessDestination } from "@/lib/post-auth";

const DEMO_ACCOUNT = {
  email: "ava@mirra.dev",
  password: "demo1234",
} as const;

/**
 * Temporary mock-only shortcut for reviewing the experience without
 * repeating account creation or avatar generation.
 */
export function QuickAccessControl() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { login } = useAuthMutations();
  const [error, setError] = useState<string | null>(null);

  const enabled =
    (import.meta.env.VITE_AUTH_PROVIDER ?? "mock") === "mock" &&
    (import.meta.env.VITE_INTEGRATION_MODE ?? "mock") === "mock";

  if (!enabled) return null;

  async function openDemo() {
    setError(null);

    try {
      await login.mutateAsync(DEMO_ACCOUNT);
      track("login_completed", {
        authenticated: true,
        properties: { method: "demo_bypass" },
      });
      navigate(demoAccessDestination(params.get("next")));
    } catch {
      setError("Quick access is unavailable. Use the standard login below.");
    }
  }

  return (
    <div className="relative">
      <motion.button
        type="button"
        onClick={openDemo}
        disabled={login.isPending}
        aria-busy={login.isPending || undefined}
        aria-label="Quick access with demo account"
        title="Open the studio with a ready-made demo profile"
        className="flex h-9 items-center justify-center gap-2 rounded-full border border-white/90 bg-white/78 px-3.5 text-xs font-semibold text-ink shadow-[0_1px_0_rgba(255,255,255,0.95)_inset,0_8px_24px_-16px_rgba(0,0,0,0.45)] backdrop-blur-xl disabled:cursor-wait disabled:opacity-60"
        whileHover={login.isPending ? undefined : { y: -1 }}
        whileTap={login.isPending ? undefined : { scale: 0.97 }}
        transition={{
          type: "spring",
          stiffness: 520,
          damping: 36,
          mass: 0.65,
        }}
      >
        {login.isPending ? (
          <Spinner className="size-3.5" />
        ) : (
          <span
            aria-hidden
            className="size-1.5 rounded-full bg-blue shadow-[0_0_0_3px_rgba(0,113,227,0.1)]"
          />
        )}
        <span className="hidden sm:inline">
          {login.isPending ? "Opening demo…" : "Quick access"}
        </span>
        <span className="sm:hidden">{login.isPending ? "Opening…" : "Demo"}</span>
        {!login.isPending && (
          <svg
            width="12"
            height="12"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden
          >
            <path d="M3 8h9M9 4.5 12.5 8 9 11.5" />
          </svg>
        )}
      </motion.button>

      {error && (
        <p
          role="alert"
          className="absolute top-11 right-0 w-56 rounded-xl border border-line bg-paper px-3 py-2 text-[11px] leading-relaxed text-error shadow-lift"
        >
          {error}
        </p>
      )}
    </div>
  );
}
