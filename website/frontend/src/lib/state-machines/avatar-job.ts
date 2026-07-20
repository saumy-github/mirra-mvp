import type { AvatarJobState } from "@/integrations/mirra-api/types";
import { assertTransition, canTransition, isTerminal, type TransitionTable } from "./machine";

export const avatarJobTransitions: TransitionTable<AvatarJobState> = {
  queued: ["validating", "failed", "cancelled"],
  validating: ["estimating", "failed", "cancelled"],
  estimating: ["generating", "failed", "cancelled"],
  generating: ["optimising", "failed", "cancelled"],
  optimising: ["ready", "failed", "cancelled"],
  ready: [],
  failed: [],
  cancelled: [],
};

/** Honest, calm stage labels — shown instead of fake percentages. */
export const avatarStageLabels: Record<AvatarJobState, string> = {
  queued: "Waiting for a fitting slot",
  validating: "Validating photographs",
  estimating: "Estimating proportions",
  generating: "Generating avatar",
  optimising: "Preparing studio assets",
  ready: "Profile synchronized",
  failed: "Generation didn't complete",
  cancelled: "Generation cancelled",
};

export const orderedAvatarStages: AvatarJobState[] = [
  "queued",
  "validating",
  "estimating",
  "generating",
  "optimising",
  "ready",
];

export const canTransitionAvatarJob = (from: AvatarJobState, to: AvatarJobState) =>
  canTransition(avatarJobTransitions, from, to);
export const assertAvatarJobTransition = (from: AvatarJobState, to: AvatarJobState) =>
  assertTransition(avatarJobTransitions, from, to, "avatar-job");
export const isAvatarJobTerminal = (s: AvatarJobState) => isTerminal(avatarJobTransitions, s);
