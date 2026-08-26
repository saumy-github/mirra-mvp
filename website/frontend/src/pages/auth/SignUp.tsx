import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { AuthHeading, AuthShell } from "@/features/auth/components/auth-shell";
import { GoogleButton } from "@/features/auth/components/oauth-buttons";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { OrDivider } from "@/components/ui/misc";
import { useAuthMutations } from "@/hooks/use-shopper";
import { MirraApiError, userMessage } from "@/integrations/mirra-api";
import { track } from "@/lib/analytics";
import { postAuthDestination } from "@/lib/post-auth";

export default function SignUp() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { signUp, google, continueAsGuest } = useAuthMutations();
  const [error, setError] = useState<string | null>(null);
  const [accepted, setAccepted] = useState(false);

  useEffect(() => {
    track("signup_started");
  }, []);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const data = new FormData(e.currentTarget);
    if (!accepted) {
      setError("Please accept the Terms and Privacy Notice to continue.");
      return;
    }
    try {
      await signUp.mutateAsync({
        displayName: String(data.get("displayName") ?? ""),
        email: String(data.get("email") ?? ""),
        password: String(data.get("password") ?? ""),
        acceptedTerms: accepted,
      });
      track("signup_completed", {
        authenticated: true,
      });
      navigate(
        `/auth/verify-email?next=${encodeURIComponent(postAuthDestination(params.get("next")))}`,
      );
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
        pill="Your private fitting profile"
        title="Create your account"
        subtitle="Save your avatar, measurements, and Signature Looks across stores"
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
          label="Name"
          name="displayName"
          placeholder="Your name"
          autoComplete="name"
          required
        />
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
          placeholder="Create a password"
          autoComplete="new-password"
          hint="At least 8 characters."
          required
          minLength={8}
        />

        <div className="auth-consent flex items-start gap-3 rounded-[14px] px-1 py-1 text-xs leading-relaxed text-muted">
          <input
            aria-labelledby="signup-consent-copy"
            type="checkbox"
            checked={accepted}
            onChange={(e) => setAccepted(e.target.checked)}
            className="mt-0.5 size-4.5 shrink-0 accent-blue"
          />
          <span id="signup-consent-copy">
            I accept the{" "}
            <Link className="underline decoration-line-strong" to="/terms">
              Terms of Service
            </Link>{" "}
            and acknowledge the{" "}
            <Link className="underline decoration-line-strong" to="/privacy">
              Privacy Notice
            </Link>
            . Photographs are used only to build your avatar and are never shown to anyone else.
          </span>
        </div>

        {error && (
          <p role="alert" className="auth-error text-sm text-error">
            {error}
          </p>
        )}

        <Button
          type="submit"
          className="auth-primary-action w-full"
          size="lg"
          loading={signUp.isPending}
        >
          Sign up <span aria-hidden>→</span>
        </Button>
      </form>

      <p className="auth-secondary-copy mt-5 text-center text-sm text-muted">
        Already have an account?{" "}
        <Link
          to={`/auth/login${params.get("next") ? `?next=${encodeURIComponent(params.get("next")!)}` : ""}`}
          className="font-semibold text-blue hover:text-blue-dark"
        >
          Log in
        </Link>
      </p>
    </AuthShell>
  );
}
