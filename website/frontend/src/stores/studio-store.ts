import { create } from "zustand";
import type { GarmentCategory, TryOnState } from "@/integrations/mirra-api/types";
import {
  DEFAULT_HANGER_CAPACITY,
  pushHangerEntry,
  touchHangerEntry,
  type HangerEntry,
  type OutfitLayer,
} from "@/lib/hanger";
import { canTransitionTryOn } from "@/lib/state-machines/try-on";

export type { OutfitLayer } from "@/lib/hanger";

export interface StudioCartItem {
  productPublicId: string;
  variantPublicId: string;
  productName: string;
  thumbnailUrl: string;
  colorName: string;
  size: string;
  unitPrice: number;
  currency: string;
  quantity: number;
}

interface TryOnStatus {
  state: TryOnState;
  renderId: string | null;
  failureReason: string | null;
}

export interface StudioState {
  tryOnSessionId: string | null;
  activeProductId: string | null;
  activeColor: string | null;
  activeSize: string | null;
  layers: Partial<Record<GarmentCategory, OutfitLayer>>;
  tryOn: TryOnStatus;
  hanger: HangerEntry[];
  appliedLookId: string | null;
  appliedLookName: string | null;
  cart: StudioCartItem[];

  setTryOnSessionId: (id: string) => void;
  selectProduct: (productId: string) => void;
  setColor: (color: string) => void;
  setSize: (size: string) => void;
  setTryOnState: (state: TryOnState, extra?: Partial<TryOnStatus>) => void;
  wearLayer: (layer: OutfitLayer) => void;
  setLayers: (layers: Partial<Record<GarmentCategory, OutfitLayer>>) => void;
  removeLayer: (category: GarmentCategory) => void;
  unlockLayer: (category: GarmentCategory) => void;
  pushHanger: (entry: HangerEntry) => void;
  touchHanger: (id: string) => void;
  markHangerStatus: (id: string, status: HangerEntry["status"]) => void;
  applyLook: (lookId: string, lookName: string) => void;
  clearLook: () => void;
  addCartItem: (item: StudioCartItem) => void;
  setCartQuantity: (variantPublicId: string, quantity: number) => void;
  removeCartItem: (variantPublicId: string) => void;
  clearCart: () => void;
  reset: () => void;
}

const initialTryOn: TryOnStatus = { state: "idle", renderId: null, failureReason: null };

export const useStudioStore = create<StudioState>((set) => ({
  tryOnSessionId: null,
  activeProductId: null,
  activeColor: null,
  activeSize: null,
  layers: {},
  tryOn: initialTryOn,
  hanger: [],
  appliedLookId: null,
  appliedLookName: null,
  cart: [],

  setTryOnSessionId: (id) => set({ tryOnSessionId: id }),
  selectProduct: (productId) => set({ activeProductId: productId }),
  setColor: (color) => set({ activeColor: color }),
  setSize: (size) => set({ activeSize: size }),

  setTryOnState: (state, extra = {}) =>
    set((s) => {
      if (s.tryOn.state !== state && !canTransitionTryOn(s.tryOn.state, state)) {
        // Tolerate but surface unexpected jumps — the table is the contract.
        console.warn(`[try-on] unexpected transition ${s.tryOn.state} → ${state}`);
      }
      return { tryOn: { ...s.tryOn, ...extra, state } };
    }),

  wearLayer: (layer) => set((s) => ({ layers: { ...s.layers, [layer.category]: layer } })),
  setLayers: (layers) => set({ layers }),
  removeLayer: (category) =>
    set((s) => {
      const next = { ...s.layers };
      delete next[category];
      return { layers: next };
    }),
  unlockLayer: (category) =>
    set((s) => {
      const layer = s.layers[category];
      if (!layer) return s;
      return { layers: { ...s.layers, [category]: { ...layer, locked: false } } };
    }),

  pushHanger: (entry) =>
    set((s) => ({ hanger: pushHangerEntry(s.hanger, entry, DEFAULT_HANGER_CAPACITY) })),
  touchHanger: (id) => set((s) => ({ hanger: touchHangerEntry(s.hanger, id) })),
  markHangerStatus: (id, status) =>
    set((s) => ({
      hanger: s.hanger.map((e) => (e.id === id ? { ...e, status } : e)),
    })),

  applyLook: (lookId, lookName) => set({ appliedLookId: lookId, appliedLookName: lookName }),
  clearLook: () =>
    set((s) => ({
      appliedLookId: null,
      appliedLookName: null,
      layers: Object.fromEntries(
        Object.entries(s.layers).map(([k, v]) => [k, v ? { ...v, locked: false } : v]),
      ) as StudioState["layers"],
    })),

  addCartItem: (item) =>
    set((s) => {
      const current = s.cart.find((line) => line.variantPublicId === item.variantPublicId);
      if (!current) {
        return {
          cart: [
            ...s.cart,
            {
              ...item,
              quantity: Math.max(1, Math.min(10, item.quantity)),
            },
          ],
        };
      }
      return {
        cart: s.cart.map((line) =>
          line.variantPublicId === item.variantPublicId
            ? {
                ...line,
                quantity: Math.min(10, line.quantity + item.quantity),
              }
            : line,
        ),
      };
    }),
  setCartQuantity: (variantPublicId, quantity) =>
    set((s) => ({
      cart:
        quantity <= 0
          ? s.cart.filter((line) => line.variantPublicId !== variantPublicId)
          : s.cart.map((line) =>
              line.variantPublicId === variantPublicId
                ? {
                    ...line,
                    quantity: Math.max(1, Math.min(10, quantity)),
                  }
                : line,
            ),
    })),
  removeCartItem: (variantPublicId) =>
    set((s) => ({
      cart: s.cart.filter((line) => line.variantPublicId !== variantPublicId),
    })),
  clearCart: () => set({ cart: [] }),

  reset: () =>
    set({
      tryOnSessionId: null,
      activeProductId: null,
      activeColor: null,
      activeSize: null,
      layers: {},
      tryOn: initialTryOn,
      hanger: [],
      appliedLookId: null,
      appliedLookName: null,
      cart: [],
    }),
}));
