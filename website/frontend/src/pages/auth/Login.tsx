import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { AuthHeading, AuthShell } from "@/features/auth/components/auth-shell";
import { GoogleButton } from "@/features/auth/components/oauth-buttons";
import { useAuthMutations } from "@/hooks/use-shopper";
import { track } from "@/lib/analytics";
import { postAuthDestination } from "@/lib/post-auth";
import { markPendingConsent } from "./pending-consent";

// Pilot: in-house login gated off, see doc 06.
// import { Link } from "react-router-dom";
// import { Button } from "@/components/ui/button";
// import { Field } from "@/components/ui/field";
// import { OrDivider } from "@/components/ui/misc";
// import { MirraApiError, userMessage } from "@/integrations/mirra-api";

export default function Login() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  // `login` mutation still wired, just unused while the UI is hidden.
  const { google, continueAsGuest } = useAuthMutations();
  const [error, setError] = useState<string | null>(
    params.get("error") ? "Google sign-in didn't complete. Please retry." : null,
  );
  // Gates the Google button — first-time Google login is now the sign-up.
  const [accepted, setAccepted] = useState(false);

  // Pilot: in-house login gated off, see doc 06.
  // async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
  //   e.preventDefault();
  //   setError(null);
  //   const data = new FormData(e.currentTarget);
  //   try {
  //     await login.mutateAsync({
  //       email: String(data.get("email") ?? ""),
  //       password: String(data.get("password") ?? ""),
  //     });
  //     track("login_completed", {
  //       authenticated: true,
  //       properties: { method: "password" },
  //     });
  //     navigate(postAuthDestination(params.get("next")));
  //   } catch (err) {
  //     setError(
  //       err instanceof MirraApiError
  //         ? userMessage(err.code)
  //         : "Something went wrong. Please retry.",
  //     );
  //   }
  // }

  async function onGoogle() {
    if (!accepted) {
      // Inert until consent is ticked.
      setError("Please accept the Terms and Privacy Notice to continue.");
      return;
    }
    setError(null);
    try {
      // Carried across the OAuth redirect to AuthCallback.tsx.
      markPendingConsent();
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

  return (
    <AuthShell>
      <AuthHeading
        pill="Welcome back"
        title="Your fitting room awaits"
        subtitle="Log in to use your saved avatar and Signature Looks"
      />

      <label className="flex cursor-pointer items-start gap-3 rounded-[14px] px-1 py-1 text-xs leading-relaxed text-muted">
        <input
          type="checkbox"
          checked={accepted}
          onChange={(e) => setAccepted(e.target.checked)}
          className="mt-0.5 size-4.5 shrink-0 accent-blue"
        />
        <span>
          I accept the <span className="underline decoration-line-strong">Terms of Service</span>{" "}
          and acknowledge the{" "}
          <span className="underline decoration-line-strong">Privacy Notice</span>. Photographs
          are used only to build your avatar and are never shown to anyone else.
        </span>
      </label>

      <div className="mt-4">
        <GoogleButton onClick={onGoogle} loading={google.isPending} />
      </div>

      {/* Pilot: in-house login gated off, see doc 06.
      <div className="my-5">
        <OrDivider label="or continue with email" />
      </div>

      <form onSubmit={onSubmit} className="space-y-4" noValidate>
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

        <Button type="submit" className="w-full" size="lg" loading={login.isPending}>
          Log in <span aria-hidden>→</span>
        </Button>
      </form>

      <div className="mt-5 flex items-center justify-between text-sm">
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
      */}

      {error && (
        <p role="alert" className="mt-4 text-sm text-error">
          {error}
        </p>
      )}

      <button
        type="button"
        onClick={onGuest}
        disabled={continueAsGuest.isPending}
        className="mt-6 w-full text-center text-sm text-muted hover:text-ink disabled:opacity-50"
      >
        {continueAsGuest.isPending
          ? "Setting up a guest avatar…"
          : "Prefer not to sign in? Continue as a guest →"}
      </button>
    </AuthShell>
  );
}
