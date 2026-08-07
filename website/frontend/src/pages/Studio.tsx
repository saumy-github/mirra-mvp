import { useNavigate } from "react-router-dom";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { MirraHeader } from "@/features/studio/components/mirra-header";
import { CollectionRail } from "@/features/studio/components/collection-rail";
import { TryOnStage } from "@/features/studio/components/try-on-stage";
import { ProductDecisionPanel } from "@/features/studio/components/product-decision-panel";
import { HangerTray } from "@/features/studio/components/hanger-tray";
import { CartDrawer } from "@/features/studio/components/cart-drawer";
import { SignatureLookDialog } from "@/features/studio/components/signature-look-dialog";
import { lookTotal, type Product } from "@/features/studio/types";
import { Skeleton, Spinner } from "@/components/ui/misc";
import { useAvatarProfile, useAccount } from "@/hooks/use-shopper";
import { useSignatureLookMutations, useSignatureLooks } from "@/hooks/use-signature-looks";
import { useTryOn } from "@/hooks/use-try-on";
import { getRuntimeProvider } from "@/integrations/mirra-api";
import type {
  GarmentCategory,
  PublicProduct,
  SignatureLook,
  TryOnRender,
} from "@/integrations/mirra-api/types";
import { hangerEntryId, type HangerEntry, type OutfitLayer } from "@/lib/hanger";
import { track } from "@/lib/analytics";
import { useStudioStore } from "@/stores/studio-store";

/**
 * The Mirra fitting room: collection rail, try-on stage, decision panel, and
 * The Hanger along the bottom. All data flows through the runtime provider —
 * the try-on engine itself sits behind `useTryOn`, and the stage only ever
 * renders what that engine hands back.
 *
 * Cart handoff to a merchant is replaced with a local cart (no real checkout
 * backend exists yet for this pilot; "Checkout" surfaces an honest toast
 * instead of a dead link).
 */
