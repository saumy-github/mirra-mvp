import type { HangerItem, SignatureLook } from "../types";
import { RecentTryOns } from "./recent-try-ons";
import { SignatureLooks } from "./signature-looks";
import { CartSummary } from "./cart-summary";

/**
 * The persistent tray along the bottom: session history on the left, saved
 * bases in the middle, the money on the right. It stays put while the rest of
 * the room changes — everything in it is already rendered, so coming back to
 * a piece costs nothing.
 */
export function HangerTray({
  entries,
  currentRenderId,
  looks,
  appliedLookId,
  canCreateLook,
  currency,
  selectedPiecePrice,
  outfitPrice,
  outfitPieceCount,
  cartCount,
  checkoutBusy,
  checkoutDisabled,
  onRestore,
  onRemoveEntry,
  onApplyLook,
  onRemoveLook,
  onCreateLook,
  onAddSelected,
  onBuyTheLook,
  onViewCart,
}: {
  entries: HangerItem[];
  currentRenderId: string | null;
  looks: SignatureLook[];
  appliedLookId: string | null;
  canCreateLook: boolean;
  currency: string;
  selectedPiecePrice: number;
  outfitPrice: number;
  outfitPieceCount: number;
  cartCount: number;
  checkoutBusy: boolean;
  checkoutDisabled: boolean;
  onRestore: (entry: HangerItem) => void;
  onRemoveEntry: (entry: HangerItem) => void;
  onApplyLook: (look: SignatureLook) => void;
  onRemoveLook: (look: SignatureLook) => void;
  onCreateLook: () => void;
  onAddSelected: () => void;
  onBuyTheLook: () => void;
  onViewCart: () => void;
}) {
  return (
    <footer className="flex shrink-0 flex-col gap-6 border-t border-hairline bg-vellum px-5 py-5 lg:h-40 lg:flex-row lg:items-center lg:gap-9 lg:px-8 lg:py-0">
      <div className="min-w-0 lg:flex-1">
        <RecentTryOns
          entries={entries}
          currentRenderId={currentRenderId}
          onRestore={onRestore}
          onRemove={onRemoveEntry}
        />
      </div>

      <span aria-hidden className="hidden h-20 w-px shrink-0 bg-hairline lg:block" />

      <div className="min-w-0 lg:w-auto lg:shrink-0">
        <SignatureLooks
          looks={looks}
          appliedLookId={appliedLookId}
          canCreate={canCreateLook}
          onApply={onApplyLook}
          onRemove={onRemoveLook}
          onCreate={onCreateLook}
        />
      </div>

      <span aria-hidden className="hidden h-20 w-px shrink-0 bg-hairline lg:block" />

      <CartSummary
        currency={currency}
        selectedPiecePrice={selectedPiecePrice}
        outfitPrice={outfitPrice}
        outfitPieceCount={outfitPieceCount}
        cartCount={cartCount}
        busy={checkoutBusy}
        disabled={checkoutDisabled}
        onAddSelected={onAddSelected}
        onBuyTheLook={onBuyTheLook}
        onViewCart={onViewCart}
      />
    </footer>
  );
}
