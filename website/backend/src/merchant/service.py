"""Merchant business logic: identity, capture, pipeline, QA, publication.

Everything the dashboard's `data/actions.ts` did in module memory, done here
against Mongo with server-side authorization — audit P0-01.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone

from ..core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from ..core.security import new_id
from ..db import (
    merchant_garments_col,
    merchant_ingestion_runs_col,
    merchant_previews_col,
    merchant_products_col,
    merchant_tenants_col,
)
from . import engine, pipeline_bridge, publication, storage
from .models import (
    ApprovedSnapshot,
    CaptureAsset,
    FabricComponent,
    IngestionRunDocument,
    MerchantGarmentDocument,
    MerchantProductDocument,
    MerchantTenantDocument,
    PreviewDocument,
    ProductContent,
    ProductVariantModel,
    QaFinding,
    SizeRow,
)
from .product_source import (
    ProductPayload,
    ShopifyAdminSource,
    draft_payload_from_ref,
    parse_product_reference,
    storefront_url,
)

logger = logging.getLogger("mirra.backend.merchant")

# Who may do what. Mirrors features/dashboard/data/rbac.ts — the audit's point
# was that a client-side permission map is a suggestion until the server
# enforces the same thing.
ROLE_PERMISSIONS = {
    "owner": {"catalogue.edit", "catalogue.publish", "settings.edit", "qa.review"},
    "admin": {"catalogue.edit", "catalogue.publish", "settings.edit"},
    "editor": {"catalogue.edit"},
    "viewer": set(),
    # Mirra's own reviewers, granted per tenant.
    "qa": {"qa.review"},
}

# Stage transitions the merchant lifecycle allows. Anything else is refused
# rather than silently applied — the prototype jumped straight to `in_qa`,
# the machine refused, and the refusal was discarded.
ALLOWED_TRANSITIONS = {
    "needs_data": {"merchant_review"},
    "merchant_review": {"needs_data", "in_qa"},
    "in_qa": {"qa_changes", "ready"},
    "qa_changes": {"needs_data", "merchant_review"},
    "ready": {"live", "needs_data"},
    "live": {"paused", "needs_data"},
    "paused": {"live", "needs_data"},
    "sync_error": {"needs_data"},
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ------------------------------------------------------------------ tenants


async def get_tenant(tenant_id: str) -> MerchantTenantDocument:
    raw = await merchant_tenants_col().find_one({"_id": tenant_id})
    if not raw:
        raise NotFound("Workspace not found")
    return MerchantTenantDocument.model_validate(raw)


async def require_member(tenant_id: str, user_id: str, permission: str) -> MerchantTenantDocument:
    """Resolve the tenant and check the caller may perform `permission`.

    A caller who is not a member gets the same 404 an unknown workspace gets:
    membership is not something an outsider should be able to probe for.
    """
    raw = await merchant_tenants_col().find_one({"_id": tenant_id})
    if not raw:
        raise NotFound("Workspace not found")
    tenant = MerchantTenantDocument.model_validate(raw)
    role = tenant.members.get(user_id)
    if role is None:
        raise NotFound("Workspace not found")
    # An empty permission is a membership check only — used by the read
    # endpoints, where being in the workspace is the whole requirement.
    if permission and permission not in ROLE_PERMISSIONS.get(role, set()):
        raise Forbidden(f"Your role ({role}) cannot {permission.replace('.', ' ')}")
    return tenant


async def list_tenants_for_user(user_id: str) -> list[MerchantTenantDocument]:
    cursor = merchant_tenants_col().find({f"members.{user_id}": {"$exists": True}})
    return [MerchantTenantDocument.model_validate(r) for r in await cursor.to_list(length=50)]


async def connect_shopify(
    tenant_id: str, user_id: str, *, store_domain: str, access_token: str, scopes: list[str]
) -> MerchantTenantDocument:
    """Record Admin API credentials, then upgrade any unlinked products."""
    await require_member(tenant_id, user_id, "settings.edit")
    domain = store_domain.strip().lower().removeprefix("https://").removeprefix("http://").strip("/")
    if not domain:
        raise ValidationFailed("A store domain is required")
    await merchant_tenants_col().update_one(
        {"_id": tenant_id},
        {
            "$set": {
                "shopify.store_domain": domain,
                "shopify.access_token": access_token,
                "shopify.scopes": scopes,
                "shopify.connected_at": _now(),
                "shopify.last_sync_error": "",
                "updated_at": _now(),
            }
        },
    )
    await reconcile_unlinked_products(tenant_id)
    return await get_tenant(tenant_id)


# ----------------------------------------------------------------- products


def _source_for(tenant: MerchantTenantDocument) -> ShopifyAdminSource:
    return ShopifyAdminSource(tenant.shopify.store_domain, tenant.shopify.access_token)


async def _find_stored_product(
    tenant_id: str, *, handle: str = "", shopify_gid: str = ""
) -> MerchantProductDocument | None:
    query: dict = {"tenant_id": tenant_id}
    if shopify_gid:
        query["shopify_gid"] = shopify_gid
    elif handle:
        query["handle"] = handle
    else:
        return None
    raw = await merchant_products_col().find_one(query)
    return MerchantProductDocument.model_validate(raw) if raw else None


def _payload_to_doc(
    payload: ProductPayload, tenant_id: str, existing: MerchantProductDocument | None
) -> MerchantProductDocument:
    now = _now()
    content = existing.content if existing else ProductContent()
    if payload.description and not content.description:
        content.description = payload.description
        content.sources = {**content.sources, "description": "shopify"}

    return MerchantProductDocument(
        id=existing.id if existing else new_id("m_p"),
        tenant_id=tenant_id,
        source=payload.source,
        link_state=payload.link_state,
        shopify_gid=payload.shopify_gid or (existing.shopify_gid if existing else ""),
        shopify_numeric_id=payload.shopify_numeric_id
        or (existing.shopify_numeric_id if existing else ""),
        handle=payload.handle or (existing.handle if existing else ""),
        store_domain=payload.store_domain or (existing.store_domain if existing else ""),
        online_store_url=payload.online_store_url
        or (existing.online_store_url if existing else ""),
        title=payload.title or (existing.title if existing else ""),
        product_type=payload.product_type or (existing.product_type if existing else ""),
        vendor=payload.vendor or (existing.vendor if existing else ""),
        option_name=payload.option_name if payload.option_name is not None else (existing.option_name if existing else None),
        image_urls=payload.image_urls or (existing.image_urls if existing else []),
        content=content,
        variants=[
            ProductVariantModel(**v.__dict__) for v in payload.variants
        ] or (existing.variants if existing else []),
        sync_status="synced" if payload.source == "shopify" else "never",
        last_synced_at=now if payload.source == "shopify" else (existing.last_synced_at if existing else None),
        created_at=existing.created_at if existing else now,
        updated_at=now,
    )


async def lookup_product(tenant_id: str, user_id: str, raw_input: str) -> dict:
    """Resolve a pasted URL / handle / GID. **Never a dead end.**

    Returns one of three outcomes, all of which let the merchant continue:

        matched   an existing Mirra product — reuse it
        resolved  fetched live from Shopify and stored
        draft     no store connected (or no such product): everything the URL
                  itself established, for the merchant to complete by hand

    The old behaviour was a fourth outcome, `error`, whenever the catalogue
    was empty — which it always was, because nothing could populate it.
    """
    await require_member(tenant_id, user_id, "catalogue.edit")
    tenant = await get_tenant(tenant_id)

    ref = parse_product_reference(raw_input)
    if not ref.usable:
        raise ValidationFailed(
            "That does not look like a Shopify product link. Paste the storefront URL "
            "(https://your-store.com/products/the-handle), the product handle, or its ID."
        )

    stored = await _find_stored_product(
        tenant_id, handle=ref.handle, shopify_gid=ref.shopify_gid
    )

    source = _source_for(tenant)
    if source.active:
        payload = await source.fetch(ref)
        if payload is not None:
            doc = _payload_to_doc(payload, tenant_id, stored)
            await merchant_products_col().replace_one({"_id": doc.id}, doc.to_mongo(), upsert=True)
            return {"outcome": "resolved", "product": doc, "store_connected": True}
        if stored is None:
            raise NotFound(
                f"No product with handle '{ref.handle or ref.shopify_numeric_id}' exists in "
                f"{tenant.shopify.store_domain}. Check the link points at this store."
            )

    if stored is not None:
        return {"outcome": "matched", "product": stored, "store_connected": source.active}

    # No connected store. Hand back a provisional identity rather than a wall.
    draft = draft_payload_from_ref(ref, tenant.shopify.store_domain or tenant.store_url)
    return {"outcome": "draft", "draft": draft, "store_connected": False}


async def create_manual_product(
    tenant_id: str,
    user_id: str,
    *,
    handle: str,
    title: str,
    online_store_url: str = "",
    store_domain: str = "",
    product_type: str = "",
    vendor: str = "",
    option_name: str | None = None,
    variants: list[dict],
    description: str | None = None,
) -> MerchantProductDocument:
    """Create the product the merchant just typed in, in `unlinked` state.

    This is the path that unblocks a workspace with no Shopify connection.
    The record is a first-class product — garments attach to it, ingestion
    runs against it, publication serves it — and `reconcile_unlinked_products`
    later fills in the Shopify identity without disturbing any of that.
    """
    await require_member(tenant_id, user_id, "catalogue.edit")
    tenant = await get_tenant(tenant_id)

    clean_handle = (handle or "").strip().lower()
    if not clean_handle:
        raise ValidationFailed("A product handle is required — it is how the Shopify link is matched later")
    if not (title or "").strip():
        raise ValidationFailed("A product title is required")
    if not variants:
        raise ValidationFailed("At least one variant (size) is required")

    existing = await _find_stored_product(tenant_id, handle=clean_handle)
    if existing is not None:
        raise Conflict(f"A product with handle '{clean_handle}' already exists in this workspace")

    domain = store_domain or tenant.shopify.store_domain
    now = _now()
    content = ProductContent()
    if description:
        content.description = description
        content.sources = {"description": "merchant"}

    doc = MerchantProductDocument(
        id=new_id("m_p"),
        tenant_id=tenant_id,
        source="manual",
        link_state="unlinked",
        handle=clean_handle,
        store_domain=domain,
        online_store_url=online_store_url or storefront_url(domain, clean_handle),
        title=title.strip(),
        product_type=product_type,
        vendor=vendor or tenant.name,
        option_name=option_name,
        content=content,
        variants=[
            ProductVariantModel(
                variant_id=v.get("variant_id") or new_id("m_v"),
                sku=v.get("sku", ""),
                title=v.get("title", ""),
                size=v.get("size", ""),
                colour=v.get("colour", ""),
                price=float(v.get("price") or 0),
                currency=v.get("currency", "USD"),
                inventory=int(v.get("inventory") or 0),
            )
            for v in variants
        ],
        sync_status="never",
        created_at=now,
        updated_at=now,
    )
    await merchant_products_col().insert_one(doc.to_mongo())
    return doc


CSV_COLUMNS = ("handle", "title", "size", "colour", "sku", "price", "inventory", "product_type", "vendor", "option_name", "description")


async def import_products_csv(tenant_id: str, user_id: str, content: bytes) -> dict:
    """Bulk-create unlinked products from a CSV export.

    One row per variant, grouped by handle. Shopify's own product CSV export
    uses `Handle`, `Title`, `Option1 Value`… — those header names are accepted
    directly so the merchant can upload the file Shopify gave them without
    reshaping it.
    """
    await require_member(tenant_id, user_id, "catalogue.edit")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationFailed("The CSV must be UTF-8 encoded")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValidationFailed("The CSV has no header row")

    # Shopify's export header → ours.
    alias = {
        "handle": "handle",
        "title": "title",
        "option1 value": "colour",
        "option2 value": "size",
        "variant sku": "sku",
        "variant price": "price",
        "variant inventory qty": "inventory",
        "type": "product_type",
        "vendor": "vendor",
        "option1 name": "option_name",
        "body (html)": "description",
    }

    def normalise(row: dict) -> dict:
        out: dict = {}
        for key, value in row.items():
            if key is None:
                continue
            low = key.strip().lower()
            out[alias.get(low, low)] = (value or "").strip()
        return out

    grouped: dict[str, list[dict]] = {}
    meta: dict[str, dict] = {}
    for raw_row in reader:
        row = normalise(raw_row)
        handle = row.get("handle", "").lower()
        if not handle:
            continue
        grouped.setdefault(handle, []).append(row)
        if handle not in meta and row.get("title"):
            meta[handle] = row

    created, skipped, failed = [], [], []
    for handle, rows in grouped.items():
        head = meta.get(handle, rows[0])
        if await _find_stored_product(tenant_id, handle=handle) is not None:
            skipped.append(handle)
            continue
        try:
            doc = await create_manual_product(
                tenant_id,
                user_id,
                handle=handle,
                title=head.get("title") or handle.replace("-", " ").title(),
                product_type=head.get("product_type", ""),
                vendor=head.get("vendor", ""),
                option_name=head.get("option_name") or None,
                description=head.get("description") or None,
                variants=[
                    {
                        "sku": r.get("sku", ""),
                        "size": r.get("size", ""),
                        "colour": r.get("colour", ""),
                        "price": float(r.get("price") or 0) if r.get("price") else 0.0,
                        "inventory": int(float(r.get("inventory") or 0)) if r.get("inventory") else 0,
                        "title": " / ".join(x for x in (r.get("colour"), r.get("size")) if x),
                    }
                    for r in rows
                ],
            )
            created.append(doc.handle)
        except (ValidationFailed, Conflict) as exc:
            failed.append({"handle": handle, "reason": exc.message})

    return {"created": created, "skipped": skipped, "failed": failed}


async def reconcile_unlinked_products(tenant_id: str) -> dict:
    """Upgrade `unlinked` products to `linked` once a store is connected.

    Matched by handle, which is exactly what the merchant pasted in the first
    place. Shopify's data wins for identity, variants and price; anything the
    merchant wrote (the content block) is left alone — they wrote it because
    Shopify did not have it.
    """
    tenant = await get_tenant(tenant_id)
    source = _source_for(tenant)
    if not source.active:
        return {"linked": [], "unmatched": [], "store_connected": False}

    cursor = merchant_products_col().find({"tenant_id": tenant_id, "link_state": "unlinked"})
    linked, unmatched = [], []
    for raw in await cursor.to_list(length=500):
        existing = MerchantProductDocument.model_validate(raw)
        ref = parse_product_reference(existing.handle or existing.online_store_url)
        try:
            payload = await source.fetch(ref)
        except Exception as exc:
            logger.warning("reconcile %s: lookup failed for %s: %s", tenant_id, existing.handle, exc)
            unmatched.append(existing.handle)
            continue
        if payload is None:
            unmatched.append(existing.handle)
            continue
        doc = _payload_to_doc(payload, tenant_id, existing)
        await merchant_products_col().replace_one({"_id": doc.id}, doc.to_mongo())
        linked.append(doc.handle)

    await merchant_tenants_col().update_one(
        {"_id": tenant_id}, {"$set": {"shopify.last_sync_at": _now()}}
    )
    return {"linked": linked, "unmatched": unmatched, "store_connected": True}


async def get_product(tenant_id: str, product_id: str) -> MerchantProductDocument:
    raw = await merchant_products_col().find_one({"_id": product_id, "tenant_id": tenant_id})
    if not raw:
        raise NotFound("Product not found")
    return MerchantProductDocument.model_validate(raw)


async def list_products(tenant_id: str) -> list[MerchantProductDocument]:
    cursor = merchant_products_col().find({"tenant_id": tenant_id}).sort("title", 1)
    return [MerchantProductDocument.model_validate(r) for r in await cursor.to_list(length=500)]


async def update_product_content(
    tenant_id: str, user_id: str, product_id: str, changes: dict
) -> MerchantProductDocument:
    """Edit the shopper-facing copy on the listing, recording who wrote it."""
    await require_member(tenant_id, user_id, "catalogue.edit")
    product = await get_product(tenant_id, product_id)
    content = product.content
    sources = dict(content.sources)
    for key, value in changes.items():
        if key not in ("description", "material_and_care", "manufacturing_info", "fit_info", "tax_note"):
            continue
        setattr(content, key, value)
        sources[key] = "merchant"
    content.sources = sources
    await merchant_products_col().update_one(
        {"_id": product_id},
        {"$set": {"content": content.model_dump(), "updated_at": _now()}},
    )
    return await get_product(tenant_id, product_id)


# ----------------------------------------------------------------- garments


async def get_garment(tenant_id: str, garment_id: str) -> MerchantGarmentDocument:
    raw = await merchant_garments_col().find_one({"_id": garment_id, "tenant_id": tenant_id})
    if not raw:
        raise NotFound("Garment not found")
    return MerchantGarmentDocument.model_validate(raw)


async def list_garments(tenant_id: str) -> list[MerchantGarmentDocument]:
    cursor = merchant_garments_col().find({"tenant_id": tenant_id}).sort("created_at", -1)
    return [MerchantGarmentDocument.model_validate(r) for r in await cursor.to_list(length=500)]


async def create_garment(
    tenant_id: str,
    user_id: str,
    *,
    product_id: str,
    option_value: str,
    merchant_title: str = "",
    category: str = "top",
) -> MerchantGarmentDocument:
    await require_member(tenant_id, user_id, "catalogue.edit")
    product = await get_product(tenant_id, product_id)

    existing = await merchant_garments_col().find_one(
        {"tenant_id": tenant_id, "product_id": product_id, "option_value": option_value}
    )
    if existing:
        raise Conflict(
            f"{product.title}{' — ' + option_value if option_value else ''} already has a garment"
        )

    now = _now()
    garment = MerchantGarmentDocument(
        id=new_id("m_g"),
        tenant_id=tenant_id,
        product_id=product_id,
        option_value=option_value,
        canonical_title=product.title,
        merchant_title=merchant_title.strip(),
        category=category,
        created_at=now,
        updated_at=now,
        updated_by=user_id,
    )
    # cloth_id is assigned at creation, not first submission: the id has to be
    # stable from the moment the garment exists so logs and run folders from a
    # failed early attempt still point at the right record.
    garment.pipeline.cloth_id = pipeline_bridge.cloth_id_for(garment.id)
    await merchant_garments_col().insert_one(garment.to_mongo())
    return garment


async def _save(garment: MerchantGarmentDocument, user_id: str, *, bump_revision: bool = False) -> MerchantGarmentDocument:
    """Persist a mutated garment.

    `bump_revision` on anything that changes what a shopper would be served.
    A revision ahead of the approved snapshot is what stops an edit reaching
    shoppers without going back through QA.
    """
    garment.updated_at = _now()
    garment.updated_by = user_id
    if bump_revision:
        garment.revision += 1
    await merchant_garments_col().replace_one({"_id": garment.id}, garment.to_mongo())
    return garment


async def set_reference_size(
    tenant_id: str, user_id: str, garment_id: str, size: str
) -> MerchantGarmentDocument:
    """Record which physical sample is in the merchant's hands.

    Existing assets keep the sample size they were shot against — changing
    this does not relabel them (audit P1-02). Assets pinned to a different
    sample are flagged so the mismatch is visible rather than silent.
    """
    await require_member(tenant_id, user_id, "catalogue.edit")
    garment = await get_garment(tenant_id, garment_id)
    garment.capture.reference_size = size

    stale = [a for a in garment.capture.assets if a.sample_size and a.sample_size != size]
    garment.capture.issues = [i for i in garment.capture.issues if not i.startswith("sample_mismatch")]
    if stale:
        garment.capture.issues.append(
            f"sample_mismatch: {len(stale)} image(s) were shot on size "
            f"{', '.join(sorted({a.sample_size for a in stale}))}, not {size}"
        )
    return await _save(garment, user_id, bump_revision=True)


async def add_capture_asset(
    tenant_id: str,
    user_id: str,
    garment_id: str,
    *,
    view: str,
    filename: str,
    content_type: str,
    data: bytes,
    is_cad: bool = False,
) -> MerchantGarmentDocument:
    await require_member(tenant_id, user_id, "catalogue.edit")
    garment = await get_garment(tenant_id, garment_id)

    if not is_cad and not garment.capture.reference_size:
        raise Conflict(
            "Choose which sample size you are photographing before uploading — "
            "otherwise the measurements have nothing to attach to.",
            code="reference_size_required",
        )

    asset = storage.store_capture_file(
        tenant_id=tenant_id,
        garment_id=garment_id,
        view=view,
        filename=filename,
        content_type=content_type,
        data=data,
        sample_size=garment.capture.reference_size,
        uploaded_by=user_id,
        is_cad=is_cad,
    )

    if is_cad:
        if garment.capture.cad_asset:
            storage.delete_capture_file(garment.capture.cad_asset.stored_path)
        garment.capture.cad_asset = asset
        garment.capture.method = "cad"
    else:
        # One accepted asset per view: a replacement supersedes rather than
        # accumulates, so view selection is never handed two "front" frames.
        superseded = [a for a in garment.capture.assets if a.view == view]
        for old in superseded:
            storage.delete_capture_file(old.stored_path)
        garment.capture.assets = [a for a in garment.capture.assets if a.view != view]
        garment.capture.assets.append(asset)

    return await _save(garment, user_id, bump_revision=True)


async def reject_capture_asset(
    tenant_id: str, user_id: str, garment_id: str, asset_id: str, reason: str
) -> MerchantGarmentDocument:
    await require_member(tenant_id, user_id, "catalogue.edit")
    garment = await get_garment(tenant_id, garment_id)
    for asset in garment.capture.assets:
        if asset.asset_id == asset_id:
            asset.accepted = False
            asset.rejected_reason = reason
            break
    else:
        raise NotFound("Capture asset not found")
    return await _save(garment, user_id, bump_revision=True)


async def set_material(
    tenant_id: str, user_id: str, garment_id: str, *, composition: list[dict], confirmed: bool,
    stretch: str | None = None, drape: str | None = None, thickness: str | None = None,
) -> MerchantGarmentDocument:
    await require_member(tenant_id, user_id, "catalogue.edit")
    garment = await get_garment(tenant_id, garment_id)

    total = sum(int(c.get("pct") or 0) for c in composition)
    if composition and total != 100:
        raise ValidationFailed(f"Fabric composition must total 100%, got {total}%")

    garment.material.composition = [
        FabricComponent(material=c["material"], pct=int(c["pct"])) for c in composition
    ]
    garment.material.confirmed = confirmed
    if stretch or drape or thickness:
        if stretch:
            garment.material.stretch = stretch
        if drape:
            garment.material.drape = drape
        if thickness:
            garment.material.thickness = thickness
        # A human set these, so they stop being a Mirra suggestion.
        garment.material.attributes_suggested = False
    return await _save(garment, user_id, bump_revision=True)


async def set_sizing(
    tenant_id: str,
    user_id: str,
    garment_id: str,
    *,
    rows: list[dict],
    fit_type: str | None = None,
    silhouette: str | None = None,
    fit_notes: str | None = None,
    source: str | None = None,
) -> MerchantGarmentDocument:
    await require_member(tenant_id, user_id, "catalogue.edit")
    garment = await get_garment(tenant_id, garment_id)

    parsed = [SizeRow(**row) for row in rows]
    labels = [r.size for r in parsed]
    if len(labels) != len(set(labels)):
        raise ValidationFailed("Each size may appear only once")

    garment.sizing.rows = parsed
    if fit_type:
        garment.sizing.fit_type = fit_type
    if silhouette is not None:
        garment.sizing.silhouette = silhouette
    if fit_notes is not None:
        garment.sizing.fit_notes = fit_notes
    if source:
        garment.sizing.source = source
    # Sizes changed, so the previously confirmed variant mapping is stale.
    garment.sizing.variant_mapping_confirmed = False
    garment.pipeline.size_ids = [
        pipeline_bridge.size_id_for(garment.id, r.size) for r in parsed
    ]
    return await _save(garment, user_id, bump_revision=True)


async def confirm_variant_mapping(
    tenant_id: str, user_id: str, garment_id: str, confirmed: bool
) -> MerchantGarmentDocument:
    await require_member(tenant_id, user_id, "catalogue.edit")
    garment = await get_garment(tenant_id, garment_id)
    garment.sizing.variant_mapping_confirmed = confirmed
    return await _save(garment, user_id)


async def set_garment_content(
    tenant_id: str, user_id: str, garment_id: str, changes: dict
) -> MerchantGarmentDocument:
    """Colourway-specific shopper copy. Overrides the product's for this garment."""
    await require_member(tenant_id, user_id, "catalogue.edit")
    garment = await get_garment(tenant_id, garment_id)
    sources = dict(garment.content.sources)
    for key, value in changes.items():
        if key not in ("description", "material_and_care", "manufacturing_info", "fit_info", "tax_note"):
            continue
        setattr(garment.content, key, value)
        sources[key] = "merchant"
    garment.content.sources = sources
    return await _save(garment, user_id, bump_revision=True)


