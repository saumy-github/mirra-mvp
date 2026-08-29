import { Link } from "react-router-dom";
import { AuthHeading, AuthShell } from "@/features/auth/components/auth-shell";

// Pilot: in-house login gated off, see doc 06.
// import { useNavigate, useSearchParams } from "react-router-dom";
// import { useState } from "react";
// import { Button } from "@/components/ui/button";
// import { Field } from "@/components/ui/field";
// import { useAuthMutations } from "@/hooks/use-shopper";
// import { postAuthDestination } from "@/lib/post-auth";
//
// export default function VerifyEmail() {
//   const navigate = useNavigate();
//   const [params] = useSearchParams();
//   const { verifyEmail } = useAuthMutations();
//   const [error, setError] = useState<string | null>(null);
//
//   async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
//     e.preventDefault();
//     setError(null);
//     const code = String(new FormData(e.currentTarget).get("code") ?? "");
//     try {
//       await verifyEmail.mutateAsync(code);
//       navigate(postAuthDestination(params.get("next")));
//     } catch {
//       setError("That code doesn't match. Check your inbox and retry.");
//     }
//   }
//
//   return (
//     <AuthShell>
//       <AuthHeading
//         pill="One more step"
//         title="Verify your email"
//         subtitle="We've sent a six-digit code to your inbox"
//       />
//
//       <form onSubmit={onSubmit} className="space-y-3" noValidate>
//         <Field
//           label="Verification code"
//           name="code"
//           inputMode="numeric"
//           placeholder="000000"
//           autoComplete="one-time-code"
//           maxLength={6}
//           required
//         />
//         {error && (
//           <p role="alert" className="text-sm text-error">
//             {error}
//           </p>
//         )}
//         <Button type="submit" className="w-full" size="lg" loading={verifyEmail.isPending}>
//           Verify <span aria-hidden>→</span>
//         </Button>
//       </form>
//
//       <button
//         type="button"
//         onClick={() => navigate(postAuthDestination(params.get("next")))}
//         className="mt-6 w-full text-center text-sm text-muted hover:text-ink"
//       >
//         Verify later
//       </button>
//     </AuthShell>
//   );
// }

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
