import type {
  AnalyticsEvent,
  AvatarGlbResult,
  AvatarJob,
  AvatarProfile,
  AvatarSetup,
  MeasurementKey,
  CaptureLink,
  CaptureLinkProgress,
  FaceCapture,
  FaceLinkProgress,
  FacePhotosInput,
  PhotoCaptureInput,
  PhotoMeasurement,
  PhotoMeasurementField,
  PhotoPairing,
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
  loginWithGoogle(next?: string): Promise<ShopperAccount>;
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
  /** Binary GLB for the signed-in shopper's own avatar, plus staleness. */
  getAvatarGlb(): Promise<AvatarGlbResult>;
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

  // Photo measurement — front + side photo → measurements to review, then
  // applied into the same saved measurements the manual form writes.
  startPhotoMeasurement(input: PhotoCaptureInput): Promise<PhotoMeasurement>;
  getPhotoMeasurement(captureId: string): Promise<PhotoMeasurement>;
  /** Desktop: a short-lived QR link that lets a signed-out phone upload the photos. */
  createPhotoPairing(
    buildAvatar?: boolean,
    measurementMethod?: "photos" | "manual",
  ): Promise<PhotoPairing>;
  refreshCaptureLink(pairingId: string): Promise<PhotoPairing>;
  getLatestAvatarSetup(): Promise<AvatarSetup | null>;
  getAvatarSetup(pairingId: string): Promise<AvatarSetup>;
  reviewAvatarSetup(
    pairingId: string,
    overrides: Partial<Record<PhotoMeasurementField, number>>,
  ): Promise<AvatarSetup>;
  retryAvatarSetup(pairingId: string, skipFace?: boolean): Promise<AvatarSetup>;
  setCaptureStage(token: string, stage: "capturing" | "uploading"): Promise<void>;
  finishCapture(token: string, skipFace?: boolean): Promise<void>;
  /** Desktop poll: has the phone uploaded, and how far along is it? */
  getPhotoPairing(
    pairingId: string,
  ): Promise<{ pairing: PhotoPairing; capture: PhotoMeasurement | null }>;
  // Phone side — no sign-in, the token is the credential.
  getCaptureLink(token: string): Promise<CaptureLink>;
  uploadViaCaptureLink(token: string, input: PhotoCaptureInput): Promise<CaptureLinkProgress>;
  getCaptureLinkProgress(token: string): Promise<CaptureLinkProgress | null>;
  // Face — 1-3 photos → a face mesh the avatar viewer attaches to the head.
  startFace(input: FacePhotosInput): Promise<FaceCapture>;
  getFace(faceId: string): Promise<FaceCapture>;
  getLatestFace(): Promise<FaceCapture | null>;
  /** The current face mesh, or null when the shopper hasn't added one. */
  getFaceGlb(): Promise<Blob | null>;
  deleteFace(): Promise<void>;
  uploadFaceViaCaptureLink(token: string, input: FacePhotosInput): Promise<FaceLinkProgress>;
  getCaptureLinkFace(token: string): Promise<FaceLinkProgress | null>;
  /** The most recent capture, so a reload mid-measurement can resume. */
  getLatestPhotoMeasurement(): Promise<PhotoMeasurement | null>;
  /** Save a ready capture; `overrides` are the shopper's corrections by backend field name. */
  applyPhotoMeasurement(
    captureId: string,
    overrides: Partial<Record<PhotoMeasurementField, number>>,
  ): Promise<AvatarProfile>;

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
  /** Binary GLB of a finished render — avatar and garment in one file. */
  getTryOnRenderGlb(tryOnSessionId: string, renderId: string): Promise<Blob>;
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
