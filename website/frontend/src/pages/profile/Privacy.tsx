import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowUpRight,
  Database,
  KeyRound,
  Settings2,
  ShieldCheck,
  Trash2,
  UserRound,
  X,
} from "lucide-react";
import { useAccount, useAuthMutations } from "@/hooks/use-shopper";
import { getRuntimeProvider } from "@/integrations/mirra-api";
import type { ShopperAccount } from "@/integrations/mirra-api/types";

const SETTINGS_TABS = [
  { id: "account", label: "Account", icon: UserRound },
  { id: "preferences", label: "Preferences", icon: Settings2 },
  { id: "data", label: "Data & privacy", icon: ShieldCheck },
  { id: "sessions", label: "Sessions", icon: KeyRound },
] as const;

type SettingsTab = (typeof SETTINGS_TABS)[number]["id"];

/** Route-backed settings dialog; account changes still use the existing API mutations. */
export default function Privacy() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: account } = useAccount();
  const { logout } = useAuthMutations();
  const [activeTab, setActiveTab] = useState<SettingsTab>("account");
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const deleteConfirmationRef = useRef<HTMLDivElement>(null);
  const api = getRuntimeProvider();

  useEffect(() => {
    if (account && dialogRef.current && !dialogRef.current.open) dialogRef.current.showModal();
  }, [account]);

  useEffect(() => {
    if (!confirmingDelete) return;
    deleteConfirmationRef.current?.scrollIntoView({
      block: "nearest",
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
    });
  }, [confirmingDelete]);

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
    <dialog
      ref={dialogRef}
      className="profile-settings-dialog"
      aria-labelledby="profile-settings-title"
      onCancel={(event) => {
        event.preventDefault();
        navigate("/profile");
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) navigate("/profile");
      }}
    >
      <div className="profile-settings-frame">
        <nav className="profile-settings-nav" aria-label="Settings sections">
          <div role="tablist" aria-label="Settings sections">
            {SETTINGS_TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                id={`settings-tab-${id}`}
                type="button"
                role="tab"
                aria-selected={activeTab === id}
                aria-controls={`settings-panel-${id}`}
                tabIndex={activeTab === id ? 0 : -1}
                onClick={() => setActiveTab(id)}
                onKeyDown={(event) => {
                  const current = SETTINGS_TABS.findIndex((tab) => tab.id === id);
                  let next = current;
                  if (event.key === "ArrowDown" || event.key === "ArrowRight")
                    next = (current + 1) % SETTINGS_TABS.length;
                  else if (event.key === "ArrowUp" || event.key === "ArrowLeft")
                    next = (current - 1 + SETTINGS_TABS.length) % SETTINGS_TABS.length;
                  else if (event.key === "Home") next = 0;
                  else if (event.key === "End") next = SETTINGS_TABS.length - 1;
                  else return;
                  event.preventDefault();
                  setActiveTab(SETTINGS_TABS[next].id);
                  (
                    event.currentTarget.parentElement?.children[next] as HTMLElement | undefined
                  )?.focus();
                }}
              >
                <Icon aria-hidden size={19} strokeWidth={1.7} />
                {label}
              </button>
            ))}
          </div>
        </nav>

        <div className="profile-settings-content">
          <header className="profile-settings-header">
            <h1 id="profile-settings-title">Settings</h1>
            <button type="button" aria-label="Close settings" onClick={() => navigate("/profile")}>
              <X aria-hidden size={19} />
            </button>
          </header>

          <div
            key={activeTab}
            id={`settings-panel-${activeTab}`}
            className="profile-settings-panel"
            role="tabpanel"
            aria-labelledby={`settings-tab-${activeTab}`}
          >
            {activeTab === "account" && (
              <section className="profile-settings-section">
                <h2>Your account</h2>
                <div className="profile-settings-identity">
                  <span className="profile-account__initial" aria-hidden>
                    {account.displayName.trim().charAt(0).toUpperCase() || "M"}
                  </span>
                  <div>
                    <strong>{account.displayName}</strong>
                    <span>{account.isGuest ? "Guest account" : account.email}</span>
                  </div>
                </div>
                {!account.isGuest && (
                  <p className="profile-settings-note">
                    {account.emailVerified ? "Email verified" : "Email verification pending"}
                    {!account.emailVerified && (
                      <>
                        {" "}
                        · <Link to="/auth/verify-email">Verify email</Link>
                      </>
                    )}
                  </p>
                )}
                <div className="profile-settings-shortcuts">
                  <h3>Manage your profile</h3>
                  <SettingsLink to="/profile/measurements" label="Measurements & fit" />
                  <SettingsLink to="/profile/avatar" label="3D avatar" />
                  <SettingsLink to="/profile/signature-looks" label="My Looks" />
                </div>
              </section>
            )}

            {activeTab === "preferences" && (
              <section className="profile-settings-section">
                <h2>Preferences</h2>
                <ConsentRow
                  title="Remember my styling preferences"
                  body="Keep optional avatar setup answers for this browser session."
                  checked={account.consents.preferenceStorage}
                  disabled={consents.isPending}
                  onChange={(value) => consents.mutate({ preferenceStorage: value })}
                />
                {consents.error && (
                  <p className="profile-inline-error" role="alert">
                    That preference could not be saved. Your previous choice has been restored.
                  </p>
                )}
                <div className="profile-settings-row">
                  <div>
                    <strong>Units & fit</strong>
                    <small>Choose display units and how each garment should fit.</small>
                  </div>
                  <Link to="/profile/measurements" className="profile-settings-action">
                    Adjust
                  </Link>
                </div>
                <p className="profile-settings-note">
                  Fit choices and display units stay in this browser session. Measurements are saved
                  to your account.
                </p>
              </section>
            )}

            {activeTab === "data" && (
              <section className="profile-settings-section">
                <h2>Data & privacy</h2>
                <p className="profile-settings-intro">
                  Review the details saved with your account and remove them when you choose.
                </p>
                <div className="profile-settings-shortcuts profile-settings-shortcuts--data">
                  <SettingsLink to="/profile/measurements" label="Measurements" />
                  <SettingsLink to="/profile/avatar" label="Generated avatar" />
                  <SettingsLink to="/profile/signature-looks" label="My Looks" />
                </div>
                <div className="profile-settings-data-copy">
                  <Database aria-hidden size={18} />
                  <p>You can remove your generated avatar separately on its page.</p>
                </div>
                <div className="profile-settings-row profile-settings-delete-row">
                  <div>
                    <strong>Delete account</strong>
                    <small>Removes your account and its profile data permanently.</small>
                  </div>
                  {!confirmingDelete && (
                    <button
                      type="button"
                      className="profile-settings-danger"
                      onClick={() => setConfirmingDelete(true)}
                    >
                      Delete account
                    </button>
                  )}
                </div>
                {confirmingDelete && (
                  <div ref={deleteConfirmationRef} className="profile-settings-confirm">
                    <Trash2 aria-hidden size={20} />
                    <div>
                      <strong>Delete everything?</strong>
                      <span>This cannot be undone.</span>
                    </div>
                    <button type="button" onClick={() => setConfirmingDelete(false)}>
                      Keep account
                    </button>
                    <button
                      type="button"
                      disabled={deleteAccount.isPending}
                      onClick={() => deleteAccount.mutate()}
                    >
                      {deleteAccount.isPending ? "Deleting…" : "Delete permanently"}
                    </button>
                  </div>
                )}
                {deleteAccount.error && (
                  <p className="profile-inline-error" role="alert">
                    Account deletion did not complete. Your account and data are still available.
                  </p>
                )}
              </section>
            )}

            {activeTab === "sessions" && (
              <section className="profile-settings-section">
                <h2>Session</h2>
                <p className="profile-settings-intro">
                  You are signed in on this device. Sign out here when you finish using it.
                </p>
                <div className="profile-settings-row">
                  <div>
                    <strong>This device</strong>
                    <small>End the current browser session.</small>
                  </div>
                  <button
                    type="button"
                    disabled={logout.isPending}
                    onClick={() =>
                      logout.mutate(undefined, { onSuccess: () => navigate("/auth/login") })
                    }
                  >
                    {logout.isPending ? "Signing out…" : "Sign out"}
                  </button>
                </div>
                {logout.error && (
                  <p className="profile-inline-error" role="alert">
                    Sign out did not complete. Please try again.
                  </p>
                )}
              </section>
            )}
          </div>
        </div>
      </div>
    </dialog>
  );
}

function SettingsLink({ to, label }: { to: string; label: string }) {
  return (
    <Link to={to}>
      <span>{label}</span>
      <ArrowUpRight aria-hidden size={17} strokeWidth={1.7} />
    </Link>
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
  onChange: (value: boolean) => void;
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
        onChange={(event) => onChange(event.target.checked)}
      />
    </label>
  );
}
