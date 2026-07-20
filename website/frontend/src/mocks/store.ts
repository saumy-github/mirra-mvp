import type {
  AvatarProfile,
  CaptureSession,
  MeasurementField,
  ShopperAccount,
  SignatureLook,
} from "@/integrations/mirra-api/types";
import { freshMeasurements } from "./fixtures";
import { swatchDataUri } from "./placeholder";

/** Single-user, in-memory store for local dev. Resets on page reload. */

export interface MockAccount extends ShopperAccount {
  password: string;
}

export interface MockCaptureSession extends CaptureSession {
  accountId: string;
}

export interface MockAvatarJob {
  jobId: string;
  accountId: string;
  startedAt: string;
  cancelled: boolean;
  simulateFailure: boolean;
  failureReason: string | null;
  avatarProfileId: string | null;
}

interface Db {
  accounts: Map<string, MockAccount>; // by shopperId
  accountsByEmail: Map<string, string>; // email -> shopperId
  currentAccountId: string | null;
  captureSessions: Map<string, MockCaptureSession>;
  captureSessionsByToken: Map<string, string>; // token -> captureSessionId
  avatarJobs: Map<string, MockAvatarJob>;
  avatarProfiles: Map<string, AvatarProfile>; // by accountId
  measurements: Map<string, MeasurementField[]>; // by accountId
  signatureLooks: Map<string, SignatureLook[]>; // by accountId
  seq: number;
}

const db: Db = {
  accounts: new Map(),
  accountsByEmail: new Map(),
  currentAccountId: null,
  captureSessions: new Map(),
  captureSessionsByToken: new Map(),
  avatarJobs: new Map(),
  avatarProfiles: new Map(),
  measurements: new Map(),
  signatureLooks: new Map(),
  seq: 0,
};

export function getDb(): Db {
  return db;
}

export function nextId(prefix: string): string {
  db.seq += 1;
  return `${prefix}_${db.seq.toString(36)}`;
}

/**
 * Demo account for QuickAccessControl — has a saved avatar already, so
 * "quick access" jumps straight to the studio like the real thing would
 * for a returning user. Seeded once at module load.
 */
function seedDemoAccount(): void {
  const shopperId = "acct_demo";
  const account: MockAccount = {
    shopperId,
    email: "ava@mirra.dev",
    displayName: "Ava",
    emailVerified: true,
    isGuest: false,
    createdAt: new Date().toISOString(),
    consents: { terms: true, privacy: true, preferenceStorage: true },
    password: "demo1234",
  };
  db.accounts.set(shopperId, account);
  db.accountsByEmail.set(account.email.toLowerCase(), shopperId);
  db.avatarProfiles.set(shopperId, {
    avatarProfileId: "avp_demo",
    avatarLabel: "09-V1",
    version: 1,
    engineVersion: "demo-avatar-0.1",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    previewAssetUrl: swatchDataUri("#c7c7cc", "avatar preview"),
    measurements: freshMeasurements(),
    unitsPreference: "metric",
  });
}
seedDemoAccount();
