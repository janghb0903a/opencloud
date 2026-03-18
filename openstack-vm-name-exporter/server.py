#!/usr/bin/env python3
import json
import os
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))
PORT = int(os.getenv("PORT", "9189"))
OS_CLOUD = os.getenv("OS_CLOUD", "")

METRICS_BODY = ""
SCRAPE_SUCCESS = 0
LAST_SUCCESS_TS = 0


def esc(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def collect_once() -> str:
    cmd = ["openstack"]
    if OS_CLOUD:
        cmd += ["--os-cloud", OS_CLOUD]

    cmd += [
        "server",
        "list",
        "--all-projects",
        "-f",
        "json",
        "-c",
        "ID",
        "-c",
        "Name",
    ]

    raw = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
    rows = json.loads(raw)

    lines = [
        "# HELP openstack_vm_identity UUID to OpenStack server display name mapping",
        "# TYPE openstack_vm_identity gauge",
    ]

    for row in rows:
        uuid = row["ID"]
        name = row["Name"]
        lines.append(f'openstack_vm_identity{{uuid="{esc(uuid)}",name="{esc(name)}"}} 1')

    return "\n".join(lines) + "\n"


def refresh_loop():
    global METRICS_BODY, SCRAPE_SUCCESS, LAST_SUCCESS_TS
    while True:
        try:
            METRICS_BODY = collect_once()
            SCRAPE_SUCCESS = 1
            LAST_SUCCESS_TS = int(time.time())
        except Exception:
            SCRAPE_SUCCESS = 0
        time.sleep(POLL_INTERVAL)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return

        meta = (
            "# HELP openstack_vm_identity_scrape_success 1 if the last OpenStack poll succeeded\n"
            "# TYPE openstack_vm_identity_scrape_success gauge\n"
            f"openstack_vm_identity_scrape_success {SCRAPE_SUCCESS}\n"
            "# HELP openstack_vm_identity_last_success_timestamp_seconds Unix timestamp of last successful poll\n"
            "# TYPE openstack_vm_identity_last_success_timestamp_seconds gauge\n"
            f"openstack_vm_identity_last_success_timestamp_seconds {LAST_SUCCESS_TS}\n"
        )

        body = (METRICS_BODY + meta).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    try:
        METRICS_BODY = collect_once()
        SCRAPE_SUCCESS = 1
        LAST_SUCCESS_TS = int(time.time())
    except Exception:
        pass

    t = threading.Thread(target=refresh_loop, daemon=True)
    t.start()

    server = HTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()
