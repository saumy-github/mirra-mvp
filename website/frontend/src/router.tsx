import { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import { PageFallback } from "@/components/layout/PageFallback";

// Marketing — the standalone landing overhaul, which is the source of truth
// for this surface. The previous landing site was phased out wholesale.
const MarketingLayout = lazy(() => import("@/features/marketing/marketing-layout"));
const Home = lazy(() => import("@/pages/Home"));
const Pricing = lazy(() => import("@/pages/Pricing"));
const FAQ = lazy(() => import("@/pages/FAQ"));

// Auth
const SignUp = lazy(() => import("@/pages/auth/SignUp"));
const Login = lazy(() => import("@/pages/auth/Login"));
const VerifyEmail = lazy(() => import("@/pages/auth/VerifyEmail"));
const ForgotPassword = lazy(() => import("@/pages/auth/ForgotPassword"));
const AuthCallback = lazy(() => import("@/pages/auth/AuthCallback"));

// Onboarding
const OnboardingMeasurements = lazy(() => import("@/pages/onboarding/Measurements"));
const OnboardingAvatar = lazy(() => import("@/pages/onboarding/Avatar"));

// Standalone manual measurement intake (no avatar/photo required)
const Measurements = lazy(() => import("@/pages/Measurements"));

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
        </Route>

        <Route path="/auth/sign-up" element={<SignUp />} />
        <Route path="/auth/login" element={<Login />} />
        <Route path="/auth/verify-email" element={<VerifyEmail />} />
        <Route path="/auth/forgot-password" element={<ForgotPassword />} />
        <Route path="/auth/callback" element={<AuthCallback />} />

        <Route path="/measurements" element={<Measurements />} />
        <Route path="/onboarding/measurements" element={<OnboardingMeasurements />} />
        <Route path="/onboarding/avatar" element={<OnboardingAvatar />} />

        <Route path="/studio" element={<Studio />} />

        <Route element={<ProfileLayout />}>
          <Route path="/profile" element={<Profile />} />
          <Route path="/profile/avatar" element={<ProfileAvatar />} />
          <Route path="/profile/measurements" element={<ProfileMeasurements />} />
          <Route path="/profile/signature-looks" element={<SignatureLooks />} />
          <Route path="/profile/privacy" element={<Privacy />} />
        </Route>

        <Route path="/error/product-unavailable" element={<ProductUnavailable />} />
        <Route path="/error/account-inactive" element={<AccountInactive />} />

        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}
