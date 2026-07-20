import { z } from "zod";
import { clearAccessToken, getAccessToken, refreshAccessToken, setAccessToken } from "./auth-token";
import { MirraHttpClient } from "./client";
import { MirraApiError } from "./errors";
import * as live from "./live-schemas";
import type { MirraRuntimeProvider } from "./runtime-provider";
import type {
  AnalyticsEvent,
  MeasurementKey,
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
  private async storeSession(envelope: z.infer<typeof live.sessionEnvelope>): Promise<ShopperAccount> {
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
  async loginWithGoogle(): Promise<ShopperAccount> {
    throw new MirraApiError("api_degraded", "Google sign-in isn't available in the pilot yet", 503);
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

  // ── Capture ──
  createCaptureSession() {
    return this.http
      .post("/capture-sessions", live.captureEnvelope, {})
      .then((envelope) => live.mapCapture(envelope.session));
  }
  getCaptureSession(sessionId: string) {
    return this.http
      .get(`/capture-sessions/${sessionId}`, live.captureEnvelope)
      .then((envelope) => live.mapCapture(envelope.session));
  }
  getCaptureSessionByToken(token: string) {
    return this.http
      .get(`/capture-sessions/by-token/${token}`, live.captureEnvelope)
      .then((envelope) => live.mapCapture(envelope.session, token));
  }
  resolveManualCode(code: string) {
    return this.http.post("/capture-sessions/resolve-code", live.tokenEnvelope, { code });
  }
  pairCaptureSession(token: string) {
    return this.http
      .post(`/capture-sessions/by-token/${token}/pair`, live.captureEnvelope, {})
      .then((envelope) => live.mapCapture(envelope.session, token));
  }
  giveCaptureConsent(token: string) {
    return this.http
      .post(`/capture-sessions/by-token/${token}/consent`, live.captureEnvelope, {})
      .then((envelope) => live.mapCapture(envelope.session, token));
  }
  submitCaptureAsset(
    token: string,
    _stepId: string,
    payload: { mimeType: string; byteSize: number; width: number; height: number; blob?: Blob },
  ) {
    const form = new FormData();
    // The camera UI currently forwards metadata only; until it passes real
    // bytes, a placeholder pixel keeps the (demo-engine) flow working.
    const blob = payload.blob ?? placeholderPng();
    form.append("file", blob, "capture.png");
    return this.http
      .postMultipart(`/capture-sessions/by-token/${token}/uploads`, live.captureEnvelope, form)
      .then((envelope) => live.mapCapture(envelope.session, token));
  }
  completeCapture(token: string) {
    return this.http
      .post(`/capture-sessions/by-token/${token}/complete`, live.captureEnvelope, {})
      .then((envelope) => live.mapCapture(envelope.session, token));
  }
  cancelCaptureSession(sessionId: string) {
    return this.http
      .post(`/capture-sessions/${sessionId}/cancel`, live.captureEnvelope, {})
      .then((envelope) => live.mapCapture(envelope.session));
  }

  // ── Avatar ──
  getAvatarJob(jobId: string) {
    return this.http
      .get(`/avatars/jobs/${jobId}`, live.jobEnvelope)
      .then((envelope) => live.mapJob(envelope.job));
  }
  async getAvatarProfile() {
    const envelope = await this.http.get("/avatars/profile", live.profileEnvelope);
    return envelope.profile ? live.mapProfile(envelope.profile) : null;
  }
  async updateMeasurements(
    changes: Partial<Record<MeasurementKey, number>>,
    _opts: { resetEstimates?: boolean; unitsPreference?: "metric" | "imperial" } = {},
  ) {
    const fields: Record<string, number> = {};
    for (const [key, value] of Object.entries(changes)) {
      if (typeof value === "number") fields[live.KEY_TO_FIELD[key as MeasurementKey]] = value;
    }
    let measurements: Record<string, unknown>;
    try {
      measurements = (await this.http.patch("/measurements/me", live.measurementsEnvelope, fields))
        .measurements;
    } catch (err) {
      if (err instanceof MirraApiError && err.status === 404) {
        // First submission — v1 field contract is male-only, so the pilot
        // defaults gender until the UI collects it.
        measurements = (
          await this.http.put("/measurements/me", live.measurementsEnvelope, {
            gender: "male",
            accuracy: "approx",
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

  // ── Try-on ──
  createTryOnSession() {
    return this.http
      .post("/tryon/sessions", live.tryonSessionEnvelope, {})
      .then((envelope) => ({
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
    return this.http
      .post(`/tryon/sessions/${input.tryOnSessionId}/renders`, live.renderEnvelope, {
        sizeId: input.productPublicId,
      })
      .then((envelope) => live.mapRender(envelope.render));
  }
  getTryOnRender(tryOnSessionId: string, renderId: string) {
    return this.http
      .get(`/tryon/sessions/${tryOnSessionId}/renders/${renderId}`, live.renderEnvelope)
      .then((envelope) => live.mapRender(envelope.render));
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

/** 1×1 transparent PNG used until the camera UI forwards real bytes. */
function placeholderPng(): Blob {
  const b64 =
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==";
  const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  return new Blob([bytes], { type: "image/png" });
}
