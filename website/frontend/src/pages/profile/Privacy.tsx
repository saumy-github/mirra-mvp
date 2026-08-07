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
    <div className="space-y-12">
      <section>
        <p className="eyebrow">Privacy</p>
        <h1 className="mt-4 text-[clamp(1.5rem,2.6vw,1.9rem)] leading-tight font-medium tracking-[-0.03em] text-graphite">
          Consents
        </h1>
        <p className="mt-3 max-w-lg text-[13px] leading-relaxed text-slate">
          Change these at any time — nothing here is required to keep shopping.
        </p>
        <div className="rule-stack mt-8 border-t border-b border-hairline">
          <ConsentRow
            title="Remember my styling preferences"
            body="Keeps optional answers (like preferred fit) to shape your own studio. Never used for advertising."
            checked={account.consents.preferenceStorage}
            onChange={(v) => consents.mutate({ preferenceStorage: v })}
          />
        </div>
      </section>

      <section className="border-t border-hairline pt-8">
        <h2 className="eyebrow">Your data</h2>
        <ul className="mt-5 space-y-2.5 text-[13px] leading-relaxed text-slate">
          <li>
            · Source photographs are deleted after avatar generation and are never shown to anyone
            else.
          </li>
          <li>· Photographs are never used to train models.</li>
          <li>· Your avatar and measurements can be deleted from the Avatar tab at any time.</li>
        </ul>
        <p className="mt-5 text-[11px] text-ash">
          [Privacy copy placeholder — subject to legal review.]
        </p>
      </section>

      <section className="border-t border-hairline pt-8">
        <h2 className="eyebrow">Sessions</h2>
        <p className="mt-5 max-w-lg text-[13px] leading-relaxed text-slate">
          Signing out ends this device&apos;s session. Phone pairing links expire on their own
          within five minutes and can be used only once.
        </p>
      </section>

      <section className="border-t border-hairline pt-8">
        <h2 className="eyebrow text-error!">Delete account</h2>
        <p className="mt-5 max-w-lg text-[13px] leading-relaxed text-slate">
          Permanently removes your account, avatar, measurements and Signature Looks. This
          can&apos;t be undone.
        </p>
        {confirmingDelete ? (
          <div className="mt-6 flex gap-3">
            <Button variant="outline" size="sm" onClick={() => setConfirmingDelete(false)}>
              Keep my account
            </Button>
            <Button
              size="sm"
              className="bg-error! text-vellum!"
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
            className="mt-6"
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
    <label className="flex cursor-pointer items-start gap-4 py-5">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 size-4 shrink-0 accent-graphite"
      />
      <span>
        <span className="block text-[14px] font-medium text-graphite">{title}</span>
        <span className="mt-1.5 block text-[12px] leading-relaxed text-slate">{body}</span>
      </span>
    </label>
  );
}
