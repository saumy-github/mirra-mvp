import { Link, useNavigate } from "react-router-dom";
import { getDb } from "../data/store";
import { signInAction } from "../data/actions";
import { ROLE_LABELS } from "../data/rbac";
import { MirraLogo } from "../components/shell";
import { Banner } from "../components/ui";

// Demo persona switcher. This is NOT the shopper sign-in at /auth/login — the
// merchant surface gets real, organisation-aware sessions when it moves onto
// the FastAPI backend; see features/dashboard/data/session.ts.
export default function DashboardLogin() {
  const navigate = useNavigate();
  const db = getDb();
  const internal = db.users.filter((u) => u.internalRole);
  const brand = db.users.filter((u) => !u.internalRole);

  const roleOf = (userId: string) => db.memberships.find((m) => m.userId === userId)?.role;
  const tenantOf = (userId: string) => {
    const m = db.memberships.find((mm) => mm.userId === userId);
    return db.tenants.find((t) => t.id === m?.tenantId)?.name;
  };

  const UserButton = ({ id, name, sub }: { id: string; name: string; sub: string }) => (
    <form action={(formData: FormData) => navigate(signInAction(formData))}>
      <input type="hidden" name="userId" value={id} />
      <button className="flex w-full cursor-pointer items-center justify-between gap-3 rounded-xl border border-line bg-surface px-4 py-3 text-left transition-colors hover:border-accent hover:bg-accent-soft/40">
        <span>
          <span className="block text-[14px] font-medium text-ink">{name}</span>
          <span className="block text-xs text-muted">{sub}</span>
        </span>
        <span className="text-muted">→</span>
      </button>
    </form>
  );

  return (
    <main className="mx-auto max-w-xl px-6 py-16">
      <MirraLogo />
      <h1 className="mt-8 text-2xl font-semibold tracking-tight">Sign in to your workspace</h1>
      <p className="mt-2 text-[13px] text-muted">
        Demo environment — choose a persona. In production this is a hosted, passwordless
        sign-in with organisation-aware sessions.
      </p>

      {/* Merchant workspaces are created by Mirra sales after the verification
          form and a conversation — there is deliberately no self-serve signup
          here. This is a different door from the shopper sign-in at
          /auth/login, not a duplicate of it. */}
      <div className="mt-4">
        <Banner tone="info">
          Mirra workspaces are set up by our team, so there is no sign-up here. If your brand
          doesn&apos;t have one yet,{" "}
          <Link to="/join" className="font-semibold underline">request access</Link> and we&apos;ll
          be in touch. Shopping rather than selling?{" "}
          <Link to="/auth/login" className="font-semibold underline">Shopper sign-in</Link>.
        </Banner>
      </div>

      <h2 className="mt-8 mb-3 text-xs font-semibold uppercase tracking-wider text-muted">Brand teams</h2>
      <div className="space-y-2">
        {brand.map((u) => {
          const role = roleOf(u.id);
          return (
            <UserButton
              key={u.id}
              id={u.id}
              name={u.name}
              sub={`${tenantOf(u.id) ?? "No workspace"} · ${role ? ROLE_LABELS[role] : "—"}`}
            />
          );
        })}
      </div>

      <h2 className="mt-8 mb-3 text-xs font-semibold uppercase tracking-wider text-muted">Mirra internal</h2>
      <div className="space-y-2">
        {internal.map((u) => (
          <UserButton key={u.id} id={u.id} name={u.name} sub={ROLE_LABELS[u.internalRole!]} />
        ))}
      </div>
    </main>
  );
}
