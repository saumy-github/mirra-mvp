import { useDbVersion } from "../../data/store";
import { useSession } from "../../data/session";
import { getEntitlements } from "../../data/entitlements";
import { garmentRows } from "../../data/queries";
import { can } from "../../data/rbac";
import { EmptyState, PageHeader, ButtonLink } from "../../components/ui";
import { GarmentTable } from "../../components/catalogue-table";
import { dashPath } from "../../routes";

export default function GarmentsPage() {
  const session = useSession();
  useDbVersion();
  if (!session?.tenant) return null;
  const tenant = session.tenant;

  const rows = garmentRows(tenant.id);
  const ent = getEntitlements(tenant);
  // Blockers and recommendations are counted separately: the Fit requirement
  // is a quality nudge, and rolling it into "missing data needed for try-on"
  // told merchants a garment was unpublishable when it wasn't.
  const blocked = rows.filter((r) => r.requirements.some((q) => q.blocking && !q.complete)).length;
  const nudges = rows.filter(
    (r) => !r.requirements.some((q) => q.blocking && !q.complete) && r.completeCount < r.requirementCount,
  ).length;

  return (
    <>
      {/* One job on this screen: get every garment's data complete. Publishing
          happens on the Publication page — both used to offer it. */}
      <PageHeader
        title="Garments"
        subtitle={
          blocked > 0
            ? `${blocked} of ${rows.length} garments are missing data try-on needs${nudges > 0 ? `, and ${nudges} could be improved` : ""}. Complete them here, then publish from Publication.`
            : nudges > 0
              ? `Every garment has what try-on needs. ${nudges} would benefit from optional fit detail. Publish from Publication.`
              : `All ${rows.length} garments have the data try-on needs. Publish them from Publication.`
        }
        action={
          <div className="flex gap-2">
            <ButtonLink href={dashPath.publication} size="sm">
              Go to publication
            </ButtonLink>
            {/* The one primary action on this screen — everything in the
                ingestion flow starts here. */}
            <ButtonLink href={dashPath.addGarment} variant="primary" size="sm">
              + Add garment
            </ButtonLink>
          </div>
        }
      />
      {rows.length === 0 ? (
        <EmptyState
          icon="👗"
          title="No garments yet"
          body="A garment is one colourway of a synced Shopify product, digitised from a physical sample. Add your first one to start."
          action={<ButtonLink href={dashPath.addGarment} variant="primary" size="sm">+ Add garment</ButtonLink>}
        />
      ) : (
        <GarmentTable
          rows={rows}
          mode="catalogue"
          canManage={can(session.role, "publication.manage")}
          bulkAllowed={ent.bulkPublishing}
        />
      )}
    </>
  );
}
