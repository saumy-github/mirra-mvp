import { useMemo, useState } from "react";
import { useDbVersion, getDb } from "../../data/store";
import { useSession } from "../../data/session";
import { can } from "../../data/rbac";
import { fmtDateTime } from "../../data/util";
import {
  Badge,
  Banner,
  EmptyState,
  PageHeader,
  Pagination,
  Table,
  Td,
} from "../../components/ui";
import { buttonClass } from "../../components/styles";
import { AuditTarget } from "../../components/audit-target";

const PAGE_SIZE = 50;

/** Coarse groups, so a merchant can find "who published something" quickly. */
const GROUPS: { value: string; label: string; match: (action: string) => boolean }[] = [
  { value: "all", label: "All activity", match: () => true },
  { value: "publication", label: "Publication", match: (a) => /^garment\.(live|paused|tryon|schedule)/.test(a) || a.startsWith("tenant.launch") },
  { value: "ingestion", label: "Ingestion edits", match: (a) => a.startsWith("garment.") && !/^garment\.(live|paused|tryon|schedule)/.test(a) },
  { value: "qa", label: "QA", match: (a) => a.includes("qa_") },
  { value: "access", label: "Access & staff", match: (a) => a.startsWith("impersonation") || a.startsWith("team.") },
  { value: "billing", label: "Billing & lifecycle", match: (a) => a.startsWith("tenant.") && !a.startsWith("tenant.launch") },
];

export default function AuditPage() {
  const session = useSession();
  const [group, setGroup] = useState("all");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  useDbVersion();

  const tenantId = session?.tenant?.id;
  const all = useMemo(
    () =>
      tenantId
        ? // Newest first, always. Seeded and live events were interleaved in
          // insertion order, so the log read as if time ran backwards in places.
          [...getDb().auditEvents]
            .filter((e) => e.tenantId === tenantId)
            .sort((a, b) => b.at.localeCompare(a.at))
        : [],
    [tenantId],
  );

  if (!session?.tenant) return null;
  const tenant = session.tenant;

  if (!can(session.role, "audit.view")) {
    return (
      <>
        <PageHeader title="Audit log" />
        <Banner tone="info">Audit history is visible to owners and viewers only.</Banner>
      </>
    );
  }

  const matcher = GROUPS.find((g) => g.value === group) ?? GROUPS[0];
  const q = query.trim().toLowerCase();
  const events = all.filter(
    (e) =>
      matcher.match(e.action) &&
      (!q ||
        e.actorName.toLowerCase().includes(q) ||
        e.action.toLowerCase().includes(q) ||
        e.target.toLowerCase().includes(q) ||
        (e.detail ?? "").toLowerCase().includes(q)),
  );
  const pageEvents = events.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const exportCsv = () => {
    const rows = [
      ["timestamp", "actor", "action", "target", "detail"],
      ...events.map((e) => [e.at, e.actorName, e.action, e.target, e.detail ?? ""]),
    ];
    const csv = rows
      .map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(","))
      .join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `mirra-audit-${tenant.slug}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <PageHeader
        title="Audit log"
        subtitle="Every catalogue edit, publication change, QA decision, seat change and staff access in this workspace — newest first."
        action={
          events.length > 0 ? (
            <button onClick={exportCsv} className={buttonClass("secondary", "sm")}>
              ↓ Export {events.length} entries
            </button>
          ) : undefined
        }
      />

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <label className="sr-only" htmlFor="audit-group">Filter by activity</label>
        <select
          id="audit-group"
          value={group}
          onChange={(e) => { setGroup(e.target.value); setPage(0); }}
          className="rounded-lg border border-line bg-surface px-2.5 py-1.5 text-[13px]"
        >
          {GROUPS.map((g) => (
            <option key={g.value} value={g.value}>{g.label}</option>
          ))}
        </select>
        <label className="sr-only" htmlFor="audit-search">Search the audit log</label>
        <input
          id="audit-search"
          type="search"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setPage(0); }}
          placeholder="Search actor, action or object…"
          className="w-64 rounded-lg border border-line bg-surface px-3 py-1.5 text-[13px] focus:border-accent focus:outline-none"
        />
        <span className="text-xs text-muted" aria-live="polite">
          {events.length} of {all.length} entries
        </span>
      </div>

      {all.length === 0 ? (
        <EmptyState icon="≡" title="No recorded actions yet" />
      ) : events.length === 0 ? (
        <EmptyState
          icon="≡"
          title="Nothing matches that filter"
          body="Try a different activity group, or clear the search."
        />
      ) : (
        <>
          <Table
            caption="Recorded actions in this workspace, newest first"
            headers={["When", "Actor", "Action", "Target", "Detail"]}
          >
            {pageEvents.map((e) => (
              <tr key={e.id} className="hover:bg-stone-50/60">
                <Td className="whitespace-nowrap text-xs text-muted">{fmtDateTime(e.at)}</Td>
                <Td className="font-medium text-ink">{e.actorName}</Td>
                <Td>
                  <Badge
                    tone={
                      e.action.startsWith("impersonation")
                        ? "warn"
                        : e.action.includes("suspend") || e.action.includes("cancel")
                          ? "danger"
                          : "neutral"
                    }
                  >
                    {e.action}
                  </Badge>
                </Td>
                <Td className="text-stone-600"><AuditTarget tenantId={tenant.id} target={e.target} /></Td>
                <Td className="text-xs text-muted">{e.detail ?? "—"}</Td>
              </tr>
            ))}
          </Table>
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            total={events.length}
            onPage={setPage}
            label="Audit log pages"
          />
        </>
      )}
    </>
  );
}
