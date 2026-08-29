import { Link } from "react-router-dom";
import { useDbVersion, getDb } from "../../data/store";
import { useSession } from "../../data/session";
import { tenantGarments } from "../../data/queries";
import { PageHeader, Badge, ButtonLink, EmptyState } from "../../components/ui";
import { CAPTURE_VIEWS } from "../../data/types";
import { dashPath } from "../../routes";

const VIEW_LABELS: Record<string, string> = {
  front: "Front",
  back: "Back",
  left: "Left",
  right: "Right",
};

export default function AssetsPage() {
  const session = useSession();
  useDbVersion();
  if (!session?.tenant) return null;
  const tenant = session.tenant;

  const garments = tenantGarments(tenant.id);
  const db = getDb();
  // A CAD asset already contains the geometry the four views recover, so a
  // garment supplied that way is not "missing" anything.
  const captureDone = (g: (typeof garments)[number]) =>
    g.capture.method === "cad" ? Boolean(g.capture.cadAsset) : g.capture.accepted.length === CAPTURE_VIEWS.length;
  const incomplete = garments.filter((g) => !captureDone(g)).length;

  return (
    <>
      <PageHeader
        title="Assets"
        subtitle={
          garments.length === 0
            ? "The four-view capture set behind every try-on: front, back, left and right."
            : incomplete > 0
              ? `${incomplete} of ${garments.length} garments have an incomplete capture set. All four views — front, back, left and right — are required before a digital garment can be built.`
              : `All ${garments.length} garments have a complete four-view capture set. Detail shots sharpen texture realism further.`
        }
      />
      {garments.length === 0 ? (
        <EmptyState
          icon="🖼"
          title="No assets yet"
          body="Assets appear here once you add a garment and capture its four views."
          action={<ButtonLink href={dashPath.addGarment} variant="primary" size="sm">+ Add garment</ButtonLink>}
        />
      ) : (
        <div className="grid grid-cols-2 gap-4 max-md:grid-cols-1">
          {garments.map((g) => {
            const p = db.products.find((x) => x.id === g.productId);
            const accepted = g.capture.accepted.length;
            const complete = captureDone(g);
            return (
              // The card's title opens the garment's full summary; continuing
              // capture is its own action. A card that silently drops you into
              // a wizard is not a card.
              <div
                key={g.id}
                className="rounded-xl border border-line bg-surface p-4 transition-colors hover:border-line-strong"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-stone-100 text-lg" aria-hidden>{p?.imageEmoji}</span>
                    <div>
                      <Link
                        to={dashPath.garment(g.id)}
                        className="text-[13px] font-medium text-ink hover:text-accent"
                      >
                        {g.title}
                      </Link>
                      {/* Which physical size these photographs are of. Without
                          it, nobody can interpret them six months from now. */}
                      <div className="text-xs text-muted">
                        {g.referenceSize ? `Reference: Size ${g.referenceSize}` : "No reference sample recorded"}
                      </div>
                    </div>
                  </div>
                  {g.capture.method === "cad" ? (
                    <Badge tone={complete ? "success" : "warn"}>
                      {complete ? "3D asset accepted" : "3D asset needed"}
                    </Badge>
                  ) : complete ? (
                    <Badge tone="success">Capture complete</Badge>
                  ) : (
                    <Badge tone="warn">{CAPTURE_VIEWS.length - accepted} view{CAPTURE_VIEWS.length - accepted === 1 ? "" : "s"} needed</Badge>
                  )}
                </div>

                <div className="mt-3 grid grid-cols-4 gap-2">
                  {CAPTURE_VIEWS.map((view) => {
                    const has = g.capture.accepted.includes(view);
                    const issue = g.capture.issues.find((i) => i.view === view);
                    return (
                      <div
                        key={view}
                        title={issue?.message}
                        className={`flex aspect-[3/4] flex-col items-center justify-center gap-0.5 rounded-lg border text-[11px] ${
                          has
                            ? "border-line bg-stone-50 text-stone-500"
                            : issue
                              ? "border-dashed border-red-300 bg-red-50/40 text-red-700"
                              : "border-dashed border-amber-300 bg-amber-50/40 text-amber-700"
                        }`}
                      >
                        <span>{has ? "✓" : issue ? "!" : "+"}</span>
                        <span>{VIEW_LABELS[view]}</span>
                      </div>
                    );
                  })}
                </div>

                {g.capture.issues.length > 0 && (
                  <p className="mt-2 text-xs text-red-700">{g.capture.issues[0].message}</p>
                )}

                <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                  <p className="text-xs text-muted">
                    Optional details: {g.capture.details.length}
                    {g.capture.details.length > 0 && ` · ${g.capture.details.map((d) => d.label).join(", ")}`}
                  </p>
                  <Link
                    to={dashPath.garmentFlow(g.id, "capture")}
                    className="text-xs font-medium text-accent hover:underline"
                  >
                    {complete ? "Manage capture →" : "Continue capture →"}
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
