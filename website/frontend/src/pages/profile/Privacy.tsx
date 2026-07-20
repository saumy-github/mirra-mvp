import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
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
    <div className="space-y-10">
      <section>
        <h1 className="text-xl font-semibold tracking-tight">Consents</h1>
        <p className="mt-1 text-sm text-muted">
          Change these at any time — nothing here is required to keep shopping.
        </p>
        <div className="mt-5 space-y-4">
          <ConsentRow
            title="Remember my styling preferences"
            body="Keeps optional answers (like preferred fit) to shape your own studio. Never used for advertising."
            checked={account.consents.preferenceStorage}
            onChange={(v) => consents.mutate({ preferenceStorage: v })}
          />
        </div>
      </section>

      <section className="border-t border-line pt-8">
        <h2 className="text-base font-semibold">Your data</h2>
        <ul className="mt-3 space-y-2 text-sm leading-relaxed text-ink-soft">
          <li>
            · Source photographs are deleted after avatar generation and are never shown to anyone
            else.
          </li>
          <li>· Photographs are never used to train models.</li>
          <li>· Your avatar and measurements can be deleted from the Avatar tab at any time.</li>
        </ul>
        <p className="mt-3 text-xs text-faint">
          [Privacy copy placeholder — subject to legal review.]
        </p>
      </section>

      <section className="border-t border-line pt-8">
        <h2 className="text-base font-semibold">Sessions</h2>
        <p className="mt-2 text-sm text-muted">
          Signing out ends this device&apos;s session. Phone pairing links expire on their own
          within five minutes and can be used only once.
        </p>
      </section>

      <section className="border-t border-line pt-8">
        <h2 className="text-base font-semibold text-error">Delete account</h2>
        <p className="mt-2 max-w-lg text-sm leading-relaxed text-muted">
          Permanently removes your account, avatar, measurements and Signature Looks. This
          can&apos;t be undone.
        </p>
        {confirmingDelete ? (
          <div className="mt-4 flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setConfirmingDelete(false)}>
              Keep my account
            </Button>
            <Button
              size="sm"
              className="bg-error!"
              onClick={() => deleteAccount.mutate()}
              loading={deleteAccount.isPending}
            >
              Delete everything
            </Button>
          </div>
        ) : (
          <Button
            variant="outline"
            size="sm"
            className="mt-4"
            onClick={() => setConfirmingDelete(true)}
          >
            Delete account…
          </Button>
        )}
      </section>
    </div>
  );
}

function ConsentRow({
  title,
  body,
  checked,
  onChange,
}: {
  title: string;
  body: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-start gap-4 rounded-[14px] border border-line bg-surface p-4">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-1 size-4 accent-ink"
      />
      <span>
        <span className="block text-sm font-medium text-ink">{title}</span>
        <span className="mt-1 block text-xs leading-relaxed text-muted">{body}</span>
      </span>
    </label>
  );
}
