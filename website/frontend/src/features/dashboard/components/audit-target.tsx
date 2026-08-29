import { Link } from "react-router-dom";
import { getDb } from "../data/store";
import { dashPath } from "../routes";

/**
 * Audit and activity entries record their target as a human string ("Ombre
 * Cashmere Crew — Graphite"). Where that resolves to a garment in this
 * workspace, link it — an audit trail you can't navigate from is a dead end.
 */
export function AuditTarget({ tenantId, target }: { tenantId: string; target: string }) {
  const garment = getDb().garments.find((g) => g.tenantId === tenantId && g.title === target);
  if (!garment) return <>{target}</>;
  return (
    <Link to={dashPath.garment(garment.id)} className="text-ink underline decoration-line hover:text-accent">
      {target}
    </Link>
  );
}
