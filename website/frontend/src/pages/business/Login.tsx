import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AuthHeading, AuthShell } from "@/features/auth/components/auth-shell";
import { GoogleButton } from "@/features/auth/components/oauth-buttons";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { OrDivider } from "@/components/ui/misc";
import { useAuthMutations } from "@/hooks/use-shopper";
import { MirraApiError, userMessage } from "@/integrations/mirra-api";
import { track } from "@/lib/analytics";
import { businessDestination } from "./destination";

/**
 * Business log-in — reached from the Join page. Unlike the shopper side
 * (Google only, see `pages/auth/Login.tsx`), brands keep the full
 * email + password flow plus quick access for pilot demos.
 */
export default function BusinessLogin() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { login, google, continueAsGuest } = useAuthMutations();
  const [error, setError] = useState<string | null>(
    params.get("error") ? "Google sign-in didn't complete. Please retry." : null,
  );

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const data = new FormData(e.currentTarget);
    try {
      await login.mutateAsync({
        email: String(data.get("email") ?? ""),
        password: String(data.get("password") ?? ""),
      });
      track("login_completed", {
        authenticated: true,
        properties: { method: "password" },
      });
      navigate(businessDestination(params.get("next")));
    } catch (err) {
      setError(
        err instanceof MirraApiError ? userMessage(err.code) : "Something went wrong. Please retry.",
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

      <div className="auth-provider-stack">
        <Button
          type="button"
          onClick={onQuickAccess}
          loading={continueAsGuest.isPending}
          className="auth-primary-action w-full bg-ink text-sm font-semibold text-white shadow-md hover:bg-black"
          size="lg"
        >
          ⚡ Quick Access (Auto Log In)
        </Button>
        <GoogleButton onClick={onGoogle} loading={google.isPending} />
      </div>

      <div className="auth-divider my-5">
        <OrDivider label="or continue with email" />
      </div>

      <form onSubmit={onSubmit} className="auth-form" noValidate>
        <Field
          label="Work email"
          name="email"
          type="email"
          placeholder="you@yourbrand.com"
          autoComplete="email"
          required
        />
        <Field
          label="Password"
          name="password"
          type="password"
          placeholder="Password"
          autoComplete="current-password"
          required
        />

        {error && (
          <p role="alert" className="auth-error text-sm text-error">
            {error}
          </p>
        )}

        <Button type="submit" className="auth-primary-action w-full" size="lg" loading={login.isPending}>
          Log in <span aria-hidden>→</span>
        </Button>
      </form>

      <div className="auth-link-row mt-5 flex items-center justify-between text-sm">
        <Link to="/business/forgot-password" className="text-muted hover:text-ink">
          Forgot password?
        </Link>
        <Link
          to={`/business/sign-up${params.get("next") ? `?next=${encodeURIComponent(params.get("next")!)}` : ""}`}
          className="font-semibold text-blue hover:text-blue-dark"
        >
          Create account
        </Link>
      </div>

      <p className="auth-secondary-copy mt-6 text-center text-sm text-muted">
        Shopping, not selling?{" "}
        <Link to="/auth/login" className="font-semibold text-blue hover:text-blue-dark">
          Shopper log in
        </Link>
      </p>
    </AuthShell>
  );
}
