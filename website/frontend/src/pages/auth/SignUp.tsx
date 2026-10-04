import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AuthHeading, AuthShell } from "@/features/auth/components/auth-shell";
import {
  GoogleButton,
  GithubButton,
} from "@/features/auth/components/oauth-buttons";
import { useAuthMutations } from "@/hooks/use-shopper";
import { MirraApiError, userMessage } from "@/integrations/mirra-api";
import { track } from "@/lib/analytics";
import { postAuthDestination } from "@/lib/post-auth";

export default function SignUp() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { signUp, google } = useAuthMutations();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!email || !password) {
      setError("Please fill in your email and password.");
      return;
    }
    try {
      await signUp.mutateAsync({
        displayName: username || email.split("@")[0],
        email,
        password,
        acceptedTerms: true,
      });
      track("signup_completed", { authenticated: true });
      navigate(postAuthDestination(params.get("next")));
    } catch (err) {
      setError(
        err instanceof MirraApiError
          ? userMessage(err.code)
          : "Sign up could not be completed. Please retry.",
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
      navigate(postAuthDestination(params.get("next")));
    } catch {
      setError("Google sign-in didn't complete. Please retry.");
    }
  }

  return (
    <AuthShell>
      <AuthHeading
        title="Create account"
        subtitle="Enter your personal details to get started"
      />

      {/* Social Login Buttons matching screenshot */}
      <div className="flex flex-col gap-2.5 w-full">
        <GoogleButton onClick={onGoogle} loading={google.isPending} />
        <GithubButton onClick={onGoogle} />
      </div>

      {/* Divider */}
      <div className="my-5 flex w-full items-center gap-3">
        <div className="h-px flex-1 bg-black/8" />
        <span className="text-xs text-neutral-400 font-normal">or</span>
        <div className="h-px flex-1 bg-black/8" />
      </div>

      {/* Inputs Form */}
      <form onSubmit={onSubmit} className="flex flex-col gap-3.5 w-full">
        <div className="flex flex-col gap-1 text-left">
          <label htmlFor="username" className="text-xs font-medium text-neutral-600">
            Username
          </label>
          <input
            id="username"
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            className="h-11 w-full rounded-xl border border-black/10 bg-white px-3.5 text-sm text-neutral-900 placeholder:text-neutral-400 shadow-[0_1px_2px_rgba(0,0,0,0.02)] transition-colors focus:border-black focus:outline-none"
          />
        </div>

        <div className="flex flex-col gap-1 text-left">
          <label htmlFor="signup-email" className="text-xs font-medium text-neutral-600">
            Email address
          </label>
          <input
            id="signup-email"
            type="email"
            placeholder="you@domain.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required
            className="h-11 w-full rounded-xl border border-black/10 bg-white px-3.5 text-sm text-neutral-900 placeholder:text-neutral-400 shadow-[0_1px_2px_rgba(0,0,0,0.02)] transition-colors focus:border-black focus:outline-none"
          />
        </div>

        <div className="flex flex-col gap-1 text-left">
          <label htmlFor="signup-password" className="text-xs font-medium text-neutral-600">
            Password
          </label>
          <div className="relative">
            <input
              id="signup-password"
              type={showPassword ? "text" : "password"}
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              required
              className="h-11 w-full rounded-xl border border-black/10 bg-white px-3.5 pr-11 text-sm text-neutral-900 placeholder:text-neutral-400 shadow-[0_1px_2px_rgba(0,0,0,0.02)] transition-colors focus:border-black focus:outline-none"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              className="absolute top-1/2 right-3 -translate-y-1/2 text-neutral-400 hover:text-neutral-700 transition-colors"
            >
              {showPassword ? (
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                  <path d="M2 12s3.5-6.5 10-6.5S22 12 22 12s-3.5 6.5-10 6.5S22 12 22 12s-3.5 6.5-10 6.5S2 12 2 12Z" />
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
        </div>

        {error && (
          <p role="alert" className="text-xs text-error mt-1 text-center">
            {error}
          </p>
        )}

        {/* CTA Button */}
        <button
          type="submit"
          disabled={signUp.isPending}
          className="mt-1 flex h-11.5 w-full items-center justify-center gap-2 rounded-xl bg-[#141414] text-sm font-medium text-white shadow-[0_2px_8px_rgba(0,0,0,0.12)] transition-all hover:bg-black active:scale-[0.99] disabled:opacity-50"
        >
          <span>{signUp.isPending ? "Creating account…" : "Sign up"}</span>
          <span className="text-base leading-none">→</span>
        </button>
      </form>

      {/* Footer */}
      <p className="mt-6 text-center text-xs text-neutral-500">
        Already have an account?{" "}
        <Link
          to={`/auth/login${params.get("next") ? `?next=${encodeURIComponent(params.get("next")!)}` : ""}`}
          className="font-semibold text-neutral-900 hover:underline"
        >
          Log in
        </Link>
      </p>
    </AuthShell>
  );
}