# ---------------------------------------------------------------- readiness


def review_issues(
    garment: MerchantGarmentDocument, product: MerchantProductDocument | None
) -> dict:
    """What blocks a submission, and what is merely advisable.

    Same shape as the dashboard's `reviewIssues`, computed server-side so the
    submit endpoint and the UI cannot disagree about readiness.
    """
    blocking: list[dict] = []
    advisory: list[dict] = []

    capability = pipeline_bridge.check_pipeline_capability(garment)
    for reason in capability.reasons:
        blocking.append({"area": "pipeline", "label": "Pipeline", "detail": reason})

    if not garment.material.composition:
        blocking.append(
            {"area": "material", "label": "Material", "detail": "No fabric composition recorded"}
        )
    elif not garment.material.confirmed:
        advisory.append(
            {
                "area": "material",
                "label": "Material unconfirmed",
                "detail": "The composition has not been confirmed against the garment label",
            }
        )

    if garment.material.attributes_suggested and garment.material.composition:
        advisory.append(
            {
                "area": "material",
                "label": "Behaviour is a suggestion",
                "detail": "Stretch, drape and weight are Mirra's inference, not confirmed",
            }
        )

    if not garment.sizing.variant_mapping_confirmed:
        blocking.append(
            {
                "area": "sizing",
                "label": "Variant mapping",
                "detail": "Size to Shopify variant mapping has not been confirmed",
            }
        )

    if product is not None:
        product_sizes = {v.size for v in product.variants if v.size}
        garment_sizes = {r.size for r in garment.sizing.rows}
        unmatched = sorted(garment_sizes - product_sizes)
        if unmatched and product_sizes:
            blocking.append(
                {
                    "area": "sizing",
                    "label": "Unmatched sizes",
                    "detail": f"No Shopify variant for {', '.join(unmatched)}",
                }
            )
        if product.link_state == "unlinked":
            advisory.append(
                {
                    "area": "identity",
                    "label": "Product not linked to Shopify",
                    "detail": (
                        "Entered by hand. Price and stock will not track Shopify until the "
                        "store is connected and the product reconciles."
                    ),
                }
            )

    for issue in garment.capture.issues:
        advisory.append({"area": "capture", "label": "Capture", "detail": issue})

    return {"blocking": blocking, "advisory": advisory, "ready": not blocking}


