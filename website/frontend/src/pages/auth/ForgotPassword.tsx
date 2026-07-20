import { Link } from "react-router-dom";
import { useState } from "react";
import { AuthHeading, AuthShell } from "@/features/auth/components/auth-shell";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { useAuthMutations } from "@/hooks/use-shopper";

export default function ForgotPassword() {
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
        <div role="status" className="rounded-field border border-line bg-surface p-5 text-center">
          <p className="text-sm text-ink-soft">
            If an account exists for that address, a reset link is on its way. It expires in 30
            minutes.
          </p>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="space-y-3" noValidate>
          <Field
            label="Email"
            name="email"
            type="email"
            placeholder="you@example.com"
            autoComplete="email"
            required
          />
          <Button type="submit" className="w-full" size="lg" loading={requestReset.isPending}>
            Send reset link <span aria-hidden>→</span>
          </Button>
        </form>
      )}

      <p className="mt-6 text-center text-sm text-muted">
        Remembered it?{" "}
        <Link to="/auth/login" className="font-semibold text-blue hover:text-blue-dark">
          Log in
        </Link>
      </p>
    </AuthShell>
  );
}
