"""Merchant routes — workspace, products, garments, capture, pipeline, QA.

Everything is tenant-scoped in the path (`/merchant/{tenant_id}/...`) and
membership is checked on every call in the service layer, so an authenticated
user of one workspace cannot read or mutate another's by guessing an id.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse

from ..core.auth_dependency import Identity, get_identity
from . import controller
from .schemas import (
    ConfirmMappingRequest,
    ConnectShopifyRequest,
    ContentRequest,
    CreateGarmentRequest,
    CreateManualProductRequest,
    LookupProductRequest,
    MaterialRequest,
    PreviewRequest,
    PublicationRequest,
    QaFindingRequest,
    ReferenceSizeRequest,
    RejectAssetRequest,
    SizingRequest,
    StageRequest,
)

router = APIRouter(prefix="/merchant", tags=["merchant"])

CurrentIdentity = Annotated[Identity, Depends(get_identity)]


# ---------------------------------------------------------------- workspace


@router.get("/workspaces")
async def list_workspaces(identity: CurrentIdentity):
    return await controller.list_workspaces(identity.user_id)


@router.get("/{tenant_id}")
async def get_workspace(tenant_id: str, identity: CurrentIdentity):
    return await controller.get_workspace(tenant_id, identity.user_id)


@router.post("/{tenant_id}/shopify/connect")
async def connect_shopify(tenant_id: str, body: ConnectShopifyRequest, identity: CurrentIdentity):
    return await controller.connect_shopify(tenant_id, identity.user_id, body)


@router.post("/{tenant_id}/shopify/reconcile")
async def reconcile(tenant_id: str, identity: CurrentIdentity):
    """Upgrade hand-entered products to linked ones, now that a store exists."""
    return await controller.reconcile(tenant_id, identity.user_id)


# ----------------------------------------------------------------- products


@router.post("/{tenant_id}/products/lookup")
async def lookup_product(tenant_id: str, body: LookupProductRequest, identity: CurrentIdentity):
    """Resolve a pasted storefront URL, handle or GID.

    Always returns a usable outcome: `resolved` (live from Shopify),
    `matched` (already in Mirra), or `draft` (no store connected — here is
    everything the URL established, complete it by hand).
    """
    return await controller.lookup_product(tenant_id, identity.user_id, body)


@router.get("/{tenant_id}/products")
async def list_products(tenant_id: str, identity: CurrentIdentity):
    return await controller.list_products(tenant_id, identity.user_id)


@router.post("/{tenant_id}/products", status_code=201)
async def create_manual_product(
    tenant_id: str, body: CreateManualProductRequest, identity: CurrentIdentity
):
    return await controller.create_manual_product(tenant_id, identity.user_id, body)


@router.post("/{tenant_id}/products/import", status_code=201)
async def import_products(
    tenant_id: str, identity: CurrentIdentity, file: UploadFile = File(...)
):
    """Bulk import from a CSV — Shopify's own product export is accepted as-is."""
    return await controller.import_csv(tenant_id, identity.user_id, await file.read())


@router.patch("/{tenant_id}/products/{product_id}/content")
async def update_product_content(
    tenant_id: str, product_id: str, body: ContentRequest, identity: CurrentIdentity
):
    """The shopper-facing copy shown in the studio's product panel."""
    return await controller.update_product_content(tenant_id, identity.user_id, product_id, body)


# ----------------------------------------------------------------- garments


@router.get("/{tenant_id}/garments")
async def list_garments(tenant_id: str, identity: CurrentIdentity):
    return await controller.list_garments(tenant_id, identity.user_id)


@router.post("/{tenant_id}/garments", status_code=201)
async def create_garment(tenant_id: str, body: CreateGarmentRequest, identity: CurrentIdentity):
    return await controller.create_garment(tenant_id, identity.user_id, body)


@router.get("/{tenant_id}/garments/{garment_id}")
async def get_garment(tenant_id: str, garment_id: str, identity: CurrentIdentity):
    return await controller.get_garment(tenant_id, identity.user_id, garment_id)


@router.put("/{tenant_id}/garments/{garment_id}/reference-size")
async def set_reference_size(
    tenant_id: str, garment_id: str, body: ReferenceSizeRequest, identity: CurrentIdentity
):
    return await controller.set_reference_size(tenant_id, identity.user_id, garment_id, body)


# ------------------------------------------------------------------ capture


@router.post("/{tenant_id}/garments/{garment_id}/capture", status_code=201)
async def upload_capture(
    tenant_id: str,
    garment_id: str,
    identity: CurrentIdentity,
    file: UploadFile = File(...),
    view: str = Form("front"),
    is_cad: bool = Form(False),
):
    """Receive one real capture file. Validated, hashed and stored."""
    return await controller.upload_capture(
        tenant_id,
        identity.user_id,
        garment_id,
        view=view,
        filename=file.filename or "upload",
        content_type=file.content_type or "",
        data=await file.read(),
        is_cad=is_cad,
    )


@router.get("/{tenant_id}/garments/{garment_id}/capture/{asset_id}")
async def get_capture_file(
    tenant_id: str, garment_id: str, asset_id: str, identity: CurrentIdentity
) -> FileResponse:
    return await controller.get_capture_file(tenant_id, identity.user_id, garment_id, asset_id)


