import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, CheckCircle2, RefreshCw, UserRound } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAccount, useAvatarProfile } from "@/hooks/use-shopper";
import { getRuntimeProvider } from "@/integrations/mirra-api";

function formatDate(value: string | Date) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

function formatTime(value: string | Date) {
  return new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function ProfileAvatar() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: account } = useAccount();
  const { data: avatar, isLoading } = useAvatarProfile(!!account);
  const [confirming, setConfirming] = useState(false);

  const remove = useMutation({
    mutationFn: () => getRuntimeProvider().deleteAvatarProfile(),
    onSuccess: () => {
      qc.setQueryData(["account", "avatar-profile"], null);
      setConfirming(false);
    },
  });

  if (isLoading) return <ProfileAvatarLoading />;

  if (!avatar) {
    return (
      <div className="profile-avatar-page">
        <header className="profile-page-heading profile-avatar-heading">
          <p className="profile-meta">Digital twin</p>
          <h1>Your avatar</h1>
          <p>A private body model that powers your virtual fitting room.</p>
        </header>

        <section className="profile-avatar-empty-state" aria-labelledby="avatar-empty-title">
          <span className="profile-avatar-empty-state__icon" aria-hidden>
            <UserRound size={30} strokeWidth={1.4} />
          </span>
          <div>
            <p className="profile-meta">No avatar on this account</p>
            <h2 id="avatar-empty-title">Start with your measurements</h2>
            <p>
              Mirra will only show an avatar here after you add measurements and generation
              finishes. No example image is presented as your own.
            </p>
          </div>
          <button
            type="button"
            className="profile-dark-button"
            onClick={() => navigate("/measurements?next=/onboarding/avatar")}
          >
            Add measurements <ArrowRight aria-hidden size={17} strokeWidth={1.7} />
          </button>
        </section>
      </div>
    );
  }

  const image = avatar.previewAssetUrl;
  const updatedAt = avatar.updatedAt;

  return (
    <div className="profile-avatar-page">
      <header className="profile-page-heading profile-avatar-heading">
        <p className="profile-meta">Digital twin</p>
        <h1>Your avatar</h1>
        <p>Review the current model, update its measurements, or rebuild it when needed.</p>
      </header>

      <div className="profile-avatar-primary">
        <section className="profile-avatar-stage" aria-label="Avatar preview">
          {image ? (
            <>
              <span
                className="profile-avatar-stage__background"
                style={{ backgroundImage: `url(${image})` }}
                aria-hidden
              />
              <img
                src={image}
                alt={`Avatar ${avatar.avatarLabel}`}
                className="profile-avatar-stage__figure"
              />
            </>
          ) : (
            <div className="profile-avatar-stage__unavailable" role="status">
              <UserRound aria-hidden size={36} strokeWidth={1.35} />
              <strong>Preview unavailable</strong>
              <span>Your avatar data is saved, but no rendered preview is available yet.</span>
            </div>
          )}

          {image && <span className="profile-avatar-stage__label">Front preview</span>}
        </section>

        <aside className="profile-panel profile-avatar-status">
          <div>
            <p className="profile-meta">Avatar status</p>
            <span
              className={
                image
                  ? "profile-avatar-status__chip"
                  : "profile-avatar-status__chip profile-avatar-status__chip--muted"
              }
            >
              {image ? (
                <CheckCircle2 aria-hidden size={15} strokeWidth={1.8} />
              ) : (
                <RefreshCw aria-hidden size={15} strokeWidth={1.8} />
              )}
              {image ? "Up to date" : "Preview unavailable"}
            </span>
          </div>

          <div className="profile-avatar-status__updated">
            <p className="profile-meta">Last updated</p>
            <p>{formatDate(updatedAt)}</p>
          </div>

          <button
            type="button"
            className="profile-dark-button profile-avatar-status__update"
            onClick={() => navigate("/onboarding/measurements")}
          >
            Review fit profile
          </button>

          <div className="profile-avatar-status__actions">
            <button type="button" onClick={() => navigate("/onboarding/avatar")}>
              <RefreshCw aria-hidden size={19} strokeWidth={1.65} />
              <span>Rebuild avatar</span>
              <ArrowRight aria-hidden size={17} strokeWidth={1.6} />
            </button>
          </div>
        </aside>
      </div>

      <section id="avatar-versions" className="profile-panel profile-avatar-versions">
        <div className="profile-avatar-versions__header">
          <p className="profile-meta">Avatar versions</p>
          <span>Current version</span>
        </div>

        <div className="profile-avatar-versions__rail">
          <article>
            {image ? (
              <img src={image} alt="" />
            ) : (
              <span className="profile-avatar-version__placeholder" aria-hidden>
                <UserRound size={24} strokeWidth={1.4} />
              </span>
            )}
            <div>
              <div className="profile-avatar-version__title">
                <h2>Current</h2>
                <span>Active</span>
              </div>
              <p>{formatDate(updatedAt)}</p>
              <p>
                Version {avatar.version} · {formatTime(updatedAt)}
              </p>
            </div>
          </article>
          <p className="profile-avatar-versions__empty">
            Previous versions will appear here after your next avatar update.
          </p>
        </div>
      </section>

      <section className="profile-panel profile-avatar-management">
        <div>
          <p className="profile-meta">Avatar management</p>
          <h2>Delete this avatar</h2>
          <p>
            Removes this avatar render. Your saved measurements remain available so you can create
            another one later.
          </p>
        </div>
        {confirming ? (
          <div className="profile-avatar-management__confirm">
            <button type="button" disabled={remove.isPending} onClick={() => setConfirming(false)}>
              Keep avatar
            </button>
            <button type="button" disabled={remove.isPending} onClick={() => remove.mutate()}>
              {remove.isPending ? "Deleting…" : "Delete permanently"}
            </button>
          </div>
        ) : (
          <button type="button" onClick={() => setConfirming(true)}>
            Delete avatar…
          </button>
        )}
        {remove.error && (
          <p className="profile-inline-error" role="alert">
            The avatar could not be deleted. Please try again.
          </p>
        )}
      </section>
    </div>
  );
}

function ProfileAvatarLoading() {
  return (
    <div className="profile-avatar-page profile-page-loading" aria-busy="true" role="status">
      <div className="profile-loading-copy">
        <span className="profile-loading-block profile-loading-block--meta" />
        <span className="profile-loading-block profile-loading-block--title" />
        <span className="profile-loading-block profile-loading-block--copy" />
      </div>
      <div className="profile-avatar-primary" aria-hidden>
        <span className="profile-loading-block profile-loading-block--stage" />
        <span className="profile-loading-block profile-loading-block--panel" />
      </div>
      <span className="sr-only">Loading your avatar…</span>
    </div>
  );
}
