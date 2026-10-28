import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { merchantApi } from "../data/merchant-api";
import { Banner, Card, Field } from "./ui";
import { buttonClass, inputClass } from "./styles";

/**
 * Seat a colleague in a real (backend) workspace — POST /merchant/{id}/members.
 * There is no invitation email in the pilot: the colleague creates a business
 * account at /business/sign-up first, then is seated here by that email.
 */
export function LiveSeatCard({ tenantId }: { tenantId: string }) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"admin" | "editor" | "viewer">("editor");
  const qc = useQueryClient();
  const seat = useMutation({
    mutationFn: () => merchantApi.addMember(tenantId, { email: email.trim(), role }),
    onSuccess: () => {
      setEmail("");
      qc.invalidateQueries({ queryKey: ["merchant-members", tenantId] });
    },
  });

  return (
    <Card title="Add a colleague">
      <p className="mb-4 text-[13px] text-muted">
        They need a Mirra business account first (they can create one at /business/sign-up). Seats
        take effect the next time they open the dashboard.
      </p>
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          seat.mutate();
        }}
      >
        <Field label="Email">
          <input
            className={inputClass}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </Field>
        <Field label="Role">
          <select
            className={inputClass}
            value={role}
            onChange={(e) => setRole(e.target.value as typeof role)}
          >
            <option value="admin">Admin — catalogue, publishing and settings</option>
            <option value="editor">Editor — catalogue</option>
            <option value="viewer">Viewer — read-only</option>
          </select>
        </Field>
        {seat.error && (
          <Banner tone="danger">
            {seat.error instanceof Error ? seat.error.message : "Could not add them."}
          </Banner>
        )}
        {seat.isSuccess && <Banner tone="info">Seat added.</Banner>}
        <button
          type="submit"
          className={buttonClass("primary")}
          disabled={seat.isPending || !email.trim()}
        >
          {seat.isPending ? "Adding…" : "Add to workspace"}
        </button>
      </form>
    </Card>
  );
}
