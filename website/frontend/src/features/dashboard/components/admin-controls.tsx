import { useState } from "react";
import { adminTenantTransitionAction, updateLeadStatusAction, inviteLeadAction } from "../data/actions";
import type { LeadStatus, TenantStatus } from "../data/types";
import { buttonClass } from "./styles";
import { useAction } from "./use-action";

/** Manual lifecycle override with an explicit typed reason — deliberately heavy. */
export function TenantOverrideButton({
  tenantId,
  to,
  label,
  danger,
}: {
  tenantId: string;
  to: TenantStatus;
  label: string;
  danger?: boolean;
}) {
  const [confirming, setConfirming] = useState(false);
  const [reason, setReason] = useState("");
  const { pending, notice, run, clear } = useAction();

  if (!confirming) {
    return (
      <button onClick={() => setConfirming(true)} className={buttonClass(danger ? "danger" : "secondary", "sm")}>
        {label}
      </button>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 p-1.5">
      <input
        autoFocus
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="Reason (required, audit-logged)"
        className="w-52 rounded-md border border-red-200 bg-white px-2 py-1 text-xs focus:outline-none"
      />
      <button
        disabled={reason.trim().length < 4 || pending}
        onClick={() =>
          run(
            () => adminTenantTransitionAction(tenantId, to, reason.trim()),
            () => setConfirming(false),
          )
        }
        className={buttonClass("danger", "sm")}
      >
        {pending ? "Working…" : `Confirm ${label.toLowerCase()}`}
      </button>
      <button onClick={() => { setConfirming(false); clear(); }} className={buttonClass("ghost", "sm")}>Cancel</button>
      {notice && (
        <span role="alert" className="text-[11px] font-medium text-red-800">{notice.message}</span>
      )}
    </span>
  );
}

export function LeadStatusSelect({ leadId, status }: { leadId: string; status: LeadStatus }) {
  return (
    <select
      value={status}
      onChange={(e) => void updateLeadStatusAction(leadId, e.target.value as LeadStatus)}
      className="rounded-lg border border-line bg-surface px-2 py-1 text-xs"
      aria-label="Lead status"
    >
      {["new", "qualifying", "qualified", "invited", "converted", "disqualified"].map((s) => (
        <option key={s} value={s}>{s.replace("_", " ")}</option>
      ))}
    </select>
  );
}

export function InviteLeadButton({ leadId, disabled }: { leadId: string; disabled: boolean }) {
  return (
    <button
      disabled={disabled}
      onClick={() => void inviteLeadAction(leadId)}
      className={buttonClass("accent", "sm")}
    >
      Invite to onboarding
    </button>
  );
}
