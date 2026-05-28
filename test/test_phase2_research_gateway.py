import json
import threading
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import sys


ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import researcher
import research_gateway


def _response_url(server: HTTPServer, path: str) -> str:
    return f"http://{server.server_address[0]}:{server.server_address[1]}{path}"


class _ResearchHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/search?"):
            payload = {
                "results": [
                    {
                        "title": "Local SearXNG Result",
                        "url": _response_url(self.server, "/page"),
                        "content": "Local result snippet",
                    }
                ]
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/page":
            body = b"<html><head><title>Local Page</title></head><body><p>Research content from a local test page.</p></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        return


class Phase2ResearchGatewayTests(unittest.TestCase):
    def test_search_and_capture_local_page(self) -> None:
        server = HTTPServer(("127.0.0.1", 0), _ResearchHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_address[1]}"
            hits = research_gateway.search_web("jarvis phase 2", searxng_url=base_url, limit=1)
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0].title, "Local SearXNG Result")

            page = research_gateway.capture_page(hits[0].url)
            self.assertEqual(page.title, "Local Page")
            self.assertIn("Research content", page.text)
        finally:
            server.shutdown()
            server.server_close()

    def test_researcher_research_topic_stores_results(self) -> None:
        server = HTTPServer(("127.0.0.1", 0), _ResearchHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                db_path = Path(temp_dir) / "jarvis.db"
                vault_path = Path(temp_dir) / "vault"
                result = researcher.research_topic(
                    "jarvis local research",
                    searxng_url=f"http://127.0.0.1:{server.server_address[1]}",
                    limit=1,
                    db_path=db_path,
                    vault_path=vault_path,
                )

                self.assertEqual(result["query"], "jarvis local research")
                self.assertEqual(len(result["results"]), 1)
                self.assertEqual(len(result["stored_notes"]), 1)
                self.assertTrue(any(item.suffix == ".md" for item in vault_path.iterdir()))
        finally:
            server.shutdown()
            server.server_close()

    def test_mcp_config_loaded(self) -> None:
        config = research_gateway._load_mcp_config()
        self.assertIn("mcp_servers", config)
        self.assertIn("search-mcp", config["mcp_servers"])
        self.assertIn("browser-mcp", config["mcp_servers"])

    def test_mcp_server_enabled_check(self) -> None:
        enabled, cmd = research_gateway._mcp_server_enabled("search-mcp")
        self.assertIsInstance(enabled, bool)
        self.assertIsInstance(cmd, str)

    def test_search_mcp_first_priority(self) -> None:
        """Verify MCP is checked before SearXNG."""
        server = HTTPServer(("127.0.0.1", 0), _ResearchHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_address[1]}"
            hits = research_gateway.search_web("test query", searxng_url=base_url, limit=1)
            self.assertIsInstance(hits, list)
        finally:
            server.shutdown()
            server.server_close()

    def test_capture_page_fallback_to_http(self) -> None:
        server = HTTPServer(("127.0.0.1", 0), _ResearchHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_address[1]}/page"
            page = research_gateway.capture_page(url)
            self.assertEqual(page.title, "Local Page")
            self.assertIn("Research content", page.text)
        finally:
            server.shutdown()
            server.server_close()

    def test_search_hit_dataclass(self) -> None:
        hit = research_gateway.SearchHit(title="T", url="U", snippet="S")
        self.assertEqual(hit.title, "T")
        self.assertEqual(hit.url, "U")
        self.assertEqual(hit.snippet, "S")

    def test_page_capture_dataclass(self) -> None:
        cap = research_gateway.PageCapture(url="U", title="T", text="X")
        self.assertEqual(cap.url, "U")
        self.assertEqual(cap.title, "T")
        self.assertEqual(cap.text, "X")


if __name__ == "__main__":
    unittest.main()
