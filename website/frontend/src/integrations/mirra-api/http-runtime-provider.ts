import { z } from "zod";
import { clearAccessToken, getAccessToken, refreshAccessToken, setAccessToken } from "./auth-token";
import { MirraHttpClient } from "./client";
import { MirraApiError } from "./errors";
import * as live from "./live-schemas";
import type { MirraRuntimeProvider } from "./runtime-provider";
import type {
  AnalyticsEvent,
  FacePhotosInput,
  MeasurementKey,
  PhotoCaptureInput,
  PhotoMeasurementField,
  ShopperAccount,
  SignatureLook,
  SignatureLookLayer,
} from "./types";

/**
 * MirraRuntimeProvider over the REAL backend (website/backend). Calls the
 * FastAPI endpoints, validates their envelopes (live-schemas.ts) and maps
 * them into the UI's domain types. The UI cannot tell this apart from the
 * mock — that's the point of the seam.
 */
export class HttpRuntimeProvider implements MirraRuntimeProvider {
  constructor(private http: MirraHttpClient) {}

  // ── Session helper ──
  private async storeSession(
    envelope: z.infer<typeof live.sessionEnvelope>,
  ): Promise<ShopperAccount> {
    setAccessToken(envelope.accessToken);
    return live.mapAccount(envelope.account);
  }

  // ── Catalogue (backend: catalog service, sizes collection) ──
  listProducts(opts: { category?: string; cursor?: string; limit?: number } = {}) {
    const q = new URLSearchParams();
    if (opts.category) q.set("category", opts.category);
    if (opts.cursor) q.set("offset", opts.cursor); // cursor is a stringified offset
    if (opts.limit) q.set("limit", String(opts.limit));
    const qs = q.toString();
    return this.http
      .get(`/catalog/garments${qs ? `?${qs}` : ""}`, live.garmentListEnvelope)
      .then(live.mapGarmentList);
  }
  getProduct(productId: string) {
    return this.http
      .get(`/catalog/garments/${encodeURIComponent(productId)}`, live.garmentEnvelope)
      .then((envelope) => live.mapGarment(envelope.garment));
  }

  // ── Auth ──
  async signUp(input: {
    displayName: string;
    email: string;
    password: string;
    acceptedTerms: boolean;
  }) {
    const envelope = await this.http.post("/auth/sign-up", live.sessionEnvelope, {
      email: input.email,
      password: input.password,
      name: input.displayName,
    });
    const account = await this.storeSession(envelope);
    if (input.acceptedTerms) {
      try {
        return await this.updateConsents({ terms: true, privacy: true });
      } catch {
        // consent write is best-effort at sign-up; account already exists
      }
    }
    return account;
  }
  async login(input: { email: string; password: string }) {
    return this.storeSession(await this.http.post("/auth/login", live.sessionEnvelope, input));
  }
  async loginWithGoogle(destination?: string): Promise<ShopperAccount> {
    // Full-page redirect flow (backend: auth/google/start + /callback) —
    // the browser navigates away, so this intentionally never resolves.
    // Signup provides its standalone setup destination. Other login surfaces
    // keep their existing safe post-auth destination.
    const next = destination ?? new URLSearchParams(window.location.search).get("next");
    const qs = next ? `?next=${encodeURIComponent(next)}` : "";
    window.location.assign(`${this.http.baseUrl}/auth/google/start${qs}`);
    return new Promise<ShopperAccount>(() => {});
  }
  async continueAsGuest() {
    return this.storeSession(await this.http.post("/auth/guest", live.sessionEnvelope, {}));
  }
  async logout() {
    try {
      await this.http.post("/auth/logout", live.okEnvelope, {});
    } finally {
      clearAccessToken();
    }
  }
  async getCurrentShopper(): Promise<ShopperAccount | null> {
    // Page-load restore: no in-memory token → try the refresh cookie once.
    if (!getAccessToken()) {
      const token = await refreshAccessToken(this.http.baseUrl);
      if (!token) return null;
    }
    try {
      const envelope = await this.http.get("/auth/me", live.accountEnvelope);
      return live.mapAccount(envelope.account);
    } catch (err) {
      if (err instanceof MirraApiError && err.code === "unauthenticated") {
        clearAccessToken();
        return null;
      }
      throw err;
    }
  }
  async requestPasswordReset(email: string) {
    await this.http.post("/auth/password-reset", live.okEnvelope, { email });
  }
  verifyEmail(code: string) {
    return this.http
      .post("/auth/verify-email", live.accountEnvelope, { code })
      .then((envelope) => live.mapAccount(envelope.account));
  }
  updateConsents(consents: Partial<ShopperAccount["consents"]>) {
    const clean = Object.fromEntries(
      Object.entries(consents).filter(([, v]) => typeof v === "boolean"),
    );
    return this.http
      .patch("/users/me/consents", live.accountEnvelope, { consents: clean })
      .then((envelope) => live.mapAccount(envelope.account));
  }
  async deleteAccount() {
    try {
      await this.http.delete("/users/me", live.okEnvelope);
    } finally {
      clearAccessToken();
    }
  }

