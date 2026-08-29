import { useState } from "react";
import { qaDecisionAction } from "../data/actions";
import { MEASUREMENT_FIELDS } from "../data/ingestion";
import { CAPTURE_VIEWS } from "../data/types";
import type { CaptureView, Garment, QaArea, QaFinding } from "../data/types";
import {
  Badge,
  Card,
  Field,
  NoticeBar,
} from "./ui";
import { useAction } from "./use-action";
import { buttonClass, inputClass } from "./styles";

type DraftFinding = Omit<QaFinding, "id" | "raisedBy" | "raisedAt" | "revision">;

const AREAS: { value: QaArea; label: string }[] = [
  { value: "capture", label: "Capture" },
  { value: "sizing", label: "Sizing" },
  { value: "material", label: "Material" },
  { value: "mapping", label: "Variant mapping" },
  { value: "fit", label: "Fit" },
  { value: "other", label: "Other" },
];

/**
 * The QA decision.
 *
 * Passing freezes a snapshot of the revision that was actually checked — that
 * snapshot is what the public surface serves, so an edit made afterwards can
 * never reach a shopper under this approval.
 *
 * Failing requires findings. "Send back" used to write one fixed sentence to
 * an audit log the merchant doesn't read, which told them a garment had been
 * rejected and nothing whatsoever about what to change.
 */
