import type { Capability, InternalCapability } from "../data/rbac";
import { dashPath } from "../routes";

export interface NavItem {
  href: string;
  label: string;
  icon: string;
  /** Index routes must match exactly, or they stay active on every child. */
  end?: boolean;
  /**
   * The capability a seat needs before this appears.
   *
   * Navigation used to list every area to every role, so a Viewer was invited
   * into Billing and Settings in order to be told no. A menu is a promise.
   */
  needs?: Capability;
}

export const PORTAL_NAV: NavItem[] = [
  { href: dashPath.portal, label: "Overview", icon: "◈", end: true },
  { href: dashPath.products, label: "Products & SKUs", icon: "▤", needs: "catalogue.view" },
  { href: dashPath.garments, label: "Garments", icon: "👗", needs: "catalogue.view" },
  { href: dashPath.assets, label: "Assets", icon: "🖼", needs: "catalogue.view" },
  { href: dashPath.sizeFit, label: "Size & fit", icon: "📐", needs: "catalogue.view" },
  { href: dashPath.fabric, label: "Fabric & material", icon: "🧵", needs: "catalogue.view" },
  { href: dashPath.publication, label: "Publication", icon: "⇱", needs: "catalogue.view" },
  { href: dashPath.analytics, label: "Analytics", icon: "∿", needs: "analytics.view" },
  { href: dashPath.team, label: "Team & permissions", icon: "👥", needs: "team.view" },
  { href: dashPath.billing, label: "Billing", icon: "▦", needs: "billing.view" },
  { href: dashPath.support, label: "Support", icon: "◉", needs: "support.create" },
  { href: dashPath.settings, label: "Settings", icon: "⚙", needs: "settings.view" },
  { href: dashPath.audit, label: "Audit log", icon: "≡", needs: "audit.view" },
];

export interface InternalNavItem extends Omit<NavItem, "needs"> {
  needs?: InternalCapability;
}

export const ADMIN_NAV: InternalNavItem[] = [
  { href: dashPath.admin, label: "Tenants", icon: "▦", end: true, needs: "console.tenants.view" },
  { href: dashPath.adminLeads, label: "Leads & CRM", icon: "◎", needs: "console.leads.view" },
  { href: dashPath.adminSupport, label: "Support queue", icon: "◉", needs: "console.support.view" },
  { href: dashPath.adminSync, label: "Sync health", icon: "∿", needs: "console.sync.view" },
  { href: dashPath.adminChurn, label: "Churn & renewals", icon: "⚠", needs: "console.churn.view" },
];
