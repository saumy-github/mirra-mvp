import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getRuntimeProvider } from "@/integrations/mirra-api";
import type { ShopperAccount } from "@/integrations/mirra-api/types";

const SHOPPER_KEY = ["account", "me"];

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
