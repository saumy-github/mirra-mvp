import { useDbVersion, getDb } from "../../data/store";
import { useSession } from "../../data/session";
import { getEntitlements } from "../../data/entitlements";
import { can, ROLE_LABELS } from "../../data/rbac";
import { inviteMemberAction, removeMemberAction, setMemberRoleAction } from "../../data/actions";
import { fmtDate } from "../../data/util";
import type { BrandRole } from "../../data/types";
import {
  Badge,
  Card,
  ConfirmAction,
  Field,
  NoticeBar,
  PageHeader,
  SubmitButton,
  Table,
  Td,
} from "../../components/ui";
import { useAction } from "../../components/use-action";
import { inputClass } from "../../components/styles";

const ROLE_DESCRIPTIONS: Record<string, string> = {
  brand_owner: "Full access, including billing, team, and settings",
  brand_merchandiser: "Catalogue, publication, and analytics",
  brand_finance: "Billing, invoices, and analytics",
  brand_viewer: "Read-only access to catalogue and analytics",
};

export default function TeamPage() {
  const session = useSession();
  useDbVersion();
  if (!session?.tenant) return null;
  const tenant = session.tenant;

  const db = getDb();
  const ent = getEntitlements(tenant);
  const members = db.memberships
    .filter((m) => m.tenantId === tenant.id)
    .map((m) => ({ ...m, user: db.users.find((u) => u.id === m.userId)! }));
  const canManage = can(session.role, "team.manage");

  return (
    <>
      <PageHeader
        title="Team & permissions"
        subtitle={`${members.length} of ${ent.seatLimit} seats used on your plan. Roles keep billing, catalogue, and publishing responsibilities separate.`}
      />
      <Table
        caption="People with access to this workspace and their roles"
        headers={canManage ? ["Member", "Email", "Role", "Status", ""] : ["Member", "Role", "Access", "", ""]}
      >
        {members.map((m) => (
          <tr key={m.userId} className="hover:bg-stone-50/60">
            <Td className="font-medium text-ink">
              {m.user.name}
              {m.userId === session.user.id && <span className="ml-2 text-xs text-muted">(you)</span>}
            </Td>
            {/* Colleagues' email addresses are directory data a Viewer has no
                reason to need, so only a seat that can manage the team sees it. */}
            {canManage ? (
              <Td className="text-stone-600">{m.user.email}</Td>
            ) : (
              <Td>
                <Badge tone={m.role === "brand_owner" ? "info" : "neutral"}>{ROLE_LABELS[m.role]}</Badge>
              </Td>
            )}
            {canManage ? (
              <Td>
                <RoleSelect userId={m.userId} role={m.role} isSelf={m.userId === session.user.id} />
              </Td>
            ) : (
              <Td className="text-xs text-muted">{ROLE_DESCRIPTIONS[m.role]}</Td>
            )}
            <Td className="text-xs">
              {m.status === "invited" ? (
                <span className="text-amber-800">
                  Invited{m.expiresAt ? ` · expires ${fmtDate(m.expiresAt)}` : ""}
                </span>
              ) : (
                <span className="text-muted">Active</span>
              )}
            </Td>
            <Td>
              {canManage && m.userId !== session.user.id && (
                <ConfirmAction
                  label="Remove"
                  size="sm"
                  title={`Remove ${m.user.name}?`}
                  impact="They lose access to this workspace immediately. Nothing they created is deleted."
                  onConfirm={() => removeMemberAction(m.userId)}
                />
              )}
            </Td>
          </tr>
        ))}
      </Table>

      {canManage && <InviteCard seatLimit={ent.seatLimit} used={members.length} />}
    </>
  );
}

/** Role changes, with the last-Owner guard the action enforces as well. */
function RoleSelect({ userId, role, isSelf }: { userId: string; role: BrandRole; isSelf: boolean }) {
  const { notice, run, clear } = useAction();
  return (
    <div>
      <label className="sr-only" htmlFor={`role-${userId}`}>Role</label>
      <select
        id={`role-${userId}`}
        value={role}
        disabled={isSelf}
        title={isSelf ? "You can't change your own role" : undefined}
        onChange={(e) => run(() => setMemberRoleAction(userId, e.target.value as BrandRole))}
        className="rounded-lg border border-line bg-surface px-2 py-1 text-xs disabled:opacity-60"
      >
        {Object.keys(ROLE_DESCRIPTIONS).map((r) => (
          <option key={r} value={r}>{ROLE_LABELS[r as BrandRole]}</option>
        ))}
      </select>
      {notice && (
        <span
          role={notice.tone === "danger" ? "alert" : "status"}
          className={`mt-1 block text-[11px] ${notice.tone === "danger" ? "text-red-700" : "text-emerald-700"}`}
        >
          {notice.message}
          <button onClick={clear} className="ml-1 cursor-pointer underline">dismiss</button>
        </span>
      )}
    </div>
  );
}

/**
 * Real invitations against real seat limits.
 *
 * The previous form was disabled with a note explaining that invitation
 * delivery needed a backend. Delivery still does — but the seat, the role and
 * the expiry are workspace state, and holding all of that hostage to an email
 * meant no merchant could add a colleague at all.
 */
function InviteCard({ seatLimit, used }: { seatLimit: number; used: number }) {
  const { pending, notice, run, clear } = useAction();
  return (
    <div className="mt-6 max-w-lg">
      <Card title="Invite a teammate">
        <NoticeBar notice={notice} onDismiss={clear} />
        <form action={(formData: FormData) => run(() => inviteMemberAction(formData))} className="space-y-4">
          <Field label="Email">
            <input name="email" type="email" required autoComplete="email" className={inputClass} placeholder="teammate@brand.com" />
          </Field>
          <Field label="Name (optional)">
            <input name="name" className={inputClass} placeholder="Their name" />
          </Field>
          <Field label="Role" hint="Least privilege: give the narrowest role that lets them do their job.">
            <select name="role" className={inputClass} defaultValue="brand_merchandiser">
              {Object.entries(ROLE_DESCRIPTIONS).map(([role, desc]) => (
                <option key={role} value={role}>{ROLE_LABELS[role as BrandRole]} — {desc}</option>
              ))}
            </select>
          </Field>
          <SubmitButton pending={pending}>Create invitation</SubmitButton>
        </form>
        <p className="mt-3 text-xs text-muted">
          {used} of {seatLimit} seats used. Invitations expire after 7 days and count against your
          plan until they do. Delivery by email arrives with the merchant API — until then, send
          them the sign-in link yourself.
        </p>
      </Card>
    </div>
  );
}
