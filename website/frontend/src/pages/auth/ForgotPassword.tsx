import { Link } from "react-router-dom";
import { AuthHeading, AuthShell } from "@/features/auth/components/auth-shell";

/**
 * Shopper accounts have no in-house password, so there is nothing to reset.
 * The real reset form lives on the business side, at
 * `/business/forgot-password`.
 */
export default function ForgotPassword() {
  return (
    <AuthShell>
      <AuthHeading
        pill="Account recovery"
        title="Reset password"
        subtitle="Sign in with Google instead — there's no in-house password to reset"
      />
      <p className="text-center text-sm text-muted">
        <Link to="/auth/login" className="font-semibold text-blue hover:text-blue-dark">
          Log in
        </Link>
      </p>

      <p className="mt-6 text-center text-sm text-muted">
        Business account?{" "}
        <Link
          to="/business/forgot-password"
          className="font-semibold text-blue hover:text-blue-dark"
        >
          Reset your business password
        </Link>
      </p>
    </AuthShell>
  );
}
