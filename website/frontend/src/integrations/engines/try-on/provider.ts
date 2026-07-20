import { getRuntimeProvider } from "@/integrations/mirra-api";
import type { TryOnEngineProvider } from "./types";

function build(mode: "live" | "demo"): TryOnEngineProvider {
  const api = getRuntimeProvider();
  return {
    mode,
    engineVersion: mode === "demo" ? "demo-tryon-0.1" : "unknown-live",
    createTryOnSession: () => api.createTryOnSession(),
    requestTryOn: (input) => api.requestTryOn(input),
    getTryOnStatus: (sid, rid) => api.getTryOnRender(sid, rid),
    getTryOnResult: (sid, rid) => api.getTryOnRender(sid, rid),
    restoreTryOnResult: (sid, rid) => api.getTryOnRender(sid, rid),
    cancelTryOn: async () => {
      // Demo renders resolve near-instantly; live mode maps to the backend cancel endpoint.
    },
    reportTryOnFailure: async () => {
      // Live mode maps to POST /tryon/sessions/{id}/renders/{rid}/failure-reports.
    },
  };
}

let instance: TryOnEngineProvider | null = null;
export function getTryOnEngine(): TryOnEngineProvider {
  if (!instance)
    instance = build(import.meta.env.VITE_TRYON_ENGINE_MODE === "live" ? "live" : "demo");
  return instance;
}
