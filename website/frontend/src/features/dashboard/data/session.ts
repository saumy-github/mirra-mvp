// Demo session layer for the dashboard prototype (was `lib/auth.ts`, which read
// httpOnly cookies in a Next server component).
//
// This is a persona switcher, NOT authentication — it is entirely separate from
// the shopper-facing session in `@/stores` + `@/integrations/mirra-api`. When
// the merchant surface moves onto the real backend, this module is the single
// seam that gets replaced: the tenant/membership/role shape below is what the
// FastAPI side needs to grow.
//
// Only the session ids are persisted (a few bytes) so a page reload keeps you
// signed in; the data itself is reseeded from `store.ts` on every load.
import { useSyncExternalStore } from "react";
import { getDb, newId, updateDb } from "./store";
import { canInternal } from "./rbac";
import type { BrandRole, Membership, Tenant, User } from "./types";

const SESSION_KEY = "mirra.dashboard.session";
const VIEW_AS_KEY = "mirra.dashboard.view-as"; // internal staff impersonation, audited

/** How long a staff view-as session lasts before it has to be re-justified. */
export const VIEW_AS_TTL_MINUTES = 30;

export type ViewAsMode = "read_only" | "write";

export interface ViewAsGrant {
  tenantId: string;
  mode: ViewAsMode;
  reason: string;
  startedAt: string;
  expiresAt: string;
}

export interface SessionContext {
  user: User;
  /** Tenant the user is operating in (own membership, or view-as for staff). */
  tenant: Tenant | null;
  /**
   * The **effective** brand role. For staff in view-as this is a projection of
   * what they are allowed to do inside someone else's workspace — never their
   * console rank. Impersonation cannot grant more than the impersonated seat.
   */
  role: BrandRole | null;
  isInternal: boolean;
  impersonating: boolean;
  viewAs: ViewAsGrant | null;
}

let version = 0;
const listeners = new Set<() => void>();

function emit() {
  version += 1;
  for (const l of listeners) l();
}

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null; // private mode / storage disabled — session just won't persist
  }
}

function write(key: string, value: string | null) {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    /* ignore */
  }
  emit();
}

function readGrant(): ViewAsGrant | null {
  const raw = read(VIEW_AS_KEY);
  if (!raw) return null;
  try {
    const grant = JSON.parse(raw) as ViewAsGrant;
    // Time-limited on purpose: an impersonation session left open for a week
    // is indistinguishable from an account takeover in an audit log.
    if (new Date(grant.expiresAt).getTime() < Date.now()) return null;
    return grant;
  } catch {
    return null;
  }
}

/**
 * Read-only is the default and the only mode most staff ever get.
 *
 * `write` requires `viewas.elevate` (admin only) AND an explicit choice, and
 * even then it maps to Merchandiser rather than Owner: nobody impersonating a
 * customer needs to change their billing or remove their team.
 */
function roleForGrant(actor: User, grant: ViewAsGrant): BrandRole {
  if (grant.mode === "write" && canInternal(actor.internalRole, "viewas.elevate")) {
    return "brand_merchandiser";
  }
  return "brand_viewer";
}

export function getSession(): SessionContext | null {
  const userId = read(SESSION_KEY);
  if (!userId) return null;
  const db = getDb();
  const user = db.users.find((u) => u.id === userId);
  if (!user) return null;

  const isInternal = Boolean(user.internalRole);
  let tenant: Tenant | null = null;
  let role: BrandRole | null = null;
  let grant: ViewAsGrant | null = null;

  if (isInternal) {
    grant = readGrant();
    if (grant && canInternal(user.internalRole, "viewas.start")) {
      tenant = db.tenants.find((t) => t.id === grant!.tenantId) ?? null;
      role = tenant ? roleForGrant(user, grant) : null;
    } else {
      grant = null;
    }
  } else {
    const membership: Membership | undefined = db.memberships.find(
      (m) => m.userId === user.id && m.status === "active",
    );
    if (membership) {
      tenant = db.tenants.find((t) => t.id === membership.tenantId) ?? null;
      role = membership.role;
    }
  }
  return {
    user,
    tenant,
    role,
    isInternal,
    impersonating: Boolean(grant && tenant),
    viewAs: tenant ? grant : null,
  };
}

/**
 * Callers below the route guards know a session exists. Throwing here would
 * take out the whole page on a stale render, so this returns the session and
 * leaves the guard in `dashboard-layout.tsx` to do the redirecting.
 */
export function requireSession(): SessionContext {
  const s = getSession();
  if (!s) throw new Error("UNAUTHENTICATED");
  return s;
}

export function signIn(userId: string) {
  write(VIEW_AS_KEY, null);
  write(SESSION_KEY, userId);
}

export function signOut() {
  write(VIEW_AS_KEY, null);
  write(SESSION_KEY, null);
}

/**
 * Staff-only: enter a tenant workspace, read-only unless explicitly elevated,
 * always with a reason, always time-limited, always audited.
 */
export function startViewAs(
  actor: User,
  tenantId: string,
  reason: string,
  mode: ViewAsMode = "read_only",
) {
  if (!canInternal(actor.internalRole, "viewas.start")) throw new Error("FORBIDDEN");
  if (mode === "write" && !canInternal(actor.internalRole, "viewas.elevate")) {
    throw new Error("FORBIDDEN");
  }
  if (reason.trim().length < 4) throw new Error("REASON_REQUIRED");

  const startedAt = new Date();
  const expires = new Date(startedAt.getTime() + VIEW_AS_TTL_MINUTES * 60_000);
  const grant: ViewAsGrant = {
    tenantId,
    mode,
    reason: reason.trim(),
    startedAt: startedAt.toISOString(),
    expiresAt: expires.toISOString(),
  };
  write(VIEW_AS_KEY, JSON.stringify(grant));
  updateDb((db) => {
    const tenant = db.tenants.find((t) => t.id === tenantId);
    db.auditEvents.unshift({
      id: newId("au"),
      tenantId,
      actorId: actor.id,
      actorName: actor.name,
      action: "impersonation.start",
      target: tenant ? `${tenant.name} workspace` : tenantId,
      detail: `${mode === "write" ? "Write access" : "Read-only"} · ${grant.reason} · expires ${expires.toLocaleTimeString()}`,
      at: startedAt.toISOString(),
    });
  });
}

export function stopViewAs(actor: User) {
  const grant = readGrant();
  write(VIEW_AS_KEY, null);
  if (grant) {
    updateDb((db) => {
      db.auditEvents.unshift({
        id: newId("au"),
        tenantId: grant.tenantId,
        actorId: actor.id,
        actorName: actor.name,
        action: "impersonation.end",
        target: grant.tenantId,
        at: new Date().toISOString(),
      });
    });
  }
}

/** Subscribe to sign-in / sign-out / view-as changes. */
export function useSession(): SessionContext | null {
  useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => version,
    () => version,
  );
  return getSession();
}
