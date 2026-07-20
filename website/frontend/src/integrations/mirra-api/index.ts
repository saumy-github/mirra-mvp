import { createMockRuntimeProvider } from "./mock-runtime-provider";
import { createPublicRuntimeProvider } from "./public-runtime-provider";
import type { MirraRuntimeProvider } from "./runtime-provider";

let provider: MirraRuntimeProvider | null = null;

/**
 * Resolve the active runtime provider from VITE_INTEGRATION_MODE.
 *  - mock: in-process fixtures behind the versioned contract
 *  - live: the real Mirra backend at VITE_API_BASE_URL
 */
export function getRuntimeProvider(): MirraRuntimeProvider {
  if (!provider) {
    provider =
      import.meta.env.VITE_INTEGRATION_MODE === "live"
        ? createPublicRuntimeProvider()
        : createMockRuntimeProvider();
  }
  return provider;
}

export * from "./types";
export * from "./errors";
export type { MirraRuntimeProvider } from "./runtime-provider";