# --------------------------------------------------------- stage machine


async def set_stage(
    tenant_id: str, user_id: str, garment_id: str, stage: str
) -> MerchantGarmentDocument:
    """Move one rung. Illegal transitions are refused, loudly."""
    permission = "qa.review" if stage in ("ready", "qa_changes") else "catalogue.edit"
    await require_member(tenant_id, user_id, permission)
    garment = await get_garment(tenant_id, garment_id)

    allowed = ALLOWED_TRANSITIONS.get(garment.stage, set())
    if stage not in allowed:
        raise Conflict(
            f"A garment in '{garment.stage}' cannot move to '{stage}' "
            f"(allowed: {', '.join(sorted(allowed)) or 'none'})"
        )

    if stage == "merchant_review":
        product = await get_product(tenant_id, garment.product_id)
        issues = review_issues(garment, product)
        if issues["blocking"]:
            raise Conflict(
                "Fix the blocking issues first: "
                + "; ".join(i["detail"] for i in issues["blocking"]),
                code="not_ready",
            )

    garment.stage = stage
    return await _save(garment, user_id)


async def add_qa_finding(
    tenant_id: str, user_id: str, garment_id: str, *, severity: str, area: str, detail: str
) -> MerchantGarmentDocument:
    await require_member(tenant_id, user_id, "qa.review")
    garment = await get_garment(tenant_id, garment_id)
    garment.qa_findings.append(
        QaFinding(
            finding_id=new_id("qaf"),
            severity=severity,
            area=area,
            detail=detail,
            raised_by=user_id,
            raised_at=_now(),
        )
    )
    return await _save(garment, user_id)


