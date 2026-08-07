import { useQuery } from "@tanstack/react-query";
import { getRuntimeProvider } from "@/integrations/mirra-api";
import { sameMerchant, type Product } from "../types";

const MAX_SUGGESTIONS = 3;

/**
 * Pieces that go with the selected one.
 *
 * Two rules, both deliberate: suggestions never leave the selected piece's
 * merchant (this flow is a store's fitting room, not a marketplace), and a
 * garment in a different category outranks another of the same kind — a
 * trouser completes a shirt, a second shirt doesn't.
 */
export function useCompleteTheLook(product: Product | null | undefined) {
  const query = useQuery({
    queryKey: ["complete-the-look", product?.publicProductId ?? "none"],
    queryFn: () => getRuntimeProvider().listProducts({ limit: 24 }),
    enabled: !!product,
    staleTime: 60_000,
  });

  const suggestions = product
    ? (query.data?.items ?? [])
        .filter(
          (candidate) =>
            candidate.publicProductId !== product.publicProductId &&
            candidate.publicationStatus === "published" &&
            sameMerchant(product, candidate),
        )
        .sort((a, b) => {
          const aComplements = a.garmentCategory === product.garmentCategory ? 1 : 0;
          const bComplements = b.garmentCategory === product.garmentCategory ? 1 : 0;
          return aComplements - bComplements;
        })
        .slice(0, MAX_SUGGESTIONS)
    : [];

  return { suggestions, isLoading: query.isLoading };
}
