import { newId, updateDb } from "./store";
import type { AuditEvent, BillingEvent } from "./types";

export function fmtDate(isoStr?: string): string {
  if (!isoStr) return "—";
  return new Date(isoStr).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

export function fmtDateTime(isoStr?: string): string {
  if (!isoStr) return "—";
  return new Date(isoStr).toLocaleString("en-US", {
    month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
  });
}

export function timeAgo(isoStr: string): string {
  const ms = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(ms / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return fmtDate(isoStr);
}

export function money(usd: number | null): string {
  if (usd === null) return "Custom";
  return usd === 0 ? "Free" : `$${usd.toLocaleString("en-US")}`;
}

export function audit(e: Omit<AuditEvent, "id" | "at">) {
  updateDb((db) => {
    db.auditEvents.unshift({ ...e, id: newId("au"), at: new Date().toISOString() });
  });
}

export function billingEvent(e: Omit<BillingEvent, "id" | "at">) {
  updateDb((db) => {
    db.billingEvents.unshift({ ...e, id: newId("be"), at: new Date().toISOString() });
  });
}

export function slugify(s: string): string {
  return s.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}
