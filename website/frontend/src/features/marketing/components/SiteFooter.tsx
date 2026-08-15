import {
  MIRRA_FOOTER_COLUMNS,
  MIRRA_FOOTER_CTA,
  MIRRA_FOOTER_LEGAL,
} from "../content";
import { LiquidCTA } from "./LiquidCTA";
import { MirraBrand } from "./MirraBrand";
import { UiIcon } from "./UiIcon";
import { Link } from "react-router-dom";

function footerHref(href: string) {
  return href.startsWith("#") ? `/${href}` : href;
}

export function SiteFooter() {
  return (
    <footer className="mirra-footer" id="footer" data-header="dark" data-nav-label="ONE EASIER DECISION">
      <span className="mirra-footer__contour mirra-footer__contour--one" aria-hidden="true" />
      <span className="mirra-footer__contour mirra-footer__contour--two" aria-hidden="true" />
      <span className="mirra-footer__glow" aria-hidden="true" />

      <div className="mirra-footer__inner">
        <div className="mirra-footer__intro">
          <div>
            <p className="mirra-footer__eyebrow">MIRRA / REALISTIC VIRTUAL TRY-ON</p>
            <h2>Make every fit<br />decision easier.</h2>
          </div>
          <div className="mirra-footer__intro-copy">
            <p>Bring the fitting-room moment into the product page your customers already trust.</p>
            <div className="mirra-footer__actions">
              <LiquidCTA href={footerHref(MIRRA_FOOTER_CTA.actions[0].href)}>BOOK A DEMO</LiquidCTA>
              <LiquidCTA href={footerHref(MIRRA_FOOTER_CTA.actions[1].href)} tone="light">SEE MIRRA IN ACTION</LiquidCTA>
            </div>
          </div>
        </div>

        <div className="mirra-footer__directory">
          <div className="mirra-footer__summary">
            <Link to="/" aria-label="Mirra homepage"><MirraBrand /></Link>
            <p>Virtual try-on that keeps the customer, the brand, and the fit decision inside your store.</p>
            <span>SHOPIFY READY · NO REPLATFORMING</span>
          </div>

          {MIRRA_FOOTER_COLUMNS.map((column) => (
            <nav aria-label={`${column.title} links`} className="mirra-footer__column" key={column.title}>
              <h3>{column.title}</h3>
              {column.links.map((link) => (
                <Link to={footerHref(link.href)} key={link.label}>
                  <span>{link.label}</span>
                  <UiIcon name="arrow-up-right" size={12} strokeWidth={1.15} />
                </Link>
              ))}
            </nav>
          ))}
        </div>

        <div className="mirra-footer__wordmark" aria-label={MIRRA_FOOTER_LEGAL.brand.symbolLabel}>
          <MirraBrand />
        </div>

        <div className="mirra-footer__end" id="data-security">
          <div className="mirra-footer__legal">
            {MIRRA_FOOTER_LEGAL.links.map((link) => <Link to={link.href} key={link.label}>{link.label}</Link>)}
          </div>
          <Link to="/#top" className="mirra-footer__top-link">
            <span>BACK TO TOP</span>
            <UiIcon name="arrow-up-right" size={12} strokeWidth={1.2} />
          </Link>
          <span>{MIRRA_FOOTER_LEGAL.copyright}</span>
        </div>
      </div>
    </footer>
  );
}
