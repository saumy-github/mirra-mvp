import { useState } from "react";
import { Link } from "react-router-dom";
import { useDbVersion, getDb } from "../../data/store";
import { useSession } from "../../data/session";
import { canInternal } from "../../data/rbac";
import {
  assignTicketAction,
  replyToTicketAction,
  setTicketStatusAction,
} from "../../data/actions";
import { fmtDateTime, timeAgo } from "../../data/util";
import {
  ActionButton,
  Badge,
  Banner,
  Card,
  EmptyState,
  NoticeBar,
  PageHeader,
} from "../../components/ui";
import { useAction } from "../../components/use-action";
import { buttonClass, inputClass } from "../../components/styles";
import type { Ticket, TicketStatus } from "../../data/types";
import { dashPath } from "../../routes";

const STATUS_TONE: Record<TicketStatus, "danger" | "info" | "neutral" | "success"> = {
  escalated: "danger",
  open: "info",
  pending: "neutral",
  resolved: "success",
};

/**
 * The internal support queue, as something you can work rather than read.
 *
 * It listed tickets and offered no way to pick one up, answer it or close it —
 * so the failures ingestion surfaces (sync errors, rejected captures, QA
 * questions) had nowhere to be resolved.
 */
export default function AdminSupportPage() {
  const session = useSession();
  const [openId, setOpenId] = useState<string | null>(null);
  useDbVersion();

  const db = getDb();
  const canManage = canInternal(session?.user.internalRole, "console.support.manage");
  const staff = db.users.filter((u) => u.internalRole);

  const tickets = [...db.tickets].sort((a, b) => {
    const rank = (t: Ticket) =>
      t.status === "escalated" ? 0 : t.status === "open" ? 1 : t.status === "pending" ? 2 : 3;
    return rank(a) - rank(b) || b.createdAt.localeCompare(a.createdAt);
  });
  const unresolved = tickets.filter((t) => t.status !== "resolved").length;
  const escalated = tickets.filter((t) => t.status === "escalated").length;
  const mine = tickets.filter((t) => t.assigneeId === session?.user.id && t.status !== "resolved").length;

  return (
    <>
      {/* The queue's one question is what needs answering now, so the counts
          that decide that lead — not the total. */}
      <PageHeader
        title="Support queue"
        subtitle={
          escalated > 0
            ? `${escalated} escalated and ${unresolved - escalated} open · ${mine} assigned to you. Escalations page the on-call engineer; SLA clocks run from the first customer message.`
            : unresolved > 0
              ? `${unresolved} ticket${unresolved === 1 ? "" : "s"} awaiting a reply, none escalated · ${mine} assigned to you.`
              : "Nothing awaiting a reply. SLA clocks run from the first customer message."
        }
      />

      {!canManage && (
        <div className="mb-5">
          <Banner tone="info">
            Your console role can read the queue but not work it. Support and Admin can assign,
            reply and change status.
          </Banner>
        </div>
      )}

      {tickets.length === 0 ? (
        <EmptyState icon="◉" title="No tickets" body="Nothing has been raised yet." />
      ) : (
        <div className="flex flex-col gap-3">
          {tickets.map((t) => {
            const tenant = db.tenants.find((x) => x.id === t.tenantId);
            const assignee = db.users.find((u) => u.id === t.assigneeId);
            const last = t.messages[t.messages.length - 1];
            const isOpen = openId === t.id;
            return (
              <Card
                key={t.id}
                title={
                  <span className="flex flex-wrap items-center gap-2">
                    <Badge tone={STATUS_TONE[t.status]}>{t.status}</Badge>
                    <span>{t.subject}</span>
                    {t.priority === "urgent" && <Badge tone="danger">urgent</Badge>}
                  </span>
                }
                action={
                  <button
                    onClick={() => setOpenId(isOpen ? null : t.id)}
                    aria-expanded={isOpen}
                    className={buttonClass("secondary", "sm")}
                  >
                    {isOpen ? "Close" : "Open"}
                  </button>
                }
              >
                <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted">
                  <span>
                    {tenant ? (
                      <Link to={dashPath.adminTenant(tenant.id)} className="font-medium text-ink hover:text-accent">
                        {tenant.name}
                      </Link>
                    ) : (
                      "—"
                    )}{" "}
                    · {t.category.replace("_", " ")} · #{t.id} · opened {timeAgo(t.createdAt)}
                  </span>
                  <span>
                    {assignee ? `Assigned to ${assignee.name}` : "Unassigned"}
                  </span>
                </div>
                {!isOpen && (
                  <p className="mt-2 truncate text-[13px] text-stone-600">
                    <span className="font-medium text-stone-700">{last.from}:</span> {last.body}
                  </p>
                )}
                {isOpen && (
                  <TicketDetail
                    ticket={t}
                    canManage={canManage}
                    staff={staff}
                    currentUserId={session?.user.id}
                  />
                )}
              </Card>
            );
          })}
        </div>
      )}
    </>
  );
}

function TicketDetail({
  ticket: t,
  canManage,
  staff,
  currentUserId,
}: {
  ticket: Ticket;
  canManage: boolean;
  staff: { id: string; name: string }[];
  currentUserId?: string;
}) {
  const [body, setBody] = useState("");
  const [internal, setInternal] = useState(false);
  const { pending, notice, run, clear } = useAction();

  return (
    <div className="mt-3 border-t border-line pt-3">
      <NoticeBar notice={notice} onDismiss={clear} />
      <ul className="space-y-2.5">
        {t.messages.map((m, i) => (
          <li
            key={i}
            className={`rounded-lg px-3 py-2 text-[13px] ${
              m.internal ? "border border-dashed border-line bg-stone-50" : "bg-stone-50"
            }`}
          >
            <div className="flex items-center justify-between gap-2 text-xs text-muted">
              <span className="font-medium text-stone-700">
                {m.from}
                {m.internal && " · internal note"}
              </span>
              <span>{fmtDateTime(m.at)}</span>
            </div>
            <p className="mt-1 text-stone-700">{m.body}</p>
          </li>
        ))}
      </ul>

      {canManage && (
        <>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <label className="sr-only" htmlFor={`assign-${t.id}`}>Assign</label>
            <select
              id={`assign-${t.id}`}
              value={t.assigneeId ?? ""}
              onChange={(e) => run(() => assignTicketAction(t.id, e.target.value || undefined))}
              className="rounded-lg border border-line bg-surface px-2 py-1 text-xs"
            >
              <option value="">Unassigned</option>
              {staff.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name}
                  {u.id === currentUserId ? " (you)" : ""}
                </option>
              ))}
            </select>
            {(["open", "pending", "escalated", "resolved"] as TicketStatus[])
              .filter((st) => st !== t.status)
              .map((st) => (
                <ActionButton key={st} onAction={() => setTicketStatusAction(t.id, st)}>
                  Mark {st}
                </ActionButton>
              ))}
          </div>

          <div className="mt-3">
            <label className="sr-only" htmlFor={`reply-${t.id}`}>Reply</label>
            <textarea
              id={`reply-${t.id}`}
              rows={2}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Reply to the merchant…"
              className={inputClass}
            />
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <button
                disabled={!body.trim() || pending}
                onClick={() => run(() => replyToTicketAction(t.id, body, internal), () => setBody(""))}
                className={buttonClass("accent", "sm")}
              >
                {pending ? "Sending…" : internal ? "Add internal note" : "Send reply"}
              </button>
              <label className="flex items-center gap-1.5 text-xs text-muted">
                <input type="checkbox" checked={internal} onChange={(e) => setInternal(e.target.checked)} />
                Internal note — not visible to the merchant
              </label>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
