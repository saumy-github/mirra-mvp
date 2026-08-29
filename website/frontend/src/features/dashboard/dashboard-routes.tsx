import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { PageFallback } from "@/components/layout/PageFallback";
import DashboardRoot, { AdminLayout, PortalLayout, RequireInternal } from "./dashboard-layout";

// The whole merchant surface is one lazy chunk off `/dashboard/*`, so nothing
// here is downloaded by a shopper who never visits it. Paths are relative to
// the splat mount in `src/router.tsx`; use `dashPath` for links.
const Login = lazy(() => import("./pages/Login"));
const Onboarding = lazy(() => import("./pages/Onboarding"));
const Preview = lazy(() => import("./pages/Preview"));
const Guides = lazy(() => import("./pages/portal/Guides"));

const Overview = lazy(() => import("./pages/portal/Overview"));
const Products = lazy(() => import("./pages/portal/Products"));
const Garments = lazy(() => import("./pages/portal/Garments"));
const GarmentDetail = lazy(() => import("./pages/portal/GarmentDetail"));
const GarmentFlow = lazy(() => import("./pages/portal/GarmentFlow"));
const Assets = lazy(() => import("./pages/portal/Assets"));
const SizeFit = lazy(() => import("./pages/portal/SizeFit"));
const Fabric = lazy(() => import("./pages/portal/Fabric"));
const Publication = lazy(() => import("./pages/portal/Publication"));
const Analytics = lazy(() => import("./pages/portal/Analytics"));
const Team = lazy(() => import("./pages/portal/Team"));
const Billing = lazy(() => import("./pages/portal/Billing"));
const Support = lazy(() => import("./pages/portal/Support"));
const Settings = lazy(() => import("./pages/portal/Settings"));
const Audit = lazy(() => import("./pages/portal/Audit"));

const AdminTenants = lazy(() => import("./pages/admin/Tenants"));
const AdminTenantDetail = lazy(() => import("./pages/admin/TenantDetail"));
const AdminLeads = lazy(() => import("./pages/admin/Leads"));
const AdminSupportQueue = lazy(() => import("./pages/admin/SupportQueue"));
const AdminSync = lazy(() => import("./pages/admin/Sync"));
const AdminChurn = lazy(() => import("./pages/admin/Churn"));

export default function DashboardRoutes() {
  return (
    <Suspense fallback={<PageFallback />}>
      <Routes>
        <Route element={<DashboardRoot />}>
          <Route index element={<Navigate to="portal" replace />} />
          <Route path="login" element={<Login />} />
          <Route path="onboarding" element={<Onboarding />} />
          {/* Outside the portal guard on purpose: a preview link is meant to
              be openable by whoever the merchant shares it with, and it is
              scoped by the tenant's preview token rather than by a session. */}
          <Route path="preview/:slug" element={<Preview />} />

          <Route path="portal" element={<PortalLayout />}>
            <Route index element={<Overview />} />
            <Route path="products" element={<Products />} />
            <Route path="garments" element={<Garments />} />
            {/* Must precede ":id" so /garments/new isn't read as a garment id.
                Adding a garment IS the flow — there is no page in between. */}
            <Route path="garments/new" element={<GarmentFlow />} />
            <Route path="garments/:id" element={<GarmentDetail />} />
            <Route path="garments/:id/setup" element={<GarmentFlow />} />
            <Route path="assets" element={<Assets />} />
            <Route path="size-fit" element={<SizeFit />} />
            <Route path="fabric" element={<Fabric />} />
            <Route path="publication" element={<Publication />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="team" element={<Team />} />
            <Route path="billing" element={<Billing />} />
            <Route path="support" element={<Support />} />
            <Route path="support/guides/:slug" element={<Guides />} />
            <Route path="support/guides" element={<Guides />} />
            <Route path="settings" element={<Settings />} />
            <Route path="audit" element={<Audit />} />
          </Route>

          {/* Each console area is guarded by the capability it needs, so a
              hand-typed URL is refused the same way the navigation is. */}
          <Route path="admin" element={<AdminLayout />}>
            <Route index element={<RequireInternal cap="console.tenants.view"><AdminTenants /></RequireInternal>} />
            <Route path="tenants/:id" element={<RequireInternal cap="console.tenants.view"><AdminTenantDetail /></RequireInternal>} />
            <Route path="leads" element={<RequireInternal cap="console.leads.view"><AdminLeads /></RequireInternal>} />
            <Route path="support" element={<RequireInternal cap="console.support.view"><AdminSupportQueue /></RequireInternal>} />
            <Route path="sync" element={<RequireInternal cap="console.sync.view"><AdminSync /></RequireInternal>} />
            <Route path="churn" element={<RequireInternal cap="console.churn.view"><AdminChurn /></RequireInternal>} />
          </Route>

          <Route path="*" element={<Navigate to="/dashboard/portal" replace />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
