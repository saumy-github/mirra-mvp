import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { getRuntimeProvider } from "@/integrations/mirra-api";
import type { ShopperAccount } from "@/integrations/mirra-api/types";

const SHOPPER_KEY = ["account", "me"];

/**
 * Called from the /auth/callback page after the Google OAuth redirect round
 * trip lands back on us — the backend has already set the refresh cookie,
 * this just hydrates the same react-query cache entry useAccount() reads,
 * reusing the existing "no in-memory token → try refresh cookie" bootstrap.
 */
export async function completeOAuthCallback(qc: QueryClient): Promise<ShopperAccount | null> {
  const account = await getRuntimeProvider().getCurrentShopper();
  qc.setQueryData(SHOPPER_KEY, account);
  return account;
}

export function useAccount() {
  return useQuery({
    queryKey: SHOPPER_KEY,
    queryFn: () => getRuntimeProvider().getCurrentShopper(),
    staleTime: 60_000,
  });
}

export function useAuthMutations() {
  const qc = useQueryClient();
  const api = getRuntimeProvider();
  const onAuthed = (account: ShopperAccount) => qc.setQueryData(SHOPPER_KEY, account);

  const signUp = useMutation({
    mutationFn: (input: {
      displayName: string;
      email: string;
      password: string;
      acceptedTerms: boolean;
    }) => api.signUp(input),
    onSuccess: onAuthed,
  });

  const login = useMutation({
    mutationFn: (input: { email: string; password: string }) => api.login(input),
    onSuccess: onAuthed,
  });

  const google = useMutation({
    mutationFn: () => api.loginWithGoogle(),
    onSuccess: onAuthed,
  });

  const continueAsGuest = useMutation({
    mutationFn: () => api.continueAsGuest(),
    onSuccess: onAuthed,
  });

  const logout = useMutation({
    mutationFn: () => api.logout(),
    onSuccess: () => {
      qc.setQueryData(SHOPPER_KEY, null);
      qc.clear();
    },
  });

  const verifyEmail = useMutation({
    mutationFn: (code: string) => api.verifyEmail(code),
    onSuccess: onAuthed,
  });

  const requestReset = useMutation({
    mutationFn: (email: string) => api.requestPasswordReset(email),
  });

  return { signUp, login, google, continueAsGuest, logout, verifyEmail, requestReset };
}

export function useAvatarProfile(enabled = true) {
  return useQuery({
    queryKey: ["account", "avatar-profile"],
    queryFn: () => getRuntimeProvider().getAvatarProfile(),
    enabled,
    staleTime: 30_000,
  });
}

/** Triggers avatar generation from the shopper's already-saved measurements
 * — no photo capture involved. */
export function useGenerateAvatar() {
  return useMutation({
    mutationFn: () => getRuntimeProvider().generateAvatar(),
  });
}

export function useAvatarJob(jobId: string | null) {
  return useQuery({
    queryKey: ["avatar-job", jobId],
    queryFn: () => getRuntimeProvider().getAvatarJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      if (state === "ready" || state === "failed" || state === "cancelled") return false;
      return 1200;
    },
  });
}
