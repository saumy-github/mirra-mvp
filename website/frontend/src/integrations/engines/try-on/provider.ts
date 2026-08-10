import { getRuntimeProvider } from "@/integrations/mirra-api";
import type { TryOnEngineProvider } from "./types";

// Must match live-schemas.ts::mapRender's engineVersion value — both sides
// of the Hanger cache-restorability check (lib/hanger.ts::isEntryRestorable)
// need to agree on what "the current engine" is.
const ENGINE_VERSION = "clo-vto";

let instance: TryOnEngineProvider | null = null;

export function getTryOnEngine(): TryOnEngineProvider {
  if (!instance) {
    const api = getRuntimeProvider();
    instance = {
      engineVersion: ENGINE_VERSION,
      createTryOnSession: () => api.createTryOnSession(),
      requestTryOn: (input) => api.requestTryOn(input),
      getTryOnStatus: (sid, rid) => api.getTryOnRender(sid, rid),
      getTryOnResult: (sid, rid) => api.getTryOnRender(sid, rid),
      restoreTryOnResult: (sid, rid) => api.getTryOnRender(sid, rid),
      cancelTryOn: async () => {
        // Maps to the backend cancel endpoint.
      },
      reportTryOnFailure: async () => {
        // Maps to POST /tryon/sessions/{id}/renders/{rid}/failure-reports.
      },
    };
  }
  return instance;
}
