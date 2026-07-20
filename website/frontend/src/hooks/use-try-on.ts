import { useCallback, useRef } from "react";
import { getTryOnEngine } from "@/integrations/engines/try-on/provider";
import type {
  GarmentCategory,
  PublicProduct,
  ProductVariant,
  TryOnRender,
} from "@/integrations/mirra-api/types";
import { hangerEntryId, isEntryRestorable, type HangerEntry } from "@/lib/hanger";
import { track } from "@/lib/analytics";
import { useStudioStore, type OutfitLayer } from "@/stores/studio-store";

/**
 * Orchestrates try-on requests against the engine provider:
 *  - restores a cached Hanger render when a valid one exists (no engine call)
 *  - otherwise requests a render and polls until ready/failed/unsupported
 *  - pushes every successful look onto the Hanger (session LRU)
 */
export function useTryOn(opts: { avatarProfileVersion: number | null }) {
  const engine = getTryOnEngine();
  const store = useStudioStore();
  const requestSeq = useRef(0);

  const wear = useCallback(
    async (product: PublicProduct, variant: ProductVariant, size: string | null) => {
      const {
        tryOnSessionId,
        layers,
        setTryOnState,
        wearLayer,
        pushHanger,
        touchHanger,
        markHangerStatus,
        hanger,
      } = useStudioStore.getState();
      if (!tryOnSessionId || opts.avatarProfileVersion === null) return;
      const seq = ++requestSeq.current;

      const baseLayers = Object.values(layers).filter(
        (l): l is OutfitLayer => !!l && l.category !== product.garmentCategory,
      );

      const targetLayers: TryOnRender["layers"] = Object.fromEntries(
        baseLayers.map((l) => [
          l.category,
          {
            productPublicId: l.productPublicId,
            variantPublicId: l.variantPublicId,
            assetUrl: l.assetUrl,
          },
        ]),
      );
      if (variant.garmentAssetUrl) {
        targetLayers[product.garmentCategory] = {
          productPublicId: product.publicProductId,
          variantPublicId: variant.publicVariantId,
          assetUrl: variant.garmentAssetUrl,
        };
      }

      // Unsupported / asset-not-ready → deliberate state, no engine request.
      if (!product.tryOnEligible || !variant.tryOnEligible) {
        setTryOnState("unsupported", {
          renderId: null,
          failureReason: "This garment type isn't supported by try-on yet.",
        });
        return;
      }
      if (variant.assetStatus !== "ready" || !variant.garmentAssetUrl) {
        setTryOnState("unsupported", {
          renderId: null,
          failureReason: "We're still preparing this garment for try-on.",
        });
        return;
      }

      // Cached-result restore path (Hanger LRU).
      const entryId = hangerEntryId(
        product.publicProductId,
        variant.publicVariantId,
        size,
        targetLayers,
      );
      const cached = hanger.find((e) => e.id === entryId);
      if (cached) {
        const restorable = isEntryRestorable(cached, {
          avatarProfileVersion: opts.avatarProfileVersion,
          engineVersion: engine.engineVersion,
        });
        if (restorable) {
          setTryOnState("restoring", { renderId: cached.renderId, failureReason: null });
          try {
            await engine.restoreTryOnResult(cached.tryOnSessionId, cached.renderId);
            if (seq !== requestSeq.current) return;
            wearLayer(layerFrom(product, variant, size, false));
            touchHanger(cached.id);
            setTryOnState("cached", { renderId: cached.renderId });
            track("hanger_item_restored", {
              productPublicId: product.publicProductId,
              variantPublicId: variant.publicVariantId,
              authenticated: true,
            });
            return;
          } catch {
            markHangerStatus(cached.id, "expired");
            // fall through to a fresh request
          }
        } else {
          markHangerStatus(cached.id, "expired");
        }
      }

      // Fresh engine request.
      setTryOnState("requesting", { renderId: null, failureReason: null });
      track("try_on_started", {
        productPublicId: product.publicProductId,
        variantPublicId: variant.publicVariantId,
        authenticated: true,
        engineVersion: engine.engineVersion,
      });

      try {
        let render = await engine.requestTryOn({
          tryOnSessionId,
          productPublicId: product.publicProductId,
          variantPublicId: variant.publicVariantId,
          size,
          baseLayers: baseLayers.map((l) => ({
            category: l.category,
            productPublicId: l.productPublicId,
            variantPublicId: l.variantPublicId,
            assetUrl: l.assetUrl,
            thumbnailUrl: l.thumbnailUrl,
            name: l.name,
          })),
        });
        if (seq !== requestSeq.current) return;

        if (render.state === "processing") {
          setTryOnState("processing", { renderId: render.renderId });
          render = await pollRender(
            engine.getTryOnStatus,
            tryOnSessionId,
            render.renderId,
            () => seq !== requestSeq.current,
          );
          if (seq !== requestSeq.current) return;
        }

        if (render.state === "ready") {
          const activeLayer = layerFrom(product, variant, size, false);
          wearLayer(activeLayer);
          setTryOnState("ready", { renderId: render.renderId });
          const outfit = Object.fromEntries([
            ...baseLayers.map((l) => [l.category, l] as const),
            [activeLayer.category, activeLayer] as const,
          ]);
          pushHanger({
            outfit,
            id: entryId,
            productPublicId: product.publicProductId,
            variantPublicId: variant.publicVariantId,
            size,
            layers: render.layers,
            avatarProfileVersion: render.avatarProfileVersion,
            tryOnSessionId,
            renderId: render.renderId,
            renderedAssetUrl: render.renderedAssetUrl,
            thumbnailUrl: variantThumb(product),
            productName: product.name,
            generatedAt: render.generatedAt,
            engineVersion: render.engineVersion,
            status: "cached",
          });
          track("try_on_completed", {
            productPublicId: product.publicProductId,
            variantPublicId: variant.publicVariantId,
            authenticated: true,
            engineVersion: engine.engineVersion,
          });
        } else if (render.state === "unsupported") {
          setTryOnState("unsupported", { failureReason: render.failureReason });
        } else {
          setTryOnState("failed", { failureReason: render.failureReason });
          track("try_on_failed", { productPublicId: product.publicProductId, authenticated: true });
        }
      } catch (e) {
        if (seq !== requestSeq.current) return;
        setTryOnState("failed", {
          failureReason: e instanceof Error ? e.message : "The try-on engine is unavailable.",
        });
        track("try_on_failed", { productPublicId: product.publicProductId, authenticated: true });
      }
    },
    [engine, opts.avatarProfileVersion],
  );

  /** Restore a Hanger entry wholesale (product panel follows the caller). */
  const restoreEntry = useCallback(
    async (entry: HangerEntry, layersFromEntry: Partial<Record<GarmentCategory, OutfitLayer>>) => {
      const { setTryOnState, setLayers, touchHanger, markHangerStatus } = useStudioStore.getState();
      if (opts.avatarProfileVersion === null) return false;
      if (
        !isEntryRestorable(entry, {
          avatarProfileVersion: opts.avatarProfileVersion,
          engineVersion: engine.engineVersion,
        })
      ) {
        markHangerStatus(entry.id, "expired");
        return false;
      }
      const seq = ++requestSeq.current;
      setTryOnState("restoring", { renderId: entry.renderId, failureReason: null });
      try {
        await engine.restoreTryOnResult(entry.tryOnSessionId, entry.renderId);
        if (seq !== requestSeq.current) return false;
        setLayers(layersFromEntry);
        touchHanger(entry.id);
        setTryOnState("cached", { renderId: entry.renderId });
        track("hanger_item_restored", {
          productPublicId: entry.productPublicId,
          variantPublicId: entry.variantPublicId,
          authenticated: true,
        });
        return true;
      } catch {
        if (seq === requestSeq.current) {
          markHangerStatus(entry.id, "expired");
          setTryOnState("failed", {
            failureReason: "This saved look has expired — try it on again.",
          });
        }
        return false;
      }
    },
    [engine, opts.avatarProfileVersion],
  );

  return { wear, restoreEntry, engineVersion: engine.engineVersion, store };
}

function layerFrom(
  product: PublicProduct,
  variant: ProductVariant,
  size: string | null,
  locked: boolean,
): OutfitLayer {
  return {
    category: product.garmentCategory,
    productPublicId: product.publicProductId,
    variantPublicId: variant.publicVariantId,
    assetUrl: variant.garmentAssetUrl ?? product.thumbnailUrl,
    thumbnailUrl: variantThumb(product),
    name: product.name,
    price: variant.price,
    size,
    locked,
  };
}

function variantThumb(product: PublicProduct): string {
  return product.thumbnailUrl;
}

async function pollRender(
  getStatus: (sid: string, rid: string) => Promise<TryOnRender>,
  sid: string,
  rid: string,
  isStale: () => boolean,
): Promise<TryOnRender> {
  for (let i = 0; i < 30; i++) {
    await new Promise((r) => setTimeout(r, 700));
    if (isStale()) throw new Error("superseded");
    const render = await getStatus(sid, rid);
    if (render.state !== "processing") return render;
  }
  throw new Error("The try-on is taking longer than expected. Please retry.");
}
