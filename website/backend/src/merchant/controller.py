"""HTTP <-> domain translation for the merchant surface.

Shaping rules that matter:
  * `access_token` never appears in a response — only `connected: true|false`.
  * a capture asset reports its checksum and real byte size, because that is
    the evidence that a file actually arrived.
  * readiness is computed server-side and returned with every garment, so the
    dashboard's submit button and the submit endpoint agree by construction.
"""

from fastapi.responses import FileResponse

from ..core.errors import NotFound
from . import service, storage
from .models import (
    CaptureAsset,
    IngestionRunDocument,
    MerchantGarmentDocument,
    MerchantProductDocument,
    MerchantTenantDocument,
    PreviewDocument,
    ProductContent,
)
from .pipeline_bridge import check_pipeline_capability
from .product_source import ProductPayload


def shape_tenant(tenant: MerchantTenantDocument) -> dict:
    return {
        "tenantId": tenant.id,
        "slug": tenant.slug,
        "name": tenant.name,
        "storeUrl": tenant.store_url,
        "status": tenant.status,
        "shopify": {
            # The token itself is never serialised.
            "connected": tenant.shopify.connected,
            "storeDomain": tenant.shopify.store_domain,
            "customDomain": tenant.shopify.custom_domain,
            "scopes": tenant.shopify.scopes,
            "connectedAt": tenant.shopify.connected_at.isoformat() if tenant.shopify.connected_at else None,
            "lastSyncAt": tenant.shopify.last_sync_at.isoformat() if tenant.shopify.last_sync_at else None,
            "lastSyncError": tenant.shopify.last_sync_error,
        },
    }


def shape_content(content: ProductContent) -> dict:
    return {
        "description": content.description,
        "materialAndCare": content.material_and_care,
        "manufacturingInfo": content.manufacturing_info,
        "fitInfo": content.fit_info,
        "taxNote": content.tax_note,
        "sources": content.sources,
    }


def shape_product(product: MerchantProductDocument) -> dict:
    return {
        "productId": product.id,
        "source": product.source,
        # The distinction the merchant needs to understand: is this identity
        # confirmed by Shopify, or provisional until the store is connected?
        "linkState": product.link_state,
        "shopifyId": product.shopify_gid or product.shopify_numeric_id,
        "handle": product.handle,
        "storeDomain": product.store_domain,
        "onlineStoreUrl": product.online_store_url,
        "title": product.title,
        "productType": product.product_type,
        "vendor": product.vendor,
        "optionName": product.option_name,
        "imageUrls": product.image_urls,
        "content": shape_content(product.content),
        "variants": [
            {
                "variantId": v.variant_id,
                "sku": v.sku,
                "title": v.title,
                "size": v.size,
                "colour": v.colour,
                "price": v.price,
                "currency": v.currency,
                "inventory": v.inventory,
            }
            for v in product.variants
        ],
        "syncStatus": product.sync_status,
        "syncError": product.sync_error,
        "lastSyncedAt": product.last_synced_at.isoformat() if product.last_synced_at else None,
    }


def shape_draft(payload: ProductPayload) -> dict:
    """The provisional identity a URL alone establishes."""
    return {
        "handle": payload.handle,
        "suggestedTitle": payload.title,
        "storeDomain": payload.store_domain,
        "onlineStoreUrl": payload.online_store_url,
        "shopifyId": payload.shopify_gid or payload.shopify_numeric_id,
    }


def shape_asset(asset: CaptureAsset) -> dict:
    return {
        "assetId": asset.asset_id,
        "view": asset.view,
        "filename": asset.filename,
        "contentType": asset.content_type,
        "bytes": asset.bytes,
        "sha256": asset.sha256,
        "width": asset.width,
        "height": asset.height,
        "accepted": asset.accepted,
        "rejectedReason": asset.rejected_reason,
        "sampleSize": asset.sample_size,
        "uploadedAt": asset.uploaded_at.isoformat(),
    }


