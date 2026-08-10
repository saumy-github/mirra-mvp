import { createPublicRuntimeProvider } from "./public-runtime-provider";
import type { MirraRuntimeProvider } from "./runtime-provider";

let provider: MirraRuntimeProvider | null = null;

/** The real Mirra backend at VITE_API_BASE_URL — the only runtime provider. */
export function getRuntimeProvider(): MirraRuntimeProvider {
  if (!provider) {
    provider = createPublicRuntimeProvider();
  }
  return provider;
}

export * from "./types";
export * from "./errors";
export type { MirraRuntimeProvider } from "./runtime-provider";