export function QaPanel({ garment: g }: { garment: Garment }) {
  const [findings, setFindings] = useState<DraftFinding[]>([]);
  const [note, setNote] = useState("");
  const [draft, setDraft] = useState<DraftFinding>({
    area: "capture",
    severity: "blocker",
    detail: "",
    instruction: "",
  });
  const { pending, notice, run, clear } = useAction();

  const measurementKeys = MEASUREMENT_FIELDS[g.category];
  const canAdd = draft.detail.trim().length > 3 && draft.instruction.trim().length > 3;

  const add = () => {
    setFindings((f) => [...f, { ...draft, detail: draft.detail.trim(), instruction: draft.instruction.trim() }]);
    setDraft({ area: draft.area, severity: "blocker", detail: "", instruction: "" });
  };

  return (
    <Card
      title="Mirra QA"
      action={<Badge tone="info">Revision {g.sourceRevision}</Badge>}
    >
      <NoticeBar notice={notice} onDismiss={clear} />
      <p className="mb-3 text-[13px] text-muted">
        Passing freezes revision {g.sourceRevision} and makes it publishable by the brand — shoppers
        are served that frozen copy, not whatever the garment says later. Sending it back returns it
        to the merchant with the findings below.
      </p>

      {g.qaHistory.length > 0 && (
        <details className="mb-3">
          <summary className="cursor-pointer text-xs font-medium text-ink">
            Decision history ({g.qaHistory.length})
          </summary>
          <ul className="mt-1.5 space-y-1">
            {g.qaHistory.map((h, i) => (
              <li key={i} className="text-xs text-muted">
                <span className={h.decision === "pass" ? "text-emerald-700" : "text-red-700"}>
                  {h.decision === "pass" ? "Passed" : "Sent back"}
                </span>{" "}
                revision {h.revision} · {h.by} ·{" "}
                {new Date(h.at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                {h.findingCount ? ` · ${h.findingCount} finding(s)` : ""}
                {h.note ? ` · ${h.note}` : ""}
              </li>
            ))}
          </ul>
        </details>
      )}

      {findings.length > 0 && (
        <ul className="mb-3 space-y-2 rounded-lg border border-line bg-stone-50 p-3">
          {findings.map((f, i) => (
            <li key={i} className="flex items-start justify-between gap-3 text-[13px]">
              <span>
                <Badge tone={f.severity === "blocker" ? "danger" : "warn"}>{f.severity}</Badge>{" "}
                <span className="font-medium capitalize">{f.area}</span>
                {f.view && <span className="text-xs text-muted"> · {f.view}</span>}
                {f.measurementKey && <span className="text-xs text-muted"> · {f.measurementKey}</span>}
                <span className="block text-stone-700">{f.detail}</span>
                <span className="block text-xs text-muted">→ {f.instruction}</span>
              </span>
              <button
                onClick={() => setFindings((x) => x.filter((_, j) => j !== i))}
                className={buttonClass("ghost", "sm")}
                aria-label={`Remove finding ${i + 1}`}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}

      <details className="mb-3">
        <summary className="cursor-pointer text-[13px] font-medium text-ink">Add a finding</summary>
        <div className="mt-2 grid grid-cols-2 gap-3 max-md:grid-cols-1">
          <Field label="Area">
            <select
              value={draft.area}
              onChange={(e) => setDraft({ ...draft, area: e.target.value as QaArea, view: undefined, measurementKey: undefined })}
              className={inputClass}
            >
              {AREAS.map((a) => (
                <option key={a.value} value={a.value}>{a.label}</option>
              ))}
            </select>
          </Field>
          <Field label="Severity">
            <select
              value={draft.severity}
              onChange={(e) => setDraft({ ...draft, severity: e.target.value as "blocker" | "advisory" })}
              className={inputClass}
            >
              <option value="blocker">Blocker — must be fixed</option>
              <option value="advisory">Advisory — would improve it</option>
            </select>
          </Field>
          {/* Anchoring a finding to the exact view or measurement is what makes
              it actionable rather than a mood. */}
          {draft.area === "capture" && (
            <Field label="Which view">
              <select
                value={draft.view ?? ""}
                onChange={(e) => setDraft({ ...draft, view: (e.target.value || undefined) as CaptureView | undefined })}
                className={inputClass}
              >
                <option value="">Not view-specific</option>
                {CAPTURE_VIEWS.map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
            </Field>
          )}
          {draft.area === "sizing" && (
            <Field label="Which measurement">
              <select
                value={draft.measurementKey ?? ""}
                onChange={(e) => setDraft({ ...draft, measurementKey: e.target.value || undefined })}
                className={inputClass}
              >
                <option value="">Not measurement-specific</option>
                {measurementKeys.map((f) => (
                  <option key={f.key} value={f.key}>{f.label}</option>
                ))}
              </select>
            </Field>
          )}
          <div className="col-span-2 max-md:col-span-1">
            <Field label="What's wrong">
              <input
                value={draft.detail}
                onChange={(e) => setDraft({ ...draft, detail: e.target.value })}
                placeholder="The left sleeve is cropped at the cuff."
                className={inputClass}
              />
            </Field>
          </div>
          <div className="col-span-2 max-md:col-span-1">
            <Field label="What the merchant should do">
              <input
                value={draft.instruction}
                onChange={(e) => setDraft({ ...draft, instruction: e.target.value })}
                placeholder="Reshoot the left view with the whole sleeve inside the frame."
                className={inputClass}
              />
            </Field>
          </div>
        </div>
        <button disabled={!canAdd} onClick={add} className={`${buttonClass("secondary", "sm")} mt-2`}>
          Add finding
        </button>
      </details>

      <Field label="Internal note (optional)">
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          className={inputClass}
          placeholder="Context for the next reviewer"
        />
      </Field>

      <div className="mt-3 flex flex-wrap gap-2">
        <button
          disabled={pending}
          onClick={() => run(() => qaDecisionAction(g.id, "pass", [], note || undefined))}
          className={buttonClass("accent", "sm")}
        >
          Pass QA — freeze revision {g.sourceRevision}
        </button>
        <button
          disabled={pending || findings.length === 0}
          title={findings.length === 0 ? "Add at least one finding the merchant can act on" : undefined}
          onClick={() => run(() => qaDecisionAction(g.id, "fail", findings, note || undefined))}
          className={buttonClass("danger", "sm")}
        >
          Send back with {findings.length} finding{findings.length === 1 ? "" : "s"}
        </button>
      </div>
    </Card>
  );
}
