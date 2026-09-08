"""Merchant-side Mongo document shapes.

Three collections carry the whole merchant surface:

    merchant_tenants    one per brand workspace
    merchant_products   the Shopify listing — *identity*
    merchant_garments   one colourway of a listing, digitised for try-on

Plus two operational ones:

    merchant_ingestion_runs   a Step 2 (product_ingestion) execution
    merchant_previews         a QA preview render on the reference avatar

Identity, and why a URL is enough
---------------------------------
A storefront URL does carry identity: the **handle** is the last path
segment of `/products/<handle>`, and it is what Shopify itself keys the
storefront on. What a URL does *not* carry is the numeric product id / GID,
the variants, or the price — those only come from the Admin API.

So a product is stored in one of two link states:

    linked      resolved through a connected store. `shopify_gid` is set and
                is the immutable identity; handle is a lookup key that may
                change under us.
    unlinked    parsed from the URL alone: (store_domain, handle) is a
                *provisional* identity, and title/price/variants were entered
                by the merchant or imported from CSV. Everything downstream
                works exactly the same.

`reconcile_unlinked_products()` in service.py upgrades unlinked → linked by
handle once credentials arrive, so nothing has to be re-entered and no
garment loses its history. This is what makes the dashboard usable before
the client's Shopify app exists.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# --------------------------------------------------------------------- enums

PRODUCT_SOURCES = ("shopify", "manual", "csv")
LINK_STATES = ("linked", "unlinked")
SYNC_STATES = ("synced", "pending", "error", "never")

GARMENT_CATEGORIES = (
    "dress", "top", "bottom", "outerwear", "knitwear", "swim", "accessory",
)

# The merchant-owned lifecycle. Mirrors data/lifecycle.ts on the dashboard
# so the two cannot disagree about what a stage means.
GARMENT_STAGES = (
    "needs_data",        # being filled in
    "merchant_review",   # merchant checking their own work
    "in_qa",             # with Mirra QA
    "qa_changes",        # QA sent findings back
    "ready",             # QA approved; publishable
    "live",              # published to shoppers
    "paused",            # was live, merchant pulled it
    "sync_error",        # the Shopify link broke
)

CAPTURE_METHODS = ("photo", "phone", "upload", "cad")

# What the ingestion/preview pipeline is doing for this garment.
PIPELINE_STATES = ("idle", "queued", "ingesting", "ingested", "previewing", "preview_ready", "failed")


# ------------------------------------------------------------------ tenants


class ShopifyConnection(BaseModel):
    """What we know about the merchant's store.

    `access_token` is deliberately absent from every API response shape in
    controller.py — it is written here and read only by the Shopify adapter.
    """

    store_domain: str = ""            # atelier-noir.myshopify.com
    custom_domain: str = ""           # ateliernoir.com, if they use one
    access_token: str = ""            # Admin API token; empty = not connected
    scopes: list[str] = []
    connected_at: datetime | None = None
    last_sync_at: datetime | None = None
    last_sync_error: str = ""

    @property
    def connected(self) -> bool:
        return bool(self.store_domain and self.access_token)


class MerchantTenantDocument(BaseModel):
    """The `merchant_tenants` collection doc shape."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    slug: str
    name: str
    store_url: str = ""
    status: Literal["active", "trialing", "suspended", "cancelled"] = "trialing"
    shopify: ShopifyConnection = ShopifyConnection()
    # Users who may act on this tenant, by backend user id → role.
    members: dict[str, str] = {}
    created_at: datetime
    updated_at: datetime

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)


# ----------------------------------------------------------------- products


class ProductVariantModel(BaseModel):
    """One purchasable SKU. `size` and `colour` are the two axes Mirra needs;
    everything else is carried through untouched for the storefront panel."""

    variant_id: str
    sku: str = ""
    title: str = ""               # "Black / S"
    size: str = ""
    colour: str = ""
    price: float = 0.0
    currency: str = "USD"
    inventory: int = 0
    shopify_variant_gid: str = ""


class ProductContent(BaseModel):
    """The shopper-facing copy — the right-hand product panel in the studio.

    Every field is nullable and every field records where it came from, so a
    merchant can see at a glance what Shopify supplied and what Mirra staff
    or they themselves wrote. `source` is per-field because in practice the
    description comes from Shopify while fit notes are written by hand.
    """

    description: str | None = None
    material_and_care: str | None = None
    manufacturing_info: str | None = None
    fit_info: str | None = None
    tax_note: str | None = None
    # field name → "shopify" | "merchant" | "mirra"
    sources: dict[str, str] = {}


