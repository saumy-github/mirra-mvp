import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { AuthHeading, AuthShell } from "@/features/auth/components/auth-shell";
import { GoogleButton } from "@/features/auth/components/oauth-buttons";
import { QuickAccessControl } from "@/features/auth/components/quick-access-control";
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
  const { signUp, google } = useAuthMutations();
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

  return (
    <AuthShell topRightAction={<QuickAccessControl />}>
      <AuthHeading
        pill="Your private fitting profile"
        title="Create your account"
        subtitle="Save your avatar, measurements, and Signature Looks across stores"
      />

      <div>
        <GoogleButton onClick={onGoogle} loading={google.isPending} />
      </div>

      <div className="my-5">
        <OrDivider label="or continue with email" />
      </div>

      <form onSubmit={onSubmit} className="space-y-4" noValidate>
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

        {error && (
          <p role="alert" className="text-sm text-error">
            {error}
          </p>
        )}

        <Button type="submit" className="w-full" size="lg" loading={signUp.isPending}>
          Sign up <span aria-hidden>→</span>
        </Button>
      </form>

      <p className="mt-5 text-center text-sm text-muted">
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