async def approve_garment(tenant_id: str, user_id: str, garment_id: str) -> MerchantGarmentDocument:
    """QA approval: freeze this exact revision as the served snapshot.

    Approval is a copy, not a flag. Everything a shopper is served comes off
    this snapshot, so a later edit cannot reach them without a new approval.
    """
    await require_member(tenant_id, user_id, "qa.review")
    garment = await get_garment(tenant_id, garment_id)
    if garment.stage != "in_qa":
        raise Conflict(f"Only a garment in QA can be approved (this one is '{garment.stage}')")

    unresolved = [f for f in garment.qa_findings if f.severity == "blocking" and not f.resolved]
    if unresolved:
        raise Conflict(f"{len(unresolved)} blocking QA finding(s) are still open")

    garment.approved = ApprovedSnapshot.freeze(garment, user_id, _now())
    garment.stage = "ready"
    return await _save(garment, user_id)


async def set_publication(
    tenant_id: str, user_id: str, garment_id: str, *, published: bool, try_on_enabled: bool | None = None
) -> MerchantGarmentDocument:
    await require_member(tenant_id, user_id, "catalogue.publish")
    garment = await get_garment(tenant_id, garment_id)

    if published:
        if garment.approved is None:
            raise Conflict("Only a QA-approved garment can be published")
        if garment.stage not in ("ready", "paused", "live"):
            raise Conflict(f"A garment in '{garment.stage}' cannot be published")
        garment.stage = "live"
        garment.publication.published = True
        garment.publication.published_at = _now()
        garment.publication.published_by = user_id
    else:
        if garment.stage == "live":
            garment.stage = "paused"
        garment.publication.published = False

    if try_on_enabled is not None:
        garment.publication.try_on_enabled = try_on_enabled
    return await _save(garment, user_id)