def shape_garment(
    garment: MerchantGarmentDocument, product: MerchantProductDocument | None = None
) -> dict:
    capability = check_pipeline_capability(garment)
    issues = service.review_issues(garment, product)
    return {
        "garmentId": garment.id,
        "productId": garment.product_id,
        "optionValue": garment.option_value,
        "canonicalTitle": garment.canonical_title,
        "merchantTitle": garment.merchant_title,
        "title": garment.merchant_title or garment.canonical_title,
        "category": garment.category,
        "stage": garment.stage,
        "revision": garment.revision,
        "capture": {
            "method": garment.capture.method,
            "referenceSize": garment.capture.reference_size,
            "assets": [shape_asset(a) for a in garment.capture.assets],
            "cadAsset": shape_asset(garment.capture.cad_asset) if garment.capture.cad_asset else None,
            "issues": garment.capture.issues,
        },
        "material": {
            "composition": [{"material": c.material, "pct": c.pct} for c in garment.material.composition],
            "confirmed": garment.material.confirmed,
            "stretch": garment.material.stretch,
            "drape": garment.material.drape,
            "thickness": garment.material.thickness,
            "attributesSuggested": garment.material.attributes_suggested,
        },
        "sizing": {
            "fitType": garment.sizing.fit_type,
            "silhouette": garment.sizing.silhouette,
            "fitNotes": garment.sizing.fit_notes,
            "source": garment.sizing.source,
            "variantMappingConfirmed": garment.sizing.variant_mapping_confirmed,
            "rows": [r.model_dump() for r in garment.sizing.rows],
        },
        "content": shape_content(garment.content),
        "pipeline": {
            "state": garment.pipeline.state,
            "clothId": garment.pipeline.cloth_id,
            "sizeIds": garment.pipeline.size_ids,
            "ingestedRuns": garment.pipeline.ingested_runs,
            "previewId": garment.pipeline.preview_id,
            "failureReason": garment.pipeline.failure_reason,
            "supported": capability.ok,
            "unsupportedReason": capability.reason,
        },
        "publication": {
            "published": garment.publication.published,
            "tryOnEnabled": garment.publication.try_on_enabled,
            "soldOutPolicy": garment.publication.sold_out_policy,
            "publishedAt": garment.publication.published_at.isoformat() if garment.publication.published_at else None,
        },
        "qaFindings": [
            {
                "findingId": f.finding_id,
                "severity": f.severity,
                "area": f.area,
                "detail": f.detail,
                "raisedAt": f.raised_at.isoformat(),
                "resolved": f.resolved,
            }
            for f in garment.qa_findings
        ],
        "approved": (
            {
                "revision": garment.approved.revision,
                "approvedAt": garment.approved.approved_at.isoformat(),
                "previewId": garment.approved.preview_id,
            }
            if garment.approved
            else None
        ),
        # A working draft ahead of the approved snapshot cannot reach shoppers.
        "draftAhead": bool(garment.approved and garment.revision > garment.approved.revision),
        "readiness": issues,
        "updatedAt": garment.updated_at.isoformat(),
    }


def shape_run(run: IngestionRunDocument) -> dict:
    return {
        "runId": run.id,
        "garmentId": run.garment_id,
        "clothId": run.cloth_id,
        "sizeId": run.size_id,
        "state": run.state,
        "productRunId": run.product_run_id,
        "panelCount": run.panel_count,
        "failureReason": run.failure_reason,
        "createdAt": run.created_at.isoformat(),
        "completedAt": run.completed_at.isoformat() if run.completed_at else None,
    }


def shape_preview(preview: PreviewDocument) -> dict:
    return {
        "previewId": preview.id,
        "garmentId": preview.garment_id,
        "clothId": preview.cloth_id,
        "sizeId": preview.size_id,
        "revision": preview.revision,
        "state": preview.state,
        # Never implied from state — only true when a file path was recorded.
        "hasModel": bool(preview.glb_path),
        "glbUrl": (
            f"/api/v1/merchant/{preview.tenant_id}/previews/{preview.id}/glb"
            if preview.glb_path
            else None
        ),
        "failureReason": preview.failure_reason,
        "cloRunId": preview.clo_run_id,
        "createdAt": preview.created_at.isoformat(),
        "completedAt": preview.completed_at.isoformat() if preview.completed_at else None,
    }


# ------------------------------------------------------------------ actions


async def list_workspaces(user_id: str) -> dict:
    tenants = await service.list_tenants_for_user(user_id)
    return {"items": [shape_tenant(t) for t in tenants]}


async def get_workspace(tenant_id: str, user_id: str) -> dict:
    await service.require_member(tenant_id, user_id, permission="")  # membership only
    return {"workspace": shape_tenant(await service.get_tenant(tenant_id))}


async def connect_shopify(tenant_id: str, user_id: str, body) -> dict:
    tenant = await service.connect_shopify(
        tenant_id,
        user_id,
        store_domain=body.store_domain,
        access_token=body.access_token,
        scopes=body.scopes,
    )
    return {"workspace": shape_tenant(tenant)}


