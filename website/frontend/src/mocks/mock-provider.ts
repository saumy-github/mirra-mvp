import type { MirraRuntimeProvider } from "@/integrations/mirra-api/runtime-provider";
import type {
  AnalyticsEvent,
  AvatarJob,
  AvatarJobState,
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
} from "@/integrations/mirra-api/types";
import { MirraApiError } from "@/integrations/mirra-api/errors";
import { avatarStageLabels } from "@/lib/state-machines/avatar-job";
import { freshMeasurements, mockCategories, mockProducts } from "./fixtures";
import { swatchDataUri } from "./placeholder";
import { getDb, nextId, type MockAccount, type MockCaptureSession } from "./store";

/** Demo stage timeline (ms since start). Honest stages — never percentages. */
const STAGE_TIMELINE: Array<[AvatarJobState, number]> = [
  ["queued", 800],
  ["validating", 2200],
  ["estimating", 3600],
  ["generating", 5200],
  ["optimising", 6400],
];

const CAPTURE_STEPS = [
  {
    id: "front",
    title: "Front view",
    guidance: "Stand facing the camera, arms relaxed.",
    silhouette: "front" as const,
    required: true,
  },
  {
    id: "side",
    title: "Side view",
    guidance: "Turn 90°, arms at your sides.",
    silhouette: "side" as const,
    required: true,
  },
  {
    id: "back",
    title: "Back view",
    guidance: "Turn around, facing away from the camera.",
    silhouette: "back" as const,
    required: true,
  },
];

function stripPassword(a: MockAccount): ShopperAccount {
  const { password: _password, ...rest } = a;
  return rest;
}

function requireAccount(): MockAccount {
  const db = getDb();
  const account = db.currentAccountId ? db.accounts.get(db.currentAccountId) : undefined;
  if (!account) throw new MirraApiError("unauthenticated", "Sign in required.", 401);
  return account;
}

function findSessionByToken(token: string): MockCaptureSession {
  const db = getDb();
  const id = db.captureSessionsByToken.get(token);
  const session = id ? db.captureSessions.get(id) : undefined;
  if (!session)
    throw new MirraApiError("capture_session_not_found", "Pairing session not found.", 404);
  return session;
}

/**
 * Implements MirraRuntimeProvider directly against in-memory fixtures — no
 * fetch, no server. See mock-runtime-provider.ts for why this deviates from
 * the ported original (which still made same-origin HTTP calls to Next.js
 * API routes): there's no Node server in this stack anymore, and this way
 * `npm run dev` runs the whole app with zero backend required.
 */
export class InProcessMockProvider implements MirraRuntimeProvider {
  // ── Catalogue ──
  async listProducts(
    opts: { category?: string; cursor?: string; limit?: number } = {},
  ): Promise<ProductListPage> {
    let items = mockProducts;
    if (opts.category) items = items.filter((p) => p.category === opts.category);
    return { items, categories: mockCategories, nextCursor: null, total: items.length };
  }

  async getProduct(productId: string): Promise<PublicProduct> {
    const product = mockProducts.find((p) => p.publicProductId === productId);
    if (!product)
      throw new MirraApiError("product_not_found", "This item is no longer available.", 404);
    return product;
  }

  // ── Auth ──
  async signUp(input: {
    displayName: string;
    email: string;
    password: string;
    acceptedTerms: boolean;
  }): Promise<ShopperAccount> {
    const db = getDb();
    if (db.accountsByEmail.has(input.email.toLowerCase())) {
      throw new MirraApiError("account_exists", "An account with this email already exists.", 409);
    }
    const shopperId = nextId("acct");
    const account: MockAccount = {
      shopperId,
      email: input.email,
      displayName: input.displayName,
      emailVerified: false,
      isGuest: false,
      createdAt: new Date().toISOString(),
      consents: {
        terms: input.acceptedTerms,
        privacy: input.acceptedTerms,
        preferenceStorage: true,
      },
      password: input.password,
    };
    db.accounts.set(shopperId, account);
    db.accountsByEmail.set(input.email.toLowerCase(), shopperId);
    db.currentAccountId = shopperId;
    return stripPassword(account);
  }

  async login(input: { email: string; password: string }): Promise<ShopperAccount> {
    const db = getDb();
    const id = db.accountsByEmail.get(input.email.toLowerCase());
    const account = id ? db.accounts.get(id) : undefined;
    if (!account || account.password !== input.password) {
      throw new MirraApiError(
        "invalid_credentials",
        "That email and password combination doesn't match our records.",
        401,
      );
    }
    db.currentAccountId = account.shopperId;
    return stripPassword(account);
  }

