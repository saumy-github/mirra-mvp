"""Merchant-service tests that need no Mongo, no Redis and no CLO.

Everything here is the logic a client pilot actually depends on being right:
what a pasted URL resolves to, what the pipeline is handed, what a shopper is
allowed to see, and what blocks a submission.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.merchant import pipeline_bridge, publication, service  # noqa: E402
from src.merchant.models import (  # noqa: E402
    ApprovedSnapshot,
    CaptureAsset,
    FabricComponent,
    MerchantGarmentDocument,
    MerchantProductDocument,
    MerchantTenantDocument,
    ProductContent,
    ProductVariantModel,
    SizeRow,
)
from src.merchant.product_source import (  # noqa: E402
    draft_payload_from_ref,
    parse_product_reference,
)


def _now():
    return datetime.now(timezone.utc)


# ------------------------------------------------------------------ identity


@pytest.mark.parametrize(
    "raw,handle,domain,numeric",
    [
        ("https://atelier-noir.com/products/perce-ribbed-tank", "perce-ribbed-tank", "atelier-noir.com", ""),
        ("https://a-n.myshopify.com/products/tank?variant=42", "tank", "a-n.myshopify.com", ""),
        ("https://www.atelier-noir.com/en-gb/products/tank/", "tank", "atelier-noir.com", ""),
        ("atelier-noir.com/products/tank", "tank", "atelier-noir.com", ""),
        ("https://admin.shopify.com/store/x/admin/products/889900", "", "admin.shopify.com", "889900"),
        ("gid://shopify/Product/889900", "", "", "889900"),
        ("889900", "", "", "889900"),
        ("perce-ribbed-tank", "perce-ribbed-tank", "", ""),
    ],
)
def test_every_shape_of_product_reference_parses(raw, handle, domain, numeric):
    ref = parse_product_reference(raw)
    assert ref.handle == handle
    assert ref.store_domain == domain
    assert ref.shopify_numeric_id == numeric
    assert ref.usable


@pytest.mark.parametrize("raw", ["", "   ", "Perce Ribbed Tank", "not a url at all"])
def test_unusable_references_are_rejected_not_guessed(raw):
    assert not parse_product_reference(raw).usable


def test_url_alone_produces_a_completable_draft():
    """The unconnected-store path: a URL is never a dead end."""
    ref = parse_product_reference("https://atelier-noir.com/products/perce-ribbed-tank")
    draft = draft_payload_from_ref(ref)
    assert draft.handle == "perce-ribbed-tank"
    assert draft.link_state == "unlinked"
    assert draft.title == "Perce Ribbed Tank"
    assert draft.online_store_url == "https://atelier-noir.com/products/perce-ribbed-tank"


# ------------------------------------------------------------ pipeline ids


def test_pipeline_ids_are_deterministic_and_dash_free():
    """A dash in either id makes `<cloth>-<size>-<run>` ambiguous to parse."""
    cloth = pipeline_bridge.cloth_id_for("m_g_ab12cd34")
    size = pipeline_bridge.size_id_for("m_g_ab12cd34", "M")
    assert cloth == "c_mgab12cd34"
    assert size == "s_mgab12cd34m"
    assert "-" not in cloth and "-" not in size
    assert cloth == pipeline_bridge.cloth_id_for("m_g_ab12cd34")


def test_pipeline_ids_match_the_run_manifest_patterns():
    from product_ingestion.run_manifest import _CLOTH_RE, _SIZE_RE

    assert _CLOTH_RE.match(pipeline_bridge.cloth_id_for("m_g_ab12"))
    assert _SIZE_RE.match(pipeline_bridge.size_id_for("m_g_ab12", "XL"))


def test_size_row_maps_onto_a_valid_pipeline_size_document():
    """The bridge's output must satisfy the pipeline's own validator."""
    from mirra_measurements.size_model import validate_size_doc

    row = SizeRow(
        size="M",
        half_chest_width_cm=52.0,
        garment_length_cm=71.0,
        shoulder_width_cm=46.0,
        neck_width_cm=18.0,
        neck_depth_front_cm=9.0,
        neck_depth_back_cm=2.5,
        sleeve_length_cm=21.0,
        bicep_width_cm=21.8,
        armhole_depth_cm=24.0,
    )
    doc = pipeline_bridge.size_row_to_size_doc(row, "s_test", "regular")
    ok, reason = validate_size_doc(doc)
    assert ok, reason


def test_taper_fields_are_derived_at_the_clo_reference_ratio():
    """Must agree exactly with size_model's own derivation, not approximately."""
    from mirra_measurements.size_model import derive_hem_width_cm, derive_wrist_width_cm

    row = SizeRow(size="M", half_chest_width_cm=52.0, bicep_width_cm=21.8)
    doc = pipeline_bridge.size_row_to_size_doc(row, "s_test", "regular")
    assert doc["hem_width_cm"] == derive_hem_width_cm(52.0)
    assert doc["wrist_width_cm"] == derive_wrist_width_cm(21.8)


