import { CAPTURE_SPEC, MEASUREMENT_FIELDS } from "../../data/ingestion";
/**
 * The knowledge base, as actual readable pages.
 *
 * Support listed six article titles as plain text — nothing to click, nothing
 * to read. The two that matter most (capture and sizing) are generated from
 * the same constants the ingestion flow enforces, so the guidance cannot drift
 * from the rules the product actually applies.
 */
export interface Guide {
  slug: string;
  icon: string;
  title: string;
  tag: string;
  summary: string;
  body: () => React.ReactNode;
}

const section = (heading: string, children: React.ReactNode) => (
  <section key={heading} className="mt-5">
    <h3 className="text-[13px] font-semibold text-ink">{heading}</h3>
    <div className="mt-1.5 space-y-2 text-[13px] leading-relaxed text-stone-700">{children}</div>
  </section>
);

export const GUIDES: Guide[] = [
  {
    slug: "launch-checklist",
    icon: "🚀",
    title: "Launch checklist: from sync to live",
    tag: "Onboarding",
    summary: "The whole path a garment takes, and who owns each step.",
    body: () => (
      <>
        <p>
          A garment moves through seven states. You own every one of them except the QA decision,
          which is ours.
        </p>
        {section("1. Identify",
          <p>
            Paste the Shopify product URL. Mirra resolves it against your connected store and locks
            the listing, so a try-on record can always be traced back to a product a shopper can buy.
            Pick the colourway and the exact size of the physical sample you have in your hands.
          </p>
        )}
        {section("2. Capture",
          <p>
            Four views of that one sample, shot to the specification in the capture guide. One
            sample plus a size chart produces every digital size — you do not photograph S, M, L and
            XL separately unless they use genuinely different pattern blocks.
          </p>
        )}
        {section("3. Material and sizing",
          <p>
            Composition as proportions, then measurements. Both are inputs to the simulation, not
            metadata: stretch and drape follow from the blend, and fit follows from the numbers.
          </p>
        )}
        {section("4. Your review, then QA",
          <p>
            When nothing is blocking, the garment moves to your review. Send it to Mirra QA when
            you&apos;re happy. QA approves a specific revision and freezes it — that frozen copy is
            what shoppers see, which is why an edit made afterwards has to go round again.
          </p>
        )}
        {section("5. Publish",
          <p>
            Publish from Publication, or schedule a go-live. Check the preview link first: it renders
            exactly what your public page resolves to.
          </p>
        )}
      </>
    ),
  },
  {
    slug: "image-guidelines",
    icon: "🖼",
    title: "Image guidelines for best try-on results",
    tag: "Assets",
    summary: "Why your Shopify photography won't work, and what does.",
    body: () => (
      <>
        <p>
          Marketing photography is styled for merchandising — models, props, crops, colour grading.
          None of that can be reconstructed into a wearable garment, which is why every drop needs
          its sample re-shot plain and flat, four ways.
        </p>
        {section("The six rules",
          <dl className="space-y-2">
            {CAPTURE_SPEC.map((s) => (
              <div key={s.rule}>
                <dt className="font-medium text-ink">✓ {s.rule}</dt>
                <dd className="text-muted">{s.why}</dd>
              </div>
            ))}
          </dl>
        )}
        {section("Detail shots",
          <p>
            Optional and worth it. A fabric close-up measurably improves texture realism; closure,
            collar and hem shots help where construction is unusual.
          </p>
        )}
        {section("If a view is rejected",
          <p>
            The rejection names what was wrong with that specific view — a cropped hem, a hard
            shadow, a skewed camera angle. Reshoot only that view; the others stand.
          </p>
        )}
      </>
    ),
  },
  {
    slug: "size-charts",
    icon: "📐",
    title: "How size charts power fit accuracy",
    tag: "Size & fit",
    summary: "Body vs finished-garment, units, and how ungraded sizes are produced.",
    body: () => (
      <>
        {section("Body or finished garment — they are not the same numbers",
          <p>
            A finished-garment measurement is taken flat across the garment, seam to seam. A body
            measurement is taken around the wearer. For the same product they differ by roughly a
            factor of two plus the garment&apos;s ease, so telling Mirra which you supplied is not a
            formality — getting it wrong is the single most common cause of a garment that fits
            nobody.
          </p>
        )}
        {section("Units",
          <p>
            Everything is stored in centimetres. You can enter or upload in inches and Mirra
            converts on the way in, showing you the conversion. A value far outside the plausible
            range for its measurement is flagged rather than accepted — that is almost always inches
            typed into a centimetre column.
          </p>
        )}
        {section("What each category asks for",
          <>
          <p>
            Only the measurements that category actually uses. A trouser is never asked for a bust
            measurement.
          </p>
          <ul className="mt-2 space-y-1">
            {(Object.keys(MEASUREMENT_FIELDS) as (keyof typeof MEASUREMENT_FIELDS)[]).map((c) => (
              <li key={c} className="text-xs">
                <span className="font-medium text-ink capitalize">{c}: </span>
                <span className="text-muted">
                  {MEASUREMENT_FIELDS[c].map((f) => f.label).join(", ")}
                </span>
              </li>
            ))}
          </ul>
          </>
        )}
        {section("How the sizes you didn't measure are produced",
          <p>
            In order of how much they can be trusted: a full graded chart you supplied; your brand
            grading rules stepped from the measured reference size; or, as a last resort, sizes
            inferred from one sample. The third is marked as a draft and will not count as complete
            until you have verified it — Mirra does not present an inference as a measurement.
          </p>
        )}
      </>
    ),
  },
  {
    slug: "shopify-sync",
    icon: "🛍",
    title: "Managing your Shopify sync",
    tag: "Catalogue",
    summary: "What syncs, what doesn't, and what a conflict means.",
    body: () => (
      <>
        <p>
          Shopify is the source of truth for products, variants and inventory. Mirra reads and never
          writes.
        </p>
        {section("Preview before you sync",
          <p>
            &quot;Preview changes&quot; on Products shows what a sync would do: new products,
            re-reads, failures and conflicts. Run it before syncing a catalogue with digitised
            garments in it.
          </p>
        )}
        {section("Failures vs conflicts",
          <>
          <p>
            A <strong>failure</strong> is Mirra being unable to read something — usually a product
            image returning 404 from Shopify&apos;s CDN. Fix it at source and retry.
          </p>
          <p>
            A <strong>conflict</strong> is a change Mirra refuses to apply on its own, because a
            digitised garment depends on the thing that changed — typically a SKU that has been
            deleted in Shopify while a QA-approved garment still covers it. Applying that silently
            would leave shoppers able to try on a size they cannot buy.
          </p>
          </>
        )}
      </>
    ),
  },
  {
    slug: "publishing",
    icon: "⇱",
    title: "Publishing, pausing, and scheduling go-lives",
    tag: "Publication",
    summary: "What each control does to a live storefront.",
    body: () => (
      <>
        {section("What shoppers actually get",
          <p>
            Publication shows two different things per garment: its stage, and what shoppers see.
            They can differ — a garment can be &quot;Live&quot; and still not reachable because
            every size is sold out under a hide-sold-out policy, or because the whole page is
            paused.
          </p>
        )}
        {section("Approved revisions",
          <p>
            Shoppers are served the revision QA approved, frozen at approval time. If you edit a
            live garment, they keep seeing the approved version until the new one passes QA. That is
            deliberate: it is the only way to be sure nobody is shown a garment built from photos or
            measurements no one checked.
          </p>
        )}
        {section("Pausing",
          <p>
            Pausing hides a garment or the whole page immediately and deletes nothing. QA approval
            survives, so resuming is a single click with no re-review.
          </p>
        )}
        {section("Scheduling",
          <p>
            A QA-passed garment can be scheduled to publish at a time you choose. It still has to
            pass the plan&apos;s SKU limit at the moment it fires; if it can&apos;t, the schedule is
            cancelled and the reason is written to your audit log.
          </p>
        )}
      </>
    ),
  },
  {
    slug: "plans-and-invoices",
    icon: "▦",
    title: "Plans, add-ons, and invoices explained",
    tag: "Billing",
    summary: "What a live SKU is, and what cancelling does.",
    body: () => (
      <>
        {section("The billable unit is a live SKU",
          <p>
            Not a garment. A colourway published in four sizes consumes four of your allowance.
            Publication shows the breakdown by garment, so you can see exactly what is using it.
          </p>
        )}
        {section("Add-ons",
          <p>
            Extra SKU capacity raises the limit by 100. Analytics+ adds CSV export of your daily
            series. Custom domain and premium support change what Settings and Support offer you.
          </p>
        )}
        {section("Cancelling",
          <p>
            Your page goes offline immediately and your data is kept for 60 days, then permanently
            erased. Reactivating inside that window restores everything exactly — including QA
            approvals, so nothing needs re-reviewing.
          </p>
        )}
      </>
    ),
  },
];
