import type {
  AnalyticsEvent,
  AvatarJob,
  AvatarProfile,
  CaptureSession,
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
 * the `catalog`, `auth`, `capture`, `avatars`, `tryon`, `signature_looks`,
 * and `analytics` services in website/backend-structure-plan.md.
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

  // Capture / pairing
  createCaptureSession(): Promise<CaptureSession>;
  getCaptureSession(sessionId: string): Promise<CaptureSession>;
  getCaptureSessionByToken(token: string): Promise<CaptureSession>;
  resolveManualCode(code: string): Promise<{ token: string }>;
  pairCaptureSession(token: string): Promise<CaptureSession>;
  giveCaptureConsent(token: string): Promise<CaptureSession>;
  submitCaptureAsset(
    token: string,
    stepId: string,
    payload: { mimeType: string; byteSize: number; width: number; height: number },
  ): Promise<CaptureSession>;
  completeCapture(token: string): Promise<CaptureSession>;
  cancelCaptureSession(sessionId: string): Promise<CaptureSession>;

  // Avatar — the CLO3D seam
  getAvatarJob(jobId: string): Promise<AvatarJob>;
  getAvatarProfile(): Promise<AvatarProfile | null>;
  updateMeasurements(
    changes: Partial<Record<MeasurementKey, number>>,
    opts?: { resetEstimates?: boolean; unitsPreference?: "metric" | "imperial" },
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