def test_measured_taper_overrides_the_derived_one():
    row = SizeRow(size="M", half_chest_width_cm=52.0, bicep_width_cm=21.8, hem_width_cm=49.0)
    doc = pipeline_bridge.size_row_to_size_doc(row, "s_test", "regular")
    assert doc["hem_width_cm"] == 49.0


# ------------------------------------------------------------- capability


def _garment(**overrides) -> MerchantGarmentDocument:
    now = _now()
    g = MerchantGarmentDocument(
        _id="m_g_test",
        tenant_id="m_t_test",
        product_id="m_p_test",
        option_value="Black",
        canonical_title="Percé Ribbed Tank",
        category="top",
        created_at=now,
        updated_at=now,
    )
    g.capture.reference_size = "M"
    g.capture.assets = [
        CaptureAsset(
            asset_id="cap_1", view="front", filename="front.jpg", content_type="image/jpeg",
            bytes=1024, sha256="x" * 64, stored_path="captures/t/g/cap_1.jpg",
            sample_size="M", uploaded_at=now,
        )
    ]
    g.sizing.rows = [
        SizeRow(
            size="M", half_chest_width_cm=52.0, garment_length_cm=71.0,
            shoulder_width_cm=46.0, armhole_depth_cm=24.0, bicep_width_cm=21.8,
            neck_width_cm=18.0, neck_depth_front_cm=9.0, neck_depth_back_cm=2.5,
            sleeve_length_cm=21.0,
        )
    ]
    g.pipeline.cloth_id = pipeline_bridge.cloth_id_for(g.id)
    g.pipeline.size_ids = [pipeline_bridge.size_id_for(g.id, "M")]
    for key, value in overrides.items():
        setattr(g, key, value)
    return g


def test_a_complete_top_passes_the_capability_gate():
    assert pipeline_bridge.check_pipeline_capability(_garment()).ok


def test_categories_the_pipeline_cannot_draft_are_refused_not_faked():
    """Audit P0-03: the engine drafts a t-shirt block and nothing else."""
    verdict = pipeline_bridge.check_pipeline_capability(_garment(category="dress"))
    assert not verdict.ok
    assert "dress" in verdict.reason


def test_capture_without_a_front_view_is_refused():
    g = _garment()
    g.capture.assets[0].view = "back"
    verdict = pipeline_bridge.check_pipeline_capability(g)
    assert not verdict.ok
    assert "front view" in verdict.reason


def test_a_size_missing_a_load_bearing_measurement_is_refused():
    g = _garment()
    g.sizing.rows[0].armhole_depth_cm = None
    verdict = pipeline_bridge.check_pipeline_capability(g)
    assert not verdict.ok
    assert "armhole_depth_cm" in verdict.reason


# -------------------------------------------------------------- publication


def _tenant() -> MerchantTenantDocument:
    now = _now()
    return MerchantTenantDocument(
        _id="m_t_test", slug="atelier-noir", name="Atelier Noir",
        status="active", created_at=now, updated_at=now,
    )


def _product() -> MerchantProductDocument:
    now = _now()
    return MerchantProductDocument(
        _id="m_p_test", tenant_id="m_t_test", handle="perce-ribbed-tank",
        title="Percé Ribbed Tank", link_state="linked", product_type="Tops",
        variants=[
            ProductVariantModel(
                variant_id="v1", sku="PRT-BLK-M", size="M", colour="Black",
                price=120.0, inventory=4,
            )
        ],
        created_at=now, updated_at=now,
    )


