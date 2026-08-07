import { Link } from "react-router-dom";
import { useAvatarProfile, useAccount } from "@/hooks/use-shopper";
import { useSignatureLooks } from "@/hooks/use-signature-looks";

export default function Profile() {
  const { data: account } = useAccount();
  const { data: avatar } = useAvatarProfile(!!account);
  const { data: looks = [] } = useSignatureLooks(!!account);

  if (!account) return null;

  return (
    <div>
      <p className="eyebrow">Account</p>
      <h1 className="mt-4 text-[clamp(1.6rem,3vw,2.1rem)] leading-[1.1] font-medium tracking-[-0.03em] text-graphite">
        Hi, {account.displayName}
      </h1>
      <p className="mt-3 text-[13px] text-slate">{account.email}</p>
      {!account.emailVerified && !account.isGuest && (
        <p className="mt-3 text-[12px] text-error">
          Email not yet verified —{" "}
          <Link to="/auth/verify-email" className="underline underline-offset-4">
            verify now
          </Link>
        </p>
      )}

      {/* Three ruled rows, not three cards. */}
      <dl className="rule-stack mt-12 border-t border-b border-hairline">
        <SummaryRow
          label="Avatar"
          value={avatar ? avatar.avatarLabel : "None yet"}
          detail={
            avatar
              ? `updated ${new Date(avatar.updatedAt).toLocaleDateString()}`
              : "created at your next try-on"
          }
          href="/profile/avatar"
        />
        <SummaryRow
          label="Signature Looks"
          value={String(looks.length)}
          detail={looks.find((l) => l.isDefault)?.name ?? "no default set"}
          href="/profile/signature-looks"
        />
        <SummaryRow
          label="Privacy"
          value={account.consents.preferenceStorage ? "Preferences saved" : "Preferences off"}
          detail="consents & deletion"
          href="/profile/privacy"
        />
      </dl>

      <p className="mt-8 max-w-lg text-[12px] leading-relaxed text-ash">
        Your avatar is generated once and reused for every future try-on — your photographs are
        never shown to anyone else.
      </p>
    </div>
  );
}

function SummaryRow({
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
    <Link to={href} className="group grid grid-cols-12 items-baseline gap-4 py-6">
      <dt className="eyebrow col-span-12 sm:col-span-4">{label}</dt>
      <dd className="col-span-8 text-[15px] font-medium text-graphite sm:col-span-5">{value}</dd>
      <dd className="col-span-4 flex items-baseline justify-end gap-3 text-[12px] text-ash sm:col-span-3">
        <span className="hidden truncate sm:inline">{detail}</span>
        <span aria-hidden className="transition-transform duration-200 group-hover:translate-x-0.5">
          →
        </span>
      </dd>
    </Link>
  );
}
