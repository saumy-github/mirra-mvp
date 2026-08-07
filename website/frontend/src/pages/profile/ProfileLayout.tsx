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
 *
 * Laid out as a ruled column: a framing header, a rule of sections, and the
 * page content. Nothing here is a card.
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
    <main className="min-h-dvh bg-vellum">
      <header className="flex items-center justify-between border-b border-hairline px-6 py-5 lg:px-12">
        <Link to="/studio" className="flex items-center gap-3.5">
          <MirraMark size={22} strokeWidth={1.15} className="text-graphite" />
          <span className="text-[11px] tracking-[0.34em] text-graphite uppercase">Mirra</span>
          <span aria-hidden className="h-4 w-px bg-hairline" />
          <span className="eyebrow">Profile</span>
        </Link>
        <button
          type="button"
          onClick={() => logout.mutate(undefined, { onSuccess: () => navigate("/auth/login") })}
          className="text-[10px] tracking-[0.14em] text-ash uppercase transition-colors hover:text-graphite"
        >
          Sign out
        </button>
      </header>

      <div className="page-grid mx-auto w-full max-w-320 px-6 lg:px-12">
        <nav
          aria-label="Profile sections"
          className="col-span-12 flex gap-6 overflow-x-auto border-b border-hairline py-4 lg:col-span-3 lg:mt-10 lg:flex-col lg:gap-0 lg:border-b-0 lg:py-0"
        >
          {NAV.map((item) => {
            const current = pathname === item.href;
            return (
              <Link
                key={item.href}
                to={item.href}
                aria-current={current ? "page" : undefined}
                className={`relative py-2 text-[11px] tracking-[0.14em] whitespace-nowrap uppercase transition-colors ${
                  current ? "font-medium text-graphite" : "text-slate hover:text-graphite"
                }`}
              >
                <span
                  aria-hidden
                  className={`absolute top-1/2 -left-3.5 hidden size-[3px] -translate-y-1/2 rounded-full bg-graphite lg:block ${
                    current ? "opacity-100" : "opacity-0"
                  }`}
                />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="col-span-12 py-10 lg:col-span-8 lg:col-start-5 lg:border-l lg:border-hairline lg:pl-10">
          <Outlet />
        </div>
      </div>
    </main>
  );
}
