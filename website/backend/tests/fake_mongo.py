"""A minimal async in-memory stand-in for the AsyncCollection methods the
merchant service actually uses.

Not a Mongo emulator — it supports exactly the operations in service.py, and
raises on anything else so an untested query shape fails loudly instead of
quietly returning nothing. Enough to exercise the real routes, real
serialisation and real authorization without a database.
"""

from __future__ import annotations

import copy
import re
from typing import Any


def _matches(doc: dict, query: dict) -> bool:
    for key, expected in query.items():
        if key.endswith("$exists"):
            raise NotImplementedError(key)
        if isinstance(expected, dict):
            if "$in" in expected:
                if _get(doc, key) not in expected["$in"]:
                    return False
                continue
            if "$exists" in expected:
                present = _get(doc, key, _MISSING) is not _MISSING
                if present != expected["$exists"]:
                    return False
                continue
            if "$regex" in expected:
                flags = re.I if "i" in expected.get("$options", "") else 0
                if not re.search(expected["$regex"], str(_get(doc, key) or ""), flags):
                    return False
                continue
            raise NotImplementedError(f"operator in {expected}")
        if _get(doc, key) != expected:
            return False
    return True


_MISSING = object()


def _get(doc: dict, dotted: str, default=None) -> Any:
    node: Any = doc
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def _set(doc: dict, dotted: str, value: Any) -> None:
    node = doc
    parts = dotted.split(".")
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


class _Cursor:
    def __init__(self, docs: list[dict]):
        self._docs = docs

    def sort(self, key, direction=1):
        self._docs.sort(key=lambda d: (_get(d, key) is None, _get(d, key)), reverse=direction < 0)
        return self

    def skip(self, n):
        self._docs = self._docs[n:]
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    async def to_list(self, length=None):
        return [copy.deepcopy(d) for d in (self._docs[:length] if length else self._docs)]


class FakeCollection:
    def __init__(self):
        self.docs: list[dict] = []

    async def create_index(self, *a, **k):
        return "ok"

    async def find_one(self, query: dict, projection=None, sort=None):
        found = [d for d in self.docs if _matches(d, query)]
        if sort:
            key, direction = sort[0]
            found.sort(key=lambda d: (_get(d, key) is None, _get(d, key)), reverse=direction < 0)
        return copy.deepcopy(found[0]) if found else None

    def find(self, query: dict | None = None, projection=None):
        return _Cursor([d for d in self.docs if _matches(d, query or {})])

    async def count_documents(self, query: dict):
        return len([d for d in self.docs if _matches(d, query)])

    async def insert_one(self, doc: dict):
        self.docs.append(copy.deepcopy(doc))
        return type("R", (), {"inserted_id": doc.get("_id")})()

    async def replace_one(self, query: dict, doc: dict, upsert: bool = False):
        for i, existing in enumerate(self.docs):
            if _matches(existing, query):
                self.docs[i] = copy.deepcopy(doc)
                return type("R", (), {"matched_count": 1})()
        if upsert:
            self.docs.append(copy.deepcopy(doc))
        return type("R", (), {"matched_count": 0})()

    async def update_one(self, query: dict, update: dict, upsert: bool = False):
        target = next((d for d in self.docs if _matches(d, query)), None)
        if target is None:
            if not upsert:
                return type("R", (), {"matched_count": 0})()
            target = copy.deepcopy(query)
            for key, value in (update.get("$setOnInsert") or {}).items():
                _set(target, key, value)
            self.docs.append(target)
        for key, value in (update.get("$set") or {}).items():
            _set(target, key, copy.deepcopy(value))
        return type("R", (), {"matched_count": 1})()


class FakeDb:
    """Swaps every merchant collection accessor for a fake, and restores them."""

    NAMES = (
        "merchant_tenants_col",
        "merchant_products_col",
        "merchant_garments_col",
        "merchant_ingestion_runs_col",
        "merchant_previews_col",
        "cloths_col",
        "sizes_col",
    )

    def __init__(self):
        self.collections = {name: FakeCollection() for name in self.NAMES}
        self._saved: dict = {}

    def install(self, monkeypatch) -> "FakeDb":
        import src.db as db_module
        import src.merchant.pipeline_bridge as bridge
        import src.merchant.service as svc

        for name in self.NAMES:
            fake = self.collections[name]
            accessor = lambda _f=fake: _f
            monkeypatch.setattr(db_module, name, accessor, raising=False)
            for module in (svc, bridge):
                if hasattr(module, name):
                    monkeypatch.setattr(module, name, accessor, raising=False)
        return self

    def col(self, name: str) -> FakeCollection:
        return self.collections[name]
