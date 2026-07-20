import { z } from "zod";
import { MirraHttpClient } from "./client";
import { MirraApiError } from "./errors";
import * as s from "./schemas";
import type { MirraRuntimeProvider } from "./runtime-provider";
import type {
  AnalyticsEvent,
  MeasurementKey,
  ShopperAccount,
  SignatureLook,
  SignatureLookLayer,
} from "./types";

const okSchema = z.object({ ok: z.boolean() }).transform(() => undefined);
const nullableShopper = z.union([s.shopperAccountSchema, z.null()]);

/**
 * MirraRuntimeProvider implemented over the versioned HTTP contract at
 * VITE_API_BASE_URL. The UI cannot tell whether this is talking to the
 * real backend or the in-process mock — that's the point of the seam.
 */
export class HttpRuntimeProvider implements MirraRuntimeProvider {
  constructor(private http: MirraHttpClient) {}

  // ── Catalogue ──
  listProducts(opts: { category?: string; cursor?: string; limit?: number } = {}) {
    const q = new URLSearchParams();
    if (opts.category) q.set("category", opts.category);
    if (opts.cursor) q.set("cursor", opts.cursor);
    if (opts.limit) q.set("limit", String(opts.limit));
    const qs = q.toString();
    return this.http.get(`/catalog/products${qs ? `?${qs}` : ""}`, s.productListPageSchema);
  }
  getProduct(productId: string) {
    return this.http.get(
      `/catalog/products/${encodeURIComponent(productId)}`,
      s.publicProductSchema,
    );
  }

  // ── Auth ──
  signUp(input: { displayName: string; email: string; password: string; acceptedTerms: boolean }) {
    return this.http.post("/auth/sign-up", s.shopperAccountSchema, input);
  }
  login(input: { email: string; password: string }) {
    return this.http.post("/auth/login", s.shopperAccountSchema, input);
  }
  loginWithGoogle() {
    return this.http.post("/auth/oauth/google", s.shopperAccountSchema, {});
  }
  continueAsGuest() {
    return this.http.post("/auth/guest", s.shopperAccountSchema, {});
  }
  async logout() {
    await this.http.post("/auth/logout", okSchema, {});
  }
  async getCurrentShopper(): Promise<ShopperAccount | null> {
    try {
      return await this.http.get("/auth/me", nullableShopper);
    } catch (err) {
      if (err instanceof MirraApiError && err.code === "unauthenticated") return null;
      throw err;
    }
  }
  async requestPasswordReset(email: string) {
    await this.http.post("/auth/password-reset", okSchema, { email });
  }
  verifyEmail(code: string) {
    return this.http.post("/auth/verify-email", s.shopperAccountSchema, { code });
  }
  updateConsents(consents: Partial<ShopperAccount["consents"]>) {
    return this.http.patch("/users/consents", s.shopperAccountSchema, consents);
  }
  async deleteAccount() {
    await this.http.delete("/users/account", okSchema);
  }

  // ── Capture ──
  createCaptureSession() {
    return this.http.post("/capture/sessions", s.captureSessionSchema, {});
  }
  getCaptureSession(sessionId: string) {
    return this.http.get(`/capture/sessions/${sessionId}`, s.captureSessionSchema);
  }
  getCaptureSessionByToken(token: string) {
    return this.http.get(`/capture/sessions/by-token/${token}`, s.captureSessionSchema);
  }
  resolveManualCode(code: string) {
    return this.http.post("/capture/sessions/resolve-code", z.object({ token: z.string() }), {
      code,
    });
  }
  pairCaptureSession(token: string) {
    return this.http.post(`/capture/sessions/by-token/${token}/pair`, s.captureSessionSchema, {});
  }
  giveCaptureConsent(token: string) {
    return this.http.post(
      `/capture/sessions/by-token/${token}/consent`,
      s.captureSessionSchema,
      {},
    );
  }
  submitCaptureAsset(
    token: string,
    stepId: string,
    payload: { mimeType: string; byteSize: number; width: number; height: number },
  ) {
    return this.http.post(`/capture/sessions/by-token/${token}/uploads`, s.captureSessionSchema, {
      stepId,
      ...payload,
    });
  }
  completeCapture(token: string) {
    return this.http.post(
      `/capture/sessions/by-token/${token}/complete`,
      s.captureSessionSchema,
      {},
    );
  }
  cancelCaptureSession(sessionId: string) {
    return this.http.post(`/capture/sessions/${sessionId}/cancel`, s.captureSessionSchema, {});
  }

  // ── Avatar ──
  getAvatarJob(jobId: string) {
    return this.http.get(`/avatars/jobs/${jobId}`, s.avatarJobSchema);
  }
  async getAvatarProfile() {
    return this.http.get("/avatars/profile", z.union([s.avatarProfileSchema, z.null()]));
  }
  updateMeasurements(
    changes: Partial<Record<MeasurementKey, number>>,
    opts: { resetEstimates?: boolean; unitsPreference?: "metric" | "imperial" } = {},
  ) {
    return this.http.patch("/measurements", s.avatarProfileSchema, { changes, ...opts });
  }
  async deleteAvatarProfile() {
    await this.http.delete("/avatars/profile", okSchema);
  }

  // ── Try-on ──
  createTryOnSession() {
    return this.http.post("/tryon/sessions", s.tryOnSessionSchema, {});
  }
  requestTryOn(input: {
    tryOnSessionId: string;
    productPublicId: string;
    variantPublicId: string;
    size: string | null;
    baseLayers?: SignatureLookLayer[];
  }) {
    return this.http.post(
      `/tryon/sessions/${input.tryOnSessionId}/renders`,
      s.tryOnRenderSchema,
      input,
    );
  }
  getTryOnRender(tryOnSessionId: string, renderId: string) {
    return this.http.get(
      `/tryon/sessions/${tryOnSessionId}/renders/${renderId}`,
      s.tryOnRenderSchema,
    );
  }
  listRecentRenders() {
    return this.http.get("/tryon/history", z.array(s.tryOnRenderSchema));
  }

  // ── Signature Looks ──
  listSignatureLooks() {
    return this.http.get("/signature-looks", z.array(s.signatureLookSchema));
  }
  createSignatureLook(input: {
    name: string;
    layers: SignatureLookLayer[];
    avatarProfileVersion: number;
    thumbnailUrl: string | null;
    isDefault?: boolean;
  }) {
    return this.http.post("/signature-looks", s.signatureLookSchema, input);
  }
  updateSignatureLook(
    lookId: string,
    patch: Partial<Pick<SignatureLook, "name" | "isDefault" | "layers" | "thumbnailUrl">>,
  ) {
    return this.http.patch(`/signature-looks/${lookId}`, s.signatureLookSchema, patch);
  }
  async deleteSignatureLook(lookId: string) {
    await this.http.delete(`/signature-looks/${lookId}`, okSchema);
  }

  // ── Analytics ──
  async trackEvent(event: AnalyticsEvent) {
    try {
      await this.http.post("/analytics/events", okSchema, event);
    } catch {
      // Analytics must never break the user's experience.
    }
  }
}
