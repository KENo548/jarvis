import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import sys


ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import capability_registry
import governance
import orchestration_graph


class _GraphResearchHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/search?"):
            body = b'{"results":[{"title":"Graph Research","url":"http://127.0.0.1/page","content":"graph research snippet"}]}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/page":
            body = b"<html><head><title>Graph Page</title></head><body><p>Graph content.</p></body></html>"
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


class Phase3OrchestrationGraphTests(unittest.TestCase):
    def test_graph_runs_code_task_with_sandbox(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "jarvis.db"
            capability_registry.seed_defaults(db_path=db_path)

            result = orchestration_graph.run_graph(
                "Please write tests for the runtime lifecycle code",
                db_path=db_path,
            )

            node_names = [node["name"] for node in result["nodes"]]
            self.assertEqual(node_names, ["plan", "route", "research", "sandbox", "qa", "security", "execute"])
            sandbox_node = next(node for node in result["nodes"] if node["name"] == "sandbox")
            self.assertEqual(sandbox_node["status"], "ok")
            self.assertIn(result["final_state"], ("ok", "warn"))

    def test_graph_runs_research_task_against_local_server(self) -> None:
        server = HTTPServer(("127.0.0.1", 0), _GraphResearchHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                db_path = Path(temp_dir) / "jarvis.db"
                capability_registry.seed_defaults(db_path=db_path)

                result = orchestration_graph.run_graph(
                    "Please research the new toolchain documentation",
                    db_path=db_path,
                    vault_path=Path(temp_dir) / "vault",
                )

            research_node = next(node for node in result["nodes"] if node["name"] == "research")
            self.assertEqual(research_node["status"], "ok")
            self.assertEqual(len(result["nodes"]), 7)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()