  // ── Avatar ──
  generateAvatar() {
    return this.http
      .post("/avatars/generate", live.jobEnvelope, {})
      .then((envelope) => live.mapJob(envelope.job));
  }
  getAvatarJob(jobId: string) {
    return this.http
      .get(`/avatars/jobs/${jobId}`, live.jobEnvelope)
      .then((envelope) => live.mapJob(envelope.job));
  }
  async getAvatarProfile() {
    const envelope = await this.http.get("/avatars/profile", live.profileEnvelope);
    if (envelope.profile) return live.mapProfile(envelope.profile);

    // Measurements can exist before the first avatar job, or after its deletion.
    // Read the existing measurement record so a page reload keeps that work visible.
    try {
      const saved = await this.http.get("/user-measurements/me", live.measurementsEnvelope);
      return live.profileFromMeasurements(saved.measurements);
    } catch (error) {
      if (error instanceof MirraApiError && error.status === 404) return null;
      throw error;
    }
  }
  async getAvatarGlb() {
    const { blob, headers } = await this.http.getBlobWithHeaders("/avatars/profile/glb");
    const raw = headers.get("X-Avatar-Measurements-Stale");
    return { blob, isStale: raw === "true" ? true : raw === "false" ? false : null };
  }
  async updateMeasurements(
    changes: Partial<Record<MeasurementKey, number>>,
    opts: {
      resetEstimates?: boolean;
      unitsPreference?: "metric" | "imperial";
      gender?: "male" | "female";
      accuracy?: "accurate" | "approx";
    } = {},
  ) {
    const fields: Record<string, number> = {};
    for (const [key, value] of Object.entries(changes)) {
      if (typeof value === "number") fields[live.KEY_TO_FIELD[key as MeasurementKey]] = value;
    }
    let measurements: Record<string, unknown>;
    try {
      measurements = (
        await this.http.patch("/user-measurements/me", live.measurementsEnvelope, fields)
      ).measurements;
    } catch (err) {
      if (err instanceof MirraApiError && err.status === 404) {
        // First submission — defaults preserve prior (pre-form) behaviour
        // for callers that don't pass gender/accuracy explicitly.
        measurements = (
          await this.http.put("/user-measurements/me", live.measurementsEnvelope, {
            gender: opts.gender ?? "male",
            accuracy: opts.accuracy ?? "approx",
            ...fields,
          })
        ).measurements;
      } else {
        throw err;
      }
    }
    const profile = await this.getAvatarProfile();
    return profile ?? live.profileFromMeasurements(measurements);
  }
  async deleteAvatarProfile() {
    await this.http.delete("/avatars/profile", live.okEnvelope);
  }

