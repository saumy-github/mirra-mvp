import { useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { AuthHeading, AuthShell } from "@/features/auth/components/auth-shell";
import { completeOAuthCallback } from "@/hooks/use-shopper";
import { track } from "@/lib/analytics";
import { postAuthDestination } from "@/lib/post-auth";

/**
 * Landing page for the Google OAuth redirect round trip
 * (backend: auth/google/start -> Google -> auth/google/callback -> here).
 * The backend has already set the refresh cookie by the time we're loaded;
 * this page just hydrates the shopper session from it and moves on.
 */
export default function AuthCallback() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const qc = useQueryClient();
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    completeOAuthCallback(qc)
      .then((account) => {
        if (!account) {
          navigate("/auth/login?error=google_failed", { replace: true });
          return;
        }
        track("login_completed", { authenticated: true, properties: { method: "google" } });
        navigate(postAuthDestination(params.get("next")), { replace: true });
      })
      .catch(() => {
        navigate("/auth/login?error=google_failed", { replace: true });
      });
  }, [navigate, params, qc]);

  return (
    <AuthShell>
      <div className="auth-callback" role="status" aria-live="polite">
        <AuthHeading
          pill="Almost there"
          title="Finishing sign-in"
          subtitle="Hang tight while we connect your Google account."
        />
      </div>
    </AuthShell>
  );
}
