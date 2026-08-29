import { Link, useParams } from "react-router-dom";
import { GUIDES } from "./guides-content";
import { ButtonLink, Card, EmptyState, PageHeader } from "../../components/ui";
import { dashPath } from "../../routes";

export default function GuidesPage() {
  const { slug } = useParams<{ slug: string }>();
  const guide = GUIDES.find((g) => g.slug === slug);

  if (slug && !guide) {
    return (
      <EmptyState
        icon="📄"
        title="No such guide"
        body="That article doesn't exist — it may have been renamed."
        action={<ButtonLink href={dashPath.support} size="sm">Back to support</ButtonLink>}
      />
    );
  }

  if (!guide) {
    return (
      <>
        <div className="mb-1 text-xs text-muted">
          <Link to={dashPath.support} className="hover:text-ink">Support</Link> / Guides
        </div>
        <PageHeader title="Guides & knowledge base" subtitle="How the ingestion pipeline actually behaves, written against the rules it enforces." />
        <div className="grid grid-cols-2 gap-4 max-md:grid-cols-1">
          {GUIDES.map((g) => (
            <Link key={g.slug} to={dashPath.guide(g.slug)} className="block">
              <Card title={<span className="flex items-center gap-2"><span aria-hidden>{g.icon}</span>{g.title}</span>}>
                <p className="text-[13px] text-muted">{g.summary}</p>
              </Card>
            </Link>
          ))}
        </div>
      </>
    );
  }

  return (
    <>
      <div className="mb-1 text-xs text-muted">
        <Link to={dashPath.support} className="hover:text-ink">Support</Link> /{" "}
        <Link to={dashPath.guides} className="hover:text-ink">Guides</Link> / {guide.tag}
      </div>
      <PageHeader title={guide.title} subtitle={guide.summary} />
      <article className="max-w-2xl rounded-xl border border-line bg-surface p-6 text-[13px] leading-relaxed text-stone-700">
        {guide.body()}
      </article>
      <p className="mt-4 text-xs text-muted">
        Still stuck?{" "}
        <Link to={dashPath.support} className="font-medium text-accent hover:underline">
          Open a ticket
        </Link>{" "}
        — onboarding help is free on every plan.
      </p>
    </>
  );
}
