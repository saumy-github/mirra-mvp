import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AvatarFigure } from "@/features/studio/components/avatar-figure";
import { Button } from "@/components/ui/button";
import { useAvatarProfile, useAccount } from "@/hooks/use-shopper";
import { getRuntimeProvider } from "@/integrations/mirra-api";

export default function ProfileAvatar() {
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

  if (isLoading) return null;

  if (!avatar) {
    return (
      <div className="max-w-md text-[13px] leading-relaxed text-slate">
        <p className="eyebrow">Avatar</p>
        <p className="mt-4">No avatar on this account.</p>
        <p className="mt-3">
          One is created the next time you complete a photo session — it takes a few photographs and
          stays fully under your control.
        </p>
      </div>
    );
  }

  return (
    <div>
      <p className="eyebrow">Avatar</p>
      <h1 className="mt-4 text-[clamp(1.5rem,2.6vw,1.9rem)] leading-tight font-medium tracking-[-0.03em] text-graphite">
        {avatar.avatarLabel}
      </h1>

      <div className="mt-10 grid grid-cols-1 gap-10 sm:grid-cols-[13rem_minmax(0,1fr)]">
        <div className="border border-hairline bg-bone p-5">
          <AvatarFigure
            previewAssetUrl={avatar.previewAssetUrl}
            layers={[]}
            glow={false}
            className="h-64"
            alt="Your saved avatar"
          />
        </div>

        <dl className="rule-stack self-start border-t border-b border-hairline text-[13px]">
          <SpecRow label="Version" value={`v${avatar.version}`} />
          <SpecRow label="Engine" value={avatar.engineVersion} />
          <SpecRow label="Created" value={new Date(avatar.createdAt).toLocaleDateString()} />
          <SpecRow label="Last updated" value={new Date(avatar.updatedAt).toLocaleDateString()} />
        </dl>
      </div>

      <section className="mt-12 border-t border-hairline pt-8">
        <h2 className="eyebrow">Delete this avatar</h2>
        <p className="mt-4 max-w-lg text-[13px] leading-relaxed text-slate">
          Removes the avatar and every measurement estimate. Source photographs were already deleted
          after generation. This can&apos;t be undone.
        </p>
        {confirming ? (
          <div className="mt-6 flex gap-3">
            <Button variant="outline" size="sm" onClick={() => setConfirming(false)}>
              Keep avatar
            </Button>
            <Button
              size="sm"
              className="bg-error! text-vellum!"
              onClick={() => remove.mutate()}
              loading={remove.isPending}
            >
              Delete permanently
            </Button>
          </div>
        ) : (
          <Button variant="outline" size="sm" className="mt-6" onClick={() => setConfirming(true)}>
            Delete avatar…
          </Button>
        )}
      </section>
    </div>
  );
}

function SpecRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-6 py-3.5">
      <dt className="eyebrow">{label}</dt>
      <dd className="text-graphite tabular-nums">{value}</dd>
    </div>
  );
}
