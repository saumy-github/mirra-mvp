import type { SignatureLookLayer, TryOnRender, TryOnSession } from "@/integrations/mirra-api/types";

/**
 * TryOnEngineProvider — the typed seam in front of the real CLO3D VTO
 * pipeline. In demo mode results are layered garment assets, not a physics
 * simulation, and are labelled as such.
 */
export interface TryOnEngineProvider {
  readonly mode: "live" | "demo";
  readonly engineVersion: string;

  createTryOnSession(): Promise<TryOnSession>;
  requestTryOn(input: {
    tryOnSessionId: string;
    productPublicId: string;
    variantPublicId: string;
    size: string | null;
    baseLayers?: SignatureLookLayer[];
  }): Promise<TryOnRender>;
  getTryOnStatus(tryOnSessionId: string, renderId: string): Promise<TryOnRender>;
  getTryOnResult(tryOnSessionId: string, renderId: string): Promise<TryOnRender>;
  /** Restore a previously generated render (Hanger) without re-running the engine. */
  restoreTryOnResult(tryOnSessionId: string, renderId: string): Promise<TryOnRender>;
  cancelTryOn(tryOnSessionId: string, renderId: string): Promise<void>;
  reportTryOnFailure(tryOnSessionId: string, renderId: string, reason: string): Promise<void>;
}
