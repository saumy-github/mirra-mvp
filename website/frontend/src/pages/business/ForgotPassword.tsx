import { useState } from "react";
import { Link } from "react-router-dom";
import { AuthHeading, AuthShell } from "@/features/auth/components/auth-shell";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { useAuthMutations } from "@/hooks/use-shopper";

/** Business password reset. Shopper accounts have no password to reset. */
export default function BusinessForgotPassword() {
  const { requestReset } = useAuthMutations();
  const [sent, setSent] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const email = String(new FormData(e.currentTarget).get("email") ?? "");
    await requestReset.mutateAsync(email).catch(() => undefined);
    // Always acknowledge — never disclose whether an account exists.
    setSent(true);
  }

  return (
    <AuthShell>
      <AuthHeading
        pill="Account recovery"
        title="Reset password"
        subtitle="We'll email you a link to choose a new password"
      />

      {sent ? (
        <div
          role="status"
          className="auth-status-card rounded-field border border-line bg-surface p-5 text-center"
        >
          <p className="text-sm text-ink-soft">
            If an account exists for that address, a reset link is on its way. It expires in 30
            minutes.
          </p>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="auth-form" noValidate>
          <Field
            label="Work email"
            name="email"
            type="email"
            placeholder="you@yourbrand.com"
            autoComplete="email"
            required
          />
          <Button
            type="submit"
            className="auth-primary-action w-full"
            size="lg"
            loading={requestReset.isPending}
          >
            Send reset link <span aria-hidden>→</span>
          </Button>
        </form>
      )}

      <p className="auth-secondary-copy mt-6 text-center text-sm text-muted">
        Remembered it?{" "}
        <Link to="/business/login" className="font-semibold text-blue hover:text-blue-dark">
          Log in
        </Link>
      </p>
    </AuthShell>
  );
}
