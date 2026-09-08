"""The publication contract — what a shopper is allowed to see, resolved once.

This is the server-side counterpart of the dashboard's
`features/dashboard/data/publication.ts`, and it exists for the same reason:
before that module, the dashboard computed visibility from stage and toggles
while the storefront mapper hardcoded every product as published and try-on
eligible. The two could not disagree, because they never met.

Now they meet here. `public_product()` is the single place a merchant garment
becomes a `PublicProduct` for the studio, and every "is this live?" question
on the merchant side resolves through `resolve_garment()`.

Order of precedence, highest first:
    1. tenant status (suspended/cancelled → nothing serves)
    2. garment stage (`live` only) and the merchant's try-on toggle
    3. QA approval — an approved snapshot must exist
    4. per-variant inventory × sold-out policy
    5. asset availability for the approved revision

Where the shopper-facing copy comes from
----------------------------------------
`PublicProduct` needs a name, price, description and material/fit copy. Each
field resolves in this order, and the winner is recorded in
`ProductContent.sources` so the merchant can see which is which:

    name              Shopify title (canonical) — never the merchant's rename
    price/currency    the cheapest purchasable variant, from Shopify
    description       garment content → product content → none
    materialAndCare   garment content → the confirmed composition → none
    fitInfo           garment content → silhouette + fit notes → none

A field with no value is `null`, not an invented string. The audit's central
finding was a UI that printed defaults as findings; the same rule applies to
everything served to a shopper.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import (
    ApprovedSnapshot,
    MerchantGarmentDocument,
    MerchantProductDocument,
    MerchantTenantDocument,
    ProductContent,
)

BLOCKED_REASONS = (
    "tenant_inactive",
    "not_live",
    "tryon_disabled",
    "not_approved",
    "no_purchasable_variant",
    "no_asset",
)

# Mirrors the dashboard's CATEGORY_TO_PUBLIC map.
_PUBLIC_CATEGORY = {
    "dress": "dress",
    "top": "top",
    "bottom": "bottom",
    "outerwear": "outerwear",
    "knitwear": "top",
    "swim": "top",
    "accessory": "accessory",
}


@dataclass
class ResolvedVariant:
    variant_id: str
    sku: str
    size: str
    colour: str
    price: float
    currency: str
    inventory: int
    in_stock: bool
    try_on_eligible: bool
    size_id: str = ""
    hidden_reason: str = ""


@dataclass
class ResolvedGarment:
    garment_id: str
    title: str
    served_revision: int | None
    visible: bool
    blocked_reason: str = ""
    blocked_detail: str = ""
    draft_ahead: bool = False
    variants: list[ResolvedVariant] = field(default_factory=list)


def resolve_garment(
    garment: MerchantGarmentDocument,
    tenant: MerchantTenantDocument,
    product: MerchantProductDocument | None,
    *,
    asset_available: bool = False,
) -> ResolvedGarment:
    """The single resolution function. Every visibility question goes here.

    Variant resolution and the visibility decision are deliberately separate.
    A QA reviewer previewing an approved-but-unpublished garment needs to see
    its sizes and prices — that is most of what the shopper's panel *is* — and
    an earlier version returned an empty variant list for anything not live,
    which made the preview a blank panel and defeated its purpose. So variants
    are resolved whenever an approved snapshot exists; `visible` decides
    separately whether a shopper may be served them.
    """
    snapshot: ApprovedSnapshot | None = garment.approved
    served_revision = snapshot.revision if snapshot else None
    draft_ahead = bool(snapshot and garment.revision > snapshot.revision)

    # --- variants, from the snapshot's sizes only ---
    # A size added to the working draft after approval is not something a
    # shopper — or a reviewer of this revision — should be shown.
    resolved_variants: list[ResolvedVariant] = []
    if snapshot is not None:
        approved_sizes = {row.size for row in snapshot.sizing.rows}
        size_to_size_id = {
            row.size: sid
            for row, sid in zip(snapshot.sizing.rows, garment.pipeline.size_ids)
        }
        hide_sold_out = garment.publication.sold_out_policy == "hide"

        for variant in (product.variants if product else []):
            if garment.option_value and variant.colour and variant.colour != garment.option_value:
                continue
            if variant.size not in approved_sizes:
                continue
            in_stock = variant.inventory > 0
            hidden = "sold_out_hidden" if (not in_stock and hide_sold_out) else ""
            resolved_variants.append(
                ResolvedVariant(
                    variant_id=variant.variant_id,
                    sku=variant.sku,
                    size=variant.size,
                    colour=variant.colour or garment.option_value,
                    price=variant.price,
                    currency=variant.currency,
                    inventory=variant.inventory,
                    in_stock=in_stock,
                    # A sold-out size stays try-on-able under the default
                    # policy — a generated size does not stop existing at
                    # zero stock. It needs a rendered asset either way.
                    try_on_eligible=asset_available and not hidden,
                    size_id=size_to_size_id.get(variant.size, ""),
                    hidden_reason=hidden,
                )
            )

    def result(visible: bool, reason: str = "", detail: str = "") -> ResolvedGarment:
        return ResolvedGarment(
            garment_id=garment.id,
            title=garment.canonical_title,
            served_revision=served_revision,
            visible=visible,
            blocked_reason=reason,
            blocked_detail=detail,
            draft_ahead=draft_ahead,
            variants=resolved_variants,
        )

    # --- visibility, in order of precedence ---
    if tenant.status in ("suspended", "cancelled"):
        return result(False, "tenant_inactive", f"Workspace is {tenant.status}")

    if snapshot is None:
        return result(False, "not_approved", "No QA-approved revision exists")

    if garment.stage != "live":
        return result(False, "not_live", f"Garment is in '{garment.stage}', not live")

    if not garment.publication.try_on_enabled:
        return result(False, "tryon_disabled", "Try-on is switched off for this garment")

    if not [v for v in resolved_variants if not v.hidden_reason]:
        return result(
            False,
            "no_purchasable_variant",
            "No variant of this colourway is available under the sold-out policy",
        )

    if not asset_available:
        return result(
            False, "no_asset", "No rendered garment asset exists for the approved revision yet"
        )

    return result(True)


# ----------------------------------------------------------------- content


def _first(*values: str | None) -> str | None:
    for value in values:
        if value and str(value).strip():
            return str(value).strip()
    return None


def merged_content(
    garment_content: ProductContent, product_content: ProductContent
) -> ProductContent:
    """Garment copy wins over product copy; neither invents a value.

    A colourway may legitimately need its own description ("in the deadstock
    silk") while inheriting everything else from the listing.
    """
    merged = ProductContent()
    sources: dict[str, str] = {}
    for field_name in ("description", "material_and_care", "manufacturing_info", "fit_info", "tax_note"):
        garment_value = getattr(garment_content, field_name, None)
        product_value = getattr(product_content, field_name, None)
        value = _first(garment_value, product_value)
        setattr(merged, field_name, value)
        if value is None:
            continue
        if garment_value and str(garment_value).strip():
            sources[field_name] = garment_content.sources.get(field_name, "merchant")
        else:
            sources[field_name] = product_content.sources.get(field_name, "shopify")
    merged.sources = sources
    return merged


def public_product(
    garment: MerchantGarmentDocument,
    tenant: MerchantTenantDocument,
    product: MerchantProductDocument | None,
    resolved: ResolvedGarment,
    *,
    asset_url: str | None,
    preview: bool = False,
) -> dict:
    """The `PublicProduct` the studio renders, in its own camelCase shape.

    Matches `website/frontend/src/integrations/mirra-api/types.ts` field for
    field, so the studio needs no mapping layer and no second source of truth.
    """
    snapshot = garment.approved
    content = merged_content(
        garment.content, product.content if product else ProductContent()
    )

    size_chart = []
    if snapshot:
        for row in snapshot.sizing.rows:
            measurements = {
                key: f"{value} cm"
                for key, value in row.model_dump().items()
                if key not in ("size", "variant_id") and isinstance(value, (int, float))
            }
            size_chart.append({"size": row.size, "measurements": measurements})

    variants = [
        {
            "publicVariantId": v.variant_id,
            "colorName": v.colour,
            "colorSwatch": None,
            "size": v.size,
            "price": v.price,
            "currency": v.currency,
            "inStock": v.in_stock,
            "tryOnEligible": v.try_on_eligible,
            # Never claim an asset exists. `asset_url` is None until the VTO
            # worker has actually produced a GLB for the approved revision.
            "garmentAssetUrl": asset_url,
            "assetStatus": "ready" if asset_url else "missing",
            # The join keys a try-on request needs. Without these the studio
            # cannot ask the pipeline for this exact garment and size.
            "clothId": garment.pipeline.cloth_id,
            "sizeId": v.size_id,
        }
        for v in resolved.variants
        if not v.hidden_reason
    ]

    prices = [v["price"] for v in variants if v["price"]]
    return {
        "publicProductId": garment.id,
        # Canonical Shopify title, never the merchant's display rename.
        "name": garment.canonical_title,
        "subtitle": garment.option_value or None,
        "category": (product.product_type if product else "") or garment.category,
        "garmentCategory": _PUBLIC_CATEGORY.get(garment.category, "top"),
        "description": content.description,
        "materialAndCare": content.material_and_care
        or (
            ", ".join(f"{c.pct}% {c.material}" for c in snapshot.material.composition)
            if snapshot and snapshot.material.composition and snapshot.material.confirmed
            else None
        ),
        "manufacturingInfo": content.manufacturing_info,
        "fitInfo": content.fit_info
        or (
            f"{snapshot.sizing.silhouette} fit — {snapshot.sizing.fit_notes}".strip(" —")
            if snapshot and (snapshot.sizing.silhouette or snapshot.sizing.fit_notes)
            else None
        ),
        "taxNote": content.tax_note,
        "price": min(prices) if prices else 0,
        "currency": variants[0]["currency"] if variants else "USD",
        "thumbnailUrl": (product.image_urls[0] if product and product.image_urls else ""),
        "publicationStatus": "preview" if preview else ("published" if resolved.visible else "paused"),
        "tryOnEligible": any(v["tryOnEligible"] for v in variants),
        "sizeChart": size_chart or None,
        "variants": variants,
        "contentSources": content.sources,
    }
