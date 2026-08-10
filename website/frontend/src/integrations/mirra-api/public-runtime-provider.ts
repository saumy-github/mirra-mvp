import { MirraHttpClient } from "./client";
import { HttpRuntimeProvider } from "./http-runtime-provider";

/**
 * The runtime provider — talks to the real Mirra backend (see
 * website/backend-structure-plan.md) at VITE_API_BASE_URL.
 */
export function createPublicRuntimeProvider() {
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
  return new HttpRuntimeProvider(new MirraHttpClient({ baseUrl }));
}
