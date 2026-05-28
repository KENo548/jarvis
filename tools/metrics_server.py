#!/usr/bin/env python3
"""Tiny local metrics server for JARVIS.

Exposes the metrics snapshot from tools/jarvis_metrics.py over HTTP so
Prometheus can scrape it without any paid or hosted dependencies.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import jarvis_metrics


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"not found")
            return

        body = jarvis_metrics.build_metrics().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def serve(host: str = "127.0.0.1", port: int = 8081) -> None:
    server = HTTPServer((host, port), MetricsHandler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    serve()