  // ── Photo measurement ──
  startPhotoMeasurement(input: PhotoCaptureInput) {
    return this.http
      .postMultipart("/photo-measurements", live.photoCaptureEnvelope, photoForm(input))
      .then((envelope) => live.mapPhotoCapture(envelope.capture));
  }
  createPhotoPairing(buildAvatar = false, measurementMethod: "photos" | "manual" = "photos") {
    return this.http
      .post("/photo-measurements/pairings", live.pairingEnvelope, {
        buildAvatar,
        measurementMethod,
      })
      .then((envelope) => envelope.pairing);
  }
  refreshCaptureLink(pairingId: string) {
    return this.http
      .post(
        `/photo-measurements/pairings/${encodeURIComponent(pairingId)}/link`,
        live.pairingEnvelope,
        {},
      )
      .then((e) => e.pairing);
  }
  getLatestAvatarSetup() {
    return this.http
      .get("/photo-measurements/setup/latest", live.setupMaybeEnvelope)
      .then((e) => e.setup);
  }
  getAvatarSetup(pairingId: string) {
    return this.http
      .get(`/photo-measurements/setup/${encodeURIComponent(pairingId)}`, live.setupEnvelope)
      .then((e) => e.setup);
  }
  reviewAvatarSetup(pairingId: string, overrides: Partial<Record<PhotoMeasurementField, number>>) {
    return this.http
      .post(
        `/photo-measurements/setup/${encodeURIComponent(pairingId)}/review`,
        live.setupEnvelope,
        { overrides },
      )
      .then((e) => e.setup);
  }
  retryAvatarSetup(pairingId: string, skipFace = false) {
    return this.http
      .post(
        `/photo-measurements/setup/${encodeURIComponent(pairingId)}/retry`,
        live.setupEnvelope,
        { skipFace },
      )
      .then((e) => e.setup);
  }
  async setCaptureStage(token: string, stage: "capturing" | "uploading") {
    await this.http.post(`/photo-capture/${encodeURIComponent(token)}/stage`, live.okEnvelope, {
      stage,
    });
  }
  async finishCapture(token: string, skipFace = false) {
    await this.http.post(`/photo-capture/${encodeURIComponent(token)}/finish`, live.okEnvelope, {
      skipFace,
    });
  }
  async getPhotoPairing(pairingId: string) {
    const envelope = await this.http.get(
      `/photo-measurements/pairings/${encodeURIComponent(pairingId)}`,
      live.pairingStatusEnvelope,
    );
    return {
      pairing: envelope.pairing,
      capture: envelope.capture ? live.mapPhotoCapture(envelope.capture) : null,
    };
  }
  startFace(input: FacePhotosInput) {
    return this.http
      .postMultipart("/faces", live.faceEnvelope, faceForm(input))
      .then((envelope) => envelope.face);
  }
  getFace(faceId: string) {
    return this.http
      .get(`/faces/${encodeURIComponent(faceId)}`, live.faceEnvelope)
      .then((envelope) => envelope.face);
  }
  getLatestFace() {
    return this.http.get("/faces/latest", live.faceMaybeEnvelope).then((envelope) => envelope.face);
  }
  async getFaceGlb() {
    try {
      return await this.http.getBlob("/faces/current/glb");
    } catch (err) {
      if (err instanceof MirraApiError && err.status === 404) return null;
      throw err;
    }
  }
  async deleteFace() {
    await this.http.delete("/faces", live.okEnvelope);
  }
  uploadFaceViaCaptureLink(token: string, input: FacePhotosInput) {
    return this.http
      .postMultipart(
        `/photo-capture/${encodeURIComponent(token)}/face`,
        live.faceLinkEnvelope,
        faceForm(input),
      )
      .then((envelope) => envelope.face);
  }
  getCaptureLinkFace(token: string) {
    return this.http
      .get(`/photo-capture/${encodeURIComponent(token)}/face`, live.faceLinkMaybeEnvelope)
      .then((envelope) => envelope.face);
  }
  getCaptureLink(token: string) {
    return this.http
      .get(`/photo-capture/${encodeURIComponent(token)}`, live.captureLinkEnvelope)
      .then((envelope) => envelope.link);
  }
  uploadViaCaptureLink(token: string, input: PhotoCaptureInput) {
    return this.http
      .postMultipart(
        `/photo-capture/${encodeURIComponent(token)}`,
        live.linkProgressEnvelope,
        photoForm(input),
      )
      .then((envelope) => envelope.capture);
  }
  getCaptureLinkProgress(token: string) {
    return this.http
      .get(`/photo-capture/${encodeURIComponent(token)}/capture`, live.linkProgressMaybeEnvelope)
      .then((envelope) => envelope.capture);
  }
  getPhotoMeasurement(captureId: string) {
    return this.http
      .get(`/photo-measurements/${encodeURIComponent(captureId)}`, live.photoCaptureEnvelope)
      .then((envelope) => live.mapPhotoCapture(envelope.capture));
  }
  async getLatestPhotoMeasurement() {
    const envelope = await this.http.get(
      "/photo-measurements/latest",
      live.photoCaptureLatestEnvelope,
    );
    return envelope.capture ? live.mapPhotoCapture(envelope.capture) : null;
  }
  async applyPhotoMeasurement(
    captureId: string,
    overrides: Partial<Record<PhotoMeasurementField, number>>,
  ) {
    const envelope = await this.http.post(
      `/photo-measurements/${encodeURIComponent(captureId)}/apply`,
      live.applyPhotoEnvelope,
      { overrides },
    );
    const profile = await this.getAvatarProfile();
    return profile ?? live.profileFromMeasurements(envelope.measurements);
  }

