import { Link } from "react-router-dom";
import { useDbVersion } from "../../data/store";
import { useSession } from "../../data/session";
import { tenantGarments } from "../../data/queries";
import { requirements } from "../../data/ingestion";
import { getDb } from "../../data/store";
import { Badge, ButtonLink, EmptyState, PageHeader, Table, Td } from "../../components/ui";
import type { FabricSource } from "../../data/types";

const FABRIC_SOURCE_LABELS: Record<FabricSource, string> = {
  shopify: "Shopify description",
  metafield: "Shopify metafield",
  brand_profile: "Brand material profile",
  tech_pack: "Tech pack",
  manual: "Merchant entered",
  estimated: "Mirra estimate",
};
import { dashPath } from "../../routes";

export default function FabricPage() {
  const session = useSession();
  useDbVersion();
  if (!session?.tenant) return null;
  const tenant = session.tenant;

  const garments = tenantGarments(tenant.id);
  const db = getDb();
  const missingFabric = garments.filter(
    (g) => !requirements(g, db.products.find((p) => p.id === g.productId)).find((r) => r.key === "material")!.complete,
  ).length;

  return (
    <>
      <PageHeader
        title="Fabric & material data"
        subtitle={
          garments.length === 0
            ? "Composition and drape attributes drive how garments move and fall in try-on."
            : missingFabric > 0
              ? `${missingFabric} of ${garments.length} garments still need material data confirmed. Composition and drape drive how a piece moves and falls in try-on — edit these on each garment's page.`
              : `All ${garments.length} garments have composition recorded. Drape, opacity and thickness fine-tune how each piece behaves.`
        }
      />
      {garments.length === 0 ? (
        <EmptyState
          icon="🧵"
          title="No garments yet"
          body="Fabric data appears here once garments are created from your synced Shopify products."
          action={<ButtonLink href={dashPath.products} size="sm">Go to Products</ButtonLink>}
        />
      ) : (
      <Table caption="Fabric composition and drape attributes per garment" headers={["Garment", "Composition", "Stretch", "Drape", "Opacity", "Thickness", "Status"]}>
        {garments.map((g) => (
          <tr key={g.id} className="hover:bg-stone-50/60">
            <Td>
              <Link to={dashPath.garment(g.id)} className="font-medium text-ink hover:text-accent">{g.title}</Link>
            </Td>
            <Td className="text-stone-600">
              {g.fabricComposition.length === 0 ? "—" : g.fabricComposition.map((f) => `${f.pct}% ${f.material}`).join(", ")}
              {/* Provenance, quietly. Useful the day an output looks wrong. */}
              {g.fabricSource && (
                <span className="block text-[11px] text-muted">
                  {FABRIC_SOURCE_LABELS[g.fabricSource]}
                  {g.fabricConfirmed ? " · confirmed" : " · unconfirmed"}
                </span>
              )}
            </Td>
            <Td className="capitalize text-stone-600">{g.attributes.stretch}</Td>
            <Td className="capitalize text-stone-600">{g.attributes.drape}</Td>
            <Td className="capitalize text-stone-600">{g.attributes.opacity}</Td>
            <Td className="capitalize text-stone-600">{g.attributes.thickness}</Td>
            {/* Complete means what it means on the Garments page: composition
                recorded, confirmed, and its behaviour signed off. This badge
                used to read "Complete" for an unconfirmed estimate while the
                garment list called the same garment incomplete. */}
            <Td>
              {(() => {
                const product = getDb().products.find((p) => p.id === g.productId);
                const material = requirements(g, product).find((r) => r.key === "material")!;
                return material.complete ? (
                  <Badge tone="success">Complete</Badge>
                ) : (
                  // Straight to the section that fixes it, not just the garment.
                  <Link
                    to={dashPath.garmentFlow(g.id, "material")}
                    title={material.detail}
                    className="text-xs font-medium text-amber-800 underline hover:text-ink"
                  >
                    {g.fabricComposition.length === 0 ? "Add composition →" : "Confirm details →"}
                  </Link>
                );
              })()}
            </Td>
          </tr>
        ))}
      </Table>
      )}
    </>
  );
}