class MerchantProductDocument(BaseModel):
    """The `merchant_products` collection doc shape — a Shopify listing."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    tenant_id: str
    source: Literal["shopify", "manual", "csv"] = "manual"
    link_state: Literal["linked", "unlinked"] = "unlinked"

    # --- identity ---
    # Immutable Shopify identity. Empty while unlinked.
    shopify_gid: str = ""
    shopify_numeric_id: str = ""
    # Always present: this is what a pasted URL actually gives us.
    handle: str
    store_domain: str = ""
    online_store_url: str = ""

    # --- content ---
    title: str
    product_type: str = ""
    vendor: str = ""
    option_name: str | None = None     # what this shop calls its colour axis
    image_urls: list[str] = []
    content: ProductContent = ProductContent()
    variants: list[ProductVariantModel] = []

    sync_status: Literal["synced", "pending", "error", "never"] = "never"
    sync_error: str = ""
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)


# ----------------------------------------------------------------- garments


class CaptureAsset(BaseModel):
    """One stored file from the capture step — a real artifact, not a flag.

    The dashboard prototype stored the constant filename "front.jpg" and an
    `accepted: true` (audit P1-01). Everything here is recorded from the
    bytes that actually arrived.
    """

    asset_id: str
    view: str                      # front | back | left | right | detail
    filename: str
    content_type: str
    bytes: int
    sha256: str
    # Relative to the upload root, like avatar/render paths.
    stored_path: str
    width: int | None = None
    height: int | None = None
    accepted: bool = True
    rejected_reason: str = ""
    # The physical sample this frame is of. Pinned per asset so changing the
    # garment's reference size later cannot silently relabel old photos
    # (audit P1-02).
    sample_size: str = ""
    uploaded_by: str = ""
    uploaded_at: datetime


class CaptureSet(BaseModel):
    method: Literal["photo", "phone", "upload", "cad"] = "photo"
    reference_size: str = ""
    assets: list[CaptureAsset] = []
    cad_asset: CaptureAsset | None = None
    issues: list[str] = []


class FabricComponent(BaseModel):
    material: str
    pct: int


class MaterialSpec(BaseModel):
    # Validated on assignment: assigning raw dicts to `composition` used to
    # leave them as dicts, and the failure surfaced far away as an
    # AttributeError while shaping the response.
    model_config = ConfigDict(validate_assignment=True)

    composition: list[FabricComponent] = []
    confirmed: bool = False
    stretch: Literal["none", "low", "moderate", "high"] = "low"
    drape: Literal["structured", "moderate", "fluid"] = "moderate"
    thickness: Literal["light", "mid", "heavy"] = "mid"
    # True while stretch/drape/thickness are Mirra's inference, not a human's.
    attributes_suggested: bool = True


class SizeRow(BaseModel):
    """One graded size, in the pipeline's own field names and units (cm).

    These are exactly `mirra_measurements/size_model.SIZE_MEASUREMENT_FIELDS`,
    so a row maps one-to-one onto a `sizes` document with no translation —
    see pipeline_bridge.py. `hem_width_cm`/`wrist_width_cm` are optional; the
    CLO block derives them from its reference taper ratios when absent
    (product_ingestion/panel_generation_clo.py).
    """

    size: str
    half_chest_width_cm: float | None = None
    garment_length_cm: float | None = None
    shoulder_width_cm: float | None = None
    neck_width_cm: float | None = None
    neck_depth_front_cm: float | None = None
    neck_depth_back_cm: float | None = None
    sleeve_length_cm: float | None = None
    bicep_width_cm: float | None = None
    armhole_depth_cm: float | None = None
    seam_allowance_cm: float | None = 1.0
    hem_width_cm: float | None = None
    wrist_width_cm: float | None = None
    # Which Shopify variant this size is sold as.
    variant_id: str = ""


class SizingSpec(BaseModel):
    fit_type: Literal["slim", "regular", "relaxed", "oversized"] = "regular"
    silhouette: str = ""
    fit_notes: str = ""
    rows: list[SizeRow] = []
    source: Literal["measured", "brand_chart", "estimated"] = "measured"
    variant_mapping_confirmed: bool = False


class PipelineState(BaseModel):
    """Where this garment is in Capture → Ingestion → VTO.

    `cloth_id` and `size_ids` are the join keys into the pipeline's own
    Mongo collections and output folders. They are assigned once, at first
    submission, and never change — a garment's ingestion history has to stay
    findable.
    """

    state: Literal[
        "idle", "queued", "ingesting", "ingested", "previewing", "preview_ready", "failed"
    ] = "idle"
    cloth_id: str = ""
    size_ids: list[str] = []
    ingestion_run_ids: list[str] = []
    # size_id → product_ingestion run id ("c_001-s_001-001")
    ingested_runs: dict[str, str] = {}
    preview_id: str = ""
    failure_reason: str = ""
    updated_at: datetime | None = None


class QaFinding(BaseModel):
    finding_id: str
    severity: Literal["blocking", "advisory"]
    area: str                       # capture | material | sizing | render
    detail: str
    raised_by: str
    raised_at: datetime
    resolved: bool = False


class ApprovedSnapshot(BaseModel):
    """The frozen copy shoppers are served. Never the working draft."""

    revision: int
    approved_at: datetime
    approved_by: str
    category: str
    capture: CaptureSet
    material: MaterialSpec
    sizing: SizingSpec
    content: ProductContent
    # The preview that was approved, so "what QA saw" stays retrievable.
    preview_id: str = ""

    @classmethod
    def freeze(cls, garment: "MerchantGarmentDocument", approved_by: str, at: datetime) -> "ApprovedSnapshot":
        """Take the snapshot. **Always** construct one through this.

        The nested specs are deep-copied. Assigning the garment's own
        `sizing`/`capture`/`material` objects instead would share them with the
        working draft: appending a size to the draft would silently add it to
        the approved revision too, and shoppers would be served a size no
        reviewer ever saw. That is precisely the guarantee approval exists to
        make, so it is enforced here rather than trusted to call sites.
        """
        return cls(
            revision=garment.revision,
            approved_at=at,
            approved_by=approved_by,
            category=garment.category,
            capture=garment.capture.model_copy(deep=True),
            material=garment.material.model_copy(deep=True),
            sizing=garment.sizing.model_copy(deep=True),
            content=garment.content.model_copy(deep=True),
            preview_id=garment.pipeline.preview_id,
        )


class PublicationState(BaseModel):
    published: bool = False
    try_on_enabled: bool = True
    sold_out_policy: Literal["keep_tryon", "hide"] = "keep_tryon"
    published_at: datetime | None = None
    published_by: str = ""


class MerchantGarmentDocument(BaseModel):
    """The `merchant_garments` collection doc shape — one colourway."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    tenant_id: str
    product_id: str
    option_value: str = ""             # the colourway
    canonical_title: str               # Shopify's title, never overwritten
    merchant_title: str = ""
    category: str = "top"

    capture: CaptureSet = CaptureSet()
    material: MaterialSpec = MaterialSpec()
    sizing: SizingSpec = SizingSpec()
    content: ProductContent = ProductContent()
    pipeline: PipelineState = PipelineState()
    publication: PublicationState = PublicationState()

    stage: str = "needs_data"
    revision: int = 1
    qa_findings: list[QaFinding] = []
    approved: ApprovedSnapshot | None = None

    created_at: datetime
    updated_at: datetime
    updated_by: str = ""

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)


