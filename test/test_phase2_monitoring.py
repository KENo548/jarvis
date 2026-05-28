import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import urlopen

import sys


ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import jarvis_metrics
import metrics_server


class Phase2MonitoringTests(unittest.TestCase):
    def test_metrics_server_serves_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            metrics = jarvis_metrics.build_metrics(db_path=Path(temp_dir) / "jarvis.db")
            self.assertIn("jarvis_pending_approvals_total", metrics)

            server = metrics_server.HTTPServer(("127.0.0.1", 0), metrics_server.MetricsHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                body = urlopen(f"http://127.0.0.1:{server.server_address[1]}/metrics").read().decode("utf-8")
                self.assertIn("jarvis_pending_approvals_total", body)
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()