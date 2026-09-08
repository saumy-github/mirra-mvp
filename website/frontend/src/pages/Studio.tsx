import { useLocation, useNavigate } from "react-router-dom";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { StudioHeader } from "@/features/studio/components/studio-header";
import { ProductRail } from "@/features/studio/components/product-rail";
import { AvatarStage } from "@/features/studio/components/avatar-stage";
import { ProductPanel } from "@/features/studio/components/product-panel";
import { HangerBar } from "@/features/studio/components/hanger-bar";
import { CartDrawer } from "@/features/studio/components/cart-drawer";
import { SignatureLookDialog } from "@/features/studio/components/signature-look-dialog";
import { Skeleton, Spinner } from "@/components/ui/misc";
import { useAvatarProfile, useAccount } from "@/hooks/use-shopper";
import { useSignatureLookMutations, useSignatureLooks } from "@/hooks/use-signature-looks";
import { useTryOn } from "@/hooks/use-try-on";
import { getRuntimeProvider } from "@/integrations/mirra-api";
import type {
  GarmentCategory,
  PublicProduct,
  ProductVariant,
  SignatureLook,
  TryOnRender,
} from "@/integrations/mirra-api/types";
import { hangerEntryId, type HangerEntry, type OutfitLayer } from "@/lib/hanger";
import { track } from "@/lib/analytics";
import { useStudioStore } from "@/stores/studio-store";

/**
 * The Mirra studio. Avatar left, garment panel right, Hanger + Signature
 * Looks below. All data flows through the runtime provider. Adapted from
 * user-side's tenant/Shopify-embedded version; the local shortlist is for
 * comparison only because this pilot has no checkout backend.
 */