async def reconcile(tenant_id: str, user_id: str) -> dict:
    await service.require_member(tenant_id, user_id, "settings.edit")
    return await service.reconcile_unlinked_products(tenant_id)


async def lookup_product(tenant_id: str, user_id: str, body) -> dict:
    result = await service.lookup_product(tenant_id, user_id, body.input)
    out: dict = {"outcome": result["outcome"], "storeConnected": result["store_connected"]}
    if "product" in result:
        out["product"] = shape_product(result["product"])
    if "draft" in result:
        out["draft"] = shape_draft(result["draft"])
        out["guidance"] = (
            "No Shopify store is connected to this workspace, so Mirra cannot read the "
            "product's variants, sizes or price. Confirm the details below and Mirra will "
            "link them to the Shopify listing automatically once the store is connected."
        )
    return out


async def create_manual_product(tenant_id: str, user_id: str, body) -> dict:
    product = await service.create_manual_product(
        tenant_id,
        user_id,
        handle=body.handle,
        title=body.title,
        online_store_url=body.online_store_url,
        store_domain=body.store_domain,
        product_type=body.product_type,
        vendor=body.vendor,
        option_name=body.option_name,
        description=body.description,
        variants=[v.model_dump() for v in body.variants],
    )
    return {"product": shape_product(product)}


async def import_csv(tenant_id: str, user_id: str, content: bytes) -> dict:
    return await service.import_products_csv(tenant_id, user_id, content)


async def list_products(tenant_id: str, user_id: str) -> dict:
    await service.require_member(tenant_id, user_id, permission="")
    return {"items": [shape_product(p) for p in await service.list_products(tenant_id)]}


async def update_product_content(tenant_id: str, user_id: str, product_id: str, body) -> dict:
    product = await service.update_product_content(
        tenant_id, user_id, product_id, body.model_dump(exclude_unset=True)
    )
    return {"product": shape_product(product)}


async def _with_product(tenant_id: str, garment) -> dict:
    try:
        product = await service.get_product(tenant_id, garment.product_id)
    except NotFound:
        product = None
    return shape_garment(garment, product)


async def list_garments(tenant_id: str, user_id: str) -> dict:
    await service.require_member(tenant_id, user_id, permission="")
    garments = await service.list_garments(tenant_id)
    products = {p.id: p for p in await service.list_products(tenant_id)}
    return {"items": [shape_garment(g, products.get(g.product_id)) for g in garments]}


async def get_garment(tenant_id: str, user_id: str, garment_id: str) -> dict:
    await service.require_member(tenant_id, user_id, permission="")
    garment = await service.get_garment(tenant_id, garment_id)
    return {"garment": await _with_product(tenant_id, garment)}


async def create_garment(tenant_id: str, user_id: str, body) -> dict:
    garment = await service.create_garment(
        tenant_id,
        user_id,
        product_id=body.product_id,
        option_value=body.option_value,
        merchant_title=body.merchant_title,
        category=body.category,
    )
    return {"garment": await _with_product(tenant_id, garment)}


async def set_reference_size(tenant_id: str, user_id: str, garment_id: str, body) -> dict:
    garment = await service.set_reference_size(tenant_id, user_id, garment_id, body.size)
    return {"garment": await _with_product(tenant_id, garment)}


async def upload_capture(
    tenant_id: str, user_id: str, garment_id: str, *, view: str, filename: str,
    content_type: str, data: bytes, is_cad: bool,
) -> dict:
    garment = await service.add_capture_asset(
        tenant_id, user_id, garment_id,
        view=view, filename=filename, content_type=content_type, data=data, is_cad=is_cad,
    )
    return {"garment": await _with_product(tenant_id, garment)}


async def reject_capture(tenant_id: str, user_id: str, garment_id: str, asset_id: str, body) -> dict:
    garment = await service.reject_capture_asset(
        tenant_id, user_id, garment_id, asset_id, body.reason
    )
    return {"garment": await _with_product(tenant_id, garment)}


async def get_capture_file(tenant_id: str, user_id: str, garment_id: str, asset_id: str) -> FileResponse:
    await service.require_member(tenant_id, user_id, permission="")
    garment = await service.get_garment(tenant_id, garment_id)
    assets = list(garment.capture.assets) + (
        [garment.capture.cad_asset] if garment.capture.cad_asset else []
    )
    for asset in assets:
        if asset.asset_id == asset_id:
            path = storage.resolve_capture_path(asset.stored_path)
            if not path.is_file():
                raise NotFound("Capture file is missing on disk")
            return FileResponse(
                path=path, media_type=asset.content_type, filename=asset.filename
            )
    raise NotFound("Capture asset not found")


