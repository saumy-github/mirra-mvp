import type { CaptureSessionState } from "@/integrations/mirra-api/types";
import { assertTransition, canTransition, isTerminal, type TransitionTable } from "./machine";

export const captureTransitions: TransitionTable<CaptureSessionState> = {
  created: ["qr_ready", "expired", "cancelled", "failed"],
  qr_ready: ["paired", "expired", "cancelled", "failed"],
  paired: ["consent_pending", "expired", "cancelled", "failed"],
  consent_pending: ["capturing", "expired", "cancelled", "failed"],
  capturing: ["uploading", "capturing", "expired", "cancelled", "failed"],
  uploading: ["capturing", "uploaded", "expired", "cancelled", "failed"],
  uploaded: ["processing", "cancelled", "failed"],
  processing: ["completed", "failed"],
  completed: [],
  expired: [],
  cancelled: [],
  failed: [],
};

export const canTransitionCapture = (from: CaptureSessionState, to: CaptureSessionState) =>
  canTransition(captureTransitions, from, to);
export const assertCaptureTransition = (from: CaptureSessionState, to: CaptureSessionState) =>
  assertTransition(captureTransitions, from, to, "capture-session");
export const isCaptureTerminal = (s: CaptureSessionState) => isTerminal(captureTransitions, s);

export function isCaptureExpired(expiresAt: string, now: Date = new Date()): boolean {
  return now.getTime() >= new Date(expiresAt).getTime();
}