  async loginWithGoogle(): Promise<ShopperAccount> {
    const db = getDb();
    const email = "demo.google@mirra.dev";
    let id = db.accountsByEmail.get(email);
    if (!id) {
      id = nextId("acct");
      const account: MockAccount = {
        shopperId: id,
        email,
        displayName: "Google Demo",
        emailVerified: true,
        isGuest: false,
        createdAt: new Date().toISOString(),
        consents: { terms: true, privacy: true, preferenceStorage: true },
        password: "",
      };
      db.accounts.set(id, account);
      db.accountsByEmail.set(email, id);
    }
    db.currentAccountId = id;
    return stripPassword(db.accounts.get(id)!);
  }

  async continueAsGuest(): Promise<ShopperAccount> {
    const db = getDb();
    const shopperId = nextId("guest");
    const account: MockAccount = {
      shopperId,
      email: "",
      displayName: "Guest",
      emailVerified: false,
      isGuest: true,
      createdAt: new Date().toISOString(),
      consents: { terms: true, privacy: true, preferenceStorage: false },
      password: "",
    };
    db.accounts.set(shopperId, account);
    db.currentAccountId = shopperId;

    // Guests skip capture/onboarding entirely — they get a shared generic
    // stock avatar (the "generate once, store, reuse" pattern applied to a
    // generic body instead of real measurements).
    db.avatarProfiles.set(shopperId, {
      avatarProfileId: "avp_guest",
      avatarLabel: "GUEST",
      version: 1,
      engineVersion: "demo-avatar-0.1",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      previewAssetUrl: swatchDataUri("#d2d2d7", "guest avatar"),
      measurements: freshMeasurements(),
      unitsPreference: "metric",
    });

    return stripPassword(account);
  }

  async logout(): Promise<void> {
    getDb().currentAccountId = null;
  }

  async getCurrentShopper(): Promise<ShopperAccount | null> {
    const db = getDb();
    const account = db.currentAccountId ? db.accounts.get(db.currentAccountId) : undefined;
    return account ? stripPassword(account) : null;
  }

  async requestPasswordReset(_email: string): Promise<void> {
    // No-op in mock mode — nothing to send.
  }

  async verifyEmail(_code: string): Promise<ShopperAccount> {
    const account = requireAccount();
    account.emailVerified = true;
    return stripPassword(account);
  }

  async updateConsents(consents: Partial<ShopperAccount["consents"]>): Promise<ShopperAccount> {
    const account = requireAccount();
    account.consents = { ...account.consents, ...consents };
    return stripPassword(account);
  }

  async deleteAccount(): Promise<void> {
    const db = getDb();
    const account = requireAccount();
    db.accounts.delete(account.shopperId);
    db.accountsByEmail.delete(account.email.toLowerCase());
    db.avatarProfiles.delete(account.shopperId);
    db.measurements.delete(account.shopperId);
    db.signatureLooks.delete(account.shopperId);
    db.currentAccountId = null;
  }

  // ── Capture ──
  async createCaptureSession(): Promise<CaptureSession> {
    const db = getDb();
    const account = requireAccount();
    const captureSessionId = nextId("cap");
    const oneTimeToken = nextId("tok");
    const manualCode = Math.random().toString(36).slice(2, 8).toUpperCase();
    const session = {
      captureSessionId,
      accountId: account.shopperId,
      state: "qr_ready" as const,
      oneTimeToken,
      manualCode,
      expiresAt: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
      steps: CAPTURE_STEPS,
      uploadedStepIds: [],
      failureReason: null,
      avatarJobId: null,
    };
    db.captureSessions.set(captureSessionId, session);
    db.captureSessionsByToken.set(oneTimeToken, captureSessionId);
    return session;
  }

  async getCaptureSession(sessionId: string): Promise<CaptureSession> {
    const session = getDb().captureSessions.get(sessionId);
    if (!session)
      throw new MirraApiError("capture_session_not_found", "Pairing session not found.", 404);
    return session;
  }

  async getCaptureSessionByToken(token: string): Promise<CaptureSession> {
    return findSessionByToken(token);
  }

  async resolveManualCode(code: string): Promise<{ token: string }> {
    const db = getDb();
    for (const session of db.captureSessions.values()) {
      if (session.manualCode === code.toUpperCase()) return { token: session.oneTimeToken };
    }
    throw new MirraApiError(
      "capture_session_not_found",
      "That code doesn't match a pairing session.",
      404,
    );
  }