export default function Studio() {
  const navigate = useNavigate();
  const location = useLocation();
  const qc = useQueryClient();
  const api = getRuntimeProvider();

  const {
    data: account,
    isLoading: accountLoading,
    isError: accountError,
    refetch: refetchAccount,
  } = useAccount();
  const {
    data: avatar,
    isLoading: avatarLoading,
    isError: avatarError,
    refetch: refetchAvatar,
  } = useAvatarProfile(!!account);
  const {
    data: looks = [],
    isLoading: looksLoading,
    isError: looksError,
  } = useSignatureLooks(!!account);
  const { createLook, deleteLook } = useSignatureLookMutations();

  const store = useStudioStore();

  const { wear, restoreEntry } = useTryOn({ avatarProfileVersion: avatar?.version ?? null });

  const [lookDialogOpen, setLookDialogOpen] = useState(false);
  const [lookNotice, setLookNotice] = useState<string | null>(null);
  const [shortlistOpen, setShortlistOpen] = useState(false);
  const [shortlistNotice, setShortlistNotice] = useState<string | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [sessionRetrying, setSessionRetrying] = useState(false);
  const [railCollectionEmpty, setRailCollectionEmpty] = useState(false);
  const [avatarViewState, setAvatarViewState] = useState<"loading" | "ready" | "error">("loading");
  const [historyState, setHistoryState] = useState<"idle" | "loading" | "ready" | "error">(
    "loading",
  );
  const requestedLookId =
    typeof (location.state as { signatureLookId?: unknown } | null)?.signatureLookId === "string"
      ? ((location.state as { signatureLookId: string }).signatureLookId ?? null)
      : null;
  const requestedLookApplied = useRef<string | null>(null);

  // ── Guards ──
  useEffect(() => {
    if (!accountLoading && !accountError && !account) {
      navigate(`/auth/login?next=${encodeURIComponent("/studio")}`, {
        replace: true,
      });
    }
  }, [account, accountError, accountLoading, navigate]);

  useEffect(() => {
    if (!avatarLoading && !avatarError && account && !avatar) {
      navigate("/profile/avatar", { replace: true });
    }
  }, [avatar, avatarError, avatarLoading, account, navigate]);

  useEffect(() => {
    if (account) useStudioStore.getState().scopeToShopper(account.shopperId);
  }, [account]);

  // ── Try-on session + telemetry ──
  const opened = useRef(false);
  const startTryOnSession = useCallback(async () => {
    if (!account || !avatar) return;

    setSessionRetrying(true);
    setSessionError(null);
    try {
      const session = await api.createTryOnSession();
      useStudioStore.getState().setTryOnSessionId(session.tryOnSessionId);
    } catch {
      setSessionError(
        "The fitting preview could not start. You can still browse pieces while you reconnect.",
      );
    } finally {
      setSessionRetrying(false);
    }
  }, [account, avatar, api]);

  useEffect(() => {
    if (!account || !avatar || opened.current) return;
    opened.current = true;
    track("studio_opened", { authenticated: true });
    void startTryOnSession();
  }, [account, avatar, startTryOnSession]);

  // ── Active product ──
  const activeProductId = store.activeProductId;

  const {
    data: activeProduct,
    isError: activeProductError,
    refetch: refetchActiveProduct,
  } = useQuery({
    queryKey: ["product", activeProductId],
    queryFn: () => getRuntimeProvider().getProduct(activeProductId!),
    enabled: !!activeProductId,
    staleTime: 60_000,
  });

  // Fall back to the first rail product when nothing is selected yet.
  const {
    data: firstPage,
    isError: catalogueError,
    refetch: refetchCatalogue,
  } = useQuery({
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
    let cancelled = false;
    setHistoryState("loading");
    api
      .listRecentRenders()
      .then(async (renders) => {
        const s = useStudioStore.getState();
        if (s.hanger.length > 0) {
          if (!cancelled) setHistoryState("ready");
          return;
        }
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
        if (!cancelled) setHistoryState("ready");
      })
      .catch(() => {
        if (!cancelled) setHistoryState("error");
      }); // history is a convenience, never a blocker

    return () => {
      cancelled = true;
    };
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
  const restoredVariantToSkip = useRef<string | null>(null);
  useEffect(() => {
    lastWorn.current = null;
    restoredVariantToSkip.current = null;
  }, [store.tryOnSessionId]);

  useEffect(() => {
    if (!activeProduct || !activeVariant || !store.tryOnSessionId || !avatar) return;
    const sig = tryOnSelectionSignature(activeProduct, activeVariant, activeVariant.size);
    if (restoredVariantToSkip.current === activeVariant.publicVariantId) {
      restoredVariantToSkip.current = null;
      lastWorn.current = sig;
      return;
    }
    if (lastWorn.current === sig) return;

    const settleTimer = window.setTimeout(() => {
      lastWorn.current = sig;
      void wear(activeProduct, activeVariant, activeVariant.size);
    }, 220);

    return () => window.clearTimeout(settleTimer);
  }, [activeProduct, activeVariant, store.tryOnSessionId, avatar, wear]);

  // ── Handlers ──
  const onSelectProduct = useCallback((product: PublicProduct) => {
    setShortlistNotice(null);
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
      const ok = await restoreEntry(entry, entry.outfit);
      if (ok) {
        const s = useStudioStore.getState();
        restoredVariantToSkip.current = entry.variantPublicId;
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
            lastWorn.current = tryOnSelectionSignature(
              product,
              variant,
              entry.size ?? variant.size,
            );
            restoredVariantToSkip.current = null;
          }
        } catch {
          restoredVariantToSkip.current = null;
          // product gone — the figure still shows the cached render
        }
      } else if (activeProduct && activeVariant) {
        // Cached result invalid → deliberate re-render of the same look.
        lastWorn.current = null;
        void wear(activeProduct, activeVariant, activeVariant.size);
      }
    },
    [restoreEntry, activeProduct, activeVariant, qc, wear],
  );

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
        void wear(activeProduct, activeVariant, activeVariant.size);
      }
    },
    [qc, activeProduct, activeVariant, wear],
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

  // A saved look opened from Profile is applied once, after its data and the
  // try-on session are ready. Clear the transient route state after consuming it.
  useEffect(() => {
    if (
      !requestedLookId ||
      requestedLookApplied.current === requestedLookId ||
      !avatar ||
      !store.tryOnSessionId ||
      looksLoading
    ) {
      return;
    }

    requestedLookApplied.current = requestedLookId;
    const requested = looks.find((look) => look.lookId === requestedLookId);
    if (!requested) {
      setLookNotice("That Signature Look is no longer available.");
      navigate(location.pathname, { replace: true, state: null });
      return;
    }
    if (requested.avatarProfileVersion !== avatar.version) {
      setLookNotice(`"${requested.name}" was created for an older avatar version.`);
      navigate(location.pathname, { replace: true, state: null });
      return;
    }

    void onApplyLook(requested).finally(() => {
      navigate(location.pathname, { replace: true, state: null });
    });
  }, [
    avatar,
    location.pathname,
    looks,
    looksLoading,
    navigate,
    onApplyLook,
    requestedLookId,
    store.tryOnSessionId,
  ]);

  // ── Default Signature Look: applied once, on entering the studio ──
  const defaultLookApplied = useRef(false);
  useEffect(() => {
    if (defaultLookApplied.current || requestedLookId || !avatar || !store.tryOnSessionId) return;
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
  }, [looks, avatar, store.tryOnSessionId, onApplyLook, requestedLookId]);

  // ── Local shortlist (comparison only; no checkout promise) ──
  const onAddToShortlist = useCallback(() => {
    if (!activeProduct || !activeVariant) return;
    const existing = useStudioStore
      .getState()
      .cart.some((line) => line.variantPublicId === activeVariant.publicVariantId);
    if (existing) {
      setShortlistNotice(`${activeProduct.name} is already in your shortlist.`);
      return;
    }
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
    setShortlistNotice(`${activeProduct.name} was added to your shortlist.`);
    toast.success(`${activeProduct.name} added to your shortlist.`);
  }, [activeProduct, activeVariant]);

  // ── Derived ──
  const wornLayers = Object.values(store.layers).filter((l): l is OutfitLayer => !!l);
  const shortlistCount = store.cart.length;
  const otherLayers = wornLayers.filter((l) => l.category !== activeProduct?.garmentCategory);

  if (accountError || avatarError) {
    return (
      <StudioLoadFailure
        title={accountError ? "We couldn't open your Studio" : "Your avatar couldn't be loaded"}
        body="Your account is still safe. Check your connection and try loading this workspace again."
        onRetry={() => {
          if (accountError) void refetchAccount();
          else void refetchAvatar();
        }}
      />
    );
  }

  if (accountLoading || avatarLoading || !avatar) {
    return (
      <main className="grid min-h-dvh place-items-center bg-canvas">
        <div className="flex flex-col items-center gap-4">
          <Spinner className="size-6 text-muted" />
          <p className="mono-tag">[ PREPARING STUDIO ]</p>
        </div>
      </main>
    );
  }

  return (
    <div className="flex min-h-dvh flex-col bg-canvas lg:h-dvh lg:overflow-hidden">
      <StudioHeader
        accountInitial={(account?.displayName?.[0] ?? "M").toUpperCase()}
        profileImageUrl={avatar.previewAssetUrl}
        shortlistCount={shortlistCount}
        onShortlistOpen={() => setShortlistOpen(true)}
      />

      {sessionError && (
        <div
          role="alert"
          className="relative z-20 flex flex-col gap-3 bg-[#fff3df] px-4 py-3 text-sm text-[#6e4614] sm:flex-row sm:items-center sm:justify-between sm:px-5"
        >
          <span className="flex items-start gap-2.5">
            <span aria-hidden className="mt-1 size-2 shrink-0 rounded-full bg-[#c77a1a]" />
            <span>
              <strong className="font-semibold">Preview temporarily unavailable.</strong>{" "}
              {sessionError}
            </span>
          </span>
          <button
            type="button"
            onClick={() => void startTryOnSession()}
            disabled={sessionRetrying}
            className="min-h-10 shrink-0 rounded-full bg-[#6e4614] px-4 text-xs font-semibold text-white transition-opacity disabled:opacity-55"
          >
            {sessionRetrying ? "Trying again…" : "Try again"}
          </button>
        </div>
      )}

      <div className="grid flex-1 grid-cols-1 lg:min-h-0 lg:grid-cols-[minmax(0,1fr)_minmax(340px,420px)]">
        {/* Stage + rail */}
        <section className="flex min-h-0 flex-col gap-3 border-b border-line bg-surface p-3 lg:flex-row lg:border-r lg:border-b-0 lg:p-4">
          <ProductRail
            activeProductId={store.activeProductId}
            onSelect={onSelectProduct}
            onCollectionEmptyChange={setRailCollectionEmpty}
          />
          <AvatarStage
            avatar={avatar}
            layers={store.layers}
            tryOnState={store.tryOn.state}
            onMakeSignatureLook={() => setLookDialogOpen(true)}
            canMakeLook={
              wornLayers.length > 0 &&
              (store.tryOn.state === "ready" || store.tryOn.state === "cached")
            }
            tryOnSessionId={store.tryOnSessionId}
            renderSessionId={store.tryOn.renderSessionId}
            renderId={store.tryOn.renderId}
            onAvatarViewStateChange={setAvatarViewState}
          />
        </section>

        {/* Product panel */}
        {railCollectionEmpty ? (
          <ProductPanelState
            title="No pieces in this collection"
            body="Choose another collection to keep browsing without changing the look on your avatar."
          />
        ) : activeProduct ? (
          <ProductPanel
            product={activeProduct}
            activeColor={store.activeColor}
            activeSize={activeVariant?.size ?? null}
            otherLayers={otherLayers}
            onColorChange={onColorChange}
            onSizeChange={onSizeChange}
            onAddToShortlist={onAddToShortlist}
            onUnlockLayer={(cat) => useStudioStore.getState().unlockLayer(cat)}
            tryOnState={store.tryOn.state}
            tryOnFailureReason={store.tryOn.failureReason}
            showPreviewFeedback={avatarViewState === "ready"}
            onRetryTryOn={() => {
              if (activeVariant) {
                lastWorn.current = null;
                void wear(activeProduct, activeVariant, activeVariant.size);
              }
            }}
            addToShortlistBusy={false}
            shortlistNotice={shortlistNotice}
          />
        ) : activeProductError || catalogueError ? (
          <ProductPanelState
            tone="error"
            title="The collection didn't load"
            body="The Studio is still here. Retry the catalogue without losing your current look."
            actionLabel="Try again"
            onAction={() => {
              void refetchCatalogue();
              if (activeProductId) void refetchActiveProduct();
            }}
          />
        ) : firstPage && firstPage.items.length === 0 ? (
          <ProductPanelState
            title="No pieces are published yet"
            body="When garments are ready, they will appear in the collection beside your avatar."
          />
        ) : (
          <div className="space-y-5 bg-paper p-7 lg:p-9" aria-label="Loading selected piece">
            <div className="grid grid-cols-[72px_1fr] gap-4">
              <Skeleton className="h-22 w-18 rounded-xl" />
              <div className="space-y-3 pt-1">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-7 w-full" />
                <Skeleton className="h-4 w-2/5" />
              </div>
            </div>
            <Skeleton className="h-px w-full" />
            <Skeleton className="h-12 w-full rounded-xl" />
          </div>
        )}
      </div>

      {lookNotice && (
        <div
          role="status"
          className="flex items-center justify-between gap-4 border-t border-line bg-mist px-5 py-2 text-xs text-ink-soft"
        >
          {lookNotice}
          <button
            type="button"
            onClick={() => setLookNotice(null)}
            aria-label="Dismiss"
            className="text-muted hover:text-ink"
          >
            ×
          </button>
        </div>
      )}

      <HangerBar
        entries={store.hanger}
        currentRenderId={store.tryOn.renderId}
        looks={looks}
        appliedLookId={store.appliedLookId}
        historyState={historyState}
        looksLoading={looksLoading}
        looksError={looksError}
        onRestore={onRestoreEntry}
        onApplyLook={onApplyLook}
        onRemoveLook={onRemoveLook}
      />

      <CartDrawer
        open={shortlistOpen}
        onClose={() => setShortlistOpen(false)}
        items={store.cart}
        onRemove={(variantPublicId) => useStudioStore.getState().removeCartItem(variantPublicId)}
      />

      <SignatureLookDialog
        open={lookDialogOpen}
        onClose={() => setLookDialogOpen(false)}
        onCreate={onCreateLook}
        busy={createLook.isPending}
        layerNames={wornLayers.map((l) => l.name)}
      />
    </div>
  );
}

