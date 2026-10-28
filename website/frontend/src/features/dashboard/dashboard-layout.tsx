import type { ReactNode } from "react";
import { Link, Navigate, Outlet, useLocation } from "react-router-dom";
import { useDbVersion } from "./data/store";
import { useSession } from "./data/session";
import { getEntitlements } from "./data/entitlements";
import { can, canInternal } from "./data/rbac";
import { AppShell, MirraLogo, TenantStatusBadge } from "./components/shell";
import { ADMIN_NAV, PORTAL_NAV } from "./components/nav-items";
import { Banner } from "./components/ui";
import { isLiveTenant } from "./data/live-session";
import { dashPath } from "./routes";
import "./dashboard.css";

/**
 * Root of the merchant surface. Owns the scoped background and type scale that
 * the prototype set on <body>, so nothing leaks into the shopper-facing routes.
 */
export default function DashboardRoot() {
  return (
    <div className="dashboard-root">
      <Outlet />
    </div>
  );
}

/**
 * Merchant portal guard. The prototype did this server-side in
 * `app/portal/layout.tsx`; the redirect ladder is unchanged.
 */
export function PortalLayout() {
  const session = useSession();
  const location = useLocation();
  useDbVersion(); // tenant status/launch changes must repaint the shell

  // No dashboard session: resolve the real business session first (Start
  // sends signed-out visitors to /business/login). The demo persona picker
  // stays reachable at /dashboard/login. `next` keeps a reload on the same page.
  const start = `${dashPath.start}?next=${encodeURIComponent(location.pathname + location.search)}`;
  if (!session) return <Navigate to={start} replace />;
  if (session.isInternal && !session.tenant) return <Navigate to={dashPath.admin} replace />;
  const tenant = session.tenant;
  if (!tenant) return <Navigate to={start} replace />;
  if (!tenant.onboarding.activated && !session.impersonating)
    return <Navigate to={dashPath.onboarding} replace />;

  const ent = getEntitlements(tenant);
  // Navigation is filtered to what this seat can actually do, so a Viewer is
  // never routed into Billing purely to be refused there.
  const live = isLiveTenant(tenant.id);
  const nav = PORTAL_NAV.filter(
    (item) => (!item.needs || can(session.role, item.needs)) && !(live && item.demoOnly),
  );

  return (
    <AppShell
      session={session}
      nav={nav}
      brand={
        <div>
          <MirraLogo />
          <div className="mt-2 flex items-center gap-2">
            <span className="truncate text-[13px] font-medium text-stone-700">{tenant.name}</span>
            <TenantStatusBadge status={tenant.status} />
          </div>
        </div>
      }
    >
      {!ent.publicSurfaceEnabled && (
        <div className="mb-6">
          <Banner tone={tenant.status === "suspended" || tenant.status === "cancelled" ? "danger" : "warn"}>
            <strong>Your public try-on page is currently offline.</strong>{" "}
            {ent.publicSurfaceDisabledReason}{" "}
            {tenant.status === "suspended" || tenant.status === "cancelled" ? (
              <Link to={dashPath.billing} className="font-semibold underline">Resolve in Billing →</Link>
            ) : (
              <Link to={dashPath.publication} className="font-semibold underline">Manage in Publication →</Link>
            )}
          </Banner>
        </div>
      )}
      <Outlet />
    </AppShell>
  );
}

/** A page with no backend yet: a real workspace is sent to the Overview instead. */
export function DemoOnly({ children }: { children: ReactNode }) {
  const session = useSession();
  if (isLiveTenant(session?.tenant?.id)) return <Navigate to={dashPath.portal} replace />;
  return <>{children}</>;
}

/**
 * Pick the page for this tenant: the server-backed one for a real workspace,
 * the in-memory one for the seeded demo. Never mix them — the demo tenant's
 * ids mean nothing to the API, and a real workspace's data isn't in the store.
 */
export function ByTenant({ live, demo }: { live: ReactNode; demo: ReactNode }) {
  const session = useSession();
  return <>{isLiveTenant(session?.tenant?.id) ? live : demo}</>;
}

/**
 * Mirra staff console.
 *
 * Least privilege means the *specific* internal role, not merely "is staff":
 * checking `isInternal` alone is what put Sales in front of tenant lifecycle
 * controls. Each console area declares the capability it needs, and a role
 * with none of them has no console at all.
 */
export function AdminLayout() {
  const session = useSession();
  useDbVersion();

  if (!session) return <Navigate to={dashPath.login} replace />;
  if (!session.isInternal) return <Navigate to={dashPath.portal} replace />;

  const role = session.user.internalRole;
  const nav = ADMIN_NAV.filter((item) => !item.needs || canInternal(role, item.needs));
  if (nav.length === 0) return <Navigate to={dashPath.login} replace />;

  return (
    <AppShell session={session} nav={nav} brand={<MirraLogo sub="Console" />}>
      <Outlet />
    </AppShell>
  );
}

/**
 * Wrap a console page in the capability it requires, so a URL typed by hand
 * is refused the same way the navigation is.
 */
export function RequireInternal({
  cap,
  children,
}: {
  cap: Parameters<typeof canInternal>[1];
  children: ReactNode;
}) {
  const session = useSession();
  if (!session?.isInternal) return <Navigate to={dashPath.portal} replace />;
  if (!canInternal(session.user.internalRole, cap)) {
    return (
      <Banner tone="warn">
        Your console role doesn&apos;t include this area. If you need it, ask an Admin rather than
        working around it.
      </Banner>
    );
  }
  return <>{children}</>;
}
