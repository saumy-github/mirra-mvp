import { Link } from "react-router-dom";
import { useSession } from "../../../data/session";
import { liveCan } from "../../../data/live-session";
import { stageMeta, useLiveGarments } from "../../../data/merchant-queries";
import { Badge, Banner, ButtonLink, EmptyState, PageHeader, Table, Td } from "../../../components/ui";
import { dashPath } from "../../../routes";

/** Garments for a real workspace, read from /merchant/{t}/garments. */
export default function LiveGarmentsPage() {
  const session = useSession();
  const tenantId = session?.tenant?.id ?? "";
  const garments = useLiveGarments(tenantId);
  const canEdit = liveCan(tenantId, "catalogue.edit");

  const rows = garments.data ?? [];
  const blocked = rows.filter((g) => !g.readiness.ready && g.stage === "needs_data").length;

  return (
    <>
      <PageHeader
        title="Garments"
        subtitle={
          rows.length === 0
            ? "Each garment is one colourway of a product, digitised from a physical sample."
            : blocked > 0
              ? `${blocked} of ${rows.length} still need data before they can go to review.`
              : `${rows.length} garment${rows.length === 1 ? "" : "s"}. Publish approved ones from Publication.`
        }
        action={
          canEdit ? (
            <ButtonLink href={dashPath.digitise} variant="primary" size="sm">
              + Add garment
            </ButtonLink>
          ) : undefined
        }
      />
      {garments.isLoading ? (
        <p className="text-[13px] text-muted">Loading garments…</p>
      ) : garments.isError ? (
        <Banner tone="danger">Could not load garments: {(garments.error as Error).message}</Banner>
      ) : rows.length === 0 ? (
        <EmptyState
          icon="👗"
          title="No garments yet"
          body="Paste a product link, photograph the sample, then add its material and sizes."
          action={
            canEdit ? (
              <ButtonLink href={dashPath.digitise} variant="primary" size="sm">
                + Add garment
              </ButtonLink>
            ) : undefined
          }
        />
      ) : (
        <Table caption="Garments" headers={["Garment", "Category", "Stage", "Readiness", "Updated"]}>
          {rows.map((g) => {
            const stage = stageMeta(g.stage);
            return (
              <tr key={g.garmentId}>
                <Td>
                  <Link to={dashPath.digitiseGarment(g.garmentId)} className="font-medium text-ink hover:text-accent">
                    {g.title}
                  </Link>
                  {g.optionValue && <span className="block text-xs text-muted">{g.optionValue}</span>}
                </Td>
                <Td className="capitalize">
                  {g.category}
                  {!g.pipeline.supported && <span className="block text-xs text-red-700">Not supported yet</span>}
                </Td>
                <Td>
                  <Badge tone={stage.tone}>{stage.label}</Badge>
                  {g.draftAhead && <span className="block text-xs text-amber-700">Edited since approval</span>}
                </Td>
                <Td>
                  {g.readiness.ready ? (
                    <span className="text-emerald-700">Complete</span>
                  ) : (
                    <span className="text-amber-700">
                      {g.readiness.blocking.length} to fix
                    </span>
                  )}
                </Td>
                <Td className="text-muted">{new Date(g.updatedAt).toLocaleDateString()}</Td>
              </tr>
            );
          })}
        </Table>
      )}
    </>
  );
}
