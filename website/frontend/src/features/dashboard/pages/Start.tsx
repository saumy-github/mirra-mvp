import { useEffect, useState } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import type { ShopperAccount } from "@/integrations/mirra-api";
import { MirraLogo } from "../components/shell";
import { Banner, Field } from "../components/ui";
import { inputClass } from "../components/styles";
import {
  bootstrapLiveSession,
  createLiveWorkspace,
  type LiveBootstrap,
} from "../data/live-session";
import { dashPath } from "../routes";

/**
 * Where a business account lands after signing in (/business/login →
 * businessDestination). Resolves the real backend session into a workspace:
 *
 *   not signed in      → /business/login, back here afterwards
 *   no workspace yet   → create one (the account becomes its owner)
 *   has a workspace    → the portal, operating on that real tenant
 *
 * The demo persona switcher at /dashboard/login is unchanged.
 */
/** Only ever resume inside the portal — `next` arrives in the URL. */
function safeNext(raw: string | null): string {
  return raw && raw.startsWith(`${dashPath.portal}`) && !raw.startsWith("//") ? raw : dashPath.portal;
}

export default function DashboardStart() {
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  const [state, setState] = useState<LiveBootstrap | "loading" | { error: string }>("loading");

  useEffect(() => {
    let cancelled = false;
    bootstrapLiveSession()
      .then((result) => !cancelled && setState(result))
      .catch(
        (err: unknown) =>
          !cancelled &&
          setState({ error: err instanceof Error ? err.message : "Could not reach Mirra." }),
      );
    return () => {
      cancelled = true;
    };
  }, []);

  if (state === "loading") {
    return (
      <p className="mx-auto max-w-xl px-6 py-16 text-sm text-muted">Opening your workspace…</p>
    );
  }
  if ("error" in state) {
    return (
      <main className="mx-auto max-w-xl px-6 py-16">
        <MirraLogo />
        <div className="mt-8">
          <Banner tone="danger">{state.error}</Banner>
        </div>
      </main>
    );
  }
  if (state.status === "signed_out") {
    const back = `${dashPath.start}?next=${encodeURIComponent(next)}`;
    return <Navigate to={`/business/login?next=${encodeURIComponent(back)}`} replace />;
  }
  if (state.status === "ready") return <Navigate to={next} replace />;
  return <CreateWorkspace account={state.account} />;
}

function CreateWorkspace({ account }: { account: ShopperAccount }) {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [storeUrl, setStoreUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (name.trim().length < 2) return setError("Enter your brand's name.");
    setBusy(true);
    setError(null);
    try {
      await createLiveWorkspace(account, { name: name.trim(), storeUrl: storeUrl.trim() });
      navigate(dashPath.portal, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "The workspace could not be created.");
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-xl px-6 py-16">
      <MirraLogo />
      <h1 className="mt-8 text-2xl font-semibold tracking-tight">Set up your brand workspace</h1>
      <p className="mt-2 text-[13px] text-muted">
        Signed in as {account.email}. You&apos;ll be the workspace owner, and can connect your
        Shopify store and seat colleagues from Settings and Team.
      </p>
      <form onSubmit={submit} className="mt-8 space-y-5">
        <Field label="Brand name">
          <input
            className={inputClass}
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
          />
        </Field>
        <Field
          label="Store URL"
          hint="Optional — e.g. https://yourbrand.com or yourbrand.myshopify.com"
        >
          <input
            className={inputClass}
            value={storeUrl}
            onChange={(e) => setStoreUrl(e.target.value)}
          />
        </Field>
        {error && <Banner tone="danger">{error}</Banner>}
        <button
          type="submit"
          disabled={busy}
          className="w-full cursor-pointer rounded-xl bg-ink px-4 py-3 text-sm font-semibold text-white disabled:opacity-50"
        >
          {busy ? "Creating…" : "Create workspace"}
        </button>
      </form>
    </main>
  );
}
