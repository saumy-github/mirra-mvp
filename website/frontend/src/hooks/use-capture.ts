import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getRuntimeProvider } from "@/integrations/mirra-api";
import type { CaptureSession } from "@/integrations/mirra-api/types";
import { isCaptureTerminal } from "@/lib/state-machines/capture-session";

/**
 * Desktop side of QR pairing: create a session, then poll it (controlled
 * polling — 1.5 s while active, stopped once terminal). The mobile device
 * mutates the same session through token-scoped endpoints.
 */

export function useCreateCaptureSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => getRuntimeProvider().createCaptureSession(),
    onSuccess: (session) => qc.setQueryData(["capture-session", session.captureSessionId], session),
  });
}

export function useCaptureSession(sessionId: string | null) {
  return useQuery({
    queryKey: ["capture-session", sessionId],
    queryFn: () => getRuntimeProvider().getCaptureSession(sessionId!),
    enabled: !!sessionId,
    refetchInterval: (query) => {
      const data = query.state.data as CaptureSession | undefined;
      if (data && isCaptureTerminal(data.state)) return false;
      return 1500;
    },
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

export function useCancelCaptureSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => getRuntimeProvider().cancelCaptureSession(sessionId),
    onSuccess: (session) => qc.setQueryData(["capture-session", session.captureSessionId], session),
  });
}