export default function Studio() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const api = getRuntimeProvider();

  const { data: account, isLoading: accountLoading } = useAccount();
  const { data: avatar, isLoading: avatarLoading } = useAvatarProfile(!!account);
  const { data: looks = [] } = useSignatureLooks(!!account);
  const { createLook, deleteLook } = useSignatureLookMutations();

  const store = useStudioStore();

  const tryOn = useTryOn({ avatarProfileVersion: avatar?.version ?? null });

  const [lookDialogOpen, setLookDialogOpen] = useState(false);
  const [lookNotice, setLookNotice] = useState<string | null>(null);
  const [cartOpen, setCartOpen] = useState(false);
  const [cartError, setCartError] = useState<string | null>(null);

  // ── Guards ──
  useEffect(() => {
    if (!accountLoading && !account) {
      navigate(`/auth/login?next=${encodeURIComponent("/studio")}`, {
        replace: true,
      });
    }
  }, [account, accountLoading, navigate]);

  useEffect(() => {
    if (!avatarLoading && account && !avatar) {
      navigate("/onboarding/avatar", { replace: true });
    }
  }, [avatar, avatarLoading, account, navigate]);

  // ── Try-on session + telemetry ──
  const opened = useRef(false);
  useEffect(() => {
    if (!account || !avatar || opened.current) return;
    opened.current = true;
    track("studio_opened", { authenticated: true });
    api.createTryOnSession().then((s) => {
      useStudioStore.getState().setTryOnSessionId(s.tryOnSessionId);
    });
  }, [account, avatar, api]);

  // ── Active product ──
  const activeProductId = store.activeProductId;

  const { data: activeProduct } = useQuery({
    queryKey: ["product", activeProductId],
    queryFn: () => getRuntimeProvider().getProduct(activeProductId!),
    enabled: !!activeProductId,
    staleTime: 60_000,
  });

  // Fall back to the first rail product when nothing is selected yet.
  const { data: firstPage } = useQuery({
    queryKey: ["rail", "all", "0"],
    queryFn: () => getRuntimeProvider().listProducts({ limit: 10 }),
    staleTime: 60_000,
  });
  useEffect(() => {
    if (!activeProductId && firstPage?.items[0]) {
      useStudioStore.getState().selectProduct(firstPage.items[0].publicProductId);
    }
  }, [activeProductId, firstPage]);

  // Initial variant once a product loads.
  const appliedInitialVariant = useRef<string | null>(null);
  useEffect(() => {
    if (!activeProduct || appliedInitialVariant.current === activeProduct.publicProductId) return;
    appliedInitialVariant.current = activeProduct.publicProductId;
    const s = useStudioStore.getState();
    const fallback = activeProduct.variants.find((v) => v.inStock) ?? activeProduct.variants[0];
    if (fallback) {
      s.setColor(fallback.colorName);
      s.setSize(fallback.size);
    }
  }, [activeProduct]);

  // ── Seed the Hanger from prior session history ──
  const seeded = useRef(false);
  useEffect(() => {
    if (seeded.current || !account || !avatar) return;
    seeded.current = true;
    api
      .listRecentRenders()
      .then(async (renders) => {
        const s = useStudioStore.getState();
        if (s.hanger.length > 0) return;
        for (const render of renders.slice(0, 5).reverse()) {
          const outfit = await outfitFromRender(render, qc);
          const active = outfit[productCategoryOf(render, outfit)] ?? Object.values(outfit)[0];
          if (!active) continue;
          s.pushHanger({
            id: hangerEntryId(
              render.productPublicId,
              render.variantPublicId,
              render.size,
              render.layers,
            ),
            productPublicId: render.productPublicId,
            variantPublicId: render.variantPublicId,
            size: render.size,
            layers: render.layers,
            avatarProfileVersion: render.avatarProfileVersion,
            tryOnSessionId: render.tryOnSessionId,
            renderId: render.renderId,
            renderedAssetUrl: render.renderedAssetUrl,
            thumbnailUrl: active.thumbnailUrl,
            productName: active.name,
            generatedAt: render.generatedAt,
            engineVersion: render.engineVersion,
            status: "cached",
            outfit,
          });
        }
      })
      .catch(() => undefined); // history is a convenience, never a blocker
  }, [account, avatar, api, qc]);

  // ── Try-on when selection settles ──
  const activeVariant = useMemo(() => {
    if (!activeProduct) return null;
    const color = store.activeColor ?? activeProduct.variants[0]?.colorName;
    const candidates = activeProduct.variants.filter((v) => v.colorName === color);
    return (
      candidates.find((v) => v.size === store.activeSize) ??
      candidates.find((v) => v.inStock) ??
      candidates[0] ??
      null
    );
  }, [activeProduct, store.activeColor, store.activeSize]);

  const lastWorn = useRef<string | null>(null);
  useEffect(() => {
    if (!activeProduct || !activeVariant || !store.tryOnSessionId || !avatar) return;
    const sig = `${activeVariant.publicVariantId}::${activeVariant.size}`;
    if (lastWorn.current === sig) return;
    lastWorn.current = sig;
    void tryOn.wear(activeProduct, activeVariant, activeVariant.size);
  }, [activeProduct, activeVariant, store.tryOnSessionId, avatar, tryOn]);

  // ── Handlers ──
  const onSelectProduct = useCallback((product: PublicProduct) => {
    const s = useStudioStore.getState();
    s.selectProduct(product.publicProductId);
    // Preserve size where compatible, otherwise fall to first in-stock.
    const sameSize = product.variants.find((v) => v.size === s.activeSize && v.inStock);
    const v = sameSize ?? product.variants.find((x) => x.inStock) ?? product.variants[0];
    if (v) {
      s.setColor(v.colorName);
      s.setSize(v.size);
    }
    track("product_selected", {
      productPublicId: product.publicProductId,
      authenticated: true,
    });
  }, []);

  const onColorChange = useCallback(
    (color: string) => {
      const s = useStudioStore.getState();
      s.setColor(color);
      const v = activeProduct?.variants.find(
        (x) => x.colorName === color && x.size === s.activeSize && x.inStock,
      );
      if (!v) {
        const fallback = activeProduct?.variants.find((x) => x.colorName === color && x.inStock);
        if (fallback) s.setSize(fallback.size);
      }
      track("variant_selected", {
        productPublicId: activeProduct?.publicProductId,
        authenticated: true,
      });
    },
    [activeProduct],
  );

  const onSizeChange = useCallback(
    (size: string) => {
      useStudioStore.getState().setSize(size);
      track("size_selected", {
        productPublicId: activeProduct?.publicProductId,
        authenticated: true,
      });
    },
    [activeProduct],
  );

  const onRestoreEntry = useCallback(
    async (entry: HangerEntry) => {
      if (!entry.outfit) return;
      const ok = await tryOn.restoreEntry(entry, entry.outfit);
      if (ok) {
        const s = useStudioStore.getState();
        s.selectProduct(entry.productPublicId);
        try {
          const product = await qc.fetchQuery({
            queryKey: ["product", entry.productPublicId],
            queryFn: () => getRuntimeProvider().getProduct(entry.productPublicId),
            staleTime: 60_000,
          });
          const variant = product.variants.find((v) => v.publicVariantId === entry.variantPublicId);
          if (variant) {
            s.setColor(variant.colorName);
            s.setSize(entry.size ?? variant.size);
            // The restored look is already on the figure — don't re-request it.
            lastWorn.current = `${variant.publicVariantId}::${entry.size ?? variant.size}`;
          }
        } catch {
          // product gone — the figure still shows the cached render
        }
      } else if (activeProduct && activeVariant) {
        // Cached result invalid → deliberate re-render of the same look.
        lastWorn.current = null;
        void tryOn.wear(activeProduct, activeVariant, activeVariant.size);
      }
    },
    [tryOn, activeProduct, activeVariant, qc],
  );

  const onRemoveEntry = useCallback((entry: HangerEntry) => {
    useStudioStore.getState().removeHanger(entry.id);
  }, []);

  const onApplyLook = useCallback(
    async (look: SignatureLook) => {
      const s = useStudioStore.getState();
      const enriched: Partial<Record<GarmentCategory, OutfitLayer>> = {};
      for (const layer of look.layers) {
        try {
          const product = await qc.fetchQuery({
            queryKey: ["product", layer.productPublicId],
            queryFn: () => getRuntimeProvider().getProduct(layer.productPublicId),
            staleTime: 60_000,
          });
          const variant =
            product.variants.find((v) => v.publicVariantId === layer.variantPublicId) ??
            product.variants[0];
          enriched[layer.category] = {
            category: layer.category,
            productPublicId: product.publicProductId,
            variantPublicId: variant.publicVariantId,
            assetUrl: layer.assetUrl,
            thumbnailUrl: layer.thumbnailUrl,
            name: layer.name,
            price: variant.price,
            size: variant.size,
            locked: true,
          };
        } catch {
          // Product no longer in the catalogue — the layer stays out.
        }
      }
      if (Object.keys(enriched).length === 0) {
        setLookNotice(
          `"${look.name}" uses pieces that are no longer in the catalogue, so it can't be worn here.`,
        );
        return;
      }
      setLookNotice(null);
      s.setLayers(enriched);
      s.applyLook(look.lookId, look.name);
      track("signature_look_applied", { authenticated: true });
      // Re-drape the active garment over the locked base.
      if (activeProduct && activeVariant) {
        lastWorn.current = null;
        void tryOn.wear(activeProduct, activeVariant, activeVariant.size);
      }
    },
    [qc, activeProduct, activeVariant, tryOn],
  );

  const onCreateLook = useCallback(
    (name: string, setAsDefault: boolean) => {
      if (!avatar) return;
      const layers = Object.values(store.layers).filter((l): l is OutfitLayer => !!l);
      createLook.mutate(
        {
          name,
          isDefault: setAsDefault,
          avatarProfileVersion: avatar.version,
          thumbnailUrl: layers[0]?.thumbnailUrl ?? null,
          layers: layers.map((l) => ({
            category: l.category,
            productPublicId: l.productPublicId,
            variantPublicId: l.variantPublicId,
            assetUrl: l.assetUrl,
            thumbnailUrl: l.thumbnailUrl,
            name: l.name,
          })),
        },
        {
          onSuccess: (look) => {
            setLookDialogOpen(false);
            useStudioStore.getState().applyLook(look.lookId, look.name);
            track("signature_look_created", { authenticated: true });
            toast.success(`"${look.name}" saved as a Signature Look.`);
          },
        },
      );
    },
    [avatar, store.layers, createLook],
  );

  const onRemoveLook = useCallback(
    (look: SignatureLook) => {
      deleteLook.mutate(look.lookId, {
        onSuccess: () => {
          const s = useStudioStore.getState();
          if (s.appliedLookId === look.lookId) s.clearLook();
          track("signature_look_removed", { authenticated: true });
        },
      });
    },
    [deleteLook],
  );

  // ── Default Signature Look: applied once, on entering the studio ──
  const defaultLookApplied = useRef(false);
  useEffect(() => {
    if (defaultLookApplied.current || !avatar || !store.tryOnSessionId) return;
    const s = useStudioStore.getState();
    if (s.appliedLookId || Object.keys(s.layers).length > 0) {
      defaultLookApplied.current = true;
      return;
    }
    const def = looks.find((l) => l.isDefault && l.avatarProfileVersion === avatar.version);
    if (def) {
      defaultLookApplied.current = true;
      void onApplyLook(def);
    }
  }, [looks, avatar, store.tryOnSessionId, onApplyLook]);

  // ── Cart (local only — no checkout backend exists yet for this pilot) ──
  const addProductToCart = useCallback((product: PublicProduct, size?: string | null) => {
    const variant =
      product.variants.find((v) => v.size === size && v.inStock) ??
      product.variants.find((v) => v.inStock) ??
      product.variants[0];
    if (!variant) return null;
    useStudioStore.getState().addCartItem({
      productPublicId: product.publicProductId,
      variantPublicId: variant.publicVariantId,
      productName: product.name,
      thumbnailUrl: product.thumbnailUrl,
      colorName: variant.colorName,
      size: variant.size,
      unitPrice: variant.price,
      currency: variant.currency,
      quantity: 1,
    });
    return variant;
  }, []);

  const onAddToCart = useCallback(() => {
    if (!activeProduct || !activeVariant) return;
    setCartError(null);
    useStudioStore.getState().addCartItem({
      productPublicId: activeProduct.publicProductId,
      variantPublicId: activeVariant.publicVariantId,
      productName: activeProduct.name,
      thumbnailUrl: activeProduct.thumbnailUrl,
      colorName: activeVariant.colorName,
      size: activeVariant.size,
      unitPrice: activeVariant.price,
      currency: activeVariant.currency,
      quantity: 1,
    });
    toast.success(`${activeProduct.name} added to your cart.`);
    track("add_to_cart_clicked", {
      productPublicId: activeProduct.publicProductId,
      variantPublicId: activeVariant.publicVariantId,
      authenticated: true,
    });
  }, [activeProduct, activeVariant]);

  /** Add a suggested piece straight to the bag without leaving the stage. */
  const onAddSuggestion = useCallback(
    (product: PublicProduct) => {
      setCartError(null);
      const variant = addProductToCart(product);
      if (!variant) return;
      toast.success(`${product.name} added to your cart.`);
      track("add_to_cart_clicked", {
        productPublicId: product.publicProductId,
        variantPublicId: variant.publicVariantId,
        authenticated: true,
      });
    },
    [addProductToCart],
  );

  /**
   * Buy every garment currently on the figure, not just the selected one.
   * Each layer is resolved back to its catalogue product so the bag line
   * carries a real colour, size and price rather than the layer's summary.
   */
  const onBuyTheLook = useCallback(async () => {
    const worn = Object.values(useStudioStore.getState().layers).filter(
      (l): l is OutfitLayer => !!l,
    );
    if (worn.length === 0) return;
    setCartError(null);

    let added = 0;
    for (const layer of worn) {
      try {
        const product = await qc.fetchQuery({
          queryKey: ["product", layer.productPublicId],
          queryFn: () => getRuntimeProvider().getProduct(layer.productPublicId),
          staleTime: 60_000,
        });
        if (addProductToCart(product, layer.size)) added += 1;
      } catch {
        // Piece has left the catalogue — the rest of the look still goes in.
      }
    }

    if (added === 0) {
      toast.error("None of these pieces are available to buy right now.");
      return;
    }
    toast.success(`The look — ${added} ${added === 1 ? "piece" : "pieces"} — added to your cart.`);
    track("add_to_cart_clicked", {
      productPublicId: activeProduct?.publicProductId,
      authenticated: true,
    });
  }, [qc, addProductToCart, activeProduct]);

  const onCheckoutCart = useCallback(() => {
    const cart = useStudioStore.getState().cart;
    if (cart.length === 0) return;
    setCartError(null);
    useStudioStore.getState().clearCart();
    setCartOpen(false);
    toast.info("Checkout isn't live in this preview yet — your picks were saved to this session.");
  }, []);

  // ── Derived ──
  const wornPieces = Object.values(store.layers).filter((l): l is OutfitLayer => !!l);
  const cartCount = store.cart.reduce((sum, line) => sum + line.quantity, 0);
  const selectedPiecePrice = activeVariant?.price ?? activeProduct?.price ?? 0;
  const selectedPieceCurrency = activeVariant?.currency ?? activeProduct?.currency ?? "INR";
  const otherPieces = wornPieces.filter((l) => l.category !== activeProduct?.garmentCategory);

  if (accountLoading || avatarLoading || !avatar) {
    return (
      <main className="studio-shell grid min-h-dvh place-items-center bg-bone">
        <div className="flex flex-col items-center gap-5">
          <Spinner className="size-4 text-ash" />
          <p className="eyebrow">Preparing your fitting room</p>
        </div>
      </main>
    );
  }

  return (
    <div className="studio-shell flex min-h-dvh flex-col bg-atelier lg:h-dvh lg:overflow-hidden">
      <MirraHeader
        accountInitial={(account?.displayName?.[0] ?? "M").toUpperCase()}
        profileImageUrl={avatar.previewAssetUrl}
        cartCount={cartCount}
        merchant={(activeProduct as Product | undefined)?.merchant ?? null}
        onCartOpen={() => setCartOpen(true)}
      />

      {/*
        DOM order is the mobile reading order — stage, then the decision, then
        discovery. The desktop grid places the rail back on the left.
      */}
      <div className="studio-regions flex-1">
        <div className="studio-region-stage flex min-h-0 flex-col">
          <TryOnStage
            avatar={avatar}
            pieces={wornPieces}
            tryOnState={store.tryOn.state}
            failureReason={store.tryOn.failureReason}
            onRetry={() => {
              if (activeProduct && activeVariant) {
                lastWorn.current = null;
                void tryOn.wear(activeProduct, activeVariant, activeVariant.size);
              }
            }}
            onMakeSignatureLook={() => setLookDialogOpen(true)}
            canMakeLook={wornPieces.length > 0}
          />
        </div>

        <div className="studio-region-panel flex min-h-0 flex-col">
          {activeProduct ? (
            <ProductDecisionPanel
              product={activeProduct}
              activeVariant={activeVariant}
              activeColor={store.activeColor}
              tryOnState={store.tryOn.state}
              otherPieces={otherPieces}
              addToCartBusy={false}
              onColorChange={onColorChange}
              onSizeChange={onSizeChange}
              onAddToCart={onAddToCart}
              onSelectProduct={onSelectProduct}
              onAddProduct={onAddSuggestion}
              onUnlockPiece={(category) => useStudioStore.getState().unlockLayer(category)}
            />
          ) : (
            <div className="space-y-5 border-hairline bg-vellum px-8 py-9 lg:border-l">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-9 w-3/4" />
              <Skeleton className="h-5 w-1/3" />
              <Skeleton className="h-28 w-full" />
            </div>
          )}
        </div>

        <div className="studio-region-rail flex min-h-0 flex-col">
          <CollectionRail
            activeProductId={activeProduct?.publicProductId ?? null}
            onSelect={onSelectProduct}
          />
        </div>
      </div>

      {lookNotice && (
        <div
          role="status"
          className="flex items-center justify-between gap-4 border-t border-hairline bg-bone px-5 py-2.5 text-[12px] text-slate lg:px-8"
        >
          {lookNotice}
          <button
            type="button"
            onClick={() => setLookNotice(null)}
            aria-label="Dismiss"
            className="text-ash transition-colors hover:text-graphite"
          >
            ×
          </button>
        </div>
      )}

      <HangerTray
        entries={store.hanger}
        currentRenderId={store.tryOn.renderId}
        looks={looks}
        appliedLookId={store.appliedLookId}
        canCreateLook={wornPieces.length > 0}
        currency={selectedPieceCurrency}
        selectedPiecePrice={selectedPiecePrice}
        outfitPrice={lookTotal(wornPieces)}
        outfitPieceCount={wornPieces.length}
        cartCount={cartCount}
        checkoutBusy={false}
        checkoutDisabled={!activeProduct || !activeVariant?.inStock}
        onRestore={onRestoreEntry}
        onRemoveEntry={onRemoveEntry}
        onApplyLook={onApplyLook}
        onRemoveLook={onRemoveLook}
        onCreateLook={() => setLookDialogOpen(true)}
        onAddSelected={onAddToCart}
        onBuyTheLook={() => void onBuyTheLook()}
        onViewCart={() => setCartOpen(true)}
      />

      <CartDrawer
        open={cartOpen}
        onClose={() => setCartOpen(false)}
        items={store.cart}
        onSetQuantity={(variantPublicId, quantity) =>
          useStudioStore.getState().setCartQuantity(variantPublicId, quantity)
        }
        onRemove={(variantPublicId) => useStudioStore.getState().removeCartItem(variantPublicId)}
        onCheckout={onCheckoutCart}
        checkoutBusy={false}
        checkoutError={cartError}
      />

      <SignatureLookDialog
        open={lookDialogOpen}
        onClose={() => setLookDialogOpen(false)}
        onCreate={onCreateLook}
        busy={createLook.isPending}
        layerNames={wornPieces.map((l) => l.name)}
      />
    </div>
  );
}