  async pairCaptureSession(token: string): Promise<CaptureSession> {
    const session = await this.getCaptureSessionByToken(token);
    session.state = "paired";
    return session;
  }

  async giveCaptureConsent(token: string): Promise<CaptureSession> {
    const session = await this.getCaptureSessionByToken(token);
    session.state = "capturing";
    return session;
  }

  async submitCaptureAsset(
    token: string,
    stepId: string,
    _payload: { mimeType: string; byteSize: number; width: number; height: number },
  ): Promise<CaptureSession> {
    const session = await this.getCaptureSessionByToken(token);
    session.state = "uploading";
    if (!session.uploadedStepIds.includes(stepId)) session.uploadedStepIds.push(stepId);
    session.state =
      session.uploadedStepIds.length >= session.steps.length ? "uploaded" : "capturing";
    return session;
  }

  async completeCapture(token: string): Promise<CaptureSession> {
    const db = getDb();
    const session = findSessionByToken(token);
    session.state = "processing";
    const jobId = nextId("job");
    db.avatarJobs.set(jobId, {
      jobId,
      accountId: session.accountId,
      startedAt: new Date().toISOString(),
      cancelled: false,
      simulateFailure: false,
      failureReason: null,
      avatarProfileId: null,
    });
    session.avatarJobId = jobId;
    session.state = "completed";
    return session;
  }

  async cancelCaptureSession(sessionId: string): Promise<CaptureSession> {
    const session = await this.getCaptureSession(sessionId);
    if (!["completed", "expired", "failed"].includes(session.state)) session.state = "cancelled";
    return session;
  }

  // ── Avatar — the CLO3D seam ──
  async getAvatarJob(jobId: string): Promise<AvatarJob> {
    const db = getDb();
    const job = db.avatarJobs.get(jobId);
    if (!job) throw new MirraApiError("avatar_job_failed", "Unknown avatar job.", 404);

    const elapsed = Date.now() - new Date(job.startedAt).getTime();
    let state: AvatarJobState = "ready";
    for (const [stage, until] of STAGE_TIMELINE) {
      if (elapsed < until) {
        state = stage;
        break;
      }
    }
    if (job.cancelled) state = "cancelled";

    if (state === "ready" && !job.avatarProfileId) {
      const existing = db.avatarProfiles.get(job.accountId);
      const version = (existing?.version ?? 0) + 1;
      const profile: AvatarProfile = {
        avatarProfileId: existing?.avatarProfileId ?? nextId("avp"),
        avatarLabel: `${String(version + 8).padStart(2, "0")}-V${version}`,
        version,
        engineVersion: "demo-avatar-0.1",
        createdAt: existing?.createdAt ?? new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        previewAssetUrl: swatchDataUri("#c7c7cc", "avatar preview"),
        measurements: existing?.measurements ?? freshMeasurements(),
        unitsPreference: existing?.unitsPreference ?? "metric",
      };
      db.avatarProfiles.set(job.accountId, profile);
      job.avatarProfileId = profile.avatarProfileId;
    }

    return {
      jobId: job.jobId,
      state,
      stageLabel: avatarStageLabels[state],
      startedAt: job.startedAt,
      failureReason: state === "failed" ? job.failureReason : null,
      avatarProfileId: job.avatarProfileId,
    };
  }

  async getAvatarProfile(): Promise<AvatarProfile | null> {
    const account = requireAccount();
    return getDb().avatarProfiles.get(account.shopperId) ?? null;
  }

  async updateMeasurements(
    changes: Partial<Record<MeasurementKey, number>>,
    opts: { resetEstimates?: boolean } = {},
  ): Promise<AvatarProfile> {
    const db = getDb();
    const account = requireAccount();
    const profile = db.avatarProfiles.get(account.shopperId);
    if (!profile) throw new MirraApiError("avatar_job_failed", "No avatar profile yet.", 404);
    profile.measurements = profile.measurements.map((field) => {
      const value = changes[field.key];
      if (value === undefined) return field;
      return { ...field, value, estimated: opts.resetEstimates ? false : field.estimated };
    });
    profile.updatedAt = new Date().toISOString();
    return profile;
  }

  async deleteAvatarProfile(): Promise<void> {
    const account = requireAccount();
    getDb().avatarProfiles.delete(account.shopperId);
  }

