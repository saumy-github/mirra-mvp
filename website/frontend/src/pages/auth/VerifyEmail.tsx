import { Link } from "react-router-dom";
import { AuthHeading, AuthShell } from "@/features/auth/components/auth-shell";

/**
 * Google accounts arrive verified, so the shopper never sees a code form.
 * Profile.tsx still links here for accounts that predate the Google-only
 * pilot. The live code form is on the business side, at
 * `/business/verify-email`.
 */
export default function VerifyEmail() {
  return (
    <AuthShell>
      <AuthHeading
        pill="One more step"
        title="Verify your email"
        subtitle="Google accounts are already verified — nothing to do here"
      />
      <p className="text-center text-sm text-muted">
        <Link to="/auth/login" className="font-semibold text-blue hover:text-blue-dark">
          Continue →
        </Link>
      </p>
    </AuthShell>
  );
}
