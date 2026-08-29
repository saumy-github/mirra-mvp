import { Link } from "react-router-dom";
import { useDbVersion } from "../../data/store";
import { useSession } from "../../data/session";
import { tenantGarments } from "../../data/queries";
import { SIZE_SOURCE_LABELS, requirements } from "../../data/ingestion";
import { getDb } from "../../data/store";
import { Badge, ButtonLink, Card, EmptyState, PageHeader, Table, Td } from "../../components/ui";
import { dashPath } from "../../routes";

export default function SizeFitPage() {
  const session = useSession();
  useDbVersion();
  if (!session?.tenant) return null;
  const tenant = session.tenant;

  const db = getDb();
  const garments = tenantGarments(tenant.id);
  // One definition of "sized", shared with the Garments table and the flow.
  const sizing = (g: (typeof garments)[number]) =>
    requirements(g, db.products.find((p) => p.id === g.productId)).find((r) => r.key === "sizing")!;
  const missing = garments.filter((g) => !sizing(g).complete);

  return (
    <>
      <PageHeader
        title="Size & fit data"
        subtitle={
          garments.length === 0
            ? "Accurate measurements are what make try-on believable."
            : missing.length > 0
              ? `${missing.length} of ${garments.length} garments still need usable measurements. Accurate measurements are what make try-on believable.`
              : `All ${garments.length} garments have a size chart. Source and reference sample are recorded for each.`
        }
      />
      {missing.length > 0 && (
        <div className="mb-5">
          <Card title={`Needs attention — ${missing.length} garment${missing.length > 1 ? "s" : ""}`}>
            <ul className="space-y-2">
              {missing.map((g) => (
                <li key={g.id} className="flex items-center justify-between gap-3 text-[13px]">
                  <span>
                    <span className="text-stone-700">{g.title}</span>
                    <span className="block text-xs text-muted">{sizing(g).detail}</span>
                  </span>
                  <ButtonLink href={dashPath.garmentFlow(g.id, "sizing")} size="sm">
                    {g.sizeChart.length === 0 ? "Add sizing →" : "Fix sizing →"}
                  </ButtonLink>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      )}
      {garments.length === 0 ? (
        <EmptyState
          icon="📐"
          title="No garments yet"
          body="Size and fit data appears here once garments are created from your synced Shopify products."
          action={<ButtonLink href={dashPath.products} size="sm">Go to Products</ButtonLink>}
        />
      ) : (
        // Reference and Source are the two columns that make this table
        // auditable: which physical sample, and where the numbers came from.
        <Table
          caption="Size chart coverage, reference sample and source per garment"
          headers={["Garment", "Reference", "Sizes", "Source", "Fit", "Status"]}
        >
          {garments.map((g) => {
            const req = sizing(g);
            const complete = req.complete;
            return (
              <tr key={g.id} className="hover:bg-stone-50/60">
                <Td>
                  <Link to={dashPath.garment(g.id)} className="font-medium text-ink hover:text-accent">{g.title}</Link>
                </Td>
                <Td className="text-stone-600">{g.referenceSize ?? "—"}</Td>
                <Td className="text-stone-600">
                  {g.sizeChart.length === 0 ? "—" : g.sizeChart.map((r) => r.size).join(" · ")}
                </Td>
                <Td className="text-stone-600">
                  {g.sizeSource ? SIZE_SOURCE_LABELS[g.sizeSource] : "—"}
                  {g.sizeChartKind && (
                    <span className="block text-[11px] text-muted">
                      {g.sizeChartKind === "body"
                        ? "Body measurements"
                        : g.sizeChartKind === "garment"
                          ? "Finished garment"
                          : "Type unconfirmed"}
                    </span>
                  )}
                </Td>
                <Td className="max-w-xs truncate text-stone-600">
                  {g.silhouette ? <span className="capitalize">{g.silhouette}</span> : "—"}
                  {g.fitNotes && <span className="block truncate text-[11px] text-muted">{g.fitNotes}</span>}
                </Td>
                <Td>
                  {complete ? (
                    <Badge tone="success">Complete</Badge>
                  ) : g.gradingUnverified ? (
                    <Badge tone="warn">Draft sizes</Badge>
                  ) : (
                    <Badge tone="warn">
                      {g.sizeChart.length === 0
                        ? "No size chart"
                        : !g.referenceSize
                          ? "No reference sample"
                          : "Incomplete measurements"}
                    </Badge>
                  )}
                </Td>
              </tr>
            );
          })}
        </Table>
      )}
    </>
  );
}