@router.post("/{tenant_id}/garments/{garment_id}/capture/{asset_id}/reject")
async def reject_capture(
    tenant_id: str,
    garment_id: str,
    asset_id: str,
    body: RejectAssetRequest,
    identity: CurrentIdentity,
):
    return await controller.reject_capture(tenant_id, identity.user_id, garment_id, asset_id, body)


# --------------------------------------------------------- material/sizing


@router.put("/{tenant_id}/garments/{garment_id}/material")
async def set_material(
    tenant_id: str, garment_id: str, body: MaterialRequest, identity: CurrentIdentity
):
    return await controller.set_material(tenant_id, identity.user_id, garment_id, body)


@router.put("/{tenant_id}/garments/{garment_id}/sizing")
async def set_sizing(
    tenant_id: str, garment_id: str, body: SizingRequest, identity: CurrentIdentity
):
    return await controller.set_sizing(tenant_id, identity.user_id, garment_id, body)


@router.put("/{tenant_id}/garments/{garment_id}/variant-mapping")
async def confirm_mapping(
    tenant_id: str, garment_id: str, body: ConfirmMappingRequest, identity: CurrentIdentity
):
    return await controller.confirm_mapping(tenant_id, identity.user_id, garment_id, body)


@router.patch("/{tenant_id}/garments/{garment_id}/content")
async def set_garment_content(
    tenant_id: str, garment_id: str, body: ContentRequest, identity: CurrentIdentity
):
    """Colourway-specific copy, overriding the listing's for this garment."""
    return await controller.set_garment_content(tenant_id, identity.user_id, garment_id, body)


# --------------------------------------------------------------- lifecycle


@router.put("/{tenant_id}/garments/{garment_id}/stage")
async def set_stage(tenant_id: str, garment_id: str, body: StageRequest, identity: CurrentIdentity):
    return await controller.set_stage(tenant_id, identity.user_id, garment_id, body)


@router.post("/{tenant_id}/garments/{garment_id}/qa/findings", status_code=201)
async def add_finding(
    tenant_id: str, garment_id: str, body: QaFindingRequest, identity: CurrentIdentity
):
    return await controller.add_finding(tenant_id, identity.user_id, garment_id, body)


@router.post("/{tenant_id}/garments/{garment_id}/qa/approve")
async def approve(tenant_id: str, garment_id: str, identity: CurrentIdentity):
    """Freeze this revision as the snapshot shoppers are served."""
    return await controller.approve(tenant_id, identity.user_id, garment_id)


@router.put("/{tenant_id}/garments/{garment_id}/publication")
async def set_publication(
    tenant_id: str, garment_id: str, body: PublicationRequest, identity: CurrentIdentity
):
    return await controller.set_publication(tenant_id, identity.user_id, garment_id, body)


# ---------------------------------------------------------------- pipeline


@router.post("/{tenant_id}/garments/{garment_id}/ingestion", status_code=202)
async def submit_ingestion(tenant_id: str, garment_id: str, identity: CurrentIdentity):
    """Capture → Product Ingestion. Queues one Step 2 run per size."""
    return await controller.submit_ingestion(tenant_id, identity.user_id, garment_id)


@router.get("/{tenant_id}/garments/{garment_id}/ingestion")
async def list_runs(tenant_id: str, garment_id: str, identity: CurrentIdentity):
    return await controller.list_runs(tenant_id, identity.user_id, garment_id)


@router.post("/{tenant_id}/garments/{garment_id}/previews", status_code=202)
async def request_preview(
    tenant_id: str, garment_id: str, body: PreviewRequest, identity: CurrentIdentity
):
    """Product Ingestion → VTO. Renders on Mirra's reference avatar for QA."""
    return await controller.request_preview(tenant_id, identity.user_id, garment_id, body)


@router.get("/{tenant_id}/garments/{garment_id}/previews")
async def list_previews(tenant_id: str, garment_id: str, identity: CurrentIdentity):
    return await controller.list_previews(tenant_id, identity.user_id, garment_id)


@router.get("/{tenant_id}/previews/{preview_id}")
async def get_preview(tenant_id: str, preview_id: str, identity: CurrentIdentity):
    return await controller.get_preview(tenant_id, identity.user_id, preview_id)


@router.get("/{tenant_id}/previews/{preview_id}/glb")
async def get_preview_glb(
    tenant_id: str, preview_id: str, identity: CurrentIdentity
) -> FileResponse:
    return await controller.get_preview_glb(tenant_id, identity.user_id, preview_id)


# ------------------------------------------------------------ shopper view


@router.get("/{tenant_id}/catalogue")
async def public_catalogue(
    tenant_id: str,
    identity: CurrentIdentity,
    preview: bool = Query(default=False),
):
    """What a shopper is served, in the studio's own PublicProduct shape.

    `preview=true` additionally includes QA-approved-but-unpublished garments
    — the merchant's own preview and the QA reviewer's view.
    """
    await controller.get_workspace(tenant_id, identity.user_id)  # membership check
    return await controller.public_catalogue(tenant_id, preview)
