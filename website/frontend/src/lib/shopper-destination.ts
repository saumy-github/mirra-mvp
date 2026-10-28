import { onboardingStudioDestination, postAuthDestination, signupDestination } from "./post-auth";

/** Sign-in opens the requested workspace. Only account creation starts onboarding. */
export function shopperDestination(next?: string | null): string {
  const destination = postAuthDestination(next);
  const url = new URL(destination, "https://mirra.local");
  // The "Already have an account" link can carry signup's next parameter.
  return url.pathname === "/onboarding/qr"
    ? onboardingStudioDestination(url.searchParams.get("next"))
    : destination;
}

export function oauthDestination(next: string | null, isNewAccount: boolean): string {
  const destination = shopperDestination(next);
  return isNewAccount ? signupDestination(destination) : destination;
}
