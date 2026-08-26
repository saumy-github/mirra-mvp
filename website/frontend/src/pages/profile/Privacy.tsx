import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Database, KeyRound, ShieldCheck, Trash2 } from "lucide-react";
import { useAccount } from "@/hooks/use-shopper";
import { getRuntimeProvider } from "@/integrations/mirra-api";
import type { ShopperAccount } from "@/integrations/mirra-api/types";

/**
 * Privacy controls: plain-language consents, deletion workflows, and no
 * hidden switches. Copy placeholders here are subject to legal review.
 */
export default function Privacy() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: account } = useAccount();
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const api = getRuntimeProvider();

  const consents = useMutation({
    mutationFn: (patch: Partial<ShopperAccount["consents"]>) => api.updateConsents(patch),
    onMutate: async (patch) => {
      await qc.cancelQueries({ queryKey: ["account", "me"] });
      const previous = qc.getQueryData<ShopperAccount>(["account", "me"]);
      qc.setQueryData<ShopperAccount>(["account", "me"], (current) =>
        current ? { ...current, consents: { ...current.consents, ...patch } } : current,
      );
      return { previous };
    },
    onError: (_error, _patch, context) => {
      if (context?.previous) qc.setQueryData(["account", "me"], context.previous);
    },
    onSuccess: (updated) => qc.setQueryData(["account", "me"], updated),
  });

  const deleteAccount = useMutation({
    mutationFn: () => api.deleteAccount(),
    onSuccess: () => {
      qc.clear();
      navigate("/auth/sign-up");
    },
  });

  if (!account) return null;

  return (
    <div className="profile-privacy-page">
      <header className="profile-page-heading profile-privacy-heading">
        <p className="profile-meta">Privacy &amp; data</p>
        <h1>Control what Mirra remembers</h1>
        <p>Change these at any time — nothing here is required to keep shopping.</p>
      </header>

      <div className="profile-privacy-layout">
        <div className="profile-privacy-main">
          <section className="profile-panel profile-privacy-card" aria-busy={consents.isPending}>
            <div className="profile-privacy-card__heading">
              <span>
                <ShieldCheck aria-hidden size={20} strokeWidth={1.55} />
              </span>
              <div>
                <p className="profile-meta">Preferences</p>
                <h2>Consents</h2>
              </div>
            </div>
            <ConsentRow
              title="Remember my styling preferences"
              body="Keeps optional answers, such as preferred fit, to shape your studio. You can turn this off at any time."
              checked={account.consents.preferenceStorage}
              disabled={consents.isPending}
              onChange={(v) => consents.mutate({ preferenceStorage: v })}
            />
            {consents.error && (
              <p className="profile-inline-error" role="alert">
                That preference could not be saved. Your previous choice has been restored.
              </p>
            )}
          </section>

          <section className="profile-panel profile-privacy-card">
            <div className="profile-privacy-card__heading">
              <span>
                <Database aria-hidden size={19} strokeWidth={1.55} />
              </span>
              <div>
                <p className="profile-meta">Storage</p>
                <h2>Your data</h2>
              </div>
            </div>
            <ul className="profile-privacy-list">
              <li>Mirra stores the measurements and avatar data shown in your profile.</li>
              <li>You can remove your current avatar from the Avatar tab.</li>
              <li>Account deletion removes the profile data associated with this account.</li>
            </ul>
            <p className="profile-privacy-legal">
              Product guidance only — final retention and legal language is still under review.
            </p>
          </section>

          <section className="profile-panel profile-privacy-card profile-privacy-sessions">
            <div className="profile-privacy-card__heading">
              <span>
                <KeyRound aria-hidden size={19} strokeWidth={1.55} />
              </span>
              <div>
                <p className="profile-meta">Security</p>
                <h2>Sessions</h2>
              </div>
            </div>
            <p>
              Signing out ends this device&apos;s session. If you open setup on another device, sign
              out there when you finish using it.
            </p>
          </section>
        </div>

        <aside className="profile-panel profile-privacy-delete">
          <span className="profile-privacy-delete__icon">
            <Trash2 aria-hidden size={20} strokeWidth={1.55} />
          </span>
          <p className="profile-meta">Account management</p>
          <h2>Delete account</h2>
          <p>
            Permanently removes your account, avatar, measurements and Signature Looks. This
            can&apos;t be undone.
          </p>
          {confirmingDelete ? (
            <div className="profile-privacy-delete__confirm">
              <button type="button" onClick={() => setConfirmingDelete(false)}>
                Keep my account
              </button>
              <button
                type="button"
                disabled={deleteAccount.isPending}
                onClick={() => deleteAccount.mutate()}
              >
                {deleteAccount.isPending ? "Deleting…" : "Delete everything"}
              </button>
            </div>
          ) : (
            <button type="button" onClick={() => setConfirmingDelete(true)}>
              Delete account…
            </button>
          )}
          {deleteAccount.error && (
            <p className="profile-inline-error" role="alert">
              Account deletion did not complete. Your account and data are still available.
            </p>
          )}
        </aside>
      </div>
    </div>
  );
}

function ConsentRow({
  title,
  body,
  checked,
  disabled,
  onChange,
}: {
  title: string;
  body: string;
  checked: boolean;
  disabled: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="profile-consent-row">
      <span className="profile-consent-row__copy">
        <strong>{title}</strong>
        <span>{body}</span>
      </span>
      <input
        type="checkbox"
        role="switch"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
    </label>
  );
}