# ------------------------------------------------------- pipeline hand-off


async def submit_for_ingestion(
    tenant_id: str, user_id: str, garment_id: str
) -> list[IngestionRunDocument]:
    """Capture → Product Ingestion. One run per size.

    Writes the `cloths`/`sizes` documents and stages the capture images, then
    queues a Step 2 run per size. The measurement documents are written before
    anything is queued so the worker can never read a size that does not exist.
    """
    await require_member(tenant_id, user_id, "catalogue.edit")
    garment = await get_garment(tenant_id, garment_id)

    verdict = pipeline_bridge.check_pipeline_capability(garment)
    if not verdict.ok:
        raise Conflict(verdict.reason, code="pipeline_unsupported")

    cloth_id, size_ids = await pipeline_bridge.publish_measurements(garment)
    staged = pipeline_bridge.stage_capture_input(garment, cloth_id)
    if staged.image_count == 0:
        raise Conflict(
            "None of the accepted capture images could be read from storage — re-upload them.",
            code="capture_missing",
        )

    now = _now()
    runs: list[IngestionRunDocument] = []
    for size_id in size_ids:
        run = IngestionRunDocument(
            id=new_id("m_ing"),
            tenant_id=tenant_id,
            garment_id=garment_id,
            cloth_id=cloth_id,
            size_id=size_id,
            state="queued",
            created_at=now,
        )
        await merchant_ingestion_runs_col().insert_one(run.to_mongo())
        runs.append(run)

    garment.pipeline.cloth_id = cloth_id
    garment.pipeline.size_ids = size_ids
    garment.pipeline.ingestion_run_ids = [r.id for r in runs]
    garment.pipeline.state = "queued"
    garment.pipeline.failure_reason = ""
    garment.pipeline.updated_at = now
    await _save(garment, user_id)

    # Enqueue only after every document is written.
    for run in runs:
        engine.start_ingestion(run.id)
    return runs


