import { useParams, useSearchParams, Link } from "react-router-dom";
import { useDbVersion, getDb } from "../data/store";
import { useSession } from "../data/session";
import { publicCatalogue, resolveTenant } from "../data/publication";
import { Badge, Banner, ButtonLink, Card, EmptyState, PageHeader } from "../components/ui";
import { MirraLogo } from "../components/shell";
import { dashPath } from "../routes";

/**
 * The merchant's preview of their own tenant surface.
 *
 * This is deliberately rendered from `publicCatalogue()` — the same function
 * the storefront contract uses — rather than from the garment records. If a
 * garment is paused, unapproved, or hidden by the sold-out policy, it is
 * missing here for exactly the reason it would be missing for a shopper.
 *
 * "Open try-on studio" used to send a merchant to the generic shopper route
 * with no tenant, garment or revision context, which could not show them
 * anything about their own page.
 */
export default function PreviewPage() {
  const { slug } = useParams<{ slug: string }>();
  const [params] = useSearchParams();
  const session = useSession();
  useDbVersion();

  const db = getDb();
  const tenant = db.tenants.find((t) => t.slug === slug);
  const token = params.get("token");

  if (!tenant) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <EmptyState icon="🔍" title="No such preview" body="That address doesn't match a workspace." />
      </main>
    );
  }

  // A preview link is a capability: it shows unpublished content, so it needs
  // either the tenant's own token or a session that already has access.
  const tokenValid = token === tenant.previewToken;
  const memberHasAccess = session?.tenant?.id === tenant.id;
  if (!tokenValid && !memberHasAccess) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <MirraLogo sub="Preview" />
        <div className="mt-8">
          <Banner tone="danger">
            This preview link is missing or no longer valid. Copy a fresh one from the Publication
            page — preview links expose content shoppers can&apos;t see, so they aren&apos;t
            guessable.
          </Banner>
        </div>
      </main>
    );
  }

  const live = publicCatalogue(tenant.id);
  const withPreview = publicCatalogue(tenant.id, { preview: true });
  const liveIds = new Set(live.map((p) => p.publicProductId));
  const resolved = resolveTenant(tenant.id);
  const blocked = resolved.filter((r) => !r.visible);

  return (
    <main className="mx-auto max-w-5xl px-6 py-10 max-md:px-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <MirraLogo sub="Preview" />
        {memberHasAccess && (
          <ButtonLink href={dashPath.publication} size="sm">
            ← Back to Publication
          </ButtonLink>
        )}
      </div>

      <div className="mt-6">
        <Banner live tone="info">
          <strong>Preview of {tenant.name}.</strong> This is exactly what your try-on page resolves
          to right now, plus QA-approved garments you haven&apos;t published — those are marked{" "}
          <em>Not published</em> and shoppers cannot see them.
        </Banner>
      </div>

      <PageHeader
        title={tenant.theme.welcomeHeadline}
        subtitle={`${live.length} garment${live.length === 1 ? "" : "s"} live · ${withPreview.length - live.length} awaiting publication · ${tenant.domain.subdomain}`}
      />

      {withPreview.length === 0 ? (
        <EmptyState
          icon="👗"
          title="Nothing to preview yet"
          body="Once a garment passes QA it appears here, so you can check it before shoppers can."
          action={<ButtonLink href={dashPath.garments} size="sm">Go to garments</ButtonLink>}
        />
      ) : (
        <div className="grid grid-cols-3 gap-4 max-lg:grid-cols-2 max-md:grid-cols-1">
          {withPreview.map((p) => {
            const isLive = liveIds.has(p.publicProductId);
            return (
              <Card
                key={p.publicProductId}
                title={p.name}
                action={
                  isLive ? <Badge tone="success">Live</Badge> : <Badge tone="warn">Not published</Badge>
                }
              >
                <div className="text-[13px] text-muted">{p.subtitle}</div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {p.variants.map((v) => (
                    <span
                      key={v.publicVariantId}
                      className={`rounded-md border px-2 py-0.5 text-xs ${
                        v.inStock ? "border-line text-stone-700" : "border-line text-stone-400 line-through"
                      }`}
                      title={v.inStock ? undefined : "Sold out in Shopify"}
                    >
                      {v.size}
                    </span>
                  ))}
                </div>
                <dl className="mt-3 space-y-1 text-xs text-muted">
                  {p.materialAndCare && (
                    <div>
                      <dt className="inline font-medium text-stone-700">Material: </dt>
                      <dd className="inline">{p.materialAndCare}</dd>
                    </div>
                  )}
                  {p.fitInfo && (
                    <div>
                      <dt className="inline font-medium text-stone-700">Fit: </dt>
                      <dd className="inline">{p.fitInfo}</dd>
                    </div>
                  )}
                  <div>
                    <dt className="inline font-medium text-stone-700">Try-on: </dt>
                    <dd className="inline">
                      {/* Honest about the one thing that isn't wired: the
                          rendered asset comes from the VTO pipeline, and until
                          that lands there is nothing to put on an avatar. */}
                      {p.tryOnEligible
                        ? "Eligible — awaiting a rendered garment asset from the pipeline"
                        : "Not eligible"}
                    </dd>
                  </div>
                </dl>
                <div className="mt-3">
                  <Link
                    to={dashPath.garment(p.publicProductId)}
                    className="text-xs font-medium text-accent hover:underline"
                  >
                    Open in dashboard →
                  </Link>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Why something a merchant expected to see isn't here. */}
      {blocked.length > 0 && (
        <div className="mt-8">
          <Card title={`Not in this preview — ${blocked.length}`}>
            <ul className="divide-y divide-stone-100">
              {blocked.slice(0, 10).map((r) => (
                <li key={r.garmentId} className="flex items-start justify-between gap-3 py-2 text-[13px]">
                  <span className="font-medium text-ink">{r.title}</span>
                  <span className="text-right text-xs text-muted">{r.blockedDetail}</span>
                </li>
              ))}
            </ul>
            {blocked.length > 10 && (
              <p className="mt-2 text-xs text-muted">…and {blocked.length - 10} more.</p>
            )}
          </Card>
        </div>
      )}
    </main>
  );
}
