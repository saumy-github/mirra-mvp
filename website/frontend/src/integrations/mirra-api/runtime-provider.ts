import type {
  AnalyticsEvent,
  AvatarJob,
  AvatarProfile,
  MeasurementKey,
  ProductListPage,
  PublicProduct,
  ShopperAccount,
  SignatureLook,
  SignatureLookLayer,
  TryOnRender,
  TryOnSession,
} from "./types";

/**
 * The single seam between the UI and the backend. UI code depends only on
 * this interface — never on fixtures, never on fetch directly. Maps onto
 * the `catalog`, `auth`, `avatars`, `tryon`, `signature_looks`, and
 * `analytics` services in website/backend-structure-plan.md.
 */
export interface MirraRuntimeProvider {
  // Catalogue
  listProducts(opts?: {
    category?: string;
    cursor?: string;
    limit?: number;
  }): Promise<ProductListPage>;
  getProduct(productId: string): Promise<PublicProduct>;

  // Auth — also covers guest sessions (isGuest: true on the returned account)
  signUp(input: {
    displayName: string;
    email: string;
    password: string;
    acceptedTerms: boolean;
  }): Promise<ShopperAccount>;
  login(input: { email: string; password: string }): Promise<ShopperAccount>;
  loginWithGoogle(): Promise<ShopperAccount>;
  continueAsGuest(): Promise<ShopperAccount>;
  logout(): Promise<void>;
  getCurrentShopper(): Promise<ShopperAccount | null>;
  requestPasswordReset(email: string): Promise<void>;
  verifyEmail(code: string): Promise<ShopperAccount>;
  updateConsents(consents: Partial<ShopperAccount["consents"]>): Promise<ShopperAccount>;
  deleteAccount(): Promise<void>;

  // Avatar — the CLO3D seam
  /** Triggers generation from the shopper's already-saved measurements —
   * no photo capture involved. */
  generateAvatar(): Promise<AvatarJob>;
  getAvatarJob(jobId: string): Promise<AvatarJob>;
  getAvatarProfile(): Promise<AvatarProfile | null>;
  updateMeasurements(
    changes: Partial<Record<MeasurementKey, number>>,
    opts?: {
      resetEstimates?: boolean;
      unitsPreference?: "metric" | "imperial";
      /** Only meaningful the first time a shopper has no profile yet. */
      gender?: "male" | "female";
      accuracy?: "accurate" | "approx";
    },
  ): Promise<AvatarProfile>;
  deleteAvatarProfile(): Promise<void>;

  // Try-on — also routes through the CLO3D seam
  createTryOnSession(): Promise<TryOnSession>;
  requestTryOn(input: {
    tryOnSessionId: string;
    productPublicId: string;
    variantPublicId: string;
    size: string | null;
    baseLayers?: SignatureLookLayer[];
  }): Promise<TryOnRender>;
  getTryOnRender(tryOnSessionId: string, renderId: string): Promise<TryOnRender>;
  /** Recent renders for this user — seeds the Hanger. */
  listRecentRenders(): Promise<TryOnRender[]>;

  // Signature Looks
  listSignatureLooks(): Promise<SignatureLook[]>;
  createSignatureLook(input: {
    name: string;
    layers: SignatureLookLayer[];
    avatarProfileVersion: number;
    thumbnailUrl: string | null;
    isDefault?: boolean;
  }): Promise<SignatureLook>;
  updateSignatureLook(
    lookId: string,
    patch: Partial<Pick<SignatureLook, "name" | "isDefault" | "layers" | "thumbnailUrl">>,
  ): Promise<SignatureLook>;
  deleteSignatureLook(lookId: string): Promise<void>;

  // Analytics
  trackEvent(event: AnalyticsEvent): Promise<void>;
}
