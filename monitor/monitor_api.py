#!/usr/bin/env python3
"""
RDMA Monitor API Server - Exposes rdma_monitor.py collectors as HTTP endpoints.

Dify workflow calls these endpoints via HTTP Request nodes to get real
monitoring data instead of relying on an LLM to hallucinate metrics.

Usage:
    python monitor_api.py                    # default :5100
    python monitor_api.py --port 8080        # custom port
    python monitor_api.py --host 0.0.0.0     # bind all interfaces

Endpoints:
    GET  /api/v1/collect/all         - Full collection (all sections)
    GET  /api/v1/collect/device      - RDMA device status only
    GET  /api/v1/collect/counters    - RDMA error & perf counters only
    GET  /api/v1/collect/network     - Network interface counters only
    GET  /api/v1/collect/topology    - RDMA fabric topology only
    GET  /api/v1/collect/hardware    - Hardware health only
    GET  /api/v1/collect/system      - System context only
    GET  /api/v1/health              - API health check
    POST /api/v1/collect/custom      - Custom section selection
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Import collectors from rdma_monitor
from rdma_monitor import (
    collect_rdma_device_status,
    collect_rdma_counters,
    collect_network_counters,
    collect_rdma_topology,
    collect_hardware_health,
    collect_system_context,
)

SECTION_MAP = {
    "device": collect_rdma_device_status,
    "counters": collect_rdma_counters,
    "network": collect_network_counters,
    "topology": collect_rdma_topology,
    "hardware": collect_hardware_health,
    "system": collect_system_context,
}


def build_report(sections):
    """Build a monitoring report for the requested sections."""
    report = {
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hostname": os.uname().nodename,
            "collector_version": "1.0.0",
            "sections_collected": list(sections),
        }
    }
    for name in sections:
        fn = SECTION_MAP.get(name)
        if fn:
            report[name] = fn()
    return report


class MonitorHandler(BaseHTTPRequestHandler):
    """HTTP handler for the monitor API."""

    def _send_json(self, data, status=200):
        body = json.dumps(data, indent=2, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/v1/health":
            self._send_json({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})
            return

        if path == "/api/v1/collect/all":
            report = build_report(SECTION_MAP.keys())
            self._send_json(report)
            return

        # Single-section endpoints: /api/v1/collect/<section>
        prefix = "/api/v1/collect/"
        if path.startswith(prefix):
            section = path[len(prefix):]
            if section in SECTION_MAP:
                report = build_report([section])
                self._send_json(report)
                return
            self._send_json({"error": f"Unknown section: {section}",
                             "available": list(SECTION_MAP.keys())}, 404)
            return

        self._send_json({"error": "Not found", "endpoints": [
            "/api/v1/health",
            "/api/v1/collect/all",
            "/api/v1/collect/device",
            "/api/v1/collect/counters",
            "/api/v1/collect/network",
            "/api/v1/collect/topology",
            "/api/v1/collect/hardware",
            "/api/v1/collect/system",
        ]}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/v1/collect/custom":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                req = json.loads(body) if body else {}
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON"}, 400)
                return

            requested = req.get("sections", list(SECTION_MAP.keys()))
            invalid = [s for s in requested if s not in SECTION_MAP]
            if invalid:
                self._send_json({"error": f"Unknown sections: {invalid}",
                                 "available": list(SECTION_MAP.keys())}, 400)
                return

            report = build_report(requested)
            self._send_json(report)
            return

        self._send_json({"error": "Not found"}, 404)

    def log_message(self, format, *args):
        """Override to add timestamp prefix."""
        sys.stderr.write(f"[{datetime.now().isoformat()}] {args[0]}\n")


def main():
    parser = argparse.ArgumentParser(description="RDMA Monitor API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5100, help="Port (default: 5100)")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), MonitorHandler)
    print(f"RDMA Monitor API listening on {args.host}:{args.port}", file=sys.stderr)
    print(f"  Health:   http://{args.host}:{args.port}/api/v1/health", file=sys.stderr)
    print(f"  Collect:  http://{args.host}:{args.port}/api/v1/collect/all", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.", file=sys.stderr)
        server.server_close()


if __name__ == "__main__":
    main()