// ── helpers ──

async function outfitFromRender(
  render: TryOnRender,
  qc: ReturnType<typeof useQueryClient>,
): Promise<Partial<Record<GarmentCategory, OutfitLayer>>> {
  const outfit: Partial<Record<GarmentCategory, OutfitLayer>> = {};
  for (const [category, layer] of Object.entries(render.layers)) {
    if (!layer) continue;
    try {
      const product = await qc.fetchQuery({
        queryKey: ["product", layer.productPublicId],
        queryFn: () => getRuntimeProvider().getProduct(layer.productPublicId),
        staleTime: 60_000,
      });
      const variant =
        product.variants.find((v) => v.publicVariantId === layer.variantPublicId) ??
        product.variants[0];
      outfit[category as GarmentCategory] = {
        category: category as GarmentCategory,
        productPublicId: product.publicProductId,
        variantPublicId: variant.publicVariantId,
        assetUrl: layer.assetUrl,
        thumbnailUrl: product.thumbnailUrl,
        name: product.name,
        price: variant.price,
        size: layer.productPublicId === render.productPublicId ? render.size : variant.size,
        locked: false,
      };
    } catch {
      // Product unpublished since the render — leave that layer out.
    }
  }
  return outfit;
}

function productCategoryOf(
  render: TryOnRender,
  outfit: Partial<Record<GarmentCategory, OutfitLayer>>,
): GarmentCategory {
  for (const [cat, layer] of Object.entries(outfit)) {
    if (layer?.productPublicId === render.productPublicId) return cat as GarmentCategory;
  }
  return (Object.keys(outfit)[0] as GarmentCategory) ?? "top";
}
