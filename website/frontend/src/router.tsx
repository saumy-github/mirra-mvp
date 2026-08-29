import { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import { PageFallback } from "@/components/layout/PageFallback";

// Marketing — the standalone landing overhaul, which is the source of truth
// for this surface. The previous landing site was phased out wholesale.
const MarketingLayout = lazy(() => import("@/features/marketing/marketing-layout"));
const Home = lazy(() => import("@/pages/Home"));
const Pricing = lazy(() => import("@/pages/Pricing"));
const FAQ = lazy(() => import("@/pages/FAQ"));
const Join = lazy(() => import("@/pages/Join"));
const PublicInfo = lazy(() => import("@/pages/PublicInfo"));

// Shopper auth — Google only for the pilot (doc 06). Reached from the "Log in"
// button in the site navbar.
const SignUp = lazy(() => import("@/pages/auth/SignUp"));
const Login = lazy(() => import("@/pages/auth/Login"));
const VerifyEmail = lazy(() => import("@/pages/auth/VerifyEmail"));
const ForgotPassword = lazy(() => import("@/pages/auth/ForgotPassword"));
const AuthCallback = lazy(() => import("@/pages/auth/AuthCallback"));

// Business auth — the full email/password flow, reached from /join. Separate
// from the shopper pages above because the two surfaces have different
// providers, different consent copy, and different destinations. This is
// distinct from /dashboard/login, which is the dashboard's demo persona
// switcher, not an account sign-in.
const BusinessSignUp = lazy(() => import("@/pages/business/SignUp"));
const BusinessLogin = lazy(() => import("@/pages/business/Login"));
const BusinessVerifyEmail = lazy(() => import("@/pages/business/VerifyEmail"));
const BusinessForgotPassword = lazy(() => import("@/pages/business/ForgotPassword"));

// Onboarding — only the QR pairing step survives. Measurement intake and
// avatar generation now live under /profile (doc 13, D7).
const QrPairing = lazy(() => import("@/pages/onboarding/QrPairing"));

// Studio — the heaviest page; kept in its own chunk like everything else
// here, and the natural place a future R3F/Three.js upgrade stays isolated.
const Studio = lazy(() => import("@/pages/Studio"));

// Profile
const ProfileLayout = lazy(() => import("@/pages/profile/ProfileLayout"));
const Profile = lazy(() => import("@/pages/profile/Profile"));
const ProfileAvatar = lazy(() => import("@/pages/profile/ProfileAvatar"));
const ProfileMeasurements = lazy(() => import("@/pages/profile/ProfileMeasurements"));
const SignatureLooks = lazy(() => import("@/pages/profile/SignatureLooks"));
const Privacy = lazy(() => import("@/pages/profile/Privacy"));

// Merchant dashboard — the ported prototype. Self-contained leaf module: it
// owns its own routes, styling, and (for now) its own seeded demo data.
const DashboardRoutes = lazy(() => import("@/features/dashboard/dashboard-routes"));

// Errors
const ProductUnavailable = lazy(() => import("@/pages/errors/ProductUnavailable"));
const AccountInactive = lazy(() => import("@/pages/errors/AccountInactive"));
const NotFound = lazy(() => import("@/pages/NotFound"));

export function AppRoutes() {
  return (
    <Suspense fallback={<PageFallback />}>
      <Routes>
        <Route element={<MarketingLayout />}>
          <Route path="/" element={<Home />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/faq" element={<FAQ />} />
          <Route path="/join" element={<Join />} />
          <Route path="/terms" element={<PublicInfo />} />
          <Route path="/privacy" element={<PublicInfo />} />
          <Route path="/security" element={<PublicInfo />} />
        </Route>

        <Route path="/auth/sign-up" element={<SignUp />} />
        <Route path="/auth/login" element={<Login />} />
        <Route path="/auth/verify-email" element={<VerifyEmail />} />
        <Route path="/auth/forgot-password" element={<ForgotPassword />} />
        <Route path="/auth/callback" element={<AuthCallback />} />

        <Route path="/business/sign-up" element={<BusinessSignUp />} />
        <Route path="/business/login" element={<BusinessLogin />} />
        <Route path="/business/verify-email" element={<BusinessVerifyEmail />} />
        <Route path="/business/forgot-password" element={<BusinessForgotPassword />} />

        <Route path="/onboarding/qr" element={<QrPairing />} />

        <Route path="/studio" element={<Studio />} />

        <Route element={<ProfileLayout />}>
          <Route path="/profile" element={<Profile />} />
          <Route path="/profile/avatar" element={<ProfileAvatar />} />
          <Route path="/profile/measurements" element={<ProfileMeasurements />} />
          <Route path="/profile/signature-looks" element={<SignatureLooks />} />
          <Route path="/profile/privacy" element={<Privacy />} />
        </Route>

        <Route path="/dashboard/*" element={<DashboardRoutes />} />

        <Route path="/error/product-unavailable" element={<ProductUnavailable />} />
        <Route path="/error/account-inactive" element={<AccountInactive />} />

        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}
