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
      <div className="text-sm text-muted">
        <p>No avatar on this account.</p>
        <p className="mt-2">
          One is created the next time you complete a photo session — it takes a few photographs and
          stays fully under your control.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-8 sm:grid-cols-[220px_1fr]">
      <div className="rounded-[14px] border border-line bg-surface p-4">
        <AvatarFigure
          previewAssetUrl={avatar.previewAssetUrl}
          layers={[]}
          className="h-72"
          alt="Your saved avatar"
        />
      </div>
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Avatar {avatar.avatarLabel}</h1>
        <dl className="mt-4 space-y-2 text-sm text-ink-soft">
          <div className="flex gap-2">
            <dt className="w-28 text-muted">Version</dt>
            <dd>v{avatar.version}</dd>
          </div>
          <div className="flex gap-2">
            <dt className="w-28 text-muted">Engine</dt>
            <dd className="font-mono text-xs">{avatar.engineVersion}</dd>
          </div>
          <div className="flex gap-2">
            <dt className="w-28 text-muted">Created</dt>
            <dd>{new Date(avatar.createdAt).toLocaleDateString()}</dd>
          </div>
          <div className="flex gap-2">
            <dt className="w-28 text-muted">Last updated</dt>
            <dd>{new Date(avatar.updatedAt).toLocaleDateString()}</dd>
          </div>
        </dl>

        <div className="mt-8 border-t border-line pt-6">
          <h2 className="text-sm font-medium">Delete this avatar</h2>
          <p className="mt-1 text-xs leading-relaxed text-muted">
            Removes the avatar and every measurement estimate. Source photographs were already
            deleted after generation. This can&apos;t be undone.
          </p>
          {confirming ? (
            <div className="mt-3 flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setConfirming(false)}>
                Keep avatar
              </Button>
              <Button
                size="sm"
                className="bg-error!"
                onClick={() => remove.mutate()}
                loading={remove.isPending}
              >
                Delete permanently
              </Button>
            </div>
          ) : (
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              onClick={() => setConfirming(true)}
            >
              Delete avatar…
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
