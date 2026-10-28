// Shared React Query hooks and labels for pages that read a real workspace.
import { useQuery } from "@tanstack/react-query";
import type { Tone } from "../components/styles";
import { merchantApi } from "./merchant-api";

export function useLiveGarments(tenantId: string) {
  return useQuery({
    queryKey: ["merchant-garments", tenantId],
    queryFn: () => merchantApi.listGarments(tenantId),
  });
}

export function useLiveProducts(tenantId: string) {
  return useQuery({
    queryKey: ["merchant-products", tenantId],
    queryFn: () => merchantApi.listProducts(tenantId),
  });
}

/** The backend stage machine (service.ALLOWED_TRANSITIONS), as merchants read it. */
export const LIVE_STAGE: Record<string, { label: string; tone: Tone }> = {
  needs_data: { label: "Needs data", tone: "warn" },
  merchant_review: { label: "Your review", tone: "info" },
  in_qa: { label: "In QA", tone: "info" },
  qa_changes: { label: "Changes requested", tone: "danger" },
  ready: { label: "Ready to publish", tone: "success" },
  live: { label: "Live", tone: "success" },
  paused: { label: "Paused", tone: "warn" },
  sync_error: { label: "Sync error", tone: "danger" },
};

export function stageMeta(stage: string) {
  return LIVE_STAGE[stage] ?? { label: stage.replace(/_/g, " "), tone: "neutral" as Tone };
}
