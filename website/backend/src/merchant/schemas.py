"""Merchant request bodies. camelCase on the wire, snake_case inside."""

from pydantic import BaseModel, ConfigDict, Field

_CFG = ConfigDict(populate_by_name=True)


class LookupProductRequest(BaseModel):
    """A pasted storefront URL, product handle, or GID."""

    model_config = _CFG
    input: str = Field(min_length=1, max_length=2048)


class ManualVariantInput(BaseModel):
    model_config = _CFG
    sku: str = ""
    title: str = ""
    size: str = ""
    colour: str = ""
    price: float = 0.0
    currency: str = "USD"
    inventory: int = 0


class CreateManualProductRequest(BaseModel):
    """Everything a URL cannot carry, typed in by the merchant."""

    model_config = _CFG
    handle: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=500)
    online_store_url: str = Field(default="", alias="onlineStoreUrl")
    store_domain: str = Field(default="", alias="storeDomain")
    product_type: str = Field(default="", alias="productType")
    vendor: str = ""
    option_name: str | None = Field(default=None, alias="optionName")
    description: str | None = None
    variants: list[ManualVariantInput]


class ConnectShopifyRequest(BaseModel):
    model_config = _CFG
    store_domain: str = Field(alias="storeDomain", min_length=1)
    access_token: str = Field(alias="accessToken", min_length=1)
    scopes: list[str] = []


class ContentRequest(BaseModel):
    """The shopper-facing product panel copy."""

    model_config = _CFG
    description: str | None = None
    material_and_care: str | None = Field(default=None, alias="materialAndCare")
    manufacturing_info: str | None = Field(default=None, alias="manufacturingInfo")
    fit_info: str | None = Field(default=None, alias="fitInfo")
    tax_note: str | None = Field(default=None, alias="taxNote")


class CreateGarmentRequest(BaseModel):
    model_config = _CFG
    product_id: str = Field(alias="productId", min_length=1)
    option_value: str = Field(default="", alias="optionValue")
    merchant_title: str = Field(default="", alias="merchantTitle")
    category: str = "top"


class ReferenceSizeRequest(BaseModel):
    model_config = _CFG
    size: str = Field(min_length=1, max_length=32)


class RejectAssetRequest(BaseModel):
    model_config = _CFG
    reason: str = Field(min_length=1, max_length=500)


class FabricComponentInput(BaseModel):
    model_config = _CFG
    material: str = Field(min_length=1)
    pct: int = Field(ge=0, le=100)


class MaterialRequest(BaseModel):
    model_config = _CFG
    composition: list[FabricComponentInput] = []
    confirmed: bool = False
    stretch: str | None = None
    drape: str | None = None
    thickness: str | None = None


class SizeRowInput(BaseModel):
    """One graded size, in the pipeline's own field names and cm units."""

    model_config = _CFG
    size: str = Field(min_length=1, max_length=32)
    half_chest_width_cm: float | None = Field(default=None, alias="halfChestWidthCm")
    garment_length_cm: float | None = Field(default=None, alias="garmentLengthCm")
    shoulder_width_cm: float | None = Field(default=None, alias="shoulderWidthCm")
    neck_width_cm: float | None = Field(default=None, alias="neckWidthCm")
    neck_depth_front_cm: float | None = Field(default=None, alias="neckDepthFrontCm")
    neck_depth_back_cm: float | None = Field(default=None, alias="neckDepthBackCm")
    sleeve_length_cm: float | None = Field(default=None, alias="sleeveLengthCm")
    bicep_width_cm: float | None = Field(default=None, alias="bicepWidthCm")
    armhole_depth_cm: float | None = Field(default=None, alias="armholeDepthCm")
    seam_allowance_cm: float | None = Field(default=1.0, alias="seamAllowanceCm")
    hem_width_cm: float | None = Field(default=None, alias="hemWidthCm")
    wrist_width_cm: float | None = Field(default=None, alias="wristWidthCm")
    variant_id: str = Field(default="", alias="variantId")


class SizingRequest(BaseModel):
    model_config = _CFG
    rows: list[SizeRowInput]
    fit_type: str | None = Field(default=None, alias="fitType")
    silhouette: str | None = None
    fit_notes: str | None = Field(default=None, alias="fitNotes")
    source: str | None = None


class ConfirmMappingRequest(BaseModel):
    model_config = _CFG
    confirmed: bool = True


class StageRequest(BaseModel):
    model_config = _CFG
    stage: str = Field(min_length=1)


class QaFindingRequest(BaseModel):
    model_config = _CFG
    severity: str = "blocking"
    area: str = "render"
    detail: str = Field(min_length=1, max_length=2000)


class PublicationRequest(BaseModel):
    model_config = _CFG
    published: bool
    try_on_enabled: bool | None = Field(default=None, alias="tryOnEnabled")


class PreviewRequest(BaseModel):
    model_config = _CFG
    size_id: str | None = Field(default=None, alias="sizeId")
