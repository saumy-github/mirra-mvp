import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "../../../data/session";
import { liveCan } from "../../../data/live-session";
import { merchantApi, type Member } from "../../../data/merchant-api";
import { Badge, Banner, PageHeader, Table, Td } from "../../../components/ui";
import { inputClass } from "../../../components/styles";
import { LiveSeatCard } from "../../../components/live-seat-card";

const ROLE_LABEL: Record<string, string> = {
  owner: "Owner",
  admin: "Admin",
  editor: "Editor",
  viewer: "Viewer",
  qa: "Mirra QA",
};

/** Seats in a real workspace, from /merchant/{t}/members. */
export default function LiveTeamPage() {
  const session = useSession();
  const tenantId = session?.tenant?.id ?? "";
  const qc = useQueryClient();
  const canManage = liveCan(tenantId, "settings.edit");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const members = useQuery({
    queryKey: ["merchant-members", tenantId],
    queryFn: () => merchantApi.listMembers(tenantId),
  });

  const act = async (m: Member, fn: () => Promise<unknown>) => {
    setBusy(m.userId);
    setError(null);
    try {
      await fn();
      await qc.invalidateQueries({ queryKey: ["merchant-members", tenantId] });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const rows = members.data ?? [];

  return (
    <>
      <PageHeader
        title="Team & permissions"
        subtitle="Owners and admins manage the catalogue, publishing and settings; editors manage the catalogue; viewers read."
      />
      {error && (
        <div className="mb-4">
          <Banner tone="danger">{error}</Banner>
        </div>
      )}
      {members.isLoading ? (
        <p className="text-[13px] text-muted">Loading team…</p>
      ) : members.isError ? (
        <Banner tone="danger">Could not load the team: {(members.error as Error).message}</Banner>
      ) : (
        <Table caption="People with access to this workspace" headers={["Member", "Email", "Role", ""]}>
          {rows.map((m) => {
            const isSelf = m.userId === session?.user.id;
            const editable = canManage && !isSelf && m.role !== "owner" && m.role !== "qa";
            return (
              <tr key={m.userId}>
                <Td className="font-medium text-ink">
                  {m.name || m.email || m.userId}
                  {isSelf && <span className="ml-2 text-xs text-muted">(you)</span>}
                </Td>
                <Td className="text-muted">{m.email || "—"}</Td>
                <Td>
                  {editable ? (
                    <select
                      aria-label={`Role for ${m.email}`}
                      value={m.role}
                      disabled={busy === m.userId}
                      onChange={(e) =>
                        act(m, () =>
                          merchantApi.addMember(tenantId, {
                            email: m.email,
                            role: e.target.value as "admin" | "editor" | "viewer",
                          }),
                        )
                      }
                      className={`${inputClass} w-32`}
                    >
                      <option value="admin">Admin</option>
                      <option value="editor">Editor</option>
                      <option value="viewer">Viewer</option>
                    </select>
                  ) : (
                    <Badge>{ROLE_LABEL[m.role] ?? m.role}</Badge>
                  )}
                </Td>
                <Td className="text-right">
                  {editable && (
                    <button
                      disabled={busy === m.userId}
                      onClick={() => act(m, () => merchantApi.removeMember(tenantId, m.userId))}
                      className="text-xs font-medium text-red-700 hover:underline"
                    >
                      Remove
                    </button>
                  )}
                </Td>
              </tr>
            );
          })}
        </Table>
      )}
      {canManage && (
        <div className="mt-5">
          <LiveSeatCard tenantId={tenantId} />
        </div>
      )}
    </>
  );
}
