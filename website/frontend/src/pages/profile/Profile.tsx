import { ArrowRight, CircleUserRound, ShoppingBag } from "lucide-react";
import { Link } from "react-router-dom";
import { useAvatarProfile, useAccount } from "@/hooks/use-shopper";
import { useSignatureLooks } from "@/hooks/use-signature-looks";
import type { MeasurementKey } from "@/integrations/mirra-api/types";

const SUMMARY_KEYS: MeasurementKey[] = ["height", "chest", "waist", "hips", "inseam"];

export default function Profile() {
  const { data: account } = useAccount();
  const { data: avatar, isLoading: avatarLoading } = useAvatarProfile(!!account);
  const { data: looks = [], isLoading: looksLoading } = useSignatureLooks(!!account);

  if (!account) return null;

  const fields = avatar?.measurements.filter((field) => field.supported) ?? [];
  const measurement = (key: MeasurementKey) => fields.find((field) => field.key === key);
  const displayField = (key: MeasurementKey) => {
    const field = measurement(key);
    return field ? `${Number(field.value.toFixed(1))} ${field.unit}` : "—";
  };
  const firstName = account.displayName.trim().split(/\s+/)[0] || account.displayName;
  const hasMeasurements = fields.length > 0;
  const heroImage = avatar?.previewAssetUrl || "/profile/signature-everyday.jpg";

  return (
    <div className="profile-overview-page">
      <header className="profile-page-heading profile-overview-heading">
        <h1>Your profile</h1>
        <p>A more accurate you makes every try-on better.</p>
      </header>

      <div className="profile-overview-layout">
        <div className="profile-overview-visual">
          <img
            src={heroImage}
            alt={
              avatar?.previewAssetUrl
                ? "Your saved avatar preview"
                : "Editorial styling inspiration"
            }
          />
          <span className="profile-overview-visual__caption">
            {avatar?.previewAssetUrl ? "Your avatar" : "Style inspiration"}
          </span>
        </div>

        <div className="profile-overview-details">
          <section className="profile-panel profile-overview-identity">
            <div className="profile-overview-card-heading">
              <div>
                <p className="profile-meta">Your details</p>
                <h2>{firstName}</h2>
              </div>
              <Link to="/profile/measurements" className="profile-outline-button">
                {hasMeasurements ? "Edit" : "Set up"}
              </Link>
            </div>
            <span
              className={hasMeasurements ? "profile-ready" : "profile-ready profile-ready--pending"}
            >
              <span aria-hidden />
              {avatarLoading
                ? "Checking profile…"
                : hasMeasurements
                  ? "Fit profile ready"
                  : "Set up your fit profile"}
            </span>
            <div className="profile-overview-stats">
              <div>
                <strong>{displayField("height")}</strong>
                <span>Height</span>
              </div>
              <div>
                <strong>{displayField("weight")}</strong>
                <span>Weight</span>
              </div>
              <div>
                <strong>{looksLoading ? "—" : looks.length}</strong>
                <span>Saved looks</span>
              </div>
            </div>
            <p className="profile-overview-updated">
              {avatar
                ? `Last updated ${new Date(avatar.updatedAt).toLocaleDateString()}`
                : "Add measurements to start creating your fit profile."}
            </p>
            {!account.emailVerified && !account.isGuest && (
              <p className="profile-overview-verification">
                Email not yet verified — <Link to="/auth/verify-email">verify now</Link>
              </p>
            )}
          </section>

          <section className="profile-panel profile-overview-measurements">
            <div className="profile-overview-card-heading">
              <h2>Measurements</h2>
              <Link to="/profile/measurements" className="profile-outline-button">
                {hasMeasurements ? "Edit" : "Add"}
              </Link>
            </div>
            <dl>
              {SUMMARY_KEYS.map((key) => (
                <div key={key}>
                  <dt>
                    {measurement(key)?.label ??
                      (key === "hips" ? "Hip" : key[0].toUpperCase() + key.slice(1))}
                  </dt>
                  <dd>{displayField(key)}</dd>
                </div>
              ))}
            </dl>
          </section>
        </div>
      </div>

      <div className="profile-overview-footer">
        <Link to="/profile/avatar">
          <CircleUserRound aria-hidden size={20} strokeWidth={1.6} />
          <span>
            <strong>
              {avatar && avatar.version > 0 ? "View your avatar" : "Create your avatar"}
            </strong>
            <small>
              {avatar && avatar.version > 0
                ? "Explore your 3D model"
                : "Built from your measurements"}
            </small>
          </span>
          <ArrowRight aria-hidden size={18} />
        </Link>
        <Link to="/profile/signature-looks">
          <ShoppingBag aria-hidden size={20} strokeWidth={1.6} />
          <span>
            <strong>My Looks</strong>
            <small>{looksLoading ? "Loading looks" : `${looks.length} saved in your studio`}</small>
          </span>
          <ArrowRight aria-hidden size={18} />
        </Link>
      </div>
    </div>
  );
}