def _approved(g: MerchantGarmentDocument) -> MerchantGarmentDocument:
    # Through freeze(), so the tests exercise the real snapshot semantics.
    g.approved = ApprovedSnapshot.freeze(g, "u_qa", _now())
    g.stage = "live"
    g.publication.published = True
    return g


def test_a_live_approved_garment_with_an_asset_is_visible():
    resolved = publication.resolve_garment(
        _approved(_garment()), _tenant(), _product(), asset_available=True
    )
    assert resolved.visible
    assert [v.size for v in resolved.variants] == ["M"]


def test_nothing_serves_without_a_rendered_asset():
    """The rule the audit was written to protect: never claim an asset exists."""
    resolved = publication.resolve_garment(
        _approved(_garment()), _tenant(), _product(), asset_available=False
    )
    assert not resolved.visible
    assert resolved.blocked_reason == "no_asset"


def test_nothing_serves_without_qa_approval():
    g = _garment()
    g.stage = "live"
    resolved = publication.resolve_garment(g, _tenant(), _product(), asset_available=True)
    assert not resolved.visible
    assert resolved.blocked_reason == "not_approved"


def test_a_suspended_workspace_serves_nothing():
    tenant = _tenant()
    tenant.status = "suspended"
    resolved = publication.resolve_garment(
        _approved(_garment()), tenant, _product(), asset_available=True
    )
    assert not resolved.visible
    assert resolved.blocked_reason == "tenant_inactive"


def test_a_size_added_after_approval_is_not_served():
    """Shoppers get the frozen snapshot, never the working draft."""
    g = _approved(_garment())
    g.sizing.rows.append(SizeRow(size="L", half_chest_width_cm=55.0))
    product = _product()
    product.variants.append(
        ProductVariantModel(variant_id="v2", sku="PRT-BLK-L", size="L", colour="Black",
                            price=120.0, inventory=2)
    )
    resolved = publication.resolve_garment(g, _tenant(), product, asset_available=True)
    assert [v.size for v in resolved.variants] == ["M"]


def test_sold_out_sizes_stay_try_on_able_under_the_default_policy():
    g = _approved(_garment())
    product = _product()
    product.variants[0].inventory = 0
    resolved = publication.resolve_garment(g, _tenant(), product, asset_available=True)
    assert resolved.visible
    assert resolved.variants[0].in_stock is False
    assert resolved.variants[0].try_on_eligible is True


def test_hide_policy_removes_a_sold_out_size_entirely():
    g = _approved(_garment())
    g.publication.sold_out_policy = "hide"
    product = _product()
    product.variants[0].inventory = 0
    resolved = publication.resolve_garment(g, _tenant(), product, asset_available=True)
    assert not resolved.visible
    assert resolved.blocked_reason == "no_purchasable_variant"


def test_draft_ahead_of_approved_revision_is_reported():
    g = _approved(_garment())
    g.revision += 1
    resolved = publication.resolve_garment(g, _tenant(), _product(), asset_available=True)
    assert resolved.draft_ahead


# --------------------------------------------------------- public product


def test_public_product_carries_the_join_keys_a_try_on_needs():
    g = _approved(_garment())
    resolved = publication.resolve_garment(g, _tenant(), _product(), asset_available=True)
    out = publication.public_product(
        g, _tenant(), _product(), resolved, asset_url="/api/v1/merchant/t/previews/p/glb"
    )
    variant = out["variants"][0]
    assert variant["clothId"] == g.pipeline.cloth_id
    assert variant["sizeId"] == g.pipeline.size_ids[0]
    assert variant["assetStatus"] == "ready"


def test_public_product_never_invents_copy_it_does_not_have():
    g = _approved(_garment())
    resolved = publication.resolve_garment(g, _tenant(), _product(), asset_available=True)
    out = publication.public_product(g, _tenant(), _product(), resolved, asset_url="/x")
    assert out["description"] is None
    assert out["manufacturingInfo"] is None


def test_garment_copy_overrides_product_copy_and_records_the_source():
    g = _approved(_garment())
    g.content.description = "Cut from deadstock silk."
    g.content.sources = {"description": "merchant"}
    product = _product()
    product.content = ProductContent(
        description="The Percé tank.", sources={"description": "shopify"}
    )
    resolved = publication.resolve_garment(g, _tenant(), product, asset_available=True)
    out = publication.public_product(g, _tenant(), product, resolved, asset_url="/x")
    assert out["description"] == "Cut from deadstock silk."
    assert out["contentSources"]["description"] == "merchant"