  // ── Try-on — demo mode: flat garment layering, resolves near-instantly ──
  async createTryOnSession(): Promise<TryOnSession> {
    return { tryOnSessionId: nextId("tos"), createdAt: new Date().toISOString() };
  }

  async requestTryOn(input: {
    tryOnSessionId: string;
    productPublicId: string;
    variantPublicId: string;
    size: string | null;
  }): Promise<TryOnRender> {
    const product = mockProducts.find((p) => p.publicProductId === input.productPublicId);
    const variant = product?.variants.find((v) => v.publicVariantId === input.variantPublicId);
    const account = requireAccount();
    const profile = getDb().avatarProfiles.get(account.shopperId);
    await new Promise((r) => setTimeout(r, 900)); // deliberate, honest "demo processing" beat

    if (!product || !variant || !variant.garmentAssetUrl) {
      return {
        renderId: nextId("render"),
        tryOnSessionId: input.tryOnSessionId,
        state: "unsupported",
        productPublicId: input.productPublicId,
        variantPublicId: input.variantPublicId,
        size: input.size,
        layers: {},
        avatarProfileVersion: profile?.version ?? 0,
        engineVersion: "demo-tryon-0.1",
        renderedAssetUrl: null,
        generatedAt: new Date().toISOString(),
        failureReason: "This garment isn't ready for try-on yet.",
      };
    }

    return {
      renderId: nextId("render"),
      tryOnSessionId: input.tryOnSessionId,
      state: "ready",
      productPublicId: input.productPublicId,
      variantPublicId: input.variantPublicId,
      size: input.size,
      layers: {
        [product.garmentCategory]: {
          productPublicId: product.publicProductId,
          variantPublicId: variant.publicVariantId,
          assetUrl: variant.garmentAssetUrl,
        },
      },
      avatarProfileVersion: profile?.version ?? 0,
      engineVersion: "demo-tryon-0.1",
      renderedAssetUrl: variant.garmentAssetUrl,
      generatedAt: new Date().toISOString(),
      failureReason: null,
    };
  }

  async getTryOnRender(_tryOnSessionId: string, renderId: string): Promise<TryOnRender> {
    // Demo renders resolve synchronously in requestTryOn and are never left
    // "processing", so there's nothing to poll for here.
    throw new MirraApiError("render_not_found", `Render ${renderId} not found.`, 404);
  }

  async listRecentRenders(): Promise<TryOnRender[]> {
    return [];
  }

  // ── Signature Looks ──
  async listSignatureLooks(): Promise<SignatureLook[]> {
    const account = requireAccount();
    return getDb().signatureLooks.get(account.shopperId) ?? [];
  }

  async createSignatureLook(input: {
    name: string;
    layers: SignatureLookLayer[];
    avatarProfileVersion: number;
    thumbnailUrl: string | null;
    isDefault?: boolean;
  }): Promise<SignatureLook> {
    const db = getDb();
    const account = requireAccount();
    const look: SignatureLook = {
      lookId: nextId("look"),
      name: input.name,
      isDefault: input.isDefault ?? false,
      avatarProfileVersion: input.avatarProfileVersion,
      thumbnailUrl: input.thumbnailUrl,
      layers: input.layers,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    const existing = db.signatureLooks.get(account.shopperId) ?? [];
    db.signatureLooks.set(account.shopperId, [look, ...existing]);
    return look;
  }

  async updateSignatureLook(
    lookId: string,
    patch: Partial<Pick<SignatureLook, "name" | "isDefault" | "layers" | "thumbnailUrl">>,
  ): Promise<SignatureLook> {
    const db = getDb();
    const account = requireAccount();
    const looks = db.signatureLooks.get(account.shopperId) ?? [];
    const look = looks.find((l) => l.lookId === lookId);
    if (!look) throw new MirraApiError("validation_failed", "Signature look not found.", 404);
    Object.assign(look, patch, { updatedAt: new Date().toISOString() });
    return look;
  }

  async deleteSignatureLook(lookId: string): Promise<void> {
    const db = getDb();
    const account = requireAccount();
    const looks = db.signatureLooks.get(account.shopperId) ?? [];
    db.signatureLooks.set(
      account.shopperId,
      looks.filter((l) => l.lookId !== lookId),
    );
  }

  // ── Analytics ──
  async trackEvent(event: AnalyticsEvent): Promise<void> {
    console.debug("[analytics:mock]", event.event, event);
  }
}