async def request_preview(
    tenant_id: str, user_id: str, garment_id: str, size_id: str | None = None
) -> PreviewDocument:
    """Product Ingestion → VTO. Renders on the reference avatar for QA.

    Requires a completed ingestion run for the size: without panels there is
    nothing to drape, and falling back to the default t-shirt here is exactly
    what made every render look identical.
    """
    await require_member(tenant_id, user_id, "catalogue.edit")
    garment = await get_garment(tenant_id, garment_id)

    if not garment.pipeline.ingested_runs:
        raise Conflict(
            "No completed ingestion run exists for this garment yet — submit it for "
            "ingestion and wait for panels to be generated.",
            code="ingestion_required",
        )

    target_size = size_id or next(iter(garment.pipeline.ingested_runs))
    if target_size not in garment.pipeline.ingested_runs:
        raise Conflict(f"No completed ingestion run for size {target_size}")

    preview = PreviewDocument(
        id=new_id("m_pv"),
        tenant_id=tenant_id,
        garment_id=garment_id,
        cloth_id=garment.pipeline.cloth_id,
        size_id=target_size,
        revision=garment.revision,
        state="requested",
        requested_by=user_id,
        created_at=_now(),
    )
    await merchant_previews_col().insert_one(preview.to_mongo())

    garment.pipeline.preview_id = preview.id
    garment.pipeline.state = "previewing"
    garment.pipeline.updated_at = _now()
    await _save(garment, user_id)

    engine.start_preview(preview.id)
    return preview


