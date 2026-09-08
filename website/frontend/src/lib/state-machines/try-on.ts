import type { TryOnState } from "@/integrations/mirra-api/types";
import { assertTransition, canTransition, type TransitionTable } from "./machine";

export const tryOnTransitions: TransitionTable<TryOnState> = {
  idle: ["requesting", "restoring", "unsupported"],
  requesting: ["processing", "ready", "failed", "unsupported"],
  processing: ["ready", "failed", "unsupported"],
  ready: ["idle", "requesting", "restoring", "cached", "unsupported"],
  cached: ["idle", "requesting", "restoring", "unsupported"],
  restoring: ["cached", "requesting", "failed", "unsupported"],
  unsupported: ["idle", "requesting"],
  failed: ["idle", "requesting", "restoring", "unsupported"],
};

export const canTransitionTryOn = (from: TryOnState, to: TryOnState) =>
  canTransition(tryOnTransitions, from, to);
export const assertTryOnTransition = (from: TryOnState, to: TryOnState) =>
  assertTransition(tryOnTransitions, from, to, "try-on");
