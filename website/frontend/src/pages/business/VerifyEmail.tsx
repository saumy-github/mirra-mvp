import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { AuthHeading, AuthShell } from "@/features/auth/components/auth-shell";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { useAuthMutations } from "@/hooks/use-shopper";
import { businessDestination } from "./destination";

/** Business email verification — the six-digit code flow. */
export default function BusinessVerifyEmail() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { verifyEmail } = useAuthMutations();
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const code = String(new FormData(e.currentTarget).get("code") ?? "");
    try {
      await verifyEmail.mutateAsync(code);
      navigate(businessDestination(params.get("next")));
    } catch {
      setError("That code doesn't match. Check your inbox and retry.");
    }
  }

  return (
    <AuthShell>
      <AuthHeading
        pill="One more step"
        title="Verify your email"
        subtitle="We've sent a six-digit code to your work inbox"
      />

      <form onSubmit={onSubmit} className="auth-form" noValidate>
        <Field
          label="Verification code"
          name="code"
          inputMode="numeric"
          placeholder="000000"
          autoComplete="one-time-code"
          maxLength={6}
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
          loading={verifyEmail.isPending}
        >
          Verify <span aria-hidden>→</span>
        </Button>
      </form>

      <button
        type="button"
        onClick={() => navigate(businessDestination(params.get("next")))}
        className="auth-secondary-action mt-6 w-full text-center text-sm text-muted hover:text-ink"
      >
        Verify later
      </button>
    </AuthShell>
  );
}