function StudioLoadFailure({
  title,
  body,
  onRetry,
}: {
  title: string;
  body: string;
  onRetry: () => void;
}) {
  return (
    <main className="grid min-h-dvh place-items-center bg-canvas px-5">
      <div className="w-full max-w-md border-y border-line py-10 text-center">
        <p className="font-mono text-[10px] tracking-[0.16em] text-muted uppercase">Mirra Studio</p>
        <h1 className="mt-4 text-2xl font-semibold tracking-[-0.035em] text-ink">{title}</h1>
        <p className="mx-auto mt-3 max-w-sm text-sm leading-6 text-muted">{body}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-6 min-h-11 rounded-full bg-ink px-5 text-sm font-semibold text-canvas transition-opacity hover:opacity-85"
        >
          Try again
        </button>
      </div>
    </main>
  );
}

function ProductPanelState({
  title,
  body,
  tone = "empty",
  actionLabel,
  onAction,
}: {
  title: string;
  body: string;
  tone?: "empty" | "error";
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <aside className="flex min-h-64 items-center bg-paper px-7 py-10 lg:h-full lg:px-9">
      <div className="max-w-sm">
        <span
          aria-hidden
          className={`block h-px w-12 ${tone === "error" ? "bg-error" : "bg-line-strong"}`}
        />
        <h2 className="mt-5 text-xl font-semibold tracking-[-0.03em] text-ink">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-muted">{body}</p>
        {actionLabel && onAction && (
          <button
            type="button"
            onClick={onAction}
            className="mt-5 min-h-11 rounded-full bg-ink px-5 text-sm font-semibold text-canvas transition-opacity hover:opacity-85"
          >
            {actionLabel}
          </button>
        )}
      </div>
    </aside>
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

function tryOnSelectionSignature(
  product: PublicProduct,
  variant: ProductVariant,
  size: string | null,
) {
  return [
    variant.publicVariantId,
    size ?? "",
    product.tryOnEligible ? "eligible" : "unsupported",
    variant.tryOnEligible ? "eligible" : "unsupported",
    variant.assetStatus,
  ].join("::");
}