def test_product_copy_is_inherited_when_the_garment_has_none():
    g = _approved(_garment())
    product = _product()
    product.content = ProductContent(
        description="The Percé tank.", sources={"description": "shopify"}
    )
    resolved = publication.resolve_garment(g, _tenant(), product, asset_available=True)
    out = publication.public_product(g, _tenant(), product, resolved, asset_url="/x")
    assert out["description"] == "The Percé tank."
    assert out["contentSources"]["description"] == "shopify"


def test_price_is_the_cheapest_purchasable_variant():
    g = _approved(_garment())
    g.approved.sizing.rows.append(SizeRow(size="L", half_chest_width_cm=55.0))
    product = _product()
    product.variants.append(
        ProductVariantModel(variant_id="v2", sku="L", size="L", colour="Black",
                            price=95.0, inventory=1)
    )
    resolved = publication.resolve_garment(g, _tenant(), product, asset_available=True)
    out = publication.public_product(g, _tenant(), product, resolved, asset_url="/x")
    assert out["price"] == 95.0


def test_material_and_care_falls_back_only_to_a_confirmed_composition():
    g = _approved(_garment())
    g.approved.material.composition = [FabricComponent(material="Cotton", pct=100)]
    g.approved.material.confirmed = False
    resolved = publication.resolve_garment(g, _tenant(), _product(), asset_available=True)
    out = publication.public_product(g, _tenant(), _product(), resolved, asset_url="/x")
    assert out["materialAndCare"] is None

    g.approved.material.confirmed = True
    out = publication.public_product(g, _tenant(), _product(), resolved, asset_url="/x")
    assert out["materialAndCare"] == "100% Cotton"


# ---------------------------------------------------------------- readiness


def test_readiness_blocks_on_an_unconfirmed_variant_mapping():
    g = _garment()
    g.material.composition = [FabricComponent(material="Cotton", pct=100)]
    issues = service.review_issues(g, _product())
    assert not issues["ready"]
    assert any(i["label"] == "Variant mapping" for i in issues["blocking"])


def test_readiness_passes_once_everything_is_recorded():
    g = _garment()
    g.material.composition = [FabricComponent(material="Cotton", pct=100)]
    g.sizing.variant_mapping_confirmed = True
    issues = service.review_issues(g, _product())
    assert issues["ready"], issues["blocking"]


def test_an_unlinked_product_is_advisory_not_blocking():
    """A workspace with no Shopify store must still be able to finish a garment."""
    g = _garment()
    g.material.composition = [FabricComponent(material="Cotton", pct=100)]
    g.sizing.variant_mapping_confirmed = True
    product = _product()
    product.link_state = "unlinked"
    issues = service.review_issues(g, product)
    assert issues["ready"]
    assert any(i["label"] == "Product not linked to Shopify" for i in issues["advisory"])


def test_a_size_with_no_shopify_variant_blocks():
    g = _garment()
    g.material.composition = [FabricComponent(material="Cotton", pct=100)]
    g.sizing.variant_mapping_confirmed = True
    g.sizing.rows.append(SizeRow(size="XXL", half_chest_width_cm=60.0, garment_length_cm=75.0,
                                 shoulder_width_cm=50.0, armhole_depth_cm=26.0))
    issues = service.review_issues(g, _product())
    assert not issues["ready"]
    assert any(i["label"] == "Unmatched sizes" for i in issues["blocking"])


# ------------------------------------------------------------- transitions


def test_the_stage_machine_forbids_skipping_merchant_review():
    assert "in_qa" not in service.ALLOWED_TRANSITIONS["needs_data"]
    assert "in_qa" in service.ALLOWED_TRANSITIONS["merchant_review"]


def test_only_qa_roles_can_review():
    assert "qa.review" in service.ROLE_PERMISSIONS["qa"]
    assert "qa.review" not in service.ROLE_PERMISSIONS["editor"]
    assert "catalogue.publish" not in service.ROLE_PERMISSIONS["editor"]
    assert service.ROLE_PERMISSIONS["viewer"] == set()
