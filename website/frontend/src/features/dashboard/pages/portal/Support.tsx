import { useDbVersion, getDb } from "../../data/store";
import { useSession } from "../../data/session";
import { getEntitlements } from "../../data/entitlements";
import { createTicketAction, escalateTicketAction } from "../../data/actions";
import { GUIDES } from "./guides-content";
import { can } from "../../data/rbac";
import { timeAgo } from "../../data/util";
import {
  ActionButton,
  Badge,
  Card,
  Field,
  NoticeBar,
  PageHeader,
  SubmitButton,
} from "../../components/ui";
import { useAction } from "../../components/use-action";
import { inputClass } from "../../components/styles";
import { Link } from "react-router-dom";
import { dashPath } from "../../routes";

const SLA: Record<string, string> = {
  standard: "Response within 1 business day",
  priority: "Response within 4 business hours",
  dedicated: "Dedicated CSM + 2h production SLA",
};

export default function SupportPage() {
  const session = useSession();
  const notice = useAction();
  useDbVersion();
  if (!session?.tenant) return null;
  const tenant = session.tenant;

  const db = getDb();
  const ent = getEntitlements(tenant);
  const tickets = db.tickets.filter((t) => t.tenantId === tenant.id);
  const open = tickets.filter((t) => t.status !== "resolved").length;
  const canCreate = can(session.role, "support.create");

  return (
    <>
      <PageHeader
        title="Support"
        subtitle={
          <span>
            {open > 0
              ? `${open} of your ${tickets.length} tickets ${open === 1 ? "is" : "are"} still open. `
              : "No open tickets — we're here when you need us. "}
            <Badge tone="info">{ent.supportTier} tier · {SLA[ent.supportTier]}</Badge>
          </span>
        }
      />

      <div className="grid grid-cols-3 gap-4 max-lg:grid-cols-1">
        <div className="col-span-2 flex flex-col gap-4 max-lg:col-span-1">
          <Card title="Your tickets">
            {tickets.length === 0 ? (
              <p className="py-4 text-center text-[13px] text-muted">No tickets yet — smooth sailing. Browse the guides or open a ticket anytime.</p>
            ) : (
              <ul className="divide-y divide-stone-100">
                {tickets.map((t) => (
                  <li key={t.id} className="py-3">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <span className="text-[13px] font-medium text-ink">{t.subject}</span>
                        <span className="ml-2 text-xs text-muted">#{t.id} · {t.category.replace("_", " ")} · {timeAgo(t.createdAt)}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge tone={t.status === "resolved" ? "success" : t.status === "escalated" ? "danger" : t.status === "open" ? "info" : "neutral"}>
                          {t.status}
                        </Badge>
                        {t.status !== "resolved" && t.status !== "escalated" && canCreate && (
                          <ActionButton variant="ghost" onAction={() => escalateTicketAction(t.id)}>
                            Escalate
                          </ActionButton>
                        )}
                      </div>
                    </div>
                    <div className="mt-2 space-y-1.5">
                      {t.messages.slice(-2).map((m, i) => (
                        <p key={i} className="text-[13px] text-stone-600">
                          <span className="font-medium text-stone-700">{m.from}:</span> {m.body}
                        </p>
                      ))}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          {canCreate && (
            <Card title="Open a ticket">
              <NoticeBar notice={notice.notice} onDismiss={notice.clear} />
              <form
                action={(formData: FormData) => notice.run(() => createTicketAction(formData))}
                className="space-y-4"
              >
                <div className="grid grid-cols-3 gap-3 max-md:grid-cols-1">
                  <div className="col-span-2 max-md:col-span-1">
                    <Field label="Subject">
                      <input name="subject" required className={inputClass} placeholder="Brief summary" />
                    </Field>
                  </div>
                  <Field label="Category">
                    <select name="category" className={inputClass}>
                      <option value="onboarding">Onboarding</option>
                      <option value="catalogue">Catalogue & sync</option>
                      <option value="billing">Billing</option>
                      <option value="production_issue">Production issue</option>
                      <option value="other">Other</option>
                    </select>
                  </Field>
                </div>
                <Field label="What's happening?">
                  <textarea name="body" required rows={3} className={inputClass} placeholder="Tell us what you expected and what you're seeing instead." />
                </Field>
                <div className="flex items-center gap-3">
                  <SubmitButton variant="primary">Submit ticket</SubmitButton>
                  <span className="text-xs text-muted">{SLA[ent.supportTier]}</span>
                </div>
              </form>
            </Card>
          )}
        </div>

        <div className="flex flex-col gap-4">
          {/* These were six lines of plain text pretending to be links. They
              are now real pages, written against the rules ingestion enforces. */}
          <Card
            title="Guides & knowledge base"
            action={
              <Link to={dashPath.guides} className="text-xs font-medium text-accent hover:underline">
                All guides →
              </Link>
            }
          >
            <ul className="space-y-2.5">
              {GUIDES.map((a) => (
                <li key={a.slug}>
                  <Link
                    to={dashPath.guide(a.slug)}
                    className="group flex items-start gap-2.5 text-[13px] hover:text-accent"
                  >
                    <span aria-hidden>{a.icon}</span>
                    <span>
                      <span className="block text-stone-700 group-hover:text-accent">{a.title}</span>
                      <span className="block text-xs text-muted">{a.summary}</span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </Card>
          <Card title="Live chat">
            <p className="text-[13px] text-muted">
              Chat with the team Mon–Fri, 9:00–18:00 CET.
            </p>
            <button className="mt-3 w-full cursor-pointer rounded-lg border border-line bg-stone-50 px-3 py-2 text-[13px] font-medium text-stone-500" disabled>
              💬 Chat (coming soon)
            </button>
          </Card>
          <Card title="Production emergency?">
            <p className="text-[13px] text-stone-700">
              If your live try-on page is down or misbehaving for shoppers, open a ticket with category
              <strong> Production issue</strong> and escalate it — it pages our on-call engineer directly.
            </p>
          </Card>
        </div>
      </div>
    </>
  );
}
