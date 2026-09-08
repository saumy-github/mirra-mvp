"""Where product data comes from — one interface, three implementations.

The problem this solves
-----------------------
A merchant pastes `https://atelier-noir.com/products/perce-ribbed-tank`. That
string contains a store domain and a handle. It does **not** contain the
Shopify product id, the variants, the sizes, the price or the inventory —
all of which Mirra needs before it can digitise anything.

Previously the dashboard resolved the URL against a pre-seeded catalogue and,
when no store was connected, simply refused: "No product in your connected
store matches that link." No code anywhere in the repository could have put a
product into that catalogue. That is the blocker.

The mechanism
-------------
`resolve()` (service.py) walks the sources in priority order and takes the
first hit:

    1. ShopifyAdminSource   — live Admin GraphQL, when the tenant has a token
    2. stored product       — already in merchant_products
    3. (no hit)             — the caller offers manual entry / CSV import,
                              seeded with everything the URL itself gave us

So the URL step always advances. With a store connected it advances with real
Shopify data; without one it advances with a provisional identity the merchant
completes by hand, and `service.reconcile_unlinked_products()` upgrades those
records in place the day credentials arrive. No garment is re-created and no
capture work is lost.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import urlparse

import httpx

from ..core.errors import DomainError

# Shopify Admin API version this adapter is written against. Pinned: an
# unpinned version silently changes field availability under us.
SHOPIFY_API_VERSION = "2025-01"

_GID_RE = re.compile(r"^gid://shopify/Product/(\d+)$")
_NUMERIC_RE = re.compile(r"^\d+$")
# /products/<handle>, tolerating a locale prefix (/en-gb/products/...), a
# query string, and a /variants/... or .json suffix.
_HANDLE_IN_PATH_RE = re.compile(r"/products/([^/?#.]+)")
# A bare handle: lowercase words joined by hyphens, which is exactly what
# Shopify generates. Deliberately strict, so a mistyped URL is not read as one.
_BARE_HANDLE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ProductLookupError(DomainError):
    status_code = 502
    code = "product_lookup_failed"


@dataclass(frozen=True)
class ProductRef:
    """What a pasted string resolved to, before any network call.

    `handle` is the useful part. `store_domain` is empty for a bare handle or
    a GID, in which case the tenant's own connected domain is assumed.
    """

    handle: str = ""
    store_domain: str = ""
    shopify_gid: str = ""
    shopify_numeric_id: str = ""
    original: str = ""

    @property
    def usable(self) -> bool:
        return bool(self.handle or self.shopify_gid or self.shopify_numeric_id)


@dataclass
class VariantPayload:
    variant_id: str
    sku: str = ""
    title: str = ""
    size: str = ""
    colour: str = ""
    price: float = 0.0
    currency: str = "USD"
    inventory: int = 0
    shopify_variant_gid: str = ""


@dataclass
class ProductPayload:
    """A product as some source knows it. Maps straight onto MerchantProductDocument."""

    handle: str
    title: str
    source: str                      # shopify | manual | csv
    link_state: str                  # linked | unlinked
    shopify_gid: str = ""
    shopify_numeric_id: str = ""
    store_domain: str = ""
    online_store_url: str = ""
    product_type: str = ""
    vendor: str = ""
    option_name: str | None = None
    image_urls: list[str] = field(default_factory=list)
    description: str | None = None
    variants: list[VariantPayload] = field(default_factory=list)


# ------------------------------------------------------------------ parsing


def parse_product_reference(raw: str) -> ProductRef:
    """Turn whatever the merchant pasted into a ProductRef.

    Accepts, in roughly the order they get pasted in practice:
      - a storefront URL, on the custom domain or the .myshopify.com one
      - the same URL with a locale prefix, query string, or /variants/ suffix
      - an admin URL (/admin/products/123456)
      - a product GID (gid://shopify/Product/123456)
      - a bare numeric id
      - a bare handle
    """
    text = (raw or "").strip()
    if not text:
        return ProductRef(original=raw or "")

    gid_match = _GID_RE.match(text)
    if gid_match:
        return ProductRef(shopify_gid=text, shopify_numeric_id=gid_match.group(1), original=text)

    if _NUMERIC_RE.match(text):
        return ProductRef(
            shopify_gid=f"gid://shopify/Product/{text}",
            shopify_numeric_id=text,
            original=text,
        )

    if "://" in text or text.startswith("www.") or "/products/" in text:
        candidate = text if "://" in text else f"https://{text}"
        parsed = urlparse(candidate)
        domain = (parsed.netloc or "").lower()
        if domain.startswith("www."):
            domain = domain[4:]
        # Admin URLs carry the numeric id rather than a handle.
        admin = re.search(r"/admin/products/(\d+)", parsed.path)
        if admin:
            return ProductRef(
                store_domain=domain,
                shopify_gid=f"gid://shopify/Product/{admin.group(1)}",
                shopify_numeric_id=admin.group(1),
                original=text,
            )
        handle_match = _HANDLE_IN_PATH_RE.search(parsed.path)
        if handle_match:
            return ProductRef(
                handle=handle_match.group(1).lower(), store_domain=domain, original=text
            )
        # A URL whose shape we recognise but whose path we don't. Keep the
        # domain so the caller can still say which store it is talking about.
        return ProductRef(store_domain=domain, original=text)

    if _BARE_HANDLE_RE.match(text.lower()):
        return ProductRef(handle=text.lower(), original=text)

    return ProductRef(original=text)


def storefront_url(store_domain: str, handle: str) -> str:
    if not store_domain or not handle:
        return ""
    return f"https://{store_domain}/products/{handle}"


# ------------------------------------------------------------------ sources


class ProductSource(Protocol):
    name: str

    async def fetch(self, ref: ProductRef) -> ProductPayload | None:
        """Return the product, or None when this source does not have it."""
        ...


_COLOUR_NAMES = ("colour", "color", "shade", "finish", "pattern", "wash")
_SIZE_NAMES = ("size", "sizing")


def _pick_colour_option(options: list[dict]) -> str | None:
    for opt in options:
        if str(opt.get("name", "")).strip().lower() in _COLOUR_NAMES:
            return opt.get("name")
    return None


def _pick_size_option(options: list[dict]) -> str | None:
    for opt in options:
        if str(opt.get("name", "")).strip().lower() in _SIZE_NAMES:
            return opt.get("name")
    return None


class ShopifyAdminSource:
    """Live Shopify Admin GraphQL lookup.

    Inactive — `fetch` returns None immediately — unless the tenant has both a
    store domain and an access token. That is the entire switch: the day the
    client installs the app and a token lands on the tenant document, every
    lookup starts returning real Shopify data through this path with no other
    change anywhere.
    """

    name = "shopify"

    _FRAGMENT = """
    fragment P on Product {
      id
      legacyResourceId
      handle
      title
      description
      productType
      vendor
      onlineStoreUrl
      options { name values }
      featuredImage { url }
      images(first: 10) { nodes { url } }
      variants(first: 100) {
        nodes {
          id
          sku
          title
          price
          inventoryQuantity
          selectedOptions { name value }
        }
      }
    }
    """

    _QUERY_BY_HANDLE = "query P($handle: String!) { productByHandle(handle: $handle) { ...P } }"
    _QUERY_BY_ID = "query P($id: ID!) { product(id: $id) { ...P } }"

    def __init__(self, store_domain: str, access_token: str, *, timeout: float = 10.0):
        self.store_domain = store_domain
        self.access_token = access_token
        self.timeout = timeout

    @property
    def active(self) -> bool:
        return bool(self.store_domain and self.access_token)

    async def fetch(self, ref: ProductRef) -> ProductPayload | None:
        if not self.active or not ref.usable:
            return None

        if ref.shopify_gid:
            query, variables, root = (
                self._QUERY_BY_ID + self._FRAGMENT,
                {"id": ref.shopify_gid},
                "product",
            )
        else:
            query, variables, root = (
                self._QUERY_BY_HANDLE + self._FRAGMENT,
                {"handle": ref.handle},
                "productByHandle",
            )

        url = f"https://{self.store_domain}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json={"query": query, "variables": variables},
                    headers={
                        "X-Shopify-Access-Token": self.access_token,
                        "Content-Type": "application/json",
                    },
                )
        except httpx.HTTPError as exc:
            raise ProductLookupError(
                f"Could not reach Shopify for {self.store_domain}: {exc}"
            ) from exc

        if response.status_code == 401:
            raise ProductLookupError(
                "Shopify rejected the stored access token. Reconnect the store in Settings.",
                code="shopify_unauthorized",
            )
        if response.status_code >= 400:
            raise ProductLookupError(
                f"Shopify returned HTTP {response.status_code} for that product lookup."
            )

        body = response.json()
        if body.get("errors"):
            first = body["errors"][0].get("message", "unknown error")
            raise ProductLookupError(f"Shopify GraphQL error: {first}")

        node = (body.get("data") or {}).get(root)
        return self._to_payload(node) if node else None

    def _to_payload(self, node: dict) -> ProductPayload:
        # Which option is the colour axis is the shop's own choice — read the
        # option name rather than assuming "Color".
        options = node.get("options") or []
        colour_option = _pick_colour_option(options)
        size_option = _pick_size_option(options)

        variants: list[VariantPayload] = []
        for v in (node.get("variants") or {}).get("nodes", []):
            selected = {
                o.get("name", ""): o.get("value", "") for o in (v.get("selectedOptions") or [])
            }
            variants.append(
                VariantPayload(
                    variant_id=str(v.get("id", "")),
                    shopify_variant_gid=str(v.get("id", "")),
                    sku=v.get("sku") or "",
                    title=v.get("title") or "",
                    size=selected.get(size_option, "") if size_option else "",
                    colour=selected.get(colour_option, "") if colour_option else "",
                    price=float(v.get("price") or 0),
                    inventory=int(v.get("inventoryQuantity") or 0),
                )
            )

        images = [n.get("url", "") for n in (node.get("images") or {}).get("nodes", [])]
        featured = (node.get("featuredImage") or {}).get("url")
        if featured and featured not in images:
            images.insert(0, featured)

        handle = node.get("handle", "")
        return ProductPayload(
            handle=handle,
            title=node.get("title", ""),
            source="shopify",
            link_state="linked",
            shopify_gid=str(node.get("id", "")),
            shopify_numeric_id=str(node.get("legacyResourceId", "")),
            store_domain=self.store_domain,
            online_store_url=node.get("onlineStoreUrl")
            or storefront_url(self.store_domain, handle),
            product_type=node.get("productType") or "",
            vendor=node.get("vendor") or "",
            option_name=colour_option,
            image_urls=[u for u in images if u],
            description=node.get("description") or None,
            variants=variants,
        )


def draft_payload_from_ref(ref: ProductRef, tenant_domain: str = "") -> ProductPayload:
    """Everything the URL alone establishes, ready for the merchant to finish.

    This is what makes the unconnected-store path work: the merchant is never
    asked to retype the handle or the URL they just pasted, only the things no
    URL can carry — title, variants, sizes, price.
    """
    domain = ref.store_domain or tenant_domain
    handle = ref.handle
    return ProductPayload(
        handle=handle,
        # A titleised handle is a good first guess and is shown as a draft the
        # merchant must confirm; it is never treated as canonical.
        title=handle.replace("-", " ").title() if handle else "",
        source="manual",
        link_state="unlinked",
        shopify_gid=ref.shopify_gid,
        shopify_numeric_id=ref.shopify_numeric_id,
        store_domain=domain,
        online_store_url=(
            ref.original if "://" in ref.original else storefront_url(domain, handle)
        ),
    )
