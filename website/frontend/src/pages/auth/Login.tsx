import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useState } from "react";
import { AuthHeading, AuthShell } from "@/features/auth/components/auth-shell";
import { GoogleButton } from "@/features/auth/components/oauth-buttons";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { OrDivider } from "@/components/ui/misc";
import { useAuthMutations } from "@/hooks/use-shopper";
import { MirraApiError, userMessage } from "@/integrations/mirra-api";
import { track } from "@/lib/analytics";
import { postAuthDestination } from "@/lib/post-auth";

export default function Login() {
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
      navigate(postAuthDestination(params.get("next")));
    } catch (err) {
      setError(
        err instanceof MirraApiError
          ? userMessage(err.code)
          : "Something went wrong. Please retry.",
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

  async function onGuest() {
    setError(null);
    try {
      await continueAsGuest.mutateAsync();
      track("guest_started", { authenticated: true });
      navigate("/studio");
    } catch {
      setError("Guest access didn't start. Please retry.");
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
      navigate(params.get("next") ? postAuthDestination(params.get("next")) : "/studio");
    } catch {
      setError("Quick access login didn't complete. Please retry.");
    }
  }

  return (
    <AuthShell>
      <AuthHeading
        pill="Welcome back"
        title="Your fitting room awaits"
        subtitle="Log in to use your saved avatar and Signature Looks"
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
          label="Email"
          name="email"
          type="email"
          placeholder="you@example.com"
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

        <Button
          type="submit"
          className="auth-primary-action w-full"
          size="lg"
          loading={login.isPending}
        >
          Log in <span aria-hidden>→</span>
        </Button>
      </form>

      <div className="auth-link-row mt-5 flex items-center justify-between text-sm">
        <Link to="/auth/forgot-password" className="text-muted hover:text-ink">
          Forgot password?
        </Link>
        <Link
          to={`/auth/sign-up${params.get("next") ? `?next=${encodeURIComponent(params.get("next")!)}` : ""}`}
          className="font-semibold text-blue hover:text-blue-dark"
        >
          Create account
        </Link>
      </div>

      <button
        type="button"
        onClick={onGuest}
        disabled={continueAsGuest.isPending}
        className="auth-secondary-action mt-6 w-full text-center text-sm text-muted hover:text-ink disabled:opacity-50"
      >
        {continueAsGuest.isPending
          ? "Setting up a guest avatar…"
          : "Prefer not to sign in? Continue as a guest →"}
      </button>
    </AuthShell>
  );
}
