"""End-to-end exercise of the merchant HTTP surface, without a database.

The point of these is the journey the client will actually take on day one:
paste a URL for a store that is not connected, and still get all the way to a
garment that the pipeline agrees it can process. That path used to end at an
error message.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from tests.fake_mongo import FakeDb  # noqa: E402

TENANT = "m_t_atelier"
USER = "u_owner"


@pytest.fixture
def env(monkeypatch, tmp_path):
    """An app with fake collections, a temp upload root and no live queue."""
    import src.merchant.engine as engine
    import src.merchant.service as service
    import src.merchant.storage as storage
    import src.merchant.pipeline_bridge as bridge
    from src.config import Settings, get_settings
    from src.core.auth_dependency import Identity, get_identity
    from src.main import create_app

    fake = FakeDb().install(monkeypatch)

    # Uploads and pipeline inputs go to a temp tree, never the real repo.
    settings = Settings(app_env="development")
    monkeypatch.setattr(
        type(settings), "avatars_upload_root", property(lambda _s: tmp_path / "upload")
    )
    monkeypatch.setattr(storage, "get_settings", lambda: settings)
    monkeypatch.setattr(bridge, "get_settings", lambda: settings)
    monkeypatch.setattr(bridge, "INGESTION_INPUT_ROOT", tmp_path / "ingestion_input")

    # The queue is a separate concern; assert it was asked, don't run it.
    queued: list[tuple[str, str]] = []
    monkeypatch.setattr(engine, "start_ingestion", lambda rid: queued.append(("ingest", rid)))
    monkeypatch.setattr(engine, "start_preview", lambda pid: queued.append(("preview", pid)))
    monkeypatch.setattr(service.engine, "start_ingestion", engine.start_ingestion)
    monkeypatch.setattr(service.engine, "start_preview", engine.start_preview)

    now = datetime.now(timezone.utc)
    fake.col("merchant_tenants_col").docs.append(
        {
            "_id": TENANT, "slug": "atelier-noir", "name": "Atelier Noir",
            "store_url": "", "status": "active",
            "shopify": {
                "store_domain": "", "custom_domain": "", "access_token": "",
                "scopes": [], "connected_at": None, "last_sync_at": None,
                "last_sync_error": "",
            },
            "members": {USER: "owner"}, "created_at": now, "updated_at": now,
        }
    )

    app = create_app()
    app.dependency_overrides[get_identity] = lambda: Identity(user_id=USER, kind="user")
    client = TestClient(app)
    client.fake = fake
    client.queued = queued
    return client


def _png(size: int = 900) -> bytes:
    """A real PNG big enough to pass the short-edge check."""
    from PIL import Image
    import io

    buf = io.BytesIO()
    Image.new("RGB", (size, size), (30, 30, 30)).save(buf, format="PNG")
    return buf.getvalue()


# ------------------------------------------------------- the blocked journey


def test_lookup_without_a_connected_store_returns_a_completable_draft(env):
    """The exact case that used to dead-end the Add-garment screen."""
    r = env.post(
        f"/api/v1/merchant/{TENANT}/products/lookup",
        json={"input": "https://atelier-noir.com/products/perce-ribbed-tank"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["outcome"] == "draft"
    assert body["storeConnected"] is False
    assert body["draft"]["handle"] == "perce-ribbed-tank"
    assert body["draft"]["suggestedTitle"] == "Perce Ribbed Tank"
    assert body["draft"]["storeDomain"] == "atelier-noir.com"
    assert "no shopify store is connected" in body["guidance"].lower()


def test_gibberish_is_still_rejected(env):
    r = env.post(f"/api/v1/merchant/{TENANT}/products/lookup", json={"input": "hello there"})
    assert r.status_code == 422
    assert "shopify product link" in r.json()["error"]["message"].lower()


def test_a_hand_entered_product_is_found_by_the_same_url_next_time(env):
    env.post(
        f"/api/v1/merchant/{TENANT}/products",
        json={
            "handle": "perce-ribbed-tank", "title": "Percé Ribbed Tank",
            "variants": [{"size": "M", "colour": "Black", "price": 120}],
        },
    ).raise_for_status()

    r = env.post(
        f"/api/v1/merchant/{TENANT}/products/lookup",
        json={"input": "https://atelier-noir.com/products/perce-ribbed-tank"},
    )
    assert r.json()["outcome"] == "matched"
    assert r.json()["product"]["title"] == "Percé Ribbed Tank"


def test_a_duplicate_handle_is_refused(env):
    body = {
        "handle": "tank", "title": "Tank",
        "variants": [{"size": "M", "price": 10}],
    }
    env.post(f"/api/v1/merchant/{TENANT}/products", json=body).raise_for_status()
    r = env.post(f"/api/v1/merchant/{TENANT}/products", json=body)
    assert r.status_code == 409


# ------------------------------------------------------------- full journey


def _make_garment(env) -> str:
    env.post(
        f"/api/v1/merchant/{TENANT}/products",
        json={
            "handle": "perce-ribbed-tank", "title": "Percé Ribbed Tank",
            "optionName": "Colour",
            "variants": [
                {"size": "M", "colour": "Black", "price": 120, "sku": "PRT-BLK-M"},
            ],
        },
    ).raise_for_status()
    product_id = env.get(f"/api/v1/merchant/{TENANT}/products").json()["items"][0]["productId"]
    r = env.post(
        f"/api/v1/merchant/{TENANT}/garments",
        json={"productId": product_id, "optionValue": "Black", "category": "top"},
    )
    assert r.status_code == 201, r.text
    return r.json()["garment"]["garmentId"]


def test_a_garment_gets_a_stable_dash_free_cloth_id_at_creation(env):
    gid = _make_garment(env)
    g = env.get(f"/api/v1/merchant/{TENANT}/garments/{gid}").json()["garment"]
    cloth_id = g["pipeline"]["clothId"]
    assert cloth_id.startswith("c_") and "-" not in cloth_id


def test_capture_upload_stores_real_bytes_and_records_the_checksum(env):
    import hashlib

    gid = _make_garment(env)
    env.put(f"/api/v1/merchant/{TENANT}/garments/{gid}/reference-size", json={"size": "M"}).raise_for_status()

    data = _png()
    r = env.post(
        f"/api/v1/merchant/{TENANT}/garments/{gid}/capture",
        files={"file": ("front.png", data, "image/png")},
        data={"view": "front"},
    )
    assert r.status_code == 201, r.text
    asset = r.json()["garment"]["capture"]["assets"][0]
    assert asset["sha256"] == hashlib.sha256(data).hexdigest()
    assert asset["bytes"] == len(data)
    assert asset["width"] == 900
    assert asset["sampleSize"] == "M"

    # And it comes back out again.
    got = env.get(f"/api/v1/merchant/{TENANT}/garments/{gid}/capture/{asset['assetId']}")
    assert got.status_code == 200
    assert got.content == data


def test_capture_is_blocked_until_the_sample_size_is_named(env):
    gid = _make_garment(env)
    r = env.post(
        f"/api/v1/merchant/{TENANT}/garments/{gid}/capture",
        files={"file": ("front.png", _png(), "image/png")},
        data={"view": "front"},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "reference_size_required"


def test_a_too_small_image_is_refused_with_a_usable_reason(env):
    gid = _make_garment(env)
    env.put(f"/api/v1/merchant/{TENANT}/garments/{gid}/reference-size", json={"size": "M"})
    r = env.post(
        f"/api/v1/merchant/{TENANT}/garments/{gid}/capture",
        files={"file": ("tiny.png", _png(64), "image/png")},
        data={"view": "front"},
    )
    assert r.status_code == 422
    assert "640px" in r.json()["error"]["message"]


def test_heic_is_refused_with_the_fix_rather_than_a_format_list(env):
    gid = _make_garment(env)
    env.put(f"/api/v1/merchant/{TENANT}/garments/{gid}/reference-size", json={"size": "M"})
    r = env.post(
        f"/api/v1/merchant/{TENANT}/garments/{gid}/capture",
        files={"file": ("IMG_1.heic", b"x" * 5000, "image/heic")},
        data={"view": "front"},
    )
    assert r.status_code == 422
    assert "Most Compatible" in r.json()["error"]["message"]


def _complete(env, gid: str) -> dict:
    env.put(f"/api/v1/merchant/{TENANT}/garments/{gid}/reference-size", json={"size": "M"})
    env.post(
        f"/api/v1/merchant/{TENANT}/garments/{gid}/capture",
        files={"file": ("front.png", _png(), "image/png")},
        data={"view": "front"},
    ).raise_for_status()
    env.put(
        f"/api/v1/merchant/{TENANT}/garments/{gid}/sizing",
        json={
            "rows": [
                {
                    "size": "M", "halfChestWidthCm": 52.0, "garmentLengthCm": 71.0,
                    "shoulderWidthCm": 46.0, "neckWidthCm": 18.0,
                    "neckDepthFrontCm": 9.0, "neckDepthBackCm": 2.5,
                    "sleeveLengthCm": 21.0, "bicepWidthCm": 21.8, "armholeDepthCm": 24.0,
                }
            ],
            "fitType": "regular",
        },
    ).raise_for_status()
    env.put(
        f"/api/v1/merchant/{TENANT}/garments/{gid}/material",
        json={"composition": [{"material": "Cotton", "pct": 100}], "confirmed": True},
    ).raise_for_status()
    env.put(f"/api/v1/merchant/{TENANT}/garments/{gid}/variant-mapping", json={"confirmed": True})
    return env.get(f"/api/v1/merchant/{TENANT}/garments/{gid}").json()["garment"]


def test_a_complete_garment_reports_itself_ready(env):
    g = _complete(env, _make_garment(env))
    assert g["readiness"]["ready"], g["readiness"]["blocking"]
    assert g["pipeline"]["supported"]


def test_an_unlinked_product_is_flagged_but_does_not_block(env):
    g = _complete(env, _make_garment(env))
    assert any(a["label"] == "Product not linked to Shopify" for a in g["readiness"]["advisory"])


def test_submitting_writes_the_pipeline_documents_and_queues_a_run(env):
    gid = _make_garment(env)
    _complete(env, gid)

    r = env.post(f"/api/v1/merchant/{TENANT}/garments/{gid}/ingestion")
    assert r.status_code == 202, r.text
    runs = r.json()["runs"]
    assert len(runs) == 1
    assert runs[0]["state"] == "queued"

    # The pipeline's own collections were written, in its own schema.
    sizes = env.fake.col("sizes_col").docs
    cloths = env.fake.col("cloths_col").docs
    assert len(sizes) == 1 and len(cloths) == 1
    assert sizes[0]["half_chest_width_cm"] == 52.0
    assert cloths[0]["size_ids"] == [sizes[0]["size_id"]]

    # And the capture image was staged where product_ingestion looks for it.
    from src.merchant import pipeline_bridge

    staged = pipeline_bridge.INGESTION_INPUT_ROOT / cloths[0]["cloth_id"]
    assert sorted(p.name for p in staged.iterdir()) == ["image_1.png"]

    assert ("ingest", runs[0]["runId"]) in env.queued


def test_an_unsupported_category_is_refused_before_anything_is_queued(env):
    gid = _make_garment(env)
    _complete(env, gid)
    env.fake.col("merchant_garments_col").docs[0]["category"] = "dress"

    r = env.post(f"/api/v1/merchant/{TENANT}/garments/{gid}/ingestion")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "pipeline_unsupported"
    assert env.queued == []


def test_a_preview_cannot_be_requested_before_panels_exist(env):
    gid = _make_garment(env)
    _complete(env, gid)
    r = env.post(f"/api/v1/merchant/{TENANT}/garments/{gid}/previews", json={})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "ingestion_required"


def test_a_preview_is_queued_once_a_run_has_completed(env):
    gid = _make_garment(env)
    g = _complete(env, gid)
    size_id = g["pipeline"]["sizeIds"][0]
    # Stand in for the worker having finished.
    env.fake.col("merchant_garments_col").docs[0]["pipeline"]["ingested_runs"] = {
        size_id: f"{g['pipeline']['clothId']}-{size_id}-001"
    }

    r = env.post(f"/api/v1/merchant/{TENANT}/garments/{gid}/previews", json={})
    assert r.status_code == 202, r.text
    preview = r.json()["preview"]
    assert preview["state"] == "requested"
    assert preview["hasModel"] is False
    assert preview["glbUrl"] is None
    assert ("preview", preview["previewId"]) in env.queued


def test_a_preview_with_no_file_refuses_to_serve_a_model(env):
    gid = _make_garment(env)
    g = _complete(env, gid)
    size_id = g["pipeline"]["sizeIds"][0]
    env.fake.col("merchant_garments_col").docs[0]["pipeline"]["ingested_runs"] = {size_id: "x-y-001"}
    pid = env.post(f"/api/v1/merchant/{TENANT}/garments/{gid}/previews", json={}).json()["preview"]["previewId"]

    r = env.get(f"/api/v1/merchant/{TENANT}/previews/{pid}/glb")
    assert r.status_code == 404
    assert "has been rendered" in r.json()["error"]["message"]


# -------------------------------------------------------------- lifecycle


def test_the_lifecycle_cannot_skip_merchant_review(env):
    gid = _make_garment(env)
    _complete(env, gid)
    r = env.put(f"/api/v1/merchant/{TENANT}/garments/{gid}/stage", json={"stage": "in_qa"})
    assert r.status_code == 409
    assert "cannot move to 'in_qa'" in r.json()["error"]["message"]


def test_review_is_refused_while_something_still_blocks(env):
    gid = _make_garment(env)  # nothing filled in
    r = env.put(f"/api/v1/merchant/{TENANT}/garments/{gid}/stage", json={"stage": "merchant_review"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "not_ready"


def test_approval_freezes_the_revision_and_publishing_needs_it(env):
    gid = _make_garment(env)
    _complete(env, gid)
    env.put(f"/api/v1/merchant/{TENANT}/garments/{gid}/stage", json={"stage": "merchant_review"}).raise_for_status()
    env.put(f"/api/v1/merchant/{TENANT}/garments/{gid}/stage", json={"stage": "in_qa"}).raise_for_status()

    r = env.post(f"/api/v1/merchant/{TENANT}/garments/{gid}/qa/approve")
    assert r.status_code == 200, r.text
    g = r.json()["garment"]
    assert g["stage"] == "ready"
    assert g["approved"]["revision"] == g["revision"]
    assert g["draftAhead"] is False

    # An edit after approval must not reach shoppers on its own.
    env.patch(f"/api/v1/merchant/{TENANT}/garments/{gid}/content", json={"description": "New copy"})
    g = env.get(f"/api/v1/merchant/{TENANT}/garments/{gid}").json()["garment"]
    assert g["draftAhead"] is True


def test_publishing_an_unapproved_garment_is_refused(env):
    gid = _make_garment(env)
    _complete(env, gid)
    r = env.put(f"/api/v1/merchant/{TENANT}/garments/{gid}/publication", json={"published": True})
    assert r.status_code == 409
    assert "QA-approved" in r.json()["error"]["message"]


def test_the_catalogue_serves_nothing_without_a_rendered_asset(env):
    """A published garment with no GLB is still not shopper-visible."""
    gid = _make_garment(env)
    _complete(env, gid)
    env.put(f"/api/v1/merchant/{TENANT}/garments/{gid}/stage", json={"stage": "merchant_review"})
    env.put(f"/api/v1/merchant/{TENANT}/garments/{gid}/stage", json={"stage": "in_qa"})
    env.post(f"/api/v1/merchant/{TENANT}/garments/{gid}/qa/approve")
    env.put(f"/api/v1/merchant/{TENANT}/garments/{gid}/publication", json={"published": True})

    live = env.get(f"/api/v1/merchant/{TENANT}/catalogue").json()["items"]
    assert live == []

    # But QA/merchant preview does show it, marked as a preview.
    previewed = env.get(f"/api/v1/merchant/{TENANT}/catalogue?preview=true").json()["items"]
    assert len(previewed) == 1
    assert previewed[0]["publicationStatus"] == "preview"
    assert previewed[0]["name"] == "Percé Ribbed Tank"
    assert previewed[0]["variants"][0]["assetStatus"] == "missing"


# ------------------------------------------------------------ authorization


def test_a_non_member_cannot_see_the_workspace_exists(env):
    from src.core.auth_dependency import Identity, get_identity

    env.app.dependency_overrides[get_identity] = lambda: Identity(user_id="u_stranger", kind="user")
    r = env.get(f"/api/v1/merchant/{TENANT}/garments")
    assert r.status_code == 404


def test_a_viewer_cannot_edit(env):
    from src.core.auth_dependency import Identity, get_identity

    env.fake.col("merchant_tenants_col").docs[0]["members"]["u_viewer"] = "viewer"
    env.app.dependency_overrides[get_identity] = lambda: Identity(user_id="u_viewer", kind="user")
    r = env.post(
        f"/api/v1/merchant/{TENANT}/products",
        json={"handle": "x", "title": "X", "variants": [{"size": "M"}]},
    )
    assert r.status_code == 403


def test_the_access_token_is_never_serialised(env):
    shopify = env.fake.col("merchant_tenants_col").docs[0]["shopify"]
    shopify["store_domain"] = "atelier-noir.myshopify.com"
    shopify["access_token"] = "shpat_secret"
    body = env.get(f"/api/v1/merchant/{TENANT}").json()
    assert body["workspace"]["shopify"]["connected"] is True
    assert "shpat_secret" not in env.get(f"/api/v1/merchant/{TENANT}").text


# ------------------------------------------------- shopper catalogue gating


def test_a_submitted_garment_reaches_shoppers_only_once_live(env):
    """Submitting writes `cloths`/`sizes` (the pipeline needs them), but the
    shopper catalogue and try-on must not serve the garment until QA has
    approved it, it is live, and a rendered asset exists."""
    from datetime import datetime, timezone

    from src.merchant.models import ApprovedSnapshot, MerchantGarmentDocument

    # A seeded, non-merchant cloth keeps showing throughout.
    env.fake.col("cloths_col").docs.append(
        {"cloth_id": "c_001", "label": "Basic Tee", "category": "top", "size_ids": ["s_001"], "brand_id": None}
    )
    env.fake.col("sizes_col").docs.append({"size_id": "s_001", "fit_type": "regular"})

    gid = _make_garment(env)
    _complete(env, gid)
    env.post(f"/api/v1/merchant/{TENANT}/garments/{gid}/ingestion").raise_for_status()
    cloth = next(c for c in env.fake.col("cloths_col").docs if c.get("brand_id"))
    size_id = cloth["size_ids"][0]

    def shopper_ids():
        return [c["clothId"] for c in env.get("/api/v1/catalog/garments").json()["items"]]

    assert shopper_ids() == ["c_001"]
    assert env.get("/api/v1/catalog/garments").json()["total"] == 1
    assert env.get(f"/api/v1/catalog/garments/{cloth['cloth_id']}").status_code == 404

    # Stand in for QA approval, publication and the preview render finishing.
    now = datetime.now(timezone.utc)
    raw = env.fake.col("merchant_garments_col").docs[0]
    garment = MerchantGarmentDocument.model_validate(raw)
    raw["approved"] = ApprovedSnapshot.freeze(garment, "u_qa", now).model_dump()
    raw["stage"] = "live"
    env.fake.col("merchant_previews_col").docs.append(
        {"_id": "mp_1", "tenant_id": TENANT, "garment_id": gid, "cloth_id": cloth["cloth_id"],
         "size_id": size_id, "revision": garment.revision, "state": "ready",
         "glb_path": "previews/mp_1.glb", "created_at": now}
    )

    assert sorted(shopper_ids()) == sorted(["c_001", cloth["cloth_id"]])
    served = env.get(f"/api/v1/catalog/garments/{cloth['cloth_id']}").json()["garment"]
    assert [s["sizeId"] for s in served["sizes"]] == [size_id]

    # Pausing takes it back out.
    raw["stage"] = "paused"
    assert shopper_ids() == ["c_001"]


# --------------------------------------------------- workspace provisioning


@pytest.fixture
def fresh(env):
    """The same app, but the signed-in user belongs to no workspace yet."""
    from src.core.auth_dependency import Identity, get_identity

    who = {"user": "u_new_brand", "kind": "user"}
    env.app.dependency_overrides[get_identity] = lambda: Identity(user_id=who["user"], kind=who["kind"])
    env.who = who
    return env


def test_a_business_account_creates_its_workspace_and_owns_it(fresh):
    assert fresh.get("/api/v1/merchant/workspaces").json()["items"] == []
    r = fresh.post("/api/v1/merchant/workspaces", json={"name": "Maison Lune", "storeUrl": "https://maisonlune.com"})
    assert r.status_code == 201, r.text
    ws = r.json()["workspace"]
    assert ws["slug"] == "maison-lune" and ws["role"] == "owner" and ws["status"] == "trialing"
    assert ws["shopify"]["connected"] is False

    listed = fresh.get("/api/v1/merchant/workspaces").json()["items"]
    assert [w["tenantId"] for w in listed] == [ws["tenantId"]] and listed[0]["role"] == "owner"
    # The rest of the merchant surface now works for this account.
    r = fresh.post(
        f"/api/v1/merchant/{ws['tenantId']}/products",
        json={"handle": "lune-slip", "title": "Lune Slip", "variants": [{"size": "S", "price": 90}]},
    )
    assert r.status_code == 201, r.text


def test_workspace_rules(fresh):
    fresh.who["kind"] = "guest"
    assert fresh.post("/api/v1/merchant/workspaces", json={"name": "Guest Co"}).status_code == 403
    fresh.who["kind"] = "user"
    assert fresh.post("/api/v1/merchant/workspaces", json={"name": "Atelier Noir"}).status_code == 201
    # slug collision with the seeded tenant gets a suffix; a second workspace is refused
    assert fresh.fake.col("merchant_tenants_col").docs[-1]["slug"] == "atelier-noir-2"
    assert fresh.post("/api/v1/merchant/workspaces", json={"name": "Another"}).status_code == 409


def test_an_owner_seats_an_existing_account(env):
    env.fake.col("users_col").docs.append({"_id": "u_colleague", "email": "sam@atelier.com", "is_guest": False})
    r = env.post(f"/api/v1/merchant/{TENANT}/members", json={"email": "Sam@Atelier.com", "role": "editor"})
    assert r.status_code == 200, r.text
    tenant = env.fake.col("merchant_tenants_col").docs[0]
    assert tenant["members"]["u_colleague"] == "editor"

    unknown = env.post(f"/api/v1/merchant/{TENANT}/members", json={"email": "nobody@x.com", "role": "viewer"})
    assert unknown.status_code == 404
    owner = env.post(f"/api/v1/merchant/{TENANT}/members", json={"email": "x", "role": "owner"})
    assert owner.status_code == 422  # owner is not grantable


def test_an_editor_cannot_seat_people(env):
    env.fake.col("merchant_tenants_col").docs[0]["members"][USER] = "editor"
    env.fake.col("users_col").docs.append({"_id": "u_colleague", "email": "sam@atelier.com", "is_guest": False})
    r = env.post(f"/api/v1/merchant/{TENANT}/members", json={"email": "sam@atelier.com", "role": "viewer"})
    assert r.status_code == 403


def _to_qa(env, gid):
    _complete(env, gid)
    env.put(f"/api/v1/merchant/{TENANT}/garments/{gid}/stage", json={"stage": "merchant_review"}).raise_for_status()
    env.put(f"/api/v1/merchant/{TENANT}/garments/{gid}/stage", json={"stage": "in_qa"}).raise_for_status()


def test_ready_cannot_be_reached_without_approval(env):
    gid = _make_garment(env)
    _to_qa(env, gid)
    r = env.put(f"/api/v1/merchant/{TENANT}/garments/{gid}/stage", json={"stage": "ready"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "use_approve"


def test_a_resolved_blocking_finding_no_longer_blocks_approval(env):
    gid = _make_garment(env)
    _to_qa(env, gid)
    g = env.post(
        f"/api/v1/merchant/{TENANT}/garments/{gid}/qa/findings",
        json={"severity": "blocking", "area": "render", "detail": "Hem clips the hip"},
    ).json()["garment"]
    fid = g["qaFindings"][0]["findingId"]
    assert env.post(f"/api/v1/merchant/{TENANT}/garments/{gid}/qa/approve").status_code == 409

    r = env.post(f"/api/v1/merchant/{TENANT}/garments/{gid}/qa/findings/{fid}/resolve")
    assert r.status_code == 200, r.text
    assert r.json()["garment"]["qaFindings"][0]["resolved"] is True
    assert env.post(f"/api/v1/merchant/{TENANT}/garments/{gid}/qa/approve").status_code == 200


def test_an_unknown_finding_severity_is_a_422_not_a_500(env):
    gid = _make_garment(env)
    r = env.post(
        f"/api/v1/merchant/{TENANT}/garments/{gid}/qa/findings",
        json={"severity": "catastrophic", "detail": "x"},
    )
    assert r.status_code == 422


def test_members_are_listed_and_can_be_removed(env):
    env.fake.col("users_col").docs.append({"_id": USER, "email": "owner@atelier.com", "name": "Elodie", "is_guest": False})
    env.fake.col("users_col").docs.append({"_id": "u_colleague", "email": "sam@atelier.com", "is_guest": False})
    env.post(f"/api/v1/merchant/{TENANT}/members", json={"email": "sam@atelier.com", "role": "editor"}).raise_for_status()

    items = env.get(f"/api/v1/merchant/{TENANT}/members").json()["items"]
    assert {(m["email"], m["role"]) for m in items} == {("owner@atelier.com", "owner"), ("sam@atelier.com", "editor")}

    assert env.delete(f"/api/v1/merchant/{TENANT}/members/{USER}").status_code == 409
    r = env.delete(f"/api/v1/merchant/{TENANT}/members/u_colleague")
    assert r.status_code == 200, r.text
    assert "u_colleague" not in env.fake.col("merchant_tenants_col").docs[0]["members"]
