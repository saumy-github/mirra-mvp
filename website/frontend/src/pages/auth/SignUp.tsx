import { Link, useSearchParams } from "react-router-dom";
import { AuthHeading, AuthShell } from "@/features/auth/components/auth-shell";

/**
 * Shopper sign-up. Google is the only pilot path (doc 06), and first-time
 * Google login *is* the sign-up — so this page only points at the login
 * page rather than carrying a form of its own.
 *
 * The email/password + verification flow still exists, but only for
 * business accounts: see `pages/business/SignUp.tsx`.
 */
export default function SignUp() {
  const [params] = useSearchParams();
  const next = params.get("next");

  return (
    <AuthShell>
      <AuthHeading
        pill="Your private fitting profile"
        title="Create your account"
        subtitle="Sign-up now happens with Google, from the login page"
      />
      <p className="text-center text-sm text-muted">
        <Link
          to={`/auth/login${next ? `?next=${encodeURIComponent(next)}` : ""}`}
          className="font-semibold text-blue hover:text-blue-dark"
        >
          Go to login →
        </Link>
      </p>

      <p className="mt-6 text-center text-sm text-muted">
        Are you a brand?{" "}
        <Link to="/business/sign-up" className="font-semibold text-blue hover:text-blue-dark">
          Create a business account
        </Link>
      </p>
    </AuthShell>
  );
}
