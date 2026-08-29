import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AuthHeading, AuthShell } from "@/features/auth/components/auth-shell";
import { GoogleButton } from "@/features/auth/components/oauth-buttons";
import { useAuthMutations } from "@/hooks/use-shopper";
import { track } from "@/lib/analytics";
import { postAuthDestination } from "@/lib/post-auth";
import { markPendingConsent } from "./pending-consent";

/**
 * Shopper login — reached from the "Log in" button in the site navbar.
 * Google is the only pilot path (doc 06); first-time Google login is also
 * the sign-up, which is why the consent checkbox gates the button here.
 *
 * Business accounts use email + password at `/business/login`.
 */
export default function Login() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { google, continueAsGuest } = useAuthMutations();
  const [error, setError] = useState<string | null>(
    params.get("error") ? "Google sign-in didn't complete. Please retry." : null,
  );
  // Gates the Google button — first-time Google login is now the sign-up.
  const [accepted, setAccepted] = useState(false);

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
      </label>

      <div className="mt-4">
        <GoogleButton onClick={onGoogle} loading={google.isPending} />
      </div>

      {error && (
        <p role="alert" className="mt-4 text-sm text-error">
          {error}
        </p>
      )}

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

      <p className="auth-secondary-copy mt-6 text-center text-sm text-muted">
        Are you a brand?{" "}
        <Link to="/business/login" className="font-semibold text-blue hover:text-blue-dark">
          Business log in
        </Link>
      </p>
    </AuthShell>
  );
}