# -------------------------------------------------------------- operational


class IngestionRunDocument(BaseModel):
    """The `merchant_ingestion_runs` collection doc shape — one Step 2 run."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    tenant_id: str
    garment_id: str
    cloth_id: str
    size_id: str
    state: Literal["queued", "running", "succeeded", "failed"] = "queued"
    # The pipeline's own run id, "c_001-s_001-001".
    product_run_id: str = ""
    run_dir: str = ""
    panel_count: int = 0
    failure_reason: str = ""
    created_at: datetime
    completed_at: datetime | None = None

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)


class PreviewDocument(BaseModel):
    """The `merchant_previews` collection doc shape — a QA/merchant preview.

    Structurally a try-on render, but rendered against Mirra's **reference
    avatar** rather than a shopper's, and owned by the tenant rather than a
    user. Keeping it in its own collection means a QA preview can never leak
    into a shopper's try-on history.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    tenant_id: str
    garment_id: str
    cloth_id: str
    size_id: str
    revision: int
    avatar_profile_id: str = ""
    state: Literal["requested", "rendering", "ready", "failed"] = "requested"
    failure_reason: str | None = None
    # Relative to the upload root, set by the worker.
    glb_path: str | None = None
    clo_run_id: str | None = None
    requested_by: str = ""
    created_at: datetime
    completed_at: datetime | None = None

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)
