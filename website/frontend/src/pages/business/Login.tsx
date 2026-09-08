import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AuthHeading, AuthShell } from "@/features/auth/components/auth-shell";
import {
  GoogleIconButton,
  GithubIconButton,
  SocialButtonRow,
} from "@/features/auth/components/oauth-buttons";
import { useAuthMutations } from "@/hooks/use-shopper";
import { MirraApiError, userMessage } from "@/integrations/mirra-api";
import { track } from "@/lib/analytics";
import { businessDestination } from "./destination";

export default function BusinessLogin() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { login, google, continueAsGuest } = useAuthMutations();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(
    params.get("error") ? "Google sign-in didn't complete. Please retry." : null,
  );

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!email || !password) {
      setError("Please fill in your email and password.");
      return;
    }
    try {
      await login.mutateAsync({ email, password });
      track("login_completed", {
        authenticated: true,
        properties: { method: "password" },
      });
      navigate(businessDestination(params.get("next")));
    } catch (err) {
      setError(
        err instanceof MirraApiError ? userMessage(err.code) : "Invalid credentials. Please retry.",
      );
    }
  }

  async function onGoogle() {
    setError(null);
    try {
      await google.mutateAsync();
      track("login_completed", {
        authenticated: true,
        properties: { method: "google" },
      });
      navigate(businessDestination(params.get("next")));
    } catch {
      setError("Google sign-in didn't complete. Please retry.");
    }
  }

  async function onQuickAccess() {
    setError(null);
    try {
      await continueAsGuest.mutateAsync();
      track("login_completed", {
        authenticated: true,
        properties: { method: "quick_access" },
      });
      navigate(businessDestination(params.get("next")));
    } catch {
      setError("Quick access login didn't complete. Please retry.");
    }
  }

  return (
    <AuthShell>
      <AuthHeading
        pill="For brands"
        title="Sign in to your workspace"
        subtitle="Manage your catalogue, garments, and try-on analytics"
      />

      {/* Quick Access Demo Button */}
      <button
        type="button"
        onClick={onQuickAccess}
        disabled={continueAsGuest.isPending}
        className="flex h-10 w-full items-center justify-center gap-2 rounded-xl border border-black/10 bg-neutral-50 text-xs font-medium text-neutral-800 shadow-[0_1px_2px_rgba(0,0,0,0.03)] transition-all hover:bg-neutral-100 hover:border-black/20 active:scale-[0.99] disabled:opacity-50"
      >
        <span>⚡</span>
        <span>{continueAsGuest.isPending ? "Entering workspace…" : "Quick Access (Auto Log In)"}</span>
      </button>

      {/* Social Logins */}
      <div className="mt-3">
        <SocialButtonRow>
          <GoogleIconButton onClick={onGoogle} loading={google.isPending} />
          <GithubIconButton onClick={onGoogle} />
        </SocialButtonRow>
      </div>

      {/* Divider */}
      <div className="my-5 flex items-center gap-3">
        <div className="h-px flex-1 bg-black/8" />
        <span className="text-xs text-neutral-400">or</span>
        <div className="h-px flex-1 bg-black/8" />
      </div>

      {/* Inputs Form */}
      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        <input
          type="email"
          placeholder="you@yourbrand.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          required
          className="h-11.5 w-full rounded-xl border border-black/10 bg-white px-4 text-sm text-neutral-900 placeholder:text-neutral-400 shadow-[0_1px_2px_rgba(0,0,0,0.03)] transition-colors focus:border-black focus:outline-none"
        />

        <div className="relative">
          <input
            type={showPassword ? "text" : "password"}
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
            className="h-11.5 w-full rounded-xl border border-black/10 bg-white px-4 pr-11 text-sm text-neutral-900 placeholder:text-neutral-400 shadow-[0_1px_2px_rgba(0,0,0,0.03)] transition-colors focus:border-black focus:outline-none"
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            aria-label={showPassword ? "Hide password" : "Show password"}
            className="absolute top-1/2 right-3 -translate-y-1/2 text-neutral-400 hover:text-neutral-700 transition-colors"
          >
            {showPassword ? (
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                <path d="M2 12s3.5-6.5 10-6.5S22 12 22 12s-3.5 6.5-10 6.5S22 12 22 12Z" />
                <circle cx="12" cy="12" r="2.5" />
              </svg>
            ) : (
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
                <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
                <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
                <line x1="2" y1="2" x2="22" y2="22" />
              </svg>
            )}
          </button>
        </div>

        {error && (
          <p role="alert" className="text-xs text-error mt-1 text-center">
            {error}
          </p>
        )}

        {/* CTA Button */}
        <button
          type="submit"
          disabled={login.isPending}
          className="mt-2 flex h-11.5 w-full items-center justify-center gap-2 rounded-xl bg-black text-sm font-medium text-white shadow-[0_2px_8px_rgba(0,0,0,0.15)] transition-all hover:bg-neutral-800 active:scale-[0.99] disabled:opacity-50"
        >
          <span>{login.isPending ? "Signing in…" : "Log in"}</span>
          <span className="text-base leading-none">→</span>
        </button>
      </form>

      {/* Auxiliary Link Row */}
      <div className="mt-5 flex items-center justify-between text-xs text-neutral-500">
        <Link to="/business/forgot-password" className="hover:text-neutral-900 transition-colors">
          Forgot password?
        </Link>
        <Link
          to={`/business/sign-up${params.get("next") ? `?next=${encodeURIComponent(params.get("next")!)}` : ""}`}
          className="font-semibold text-neutral-900 hover:underline"
        >
          Create account
        </Link>
      </div>

      {/* Shopper switch */}
      <p className="mt-6 text-center text-xs text-neutral-500">
        Shopping, not selling?{" "}
        <Link to="/auth/login" className="font-semibold text-neutral-900 hover:underline">
          Shopper log in
        </Link>
      </p>
    </AuthShell>
  );
}
