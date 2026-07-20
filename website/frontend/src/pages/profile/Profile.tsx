import { Link } from "react-router-dom";
import { useAvatarProfile, useAccount } from "@/hooks/use-shopper";
import { useSignatureLooks } from "@/hooks/use-signature-looks";

export default function Profile() {
  const { data: account } = useAccount();
  const { data: avatar } = useAvatarProfile(!!account);
  const { data: looks = [] } = useSignatureLooks(!!account);

  if (!account) return null;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Hi, {account.displayName}</h1>
        <p className="mt-1 text-sm text-muted">{account.email}</p>
        {!account.emailVerified && !account.isGuest && (
          <p className="mt-2 text-xs text-error">
            Email not yet verified —{" "}
            <Link to="/auth/verify-email" className="underline">
              verify now
            </Link>
          </p>
        )}
      </div>

      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <SummaryCard
          label="Avatar"
          value={avatar ? avatar.avatarLabel : "None yet"}
          detail={
            avatar
              ? `updated ${new Date(avatar.updatedAt).toLocaleDateString()}`
              : "created at your next try-on"
          }
          href="/profile/avatar"
        />
        <SummaryCard
          label="Signature Looks"
          value={String(looks.length)}
          detail={looks.find((l) => l.isDefault)?.name ?? "no default set"}
          href="/profile/signature-looks"
        />
        <SummaryCard
          label="Privacy"
          value={account.consents.preferenceStorage ? "Preferences saved" : "Preferences off"}
          detail="consents & deletion"
          href="/profile/privacy"
        />
      </dl>

      <p className="text-xs leading-relaxed text-faint">
        Your avatar is generated once and reused for every future try-on — your photographs are
        never shown to anyone else.
      </p>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  detail,
  href,
}: {
  label: string;
  value: string;
  detail: string;
  href: string;
}) {
  return (
    <Link
      to={href}
      className="rounded-[14px] border border-line bg-surface p-5 transition-colors hover:border-line-strong"
    >
      <dt className="font-mono text-[10px] tracking-[0.18em] text-muted uppercase">{label}</dt>
      <dd className="mt-2 text-lg font-medium">{value}</dd>
      <dd className="mt-0.5 text-xs text-muted">{detail}</dd>
    </Link>
  );
}
