#!/usr/bin/env python3
"""Research gateway for JARVIS — MCP-first architecture.

Execution priority:
  1. Official MCP servers via stdio (search-mcp, browser-mcp)
  2. MCP HTTP bridge (when stdio is not available)
  3. SearXNG self-hosted search (Phase 2 local fallback)
  4. Raw HTTP page capture (browser-mcp fallback)

Phase 2 fix: MCP servers are now the PRIMARY path, not a fallback.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urljoin, urlparse
from urllib.request import Request, urlopen


MCP_HTTP_BRIDGE_URL = os.getenv("MCP_HTTP_BRIDGE_URL", "http://localhost:8099")


@dataclass(frozen=True)
class SearchHit:
    title: str
    url: str
    snippet: str


@dataclass(frozen=True)
class PageCapture:
    url: str
    title: str
    text: str


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._pieces: list[str] = []
        self._in_title = False
        self.title = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title += (" " if self.title else "") + text
        else:
            self._pieces.append(text)

    @property
    def text(self) -> str:
        return " ".join(self._pieces)


def _read_url(url: str, timeout_seconds: int = 15) -> tuple[str, str]:
    request = Request(url, headers={"User-Agent": "JARVIS/1.0"})
    with urlopen(request, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8", errors="ignore")
        content_type = response.headers.get_content_type()
        return body, content_type


# ---------------------------------------------------------------------------
# MCP server resolution
# ---------------------------------------------------------------------------

def _load_mcp_config() -> dict[str, Any]:
    registry = Path(__file__).resolve().parent.parent / "mcp-servers" / "mcp-registry.json"
    if not registry.exists():
        return {}
    return json.loads(registry.read_text(encoding="utf-8"))


def _mcp_server_enabled(server_name: str) -> tuple[bool, str]:
    """Return (enabled, install_command) for an MCP server."""
    config = _load_mcp_config()
    server = config.get("mcp_servers", {}).get(server_name, {})
    return server.get("enabled", False), server.get("install_command", "")


def _call_mcp_via_stdio(install_cmd: str, tool_name: str, arguments: dict[str, Any], timeout_seconds: int = 30) -> dict[str, Any] | None:
    """Call an MCP server tool via stdio JSON-RPC."""
    try:
        from mcp_client import MCPClient
        with MCPClient(install_cmd, timeout_seconds=timeout_seconds) as client:
            return client.call_tool(tool_name, arguments)
    except Exception:
        return None


def _call_mcp_via_http(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
    """Call an MCP server tool via the HTTP bridge."""
    try:
        payload = json.dumps({"tool": tool_name, "arguments": arguments}).encode("utf-8")
        request = Request(
            f"{MCP_HTTP_BRIDGE_URL}/call",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def _parse_mcp_search_result(result: dict[str, Any], max_hits: int = 10) -> list[SearchHit]:
    """Extract SearchHit list from an MCP tools/call response."""
    hits: list[SearchHit] = []
    content = result.get("content", [])
    for item in content:
        if not isinstance(item, dict):
            continue
        text = item.get("text", "")
        try:
            items = json.loads(text)
            if isinstance(items, list):
                for entry in items:
                    hits.append(
                        SearchHit(
                            title=str(entry.get("title", "")),
                            url=str(entry.get("url", "")),
                            snippet=str(entry.get("content", entry.get("snippet", ""))),
                        )
                    )
            elif isinstance(items, dict):
                hits.append(
                    SearchHit(
                        title=str(items.get("title", "")),
                        url=str(items.get("url", "")),
                        snippet=str(items.get("content", items.get("snippet", ""))),
                    )
                )
        except (json.JSONDecodeError, TypeError):
            if item.get("type") == "text":
                hits.append(SearchHit(title="Search result", url="", snippet=text))
    return hits[:max_hits]


# ---------------------------------------------------------------------------
# Search: MCP-first → SearXNG fallback
# ---------------------------------------------------------------------------

def search_web(query: str, searxng_url: str = "http://localhost:8888", limit: int = 5) -> list[SearchHit]:
    """Search the web. MCP servers (search-mcp) are tried FIRST."""

    # --- Priority 1: search-mcp via stdio ---
    enabled, install_cmd = _mcp_server_enabled("search-mcp")
    if enabled and install_cmd:
        import shutil
        first_word = install_cmd.split()[0]
        if shutil.which(first_word):
            brave_key_env = "BRAVE_API_KEY"
            if os.getenv(brave_key_env):
                result = _call_mcp_via_stdio(install_cmd, "brave_web_search", {"query": query, "count": limit})
                if result:
                    hits = _parse_mcp_search_result(result, max_hits=limit)
                    if hits:
                        return hits

    # --- Priority 2: search-mcp via HTTP bridge ---
    if enabled:
        result = _call_mcp_via_http("brave_web_search", {"query": query, "count": limit})
        if result:
            hits = _parse_mcp_search_result(result, max_hits=limit)
            if hits:
                return hits

    # --- Priority 3: SearXNG (self-hosted, local) ---
    try:
        endpoint = f"{searxng_url.rstrip('/')}/search?q={quote_plus(query)}&format=json"
        body, _ = _read_url(endpoint)
        payload = json.loads(body)
        results = payload.get("results", [])
        if results:
            hits: list[SearchHit] = []
            for result in results[:limit]:
                hits.append(
                    SearchHit(
                        title=str(result.get("title", "")),
                        url=str(result.get("url", "")),
                        snippet=str(result.get("content", result.get("snippet", ""))),
                    )
                )
            return hits
    except Exception:
        pass

    return []


# ---------------------------------------------------------------------------
# Page capture: browser-mcp (Playwright) first → raw HTTP fallback
# ---------------------------------------------------------------------------

def _mcp_capture_page(url: str, timeout_seconds: int = 15) -> PageCapture | None:
    """Capture a page via browser-mcp (Playwright) MCP server.

    Only attempts MCP if:
      1. browser-mcp is enabled in the registry
      2. The MCP executable is actually available on PATH
      3. The MCP HTTP bridge is reachable (preferred) or stdio works
    """
    enabled, install_cmd = _mcp_server_enabled("browser-mcp")
    if not enabled:
        return None

    # Check if MCP executable is actually available
    import shutil
    if install_cmd:
        first_word = install_cmd.split()[0]
        if not shutil.which(first_word):
            return None

    # --- Try HTTP bridge first (most reliable) ---
    result = _call_mcp_via_http("browser_navigate", {"url": url})
    if result is not None:
        page = _extract_page_from_mcp(result, url)
        if page and page.text:
            return page

    # --- Try stdio (only if HTTP bridge not available) ---
    if install_cmd:
        result = _call_mcp_via_stdio(
            install_cmd,
            "browser_navigate",
            {"url": url},
            timeout_seconds=timeout_seconds,
        )
        if result is not None:
            page = _extract_page_from_mcp(result, url)
            if page and page.text:
                return page

    return None


def _extract_page_from_mcp(result: dict[str, Any], url: str) -> PageCapture | None:
    """Extract page content from MCP browser_navigate result.

    Returns None if the MCP response doesn't contain usable page content
    (e.g., Playwright internal messages, code snippets, error messages).
    """
    try:
        content_items = result.get("content", [])
        text = ""
        title = ""
        for item in content_items:
            if isinstance(item, dict) and item.get("text"):
                raw = item["text"]
                # Skip Playwright internal messages
                if raw.startswith("### Ran Playwright") or raw.startswith("### Result"):
                    lines = raw.strip().split("\n")
                    if len(lines) >= 2:
                        raw = "\n".join(lines[1:]).strip()
                    else:
                        continue
                # Skip markdown code blocks (JS/TS snippets from Playwright MCP)
                if raw.strip().startswith("```"):
                    continue
                if not raw:
                    continue
                # Try to extract title and text from MCP response
                lines = raw.strip().split("\n")
                if len(lines) >= 2:
                    title = lines[0].strip()
                    text = "\n".join(lines[1:]).strip()
                else:
                    text = raw.strip()
        if not text or len(text) < 10:
            return None
        # Filter out code-like content
        if text.startswith("```") or text.startswith("async ") or text.startswith("const "):
            return None
        if not title:
            title = urlparse(url).netloc or url
        return PageCapture(url=url, title=title, text=text)
    except Exception:
        return None


def capture_page(url: str, timeout_seconds: int = 15) -> PageCapture:
    """Capture a page. browser-mcp (Playwright) is tried FIRST."""
    # --- Priority 1: browser-mcp via MCP ---
    result = _mcp_capture_page(url, timeout_seconds=timeout_seconds)
    if result is not None:
        return result

    # --- Priority 2: raw HTTP fallback ---
    body, content_type = _read_url(url, timeout_seconds=timeout_seconds)
    if "html" not in content_type:
        return PageCapture(url=url, title=urlparse(url).netloc or url, text=body.strip())

    parser = _TextExtractor()
    parser.feed(body)
    title = parser.title.strip() or urlparse(url).netloc or url
    text = re.sub(r"\s+", " ", parser.text).strip()
    return PageCapture(url=url, title=title, text=text)


def resolve_relative(base_url: str, link: str) -> str:
    return urljoin(base_url, link)
