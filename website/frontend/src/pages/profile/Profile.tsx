import type { ReactNode } from "react";
import { ArrowRight, Ruler, Sparkles, UserRound } from "lucide-react";
import { Link } from "react-router-dom";
import { useAvatarProfile, useAccount } from "@/hooks/use-shopper";
import { useSignatureLooks } from "@/hooks/use-signature-looks";

export default function Profile() {
  const { data: account } = useAccount();
  const { data: avatar, isLoading: avatarLoading } = useAvatarProfile(!!account);
  const { data: looks = [], isLoading: looksLoading } = useSignatureLooks(!!account);

  if (!account) return null;

  return (
    <div className="profile-overview-page">
      <header className="profile-page-heading profile-overview-heading">
        <p className="profile-meta">Profile overview</p>
        <h1>Hi, {account.displayName}</h1>
        <p>{account.email}</p>
        {!account.emailVerified && !account.isGuest && (
          <p className="profile-overview-verification">
            Email not yet verified — <Link to="/auth/verify-email">verify now</Link>
          </p>
        )}
        <div className="profile-overview-heading__actions">
          <Link
            to={avatar ? "/studio" : "/measurements?next=/onboarding/avatar"}
            className="profile-dark-button"
          >
            {avatar ? "Open Studio" : "Set up fit profile"}
            <ArrowRight aria-hidden size={17} strokeWidth={1.7} />
          </Link>
          <Link to="/profile/measurements" className="profile-text-link">
            Review Fit Profile
          </Link>
        </div>
      </header>

      <ul className="profile-overview-grid" aria-label="Profile summary">
        <SummaryCard
          icon={<UserRound aria-hidden size={21} strokeWidth={1.55} />}
          label="Avatar"
          value={avatarLoading ? "Checking…" : avatar ? avatar.avatarLabel : "Not created"}
          detail={
            avatarLoading
              ? "Loading avatar status"
              : avatar
                ? `Updated ${new Date(avatar.updatedAt).toLocaleDateString()}`
                : "Add measurements, then create one"
          }
          href="/profile/avatar"
        />
        <SummaryCard
          icon={<Ruler aria-hidden size={21} strokeWidth={1.55} />}
          label="Fit Profile"
          value={avatarLoading ? "Checking…" : avatar ? "Ready to review" : "Not set up"}
          detail={avatar ? "Measurements and fit preferences" : "Start with your measurements"}
          href="/profile/measurements"
        />
        <SummaryCard
          icon={<Sparkles aria-hidden size={21} strokeWidth={1.55} />}
          label="Saved Looks"
          value={looksLoading ? "Checking…" : `${looks.length} saved`}
          detail={
            looksLoading
              ? "Loading your Studio library"
              : (looks.find((look) => look.isDefault)?.name ?? "Build your first look in Studio")
          }
          href="/profile/signature-looks"
        />
      </ul>

      <section className="profile-panel profile-overview-trust">
        <span className="profile-overview-trust__icon">
          <Ruler aria-hidden size={20} strokeWidth={1.55} />
        </span>
        <div>
          <h2>Your fitting profile, ready when you are</h2>
          <p>
            Your fit profile stays under your control. Review what Mirra stores and remove it when
            you choose.
          </p>
        </div>
        <Link to="/profile/privacy">
          Review privacy <ArrowRight aria-hidden size={16} strokeWidth={1.6} />
        </Link>
      </section>
    </div>
  );
}

function SummaryCard({
  icon,
  label,
  value,
  detail,
  href,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  detail: string;
  href: string;
}) {
  return (
    <li>
      <Link to={href} className="profile-panel profile-overview-card">
        <span className="profile-overview-card__icon">{icon}</span>
        <span className="profile-meta">{label}</span>
        <span className="profile-overview-card__value">{value}</span>
        <span className="profile-overview-card__detail">{detail}</span>
        <ArrowRight
          className="profile-overview-card__arrow"
          aria-hidden
          size={17}
          strokeWidth={1.55}
        />
      </Link>
    </li>
  );
}
