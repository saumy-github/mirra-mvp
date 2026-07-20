import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useEffect } from "react";
import { MirraMark } from "@/components/ui/logo";
import { useAuthMutations, useAccount } from "@/hooks/use-shopper";

const NAV = [
  { href: "/profile", label: "Overview" },
  { href: "/profile/avatar", label: "Avatar" },
  { href: "/profile/measurements", label: "Measurements" },
  { href: "/profile/signature-looks", label: "Signature Looks" },
  { href: "/profile/privacy", label: "Privacy" },
];

/**
 * Lightweight account profile area. Deliberately not a social space:
 * no feeds, no cross-account products — just the account's own data.
 */
export default function ProfileLayout() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { data: account, isLoading } = useAccount();
  const { logout } = useAuthMutations();

  useEffect(() => {
    if (!isLoading && !account) navigate("/auth/login?next=%2Fprofile", { replace: true });
  }, [account, isLoading, navigate]);

  if (!account) return null;

  return (
    <main className="mx-auto min-h-dvh w-full max-w-3xl px-6 py-10">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <MirraMark size={26} className="text-ink" />
          <span className="font-mono text-xs tracking-[0.3em] text-muted uppercase">Profile</span>
        </div>
        <button
          type="button"
          onClick={() => logout.mutate(undefined, { onSuccess: () => navigate("/auth/login") })}
          className="text-sm text-muted hover:text-ink"
        >
          Sign out
        </button>
      </header>

      <nav aria-label="Profile sections" className="mt-8 flex flex-wrap gap-1 border-b border-line">
        {NAV.map((item) => (
          <Link
            key={item.href}
            to={item.href}
            aria-current={pathname === item.href ? "page" : undefined}
            className={`-mb-px border-b-2 px-3.5 py-2.5 text-sm transition-colors ${
              pathname === item.href
                ? "border-ink font-medium text-ink"
                : "border-transparent text-muted hover:text-ink"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="py-8">
        <Outlet />
      </div>
    </main>
  );
}