async def get_preview(tenant_id: str, preview_id: str) -> PreviewDocument:
    raw = await merchant_previews_col().find_one({"_id": preview_id, "tenant_id": tenant_id})
    if not raw:
        raise NotFound("Preview not found")
    return PreviewDocument.model_validate(raw)


async def list_previews(tenant_id: str, garment_id: str) -> list[PreviewDocument]:
    cursor = (
        merchant_previews_col()
        .find({"tenant_id": tenant_id, "garment_id": garment_id})
        .sort("created_at", -1)
    )
    return [PreviewDocument.model_validate(r) for r in await cursor.to_list(length=20)]


async def latest_ready_preview(tenant_id: str, garment_id: str) -> PreviewDocument | None:
    raw = await merchant_previews_col().find_one(
        {"tenant_id": tenant_id, "garment_id": garment_id, "state": "ready"},
        sort=[("created_at", -1)],
    )
    return PreviewDocument.model_validate(raw) if raw else None


async def list_ingestion_runs(tenant_id: str, garment_id: str) -> list[IngestionRunDocument]:
    cursor = (
        merchant_ingestion_runs_col()
        .find({"tenant_id": tenant_id, "garment_id": garment_id})
        .sort("created_at", -1)
    )
    return [IngestionRunDocument.model_validate(r) for r in await cursor.to_list(length=50)]


# -------------------------------------------------------------- shopper API


async def public_catalogue(tenant_id: str, *, preview: bool = False) -> list[dict]:
    """Every garment a shopper may see, in the studio's `PublicProduct` shape.

    `preview=True` additionally includes QA-approved-but-unpublished garments,
    which is what the merchant preview and the QA reviewer see.
    """
    tenant = await get_tenant(tenant_id)
    products = {p.id: p for p in await list_products(tenant_id)}
    out: list[dict] = []

    for garment in await list_garments(tenant_id):
        product = products.get(garment.product_id)
        ready_preview = await latest_ready_preview(tenant_id, garment.id)
        asset_available = ready_preview is not None and bool(ready_preview.glb_path)
        resolved = publication.resolve_garment(
            garment, tenant, product, asset_available=asset_available
        )

        previewable = (
            preview and not resolved.visible and garment.approved is not None
        )
        if not resolved.visible and not previewable:
            continue

        asset_url = (
            f"/api/v1/merchant/{tenant_id}/previews/{ready_preview.id}/glb"
            if asset_available
            else None
        )
        out.append(
            publication.public_product(
                garment,
                tenant,
                product,
                resolved,
                asset_url=asset_url,
                preview=previewable,
            )
        )
    return out
