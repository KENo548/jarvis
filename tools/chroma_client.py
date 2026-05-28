#!/usr/bin/env python3
"""Minimal Chroma REST client for JARVIS — v2 API.

Supports the Chroma v2 REST API (available in chromadb >= 0.6.x / latest).
Endpoints follow the /api/v2/tenants/{tenant}/databases/{db}/collections/...
hierarchy.  The v1 API is deprecated and will be removed.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ChromaConfig:
    host: str
    port: int
    collection_name: str
    tenant: str
    database: str

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


def config_from_env() -> ChromaConfig:
    host = os.getenv("CHROMA_HOST", "localhost")
    port = int(os.getenv("CHROMA_PORT", "8000"))
    collection_name = os.getenv("CHROMA_COLLECTION", "jarvis_memory")
    tenant = os.getenv("CHROMA_TENANT", "default_tenant")
    database = os.getenv("CHROMA_DATABASE", "default_database")
    return ChromaConfig(host=host, port=port, collection_name=collection_name, tenant=tenant, database=database)


class ChromaClient:
    _collection_id: str | None = None

    def __init__(self, config: ChromaConfig | None = None) -> None:
        self.config = config or config_from_env()

    # ------------------------------------------------------------------
    # low-level request
    # ------------------------------------------------------------------

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        url = f"{self.config.base_url}{path}"
        data = None
        headers = {"Content-Type": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            raise ConnectionError(f"Chroma request failed: {exc.code} {message}") from exc
        except urllib.error.URLError as exc:
            raise ConnectionError(f"Chroma server unavailable at {url}: {exc.reason}") from exc

    # ------------------------------------------------------------------
    # health
    # ------------------------------------------------------------------

    def health(self) -> bool:
        try:
            result = self._request("GET", "/api/v2/healthcheck")
        except ConnectionError:
            return False
        return bool(result)

    # ------------------------------------------------------------------
    # collection resolution (UUID caching)
    # ------------------------------------------------------------------

    def _api_base(self) -> str:
        t = urllib.parse.quote(self.config.tenant, safe="")
        d = urllib.parse.quote(self.config.database, safe="")
        return f"/api/v2/tenants/{t}/databases/{d}/collections"

    def _resolve_collection_id(self) -> str:
        if self._collection_id is not None:
            return self._collection_id

        # Try to create the collection (idempotent create)
        base = self._api_base()
        payload = {"name": self.config.collection_name, "metadata": {"hnsw:space": "cosine"}}
        try:
            created = self._request("POST", base, payload)
            if isinstance(created, dict):
                self._collection_id = str(created.get("id", self.config.collection_name))
                return self._collection_id
        except ConnectionError:
            pass

        # Already exists — list and find by name
        try:
            collections = self._request("GET", base)
            if isinstance(collections, list):
                for c in collections:
                    if c.get("name") == self.config.collection_name:
                        self._collection_id = str(c["id"])
                        return self._collection_id
        except ConnectionError:
            pass

        # Last resort: use the collection name (will fail on strict v2 servers)
        self._collection_id = self.config.collection_name
        return self._collection_id

    def _collection_path(self) -> str:
        cid = urllib.parse.quote(self._resolve_collection_id(), safe="")
        return f"{self._api_base()}/{cid}"

    # ------------------------------------------------------------------
    # data operations
    # ------------------------------------------------------------------

    def upsert(self, ids: list[str], documents: list[str], metadatas: list[dict[str, Any]], embeddings: list[list[float]]) -> None:
        payload = {"ids": ids, "documents": documents, "metadatas": metadatas, "embeddings": embeddings}
        self._request("POST", f"{self._collection_path()}/upsert", payload)

    def add(self, ids: list[str], documents: list[str], metadatas: list[dict[str, Any]], embeddings: list[list[float]]) -> None:
        payload = {"ids": ids, "documents": documents, "metadatas": metadatas, "embeddings": embeddings}
        self._request("POST", f"{self._collection_path()}/add", payload)

    def query(self, query_embeddings: list[list[float]], n_results: int = 5) -> list[list[str]]:
        payload = {"query_embeddings": query_embeddings, "n_results": n_results}
        response = self._request("POST", f"{self._collection_path()}/query", payload)
        if not isinstance(response, dict):
            return []
        ids = response.get("ids")
        return ids if isinstance(ids, list) else []

    def count(self) -> int:
        result = self._request("GET", f"{self._collection_path()}/count")
        return int(result) if isinstance(result, (int, float)) else 0
