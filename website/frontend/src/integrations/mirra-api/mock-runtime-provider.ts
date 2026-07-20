import { InProcessMockProvider } from "@/mocks/mock-provider";
import type { MirraRuntimeProvider } from "./runtime-provider";

/**
 * MOCK provider — development only (VITE_INTEGRATION_MODE=mock).
 *
 * Unlike the ported original (which still made same-origin HTTP calls to
 * Next.js API routes), this implements MirraRuntimeProvider directly
 * in-process against in-memory fixtures (src/mocks/). There's no Next
 * server to host mock API routes on anymore, and this way the frontend
 * runs standalone with `npm run dev` — no backend required at all.
 */
export function createMockRuntimeProvider(): MirraRuntimeProvider {
  return new InProcessMockProvider();
}
