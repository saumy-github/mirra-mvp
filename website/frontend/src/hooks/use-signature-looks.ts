import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getRuntimeProvider } from "@/integrations/mirra-api";
import type { SignatureLook, SignatureLookLayer } from "@/integrations/mirra-api/types";

const KEY = ["account", "signature-looks"];

export function useSignatureLooks(enabled = true) {
  return useQuery({
    queryKey: KEY,
    queryFn: () => getRuntimeProvider().listSignatureLooks(),
    enabled,
    staleTime: 60_000,
  });
}

export function useSignatureLookMutations() {
  const qc = useQueryClient();
  const api = getRuntimeProvider();
  const invalidate = () => qc.invalidateQueries({ queryKey: KEY });

  const createLook = useMutation({
    mutationFn: (input: {
      name: string;
      layers: SignatureLookLayer[];
      avatarProfileVersion: number;
      thumbnailUrl: string | null;
      isDefault?: boolean;
    }) => api.createSignatureLook(input),
    onSuccess: invalidate,
  });

  const updateLook = useMutation({
    mutationFn: ({
      lookId,
      patch,
    }: {
      lookId: string;
      patch: Partial<Pick<SignatureLook, "name" | "isDefault" | "layers" | "thumbnailUrl">>;
    }) => api.updateSignatureLook(lookId, patch),
    onSuccess: invalidate,
  });

  const deleteLook = useMutation({
    mutationFn: (lookId: string) => api.deleteSignatureLook(lookId),
    onSuccess: invalidate,
  });

  return { createLook, updateLook, deleteLook };
}
