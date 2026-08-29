import { Link, useLocation } from "react-router-dom";
import styles from "./public-info.module.css";

type InfoPage = {
  eyebrow: string;
  title: string;
  introduction: string;
  sections: ReadonlyArray<{
    title: string;
    body: string;
  }>;
};

const PAGES: Record<string, InfoPage> = {
  "/terms": {
    eyebrow: "Pilot information",
    title: "Terms, before the test begins.",
    introduction:
      "Joining Mirra is an expression of interest, not a commitment or a guarantee of pilot access.",
    sections: [
      {
        title: "Application",
        body: "We review each store, catalogue, and use case individually. Submitting the Join form lets the Mirra team contact you about fit and availability.",
      },
      {
        title: "Pilot agreement",
        body: "Eligible partners receive the commercial, implementation, support, and data terms that apply to their pilot before anything is activated.",
      },
      {
        title: "What to share",
        body: "Use the public form for a high-level description of your goals. Do not include passwords, payment details, customer records, or confidential files.",
      },
    ],
  },
  "/privacy": {
    eyebrow: "Privacy overview",
    title: "Clear about what the Join form collects.",
    introduction:
      "The early-access form asks only for the information the team needs to understand your store and reply to you.",
    sections: [
      {
        title: "Information submitted",
        body: "The form collects your name, work email, company, role, goals, and—if you choose to add them—your website and monthly order range.",
      },
      {
        title: "How it is used",
        body: "Application details are stored with a reference ID so the Mirra team can assess the request, send an acknowledgement when email delivery is configured, and follow up about a possible test.",
      },
      {
        title: "Shopper profiles",
        body: "Authenticated shopper data and avatar controls live separately inside the Mirra account experience; the public Join form does not collect photos or body measurements.",
      },
    ],
  },
  "/security": {
    eyebrow: "Security overview",
    title: "A narrow handoff, with no hidden detour.",
    introduction:
      "Mirra keeps the public application flow separate from shopper accounts, measurements, and the virtual try-on studio.",
    sections: [
      {
        title: "Application boundary",
        body: "Join submissions travel to the Mirra application endpoint and are stored in the backend database. The form never asks for account passwords, payment information, photos, or measurements.",
      },
      {
        title: "Email delivery",
        body: "When transactional email is configured, the backend sends an acknowledgement to the submitted address. If delivery is unavailable, the interface says so instead of presenting a false email confirmation.",
      },
      {
        title: "Partner review",
        body: "Detailed hosting, access, retention, and integration requirements are reviewed with eligible brands before a pilot is activated.",
      },
    ],
  },
};

export default function PublicInfo() {
  const page = PAGES[useLocation().pathname] ?? PAGES["/privacy"];

  return (
    <main className={styles.page} id="top">
      <article className={styles.article}>
        <Link className={styles.back} to="/">
          <span aria-hidden="true">←</span>
          Back to Mirra
        </Link>
        <header>
          <p>{page.eyebrow}</p>
          <h1>{page.title}</h1>
          <div className={styles.meta}>
            <span>Public pilot note</span>
            <span>Updated 25 August 2026</span>
          </div>
          <p className={styles.introduction}>{page.introduction}</p>
        </header>

        <div className={styles.sections}>
          {page.sections.map((section, index) => (
            <section key={section.title}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <div>
                <h2>{section.title}</h2>
                <p>{section.body}</p>
              </div>
            </section>
          ))}
        </div>

        <aside className={styles.cta}>
          <div>
            <p>Interested in testing Mirra?</p>
            <h2>Tell us about your store.</h2>
          </div>
          <Link to="/join">
            Join
            <span aria-hidden="true">↗</span>
          </Link>
        </aside>
      </article>
    </main>
  );
}