  // ── Try-on ──
  createTryOnSession() {
    return this.http.post("/tryon/sessions", live.tryonSessionEnvelope, {}).then((envelope) => ({
      tryOnSessionId: envelope.session.sessionId,
      createdAt: envelope.session.createdAt,
    }));
  }
  requestTryOn(input: {
    tryOnSessionId: string;
    productPublicId: string;
    variantPublicId: string;
    size: string | null;
    baseLayers?: SignatureLookLayer[];
  }) {
    // A product is a cloth and a variant is a size — see doc 13 §47.
    return this.http
      .post(`/tryon/sessions/${input.tryOnSessionId}/renders`, live.renderEnvelope, {
        clothId: input.productPublicId,
        sizeId: input.variantPublicId,
      })
      .then((envelope) => live.mapRender(envelope.render));
  }
  getTryOnRender(tryOnSessionId: string, renderId: string) {
    return this.http
      .get(`/tryon/sessions/${tryOnSessionId}/renders/${renderId}`, live.renderEnvelope)
      .then((envelope) => live.mapRender(envelope.render));
  }
  getTryOnRenderGlb(tryOnSessionId: string, renderId: string) {
    return this.http.getBlob(`/tryon/sessions/${tryOnSessionId}/renders/${renderId}/glb`);
  }
  listRecentRenders() {
    return this.http
      .get("/tryon/history", live.renderListEnvelope)
      .then((envelope) => envelope.items.map(live.mapRender));
  }

  // ── Signature Looks ──
  listSignatureLooks() {
    return this.http
      .get("/signature-looks", live.lookListEnvelope)
      .then((envelope) => envelope.items.map(live.mapLook));
  }
  createSignatureLook(input: {
    name: string;
    layers: SignatureLookLayer[];
    avatarProfileVersion: number;
    thumbnailUrl: string | null;
    isDefault?: boolean;
  }) {
    return this.http
      .post("/signature-looks", live.lookEnvelope, {
        name: input.name,
        items: input.layers.map((l) => ({ sizeId: l.productPublicId, renderId: null })),
        isDefault: input.isDefault ?? false,
      })
      .then((envelope) => live.mapLook(envelope.look));
  }
  updateSignatureLook(
    lookId: string,
    patch: Partial<Pick<SignatureLook, "name" | "isDefault" | "layers" | "thumbnailUrl">>,
  ) {
    const body: Record<string, unknown> = {};
    if (patch.name !== undefined) body.name = patch.name;
    if (patch.isDefault !== undefined) body.isDefault = patch.isDefault;
    if (patch.layers !== undefined) {
      body.items = patch.layers.map((l) => ({ sizeId: l.productPublicId, renderId: null }));
    }
    return this.http
      .patch(`/signature-looks/${lookId}`, live.lookEnvelope, body)
      .then((envelope) => live.mapLook(envelope.look));
  }
  async deleteSignatureLook(lookId: string) {
    await this.http.delete(`/signature-looks/${lookId}`, live.okEnvelope);
  }

  // ── Analytics ──
  async trackEvent(event: AnalyticsEvent) {
    try {
      await this.http.post("/analytics/events", live.okEnvelope, event);
    } catch {
      // Analytics must never break the user's experience.
    }
  }
}

function photoForm(input: PhotoCaptureInput): FormData {
  const form = new FormData();
  form.append("front", input.front);
  form.append("side", input.side);
  form.append("height_cm", String(input.heightCm));
  form.append("gender", input.gender);
  if (typeof input.weightKg === "number") form.append("weight_kg", String(input.weightKg));
  if (input.shoeSoleCm) form.append("shoe_sole_cm", String(input.shoeSoleCm));
  return form;
}

function faceForm(input: FacePhotosInput): FormData {
  const form = new FormData();
  form.append("front", input.front);
  if (input.left) form.append("left", input.left);
  if (input.right) form.append("right", input.right);
  return form;
}