async def set_material(tenant_id: str, user_id: str, garment_id: str, body) -> dict:
    garment = await service.set_material(
        tenant_id, user_id, garment_id,
        composition=[c.model_dump() for c in body.composition],
        confirmed=body.confirmed,
        stretch=body.stretch, drape=body.drape, thickness=body.thickness,
    )
    return {"garment": await _with_product(tenant_id, garment)}


async def set_sizing(tenant_id: str, user_id: str, garment_id: str, body) -> dict:
    garment = await service.set_sizing(
        tenant_id, user_id, garment_id,
        rows=[r.model_dump() for r in body.rows],
        fit_type=body.fit_type, silhouette=body.silhouette,
        fit_notes=body.fit_notes, source=body.source,
    )
    return {"garment": await _with_product(tenant_id, garment)}


async def confirm_mapping(tenant_id: str, user_id: str, garment_id: str, body) -> dict:
    garment = await service.confirm_variant_mapping(tenant_id, user_id, garment_id, body.confirmed)
    return {"garment": await _with_product(tenant_id, garment)}


async def set_garment_content(tenant_id: str, user_id: str, garment_id: str, body) -> dict:
    garment = await service.set_garment_content(
        tenant_id, user_id, garment_id, body.model_dump(exclude_unset=True)
    )
    return {"garment": await _with_product(tenant_id, garment)}


async def set_stage(tenant_id: str, user_id: str, garment_id: str, body) -> dict:
    garment = await service.set_stage(tenant_id, user_id, garment_id, body.stage)
    return {"garment": await _with_product(tenant_id, garment)}


async def approve(tenant_id: str, user_id: str, garment_id: str) -> dict:
    garment = await service.approve_garment(tenant_id, user_id, garment_id)
    return {"garment": await _with_product(tenant_id, garment)}


async def add_finding(tenant_id: str, user_id: str, garment_id: str, body) -> dict:
    garment = await service.add_qa_finding(
        tenant_id, user_id, garment_id,
        severity=body.severity, area=body.area, detail=body.detail,
    )
    return {"garment": await _with_product(tenant_id, garment)}


async def set_publication(tenant_id: str, user_id: str, garment_id: str, body) -> dict:
    garment = await service.set_publication(
        tenant_id, user_id, garment_id,
        published=body.published, try_on_enabled=body.try_on_enabled,
    )
    return {"garment": await _with_product(tenant_id, garment)}


async def submit_ingestion(tenant_id: str, user_id: str, garment_id: str) -> dict:
    runs = await service.submit_for_ingestion(tenant_id, user_id, garment_id)
    return {"runs": [shape_run(r) for r in runs]}


async def list_runs(tenant_id: str, user_id: str, garment_id: str) -> dict:
    await service.require_member(tenant_id, user_id, permission="")
    return {"items": [shape_run(r) for r in await service.list_ingestion_runs(tenant_id, garment_id)]}


async def request_preview(tenant_id: str, user_id: str, garment_id: str, body) -> dict:
    preview = await service.request_preview(tenant_id, user_id, garment_id, body.size_id)
    return {"preview": shape_preview(preview)}


async def list_previews(tenant_id: str, user_id: str, garment_id: str) -> dict:
    await service.require_member(tenant_id, user_id, permission="")
    return {"items": [shape_preview(p) for p in await service.list_previews(tenant_id, garment_id)]}


async def get_preview(tenant_id: str, user_id: str, preview_id: str) -> dict:
    await service.require_member(tenant_id, user_id, permission="")
    return {"preview": shape_preview(await service.get_preview(tenant_id, preview_id))}


async def get_preview_glb(tenant_id: str, user_id: str, preview_id: str) -> FileResponse:
    await service.require_member(tenant_id, user_id, permission="")
    preview = await service.get_preview(tenant_id, preview_id)
    if not preview.glb_path:
        raise NotFound("No preview model has been rendered yet")
    path = storage.resolve_capture_path(preview.glb_path)
    if not path.is_file():
        raise NotFound("Preview model file is missing on disk")
    return FileResponse(
        path=path,
        media_type="model/gltf-binary",
        filename="preview.glb",
        headers={"Cache-Control": "private, max-age=3600"},
    )


async def public_catalogue(tenant_id: str, preview: bool) -> dict:
    return {"items": await service.public_catalogue(tenant_id, preview=preview)}
