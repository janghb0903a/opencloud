#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import platform
import re
import shlex
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Iterable
from urllib.parse import parse_qs, quote, unquote, urlparse

DB_PATH = os.getenv("DB_PATH", "/data/openstack_vm_recovery.db")
HTTP_PORT = int(os.getenv("HTTP_PORT", "9088"))
PING_COUNT = int(os.getenv("PING_COUNT", "2"))
PING_TIMEOUT_SEC = int(os.getenv("PING_TIMEOUT_SEC", "3"))
OPENSTACK_TIMEOUT_SEC = int(os.getenv("OPENSTACK_TIMEOUT_SEC", "30"))
SLEEP_BETWEEN_TARGETS_SEC = int(os.getenv("SLEEP_BETWEEN_TARGETS_SEC", "1"))
FAILURE_THRESHOLD = int(os.getenv("FAILURE_THRESHOLD", "3"))
CRON_SCHEDULE = os.getenv("CRON_SCHEDULE", "*/10 * * * *")
VM_DISCOVERY_ENABLED = os.getenv("VM_DISCOVERY_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
DISCOVERY_NETWORK_PREFIXES = [
    item.strip().lower()
    for item in os.getenv("DISCOVERY_NETWORK_PREFIXES", "ap,db").split(",")
    if item.strip()
]
DISCOVERY_IP_PREFIXES = [
    item.strip()
    for item in os.getenv("DISCOVERY_IP_PREFIXES", "16.120.,16.120.120.,16.120.121.").split(",")
    if item.strip()
]
DISCOVERY_SERVER_LIST_ARGS = [
    item.strip()
    for item in os.getenv("DISCOVERY_SERVER_LIST_ARGS", "").split()
    if item.strip()
]


@dataclass
class VmTarget:
    address: str
    name: str | None = None
    server_id: str | None = None
    project_id: str | None = None

    @property
    def identifier(self) -> str:
        return self.server_id or self.name or self.address

    @property
    def display_name(self) -> str:
        return self.name or self.server_id or self.address


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(level: str, message: str, **fields: Any) -> None:
    payload = {"ts": now_utc(), "level": level.upper(), "message": message}
    payload.update(fields)
    print(json.dumps(payload, ensure_ascii=True), flush=True)


def ensure_db() -> None:
    parent = os.path.dirname(DB_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS managed_vms (
              identifier TEXT PRIMARY KEY,
              name TEXT,
              address TEXT NOT NULL,
              server_id TEXT,
              project_id TEXT,
              suppressed INTEGER NOT NULL DEFAULT 0,
              suppressed_reason TEXT,
              suppressed_until TEXT,
              reboot_on_active INTEGER NOT NULL DEFAULT 0,
              recovery_pending INTEGER NOT NULL DEFAULT 0,
              unresponsive INTEGER NOT NULL DEFAULT 0,
              unresponsive_reason TEXT,
              unresponsive_since TEXT,
              consecutive_failures INTEGER NOT NULL DEFAULT 0,
              last_outcome TEXT,
              last_checked_at TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS recovery_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              created_at TEXT NOT NULL,
              vm_identifier TEXT NOT NULL,
              vm_name TEXT,
              address TEXT,
              event_type TEXT NOT NULL,
              status TEXT,
              vm_state TEXT,
              task_state TEXT,
              action TEXT,
              details_json TEXT
            );
            """
        )
        ensure_columns(
            conn,
            "managed_vms",
            {
                "reboot_on_active": "INTEGER NOT NULL DEFAULT 0",
                "recovery_pending": "INTEGER NOT NULL DEFAULT 0",
                "unresponsive": "INTEGER NOT NULL DEFAULT 0",
                "unresponsive_reason": "TEXT",
                "unresponsive_since": "TEXT",
            },
        )


def ensure_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    existing = {
        row[1]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }
    for name, ddl in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_targets() -> list[VmTarget]:
    raw = os.getenv("VM_TARGETS_JSON", "").strip()
    path = os.getenv("VM_TARGETS_FILE", "").strip()
    if raw:
        data = json.loads(raw)
    elif path:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    else:
        raise SystemExit("Set VM_TARGETS_JSON or VM_TARGETS_FILE.")
    targets = []
    for item in data:
        if not item.get("address") or not (item.get("name") or item.get("id")):
            raise SystemExit(f"Invalid target: {item}")
        targets.append(
            VmTarget(
                address=str(item["address"]).strip(),
                name=str(item.get("name", "")).strip() or None,
                server_id=str(item.get("id", "")).strip() or None,
                project_id=str(item.get("project_id", "")).strip() or None,
            )
        )
    return targets


def parse_network_addresses(value: Any) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    if not value:
        return pairs
    if isinstance(value, dict):
        for network, addresses in value.items():
            if isinstance(addresses, str):
                for ip in extract_ipv4s(addresses):
                    pairs.append((str(network), ip))
            elif isinstance(addresses, list):
                for item in addresses:
                    for ip in extract_ipv4s(item):
                        pairs.append((str(network), ip))
            else:
                for ip in extract_ipv4s(addresses):
                    pairs.append((str(network), ip))
        return pairs
    if isinstance(value, list):
        for item in value:
            pairs.extend(parse_network_addresses(item))
        return pairs

    text = str(value)
    markers = list(re.finditer(r"(^|[,;]\s*)([^=,;]+)=", text))
    for index, marker in enumerate(markers):
        network = marker.group(2).strip()
        start = marker.end()
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        for ip in extract_ipv4s(text[start:end]):
            pairs.append((network, ip))
    if pairs:
        return pairs
    return [("", ip) for ip in extract_ipv4s(text)]


def extract_ipv4s(value: Any) -> list[str]:
    return re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", str(value))


def choose_discovered_address(server: dict[str, Any]) -> str | None:
    network_value = (
        server.get("Networks")
        or server.get("addresses")
        or server.get("Addresses")
        or server.get("Network")
    )
    pairs = parse_network_addresses(network_value)
    for prefix in DISCOVERY_NETWORK_PREFIXES:
        for network, ip in pairs:
            if network.strip().lower().startswith(prefix):
                return ip
    for prefix in DISCOVERY_IP_PREFIXES:
        for _, ip in pairs:
            if ip.startswith(prefix):
                return ip
    return None


def discover_targets() -> list[VmTarget]:
    output = run_cmd(
        openstack_base() + ["server", "list", "--long", "-f", "json"] + DISCOVERY_SERVER_LIST_ARGS,
        OPENSTACK_TIMEOUT_SEC,
    )
    servers = json.loads(output)
    targets: list[VmTarget] = []
    skipped = 0
    for server in servers:
        server_id = str(server.get("ID") or server.get("Id") or server.get("id") or "").strip() or None
        name = str(server.get("Name") or server.get("name") or server_id or "").strip() or None
        address = choose_discovered_address(server)
        if not address or not (server_id or name):
            skipped += 1
            continue
        targets.append(VmTarget(address=address, name=name, server_id=server_id))
    log("info", "OpenStack discovery completed", discovered=len(targets), skipped=skipped)
    return targets


def sync_targets() -> list[VmTarget]:
    targets = discover_targets() if VM_DISCOVERY_ENABLED else load_targets()
    ts = now_utc()
    with db() as conn:
        for t in targets:
            conn.execute(
                """
                INSERT INTO managed_vms
                (identifier, name, address, server_id, project_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(identifier) DO UPDATE SET
                  name=excluded.name,
                  address=excluded.address,
                  server_id=excluded.server_id,
                  project_id=excluded.project_id,
                  updated_at=excluded.updated_at
                """,
                (t.identifier, t.name, t.address, t.server_id, t.project_id, ts, ts),
            )
    return targets


def set_failure_count(identifier: str, value: int) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE managed_vms SET consecutive_failures=?, updated_at=? WHERE identifier=?",
            (value, now_utc(), identifier),
        )


def recovery_state(identifier: str) -> tuple[bool, bool, str | None, str | None]:
    with db() as conn:
        row = conn.execute(
            """
            SELECT recovery_pending, unresponsive, unresponsive_reason, unresponsive_since
            FROM managed_vms
            WHERE identifier=?
            """,
            (identifier,),
        ).fetchone()
    if not row:
        return False, False, None, None
    return (
        bool(row["recovery_pending"]),
        bool(row["unresponsive"]),
        row["unresponsive_reason"],
        row["unresponsive_since"],
    )


def reboot_on_active_state(identifier: str) -> bool:
    with db() as conn:
        row = conn.execute(
            "SELECT reboot_on_active FROM managed_vms WHERE identifier=?",
            (identifier,),
        ).fetchone()
    return bool(row["reboot_on_active"]) if row else False


def set_reboot_on_active(identifier: str, value: bool) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE managed_vms SET reboot_on_active=?, updated_at=? WHERE identifier=?",
            (1 if value else 0, now_utc(), identifier),
        )


def set_recovery_pending(identifier: str, value: bool) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE managed_vms SET recovery_pending=?, updated_at=? WHERE identifier=?",
            (1 if value else 0, now_utc(), identifier),
        )


def clear_unresponsive(identifier: str) -> None:
    with db() as conn:
        conn.execute(
            """
            UPDATE managed_vms
            SET recovery_pending=0,
                unresponsive=0,
                unresponsive_reason=NULL,
                unresponsive_since=NULL,
                consecutive_failures=0,
                updated_at=?
            WHERE identifier=?
            """,
            (now_utc(), identifier),
        )


def mark_unresponsive(identifier: str, reason: str) -> None:
    with db() as conn:
        conn.execute(
            """
            UPDATE managed_vms
            SET recovery_pending=0,
                unresponsive=1,
                unresponsive_reason=?,
                unresponsive_since=?,
                updated_at=?
            WHERE identifier=?
            """,
            (reason, now_utc(), now_utc(), identifier),
        )


def failure_count(identifier: str) -> int:
    with db() as conn:
        row = conn.execute(
            "SELECT consecutive_failures FROM managed_vms WHERE identifier=?",
            (identifier,),
        ).fetchone()
    return int(row["consecutive_failures"] or 0) if row else 0


def record_event(target: VmTarget, event_type: str, action: str = "none", **details: Any) -> None:
    ts = now_utc()
    status = details.pop("status", None)
    vm_state = details.pop("vm_state", None)
    task_state = details.pop("task_state", None)
    with db() as conn:
        conn.execute(
            """
            INSERT INTO recovery_events
            (created_at, vm_identifier, vm_name, address, event_type, status, vm_state, task_state, action, details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts, target.identifier, target.display_name, target.address,
                event_type, status, vm_state, task_state, action,
                json.dumps(details, ensure_ascii=True),
            ),
        )
        conn.execute(
            "UPDATE managed_vms SET last_outcome=?, last_checked_at=?, updated_at=? WHERE identifier=?",
            (event_type, ts, ts, target.identifier),
        )


def normalize_suppression(identifier: str) -> None:
    with db() as conn:
        row = conn.execute(
            "SELECT suppressed, suppressed_until FROM managed_vms WHERE identifier=?",
            (identifier,),
        ).fetchone()
        if row and row["suppressed"] and row["suppressed_until"] and row["suppressed_until"] <= now_utc():
            conn.execute(
                "UPDATE managed_vms SET suppressed=0, suppressed_reason=NULL, suppressed_until=NULL, updated_at=? WHERE identifier=?",
                (now_utc(), identifier),
            )


def suppression_state(identifier: str) -> tuple[bool, str | None, str | None]:
    normalize_suppression(identifier)
    with db() as conn:
        row = conn.execute(
            "SELECT suppressed, suppressed_reason, suppressed_until FROM managed_vms WHERE identifier=?",
            (identifier,),
        ).fetchone()
    if not row:
        return False, None, None
    return bool(row["suppressed"]), row["suppressed_reason"], row["suppressed_until"]


def run_cmd(cmd: list[str], timeout: int) -> str:
    log("debug", "Executing command", command=" ".join(shlex.quote(x) for x in cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)} stdout={result.stdout} stderr={result.stderr}")
    return result.stdout


def ping_ok(address: str) -> bool:
    if platform.system().lower() == "windows":
        cmd = ["ping", "-n", str(PING_COUNT), "-w", str(PING_TIMEOUT_SEC * 1000), address]
    else:
        cmd = ["ping", "-c", str(PING_COUNT), "-W", str(PING_TIMEOUT_SEC), address]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.returncode == 0


def openstack_base() -> list[str]:
    cmd = ["openstack"]
    os_cloud = os.getenv("OS_CLOUD", "").strip()
    if os_cloud:
        cmd += ["--os-cloud", os_cloud]
    return cmd


def openstack_show(target: VmTarget) -> dict[str, Any]:
    data = json.loads(run_cmd(openstack_base() + ["server", "show", target.identifier, "-f", "json"], OPENSTACK_TIMEOUT_SEC))
    if target.project_id and str(data.get("project_id", "")).strip() not in {"", target.project_id}:
        raise RuntimeError(f"project mismatch for {target.identifier}")
    return data


def soft_reboot(target: VmTarget) -> None:
    run_cmd(openstack_base() + ["server", "reboot", "--soft", target.identifier], OPENSTACK_TIMEOUT_SEC)


def evaluate(target: VmTarget) -> str:
    if ping_ok(target.address):
        set_failure_count(target.identifier, 0)
        clear_unresponsive(target.identifier)
        record_event(target, "ping_ok")
        return "ping_ok"

    suppressed, reason, until = suppression_state(target.identifier)
    if suppressed:
        set_failure_count(target.identifier, 0)
        record_event(target, "suppressed_skip", reason=reason, until=until)
        return "suppressed_skip"

    recovery_pending, unresponsive, unresponsive_reason, unresponsive_since = recovery_state(target.identifier)
    reboot_on_active = reboot_on_active_state(target.identifier)
    if unresponsive:
        record_event(
            target,
            "unresponsive_skip",
            reason=unresponsive_reason,
            unresponsive_since=unresponsive_since,
        )
        return "unresponsive_skip"

    streak = failure_count(target.identifier) + 1
    set_failure_count(target.identifier, streak)
    if streak < FAILURE_THRESHOLD:
        record_event(target, "grace_skip", failure_streak=streak, threshold=FAILURE_THRESHOLD)
        return "grace_skip"

    data = openstack_show(target)
    status = str(data.get("status", "")).strip().upper()
    vm_state = str(data.get("OS-EXT-STS:vm_state", "")).strip().lower()
    task_state = str(data.get("OS-EXT-STS:task_state", "")).strip().lower()

    should_reboot = task_state in {"", "none", "null"} and (status != "ACTIVE" or reboot_on_active)

    if should_reboot:
        if recovery_pending:
            reason = "still failing after previous reboot attempt"
            mark_unresponsive(target.identifier, reason)
            record_event(
                target,
                "marked_unresponsive",
                action="classify_unresponsive",
                status=status,
                vm_state=vm_state,
                task_state=task_state,
                failure_streak=streak,
                reason=reason,
                reboot_on_active=reboot_on_active,
            )
            return "marked_unresponsive"
        soft_reboot(target)
        set_recovery_pending(target.identifier, True)
        record_event(
            target, "reboot_requested", action="soft_reboot",
            status=status, vm_state=vm_state, task_state=task_state, failure_streak=streak, reboot_on_active=reboot_on_active
        )
        return "reboot_requested"

    record_event(
        target, "no_action",
        status=status, vm_state=vm_state, task_state=task_state, failure_streak=streak, reboot_on_active=reboot_on_active
    )
    return "no_action"


def run_once() -> int:
    ensure_db()
    targets = sync_targets()
    counts = {
        "ping_ok": 0,
        "suppressed_skip": 0,
        "unresponsive_skip": 0,
        "grace_skip": 0,
        "reboot_requested": 0,
        "marked_unresponsive": 0,
        "no_action": 0,
        "error": 0,
    }
    for index, target in enumerate(targets):
        try:
            outcome = evaluate(target)
            counts[outcome] += 1
        except Exception as exc:
            counts["error"] += 1
            record_event(target, "error", error=str(exc))
            log("error", "Target evaluation failed", vm=target.display_name, error=str(exc))
        if index != len(targets) - 1 and SLEEP_BETWEEN_TARGETS_SEC > 0:
            time.sleep(SLEEP_BETWEEN_TARGETS_SEC)
    log("info", "Run completed", total_targets=len(targets), **counts)
    return 0 if counts["error"] == 0 else 1


def h(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def rows_and_events() -> tuple[list[sqlite3.Row], list[sqlite3.Row]]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT m.*, e.status, e.vm_state, e.task_state
            FROM managed_vms m
            LEFT JOIN recovery_events e ON e.id = (
              SELECT id FROM recovery_events x WHERE x.vm_identifier=m.identifier ORDER BY id DESC LIMIT 1
            )
            ORDER BY m.name IS NULL, m.name, m.identifier
            """
        ).fetchall()
        events = conn.execute(
            "SELECT created_at, vm_name, vm_identifier, event_type, status, action FROM recovery_events ORDER BY id DESC LIMIT 100"
        ).fetchall()
    return rows, events


def get_vm_detail(identifier: str) -> tuple[sqlite3.Row | None, list[sqlite3.Row]]:
    with db() as conn:
        row = conn.execute(
            """
            SELECT m.*, e.status, e.vm_state, e.task_state
            FROM managed_vms m
            LEFT JOIN recovery_events e ON e.id = (
              SELECT id FROM recovery_events x WHERE x.vm_identifier=m.identifier ORDER BY id DESC LIMIT 1
            )
            WHERE m.identifier = ?
            """,
            (identifier,),
        ).fetchone()
        events = conn.execute(
            """
            SELECT created_at, vm_name, vm_identifier, event_type, status, action
            FROM recovery_events
            WHERE vm_identifier = ?
            ORDER BY id DESC
            LIMIT 50
            """,
            (identifier,),
        ).fetchall()
    return row, events


def render_outcome_badge(outcome: str | None) -> str:
    if not outcome:
        return "-"
    highlight = {"suppression_updated", "active_reboot_policy_updated"}
    klass = "badge-event" if outcome in highlight else "badge-muted"
    return f"<span class='badge {klass}'>{h(outcome)}</span>"


def matches_filter(row: sqlite3.Row, query: str, status_filter: str) -> bool:
    haystack = " ".join(
        str(value or "")
        for value in [
            row["name"],
            row["identifier"],
            row["address"],
            row["last_outcome"],
            row["unresponsive_reason"],
            row["suppressed_reason"],
        ]
    ).lower()
    if query and query not in haystack:
        return False

    if status_filter == "suppressed":
        return bool(row["suppressed"])
    if status_filter == "unresponsive":
        return bool(row["unresponsive"])
    if status_filter == "active-reboot":
        return bool(row["reboot_on_active"])
    if status_filter == "enabled":
        return not bool(row["suppressed"]) and not bool(row["unresponsive"])
    return True


def dashboard_html(search: str = "", status_filter: str = "all") -> bytes:
    rows, events = rows_and_events()
    normalized_search = search.strip().lower()
    filtered_rows = [row for row in rows if matches_filter(row, normalized_search, status_filter)]
    vm_rows = []
    for row in filtered_rows:
        state = " / ".join(x for x in [row["status"], row["vm_state"], row["task_state"]] if x) or "-"
        vm_name = row["name"] or row["identifier"]
        reboot_policy = "REBOOT" if row["reboot_on_active"] else "NO REBOOT"
        status_label = "Unresponsive" if row["unresponsive"] else "Suppressed" if row["suppressed"] else "Enabled"
        status_class = "badge-danger" if row["unresponsive"] else "badge-warn" if row["suppressed"] else "badge-ok"
        reboot_policy_class = "badge-accent" if row["reboot_on_active"] else "badge-muted"
        vm_rows.append(
            "<tr class='vm-row'>"
            f"<td class='vm-cell'><strong><a class='vm-link' href='/vm/{quote(row['identifier'], safe='')}'>{h(vm_name)}</a></strong><div class='sub'>{h(row['identifier'])}</div></td>"
            f"<td>{h(row['address'])}</td>"
            f"<td><span class='badge {status_class}'>{h(status_label)}</span></td>"
            f"<td><span class='badge {reboot_policy_class}'>{h(reboot_policy)}</span></td>"
            f"<td>{h(row['consecutive_failures'])}</td>"
            f"<td>{render_outcome_badge(row['last_outcome'])}</td>"
            f"<td>{h(state)}</td>"
            f"<td>{h(row['unresponsive_reason'] or row['suppressed_reason'] or '-')}</td>"
            f"<td>{h(row['unresponsive_since'] or row['suppressed_until'] or '-')}</td>"
            "</tr>"
        )
    summary_cards = (
        f"<div class='stat-card'><div class='stat-label'>Managed</div><div class='stat-value'>{len(rows)}</div></div>"
        f"<div class='stat-card'><div class='stat-label'>Filtered</div><div class='stat-value'>{len(filtered_rows)}</div></div>"
        f"<div class='stat-card'><div class='stat-label'>Suppressed</div><div class='stat-value'>{sum(1 for r in rows if r['suppressed'])}</div></div>"
        f"<div class='stat-card'><div class='stat-label'>Unresponsive</div><div class='stat-value'>{sum(1 for r in rows if r['unresponsive'])}</div></div>"
        f"<div class='stat-card'><div class='stat-label'>Recent Events</div><div class='stat-value'>{len(events)}</div></div>"
    )
    page = f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>OpenStack VM Recovery</title>
<style>
body{{font-family:Georgia,"Noto Serif KR",serif;margin:0;background:#f5f8f3;color:#18251c}} .wrap{{max-width:1280px;margin:0 auto;padding:24px}}
.hero{{background:linear-gradient(135deg,#1d5b42,#2f8a63);color:#fff;padding:24px;border-radius:20px}} .hero h1{{margin:0 0 8px}} .hero p{{margin:0}}
.hero form{{margin:0}} button,.hero a.button{{background:#1d7b52;color:#fff;border:0;border-radius:10px;padding:10px 14px;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;line-height:1.2;font:inherit;box-sizing:border-box;min-height:42px}}
.hero button.secondary, button.secondary{{background:#c8d0cb;color:#314038}}
.badge{{display:inline-block;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:600}}
.badge-ok{{background:#dff3e7;color:#17603d}}
.badge-warn{{background:#fff2cc;color:#8a6300}}
.badge-danger{{background:#f8d7da;color:#842029}}
.badge-accent{{background:#dce8ff;color:#1d4ed8}}
.badge-muted{{background:#eceff1;color:#54606b}}
.badge-event{{background:#e6f4ea;color:#1f6b3b}}
table{{width:100%;border-collapse:separate;border-spacing:0;background:#fff;margin-top:18px;border-radius:16px;overflow:hidden}} th,td{{padding:10px;border-bottom:1px solid #e7eee5;text-align:left;vertical-align:top;font-size:14px}}
th{{background:#f0f5ef}} input,select{{padding:8px;border:1px solid #cfd9cb;border-radius:8px;margin-right:6px;background:#fff}} .sub{{color:#6a786e;font-size:12px}} .meta{{margin-top:18px;color:#546257}}
.vm-row td{{background:#fff}}
.vm-row:nth-child(odd) td{{background:#fbfcfb}}
.vm-cell{{border-left:4px solid #2f8a63}}
.vm-link{{color:#173f2f;text-decoration:none}}
.vm-link:hover{{text-decoration:underline}}
.help-tip{{display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;margin-left:6px;border-radius:999px;background:#dce8ff;color:#1d4ed8;font-size:11px;font-weight:700;cursor:help;position:relative;vertical-align:middle}}
.help-tip::after{{content:attr(data-tip);position:absolute;left:50%;top:calc(100% + 10px);transform:translateX(-50%);min-width:270px;max-width:320px;white-space:pre-line;padding:10px 12px;border-radius:10px;background:#173f2f;color:#fff;font-size:12px;line-height:1.5;box-shadow:0 10px 30px rgba(0,0,0,.18);opacity:0;pointer-events:none;transition:opacity .15s ease}}
.help-tip:hover::after{{opacity:1}}
.toolbar{{display:flex;gap:10px;flex-wrap:wrap;align-items:stretch;margin-top:16px}}
.toolbar form{{display:flex;gap:10px;flex-wrap:wrap;align-items:stretch;margin:0}}
.toolbar input[type=text]{{min-width:280px}}
.toolbar > a.button{{align-self:stretch}}
.toolbar button,.toolbar a.button{{background:#173f2f}}
.summary-grid{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin-top:18px}}
.stat-card{{background:rgba(255,255,255,.14);backdrop-filter:blur(6px);border:1px solid rgba(255,255,255,.18);border-radius:16px;padding:14px 16px}}
.stat-label{{font-size:11px;letter-spacing:.08em;text-transform:uppercase;opacity:.85}}
.stat-value{{font-family:"Trebuchet MS","Segoe UI",sans-serif;font-size:30px;font-weight:700;line-height:1.1;margin-top:6px}}
@media (max-width: 980px) {{ .summary-grid{{grid-template-columns:repeat(2,minmax(0,1fr));}} }}
</style></head><body><div class='wrap'>
<div class='hero'><h1>OpenStack VM Recovery Console</h1><p>Checks every 10 minutes. Recovery starts only from the {FAILURE_THRESHOLD}rd consecutive ping failure. Intentionally stopped VMs can be suppressed here.</p><div class='toolbar'><form method='post' action='/sync'><button type='submit'>Sync Targets</button></form><form method='get' action='/'><input type='text' name='q' value='{h(search)}' placeholder='Search VM, address, outcome'><select name='status'><option value='all' {'selected' if status_filter == 'all' else ''}>All</option><option value='enabled' {'selected' if status_filter == 'enabled' else ''}>Enabled</option><option value='suppressed' {'selected' if status_filter == 'suppressed' else ''}>Suppressed</option><option value='unresponsive' {'selected' if status_filter == 'unresponsive' else ''}>Unresponsive</option><option value='active-reboot' {'selected' if status_filter == 'active-reboot' else ''}>Reboot ACTIVE</option></select><button type='submit'>Filter</button></form><a class='button' href='/history'>History</a></div><div class='summary-grid'>{summary_cards}</div></div>
<table><thead><tr><th>VM</th><th>Address</th><th>Suppression</th><th>ACTIVE Policy<span class='help-tip' data-tip='Openstack에서 Active 상태이나 VM이 비정상 상태일 경우 재기동을 하는지 여부&#10;&#10;NO REBOOT - 재부팅 X&#10;REBOOT - 재부팅 O'>?</span></th><th>Failure Streak</th><th>Last Outcome</th><th>OpenStack</th><th>Reason</th><th>Until</th></tr></thead><tbody>{''.join(vm_rows) or "<tr><td colspan='9'>No VMs</td></tr>"}</tbody></table>
</div></body></html>"""
    return page.encode("utf-8")


def vm_detail_html(identifier: str) -> bytes:
    row, events = get_vm_detail(identifier)
    if not row:
        return b"Not Found"
    vm_name = row["name"] or row["identifier"]
    state = " / ".join(x for x in [row["status"], row["vm_state"], row["task_state"]] if x) or "-"
    status_label = "Unresponsive" if row["unresponsive"] else "Suppressed" if row["suppressed"] else "Enabled"
    status_class = "badge-danger" if row["unresponsive"] else "badge-warn" if row["suppressed"] else "badge-ok"
    reboot_policy = "REBOOT" if row["reboot_on_active"] else "NO REBOOT"
    reboot_policy_class = "badge-accent" if row["reboot_on_active"] else "badge-muted"
    until_val = ((row["suppressed_until"] or "").replace("Z", ""))[:16]
    if row["unresponsive"]:
        state_action = (
            f"<form class='action-form' method='post' action='/vm/{quote(identifier, safe='')}/unresponsive'>"
            "<input type='hidden' name='enabled' value='0'>"
            "<button type='submit' class='secondary'>Clear Unresponsive</button></form>"
        )
    elif row["suppressed"]:
        state_action = (
            f"<form class='action-form' method='post' action='/vm/{quote(identifier, safe='')}/suppression'>"
            "<input type='hidden' name='enabled' value='0'>"
            "<button type='submit' class='secondary'>Disable Suppression</button></form>"
        )
    else:
        state_action = (
            f"<form class='action-form action-form-wide' method='post' action='/vm/{quote(identifier, safe='')}/suppression'>"
            "<input type='hidden' name='enabled' value='1'>"
            "<input name='reason' placeholder='Intentional shutdown' value='Intentional shutdown'>"
            f"<input name='until' type='datetime-local' value='{h(until_val)}'>"
            "<button type='submit'>Enable Suppression</button></form>"
        )
    active_button_class = "secondary" if row["reboot_on_active"] else ""
    active_policy_action = (
        f"<form class='action-form' method='post' action='/vm/{quote(identifier, safe='')}/active-reboot'>"
        f"<input type='hidden' name='enabled' value='{'0' if row['reboot_on_active'] else '1'}'>"
        f"<button type='submit' class='{active_button_class}'>{'Disable' if row['reboot_on_active'] else 'Enable'} ACTIVE Reboot</button></form>"
    )
    event_rows = "".join(
        f"<tr><td>{h(e['created_at'])}</td><td>{render_outcome_badge(e['event_type'])}</td><td>{h(e['status'] or '-')}</td><td>{h(e['action'] or '-')}</td></tr>"
        for e in events
    ) or "<tr><td colspan='4'>No events</td></tr>"
    page = f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>{h(vm_name)} - OpenStack VM Recovery</title>
<style>
body{{font-family:Georgia,"Noto Serif KR",serif;margin:0;background:#f5f8f3;color:#18251c}} .wrap{{max-width:1120px;margin:0 auto;padding:24px}}
.hero{{background:linear-gradient(135deg,#1d5b42,#2f8a63);color:#fff;padding:24px;border-radius:20px}} .hero h1{{margin:0 0 6px}} .hero a{{display:inline-block;margin-top:12px;background:#d8e2dc;color:#183126;text-decoration:none;padding:10px 14px;border-radius:10px}}
.grid{{display:grid;grid-template-columns:1.1fr .9fr;gap:18px;margin-top:18px}} .card{{background:#fff;border-radius:16px;padding:18px;border:1px solid #e3ebe0}}
.label{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#607064;margin-bottom:6px}} .value{{font-size:15px;margin-bottom:14px}}
.badge{{display:inline-block;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:600}} .badge-ok{{background:#dff3e7;color:#17603d}} .badge-warn{{background:#fff2cc;color:#8a6300}} .badge-danger{{background:#f8d7da;color:#842029}} .badge-accent{{background:#dce8ff;color:#1d4ed8}} .badge-muted{{background:#eceff1;color:#54606b}} .badge-event{{background:#e6f4ea;color:#1f6b3b}}
.help-tip{{display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;margin-left:6px;border-radius:999px;background:#dce8ff;color:#1d4ed8;font-size:11px;font-weight:700;cursor:help;position:relative;vertical-align:middle}}
.help-tip::after{{content:attr(data-tip);position:absolute;left:50%;top:calc(100% + 10px);transform:translateX(-50%);min-width:270px;max-width:320px;white-space:pre-line;padding:10px 12px;border-radius:10px;background:#173f2f;color:#fff;font-size:12px;line-height:1.5;box-shadow:0 10px 30px rgba(0,0,0,.18);opacity:0;pointer-events:none;transition:opacity .15s ease;z-index:10}}
.help-tip:hover::after{{opacity:1}}
button{{background:#1d7b52;color:#fff;border:0;border-radius:10px;padding:10px 14px;cursor:pointer}} button.secondary{{background:#c8d0cb;color:#314038}}
input{{padding:8px;border:1px solid #cfd9cb;border-radius:8px;background:#fff;width:100%;margin:0 0 8px}} .action-block{{margin-bottom:16px;padding:12px;border:1px solid #dde6da;border-radius:12px;background:#f8fbf7}}
table{{width:100%;border-collapse:separate;border-spacing:0;background:#fff;margin-top:18px;border-radius:16px;overflow:hidden}} th,td{{padding:10px;border-bottom:1px solid #e7eee5;text-align:left;font-size:14px}} th{{background:#f0f5ef}}
@media (max-width: 900px) {{ .grid{{grid-template-columns:1fr;}} }}
</style></head><body><div class='wrap'><div class='hero'><h1>{h(vm_name)}</h1><p>{h(row['identifier'])}</p><a href='/'>Back to Dashboard</a></div><div class='grid'><div class='card'><div class='label'>Address</div><div class='value'>{h(row['address'])}</div><div class='label'>Suppression</div><div class='value'><span class='badge {status_class}'>{h(status_label)}</span></div><div class='label'>ACTIVE Policy<span class='help-tip' data-tip='Openstack에서 Active 상태이나 VM이 비정상 상태일 경우 재기동을 하는지 여부&#10;&#10;NO REBOOT - 재부팅 X&#10;REBOOT - 재부팅 O'>?</span></div><div class='value'><span class='badge {reboot_policy_class}'>{h(reboot_policy)}</span></div><div class='label'>Failure Streak</div><div class='value'>{h(row['consecutive_failures'])}</div><div class='label'>Last Outcome</div><div class='value'>{render_outcome_badge(row['last_outcome'])}</div><div class='label'>OpenStack</div><div class='value'>{h(state)}</div><div class='label'>Reason</div><div class='value'>{h(row['unresponsive_reason'] or row['suppressed_reason'] or '-')}</div><div class='label'>Until</div><div class='value'>{h(row['unresponsive_since'] or row['suppressed_until'] or '-')}</div></div><div class='card'><div class='action-block'><div class='label'>Reboot Policy</div>{active_policy_action}</div><div class='action-block'><div class='label'>Server State</div>{state_action}</div></div></div><table><thead><tr><th>Time</th><th>Event</th><th>Status</th><th>Action</th></tr></thead><tbody>{event_rows}</tbody></table></div></body></html>"""
    return page.encode("utf-8")


def history_html() -> bytes:
    _, events = rows_and_events()
    event_rows = "".join(
        f"<tr><td>{h(e['created_at'])}</td><td>{h(e['vm_name'] or e['vm_identifier'])}</td><td>{render_outcome_badge(e['event_type'])}</td><td>{h(e['status'] or '-')}</td><td>{h(e['action'] or '-')}</td></tr>"
        for e in events
    ) or "<tr><td colspan='5'>No events</td></tr>"
    page = f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>OpenStack VM Recovery History</title>
<style>
body{{font-family:Georgia,"Noto Serif KR",serif;margin:0;background:#f5f8f3;color:#18251c}} .wrap{{max-width:1120px;margin:0 auto;padding:24px}}
.hero{{background:linear-gradient(135deg,#243b2f,#315a45);color:#fff;padding:22px;border-radius:18px}} .hero h1{{margin:0 0 6px}} .hero a{{display:inline-block;margin-top:12px;background:#d8e2dc;color:#183126;text-decoration:none;padding:10px 14px;border-radius:10px}}
.badge{{display:inline-block;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:600}} .badge-event{{background:#e6f4ea;color:#1f6b3b}} .badge-muted{{background:#eceff1;color:#54606b}}
table{{width:100%;border-collapse:separate;border-spacing:0;background:#fff;margin-top:18px;border-radius:16px;overflow:hidden}} th,td{{padding:10px;border-bottom:1px solid #e7eee5;text-align:left;vertical-align:top;font-size:14px}} th{{background:#f0f5ef}}
</style></head><body><div class='wrap'><div class='hero'><h1>Recovery History</h1><p>Recent event log for VM recovery decisions and policy changes.</p><a href='/'>Back to Dashboard</a></div><table><thead><tr><th>Time</th><th>VM</th><th>Event</th><th>Status</th><th>Action</th></tr></thead><tbody>{event_rows}</tbody></table></div></body></html>"""
    return page.encode("utf-8")


def normalize_until(raw: str) -> str | None:
    raw = raw.strip()
    if not raw:
        return None
    return raw + ":00Z" if len(raw) == 16 else raw


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            query = parse_qs(parsed.query, keep_blank_values=True)
            search = query.get("q", [""])[-1]
            status_filter = query.get("status", ["all"])[-1]
            body = dashboard_html(search=search, status_filter=status_filter)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path.startswith("/vm/"):
            vm_id = unquote(parsed.path[len("/vm/") :]).strip("/")
            if vm_id and "/" not in vm_id:
                body = vm_detail_html(vm_id)
                if body == b"Not Found":
                    self.send_error(404, "VM not found")
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
        if parsed.path == "/history":
            body = history_html()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/status":
            rows, events = rows_and_events()
            body = json.dumps({"managed_vms": [dict(x) for x in rows], "recent_events": [dict(x) for x in events]}, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/sync":
            sync_targets()
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
            return
        if parsed.path.startswith("/vm/") and parsed.path.endswith("/suppression"):
            vm_id = unquote(parsed.path[len("/vm/") : -len("/suppression")]).strip("/")
            length = int(self.headers.get("Content-Length", "0") or "0")
            form = {k: v[-1] for k, v in parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True).items()}
            enabled = form.get("enabled", "1") == "1"
            reason = (form.get("reason") or "").strip() or None
            until = normalize_until(form.get("until", ""))
            with db() as conn:
                row = conn.execute(
                    "SELECT identifier, name, address, server_id FROM managed_vms WHERE identifier=?",
                    (vm_id,),
                ).fetchone()
                if not row:
                    self.send_error(404, "VM not found")
                    return
                conn.execute(
                    "UPDATE managed_vms SET suppressed=?, suppressed_reason=?, suppressed_until=?, consecutive_failures=0, updated_at=? WHERE identifier=?",
                    (1 if enabled else 0, reason if enabled else None, until if enabled else None, now_utc(), vm_id),
                )
            record_event(VmTarget(address=row["address"], name=row["name"], server_id=row["server_id"]), "suppression_updated", action="enable" if enabled else "disable")
            self.send_response(303)
            self.send_header("Location", f"/vm/{quote(vm_id, safe='')}")
            self.end_headers()
            return
        if parsed.path.startswith("/vm/") and parsed.path.endswith("/unresponsive"):
            vm_id = unquote(parsed.path[len("/vm/") : -len("/unresponsive")]).strip("/")
            with db() as conn:
                row = conn.execute(
                    "SELECT identifier, name, address, server_id FROM managed_vms WHERE identifier=?",
                    (vm_id,),
                ).fetchone()
                if not row:
                    self.send_error(404, "VM not found")
                    return
            clear_unresponsive(vm_id)
            record_event(
                VmTarget(address=row["address"], name=row["name"], server_id=row["server_id"]),
                "unresponsive_cleared",
                action="clear_unresponsive",
            )
            self.send_response(303)
            self.send_header("Location", f"/vm/{quote(vm_id, safe='')}")
            self.end_headers()
            return
        if parsed.path.startswith("/vm/") and parsed.path.endswith("/active-reboot"):
            vm_id = unquote(parsed.path[len("/vm/") : -len("/active-reboot")]).strip("/")
            length = int(self.headers.get("Content-Length", "0") or "0")
            form = {k: v[-1] for k, v in parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True).items()}
            enabled = form.get("enabled", "0") == "1"
            with db() as conn:
                row = conn.execute(
                    "SELECT identifier, name, address, server_id FROM managed_vms WHERE identifier=?",
                    (vm_id,),
                ).fetchone()
                if not row:
                    self.send_error(404, "VM not found")
                    return
            set_reboot_on_active(vm_id, enabled)
            record_event(
                VmTarget(address=row["address"], name=row["name"], server_id=row["server_id"]),
                "active_reboot_policy_updated",
                action="enable_active_reboot" if enabled else "disable_active_reboot",
                reboot_on_active=enabled,
            )
            self.send_response(303)
            self.send_header("Location", f"/vm/{quote(vm_id, safe='')}")
            self.end_headers()
            return
        self.send_error(404)

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def serve_web() -> int:
    ensure_db()
    try:
        sync_targets()
    except Exception as exc:
        log("warning", "Initial sync skipped", error=str(exc))
    server = ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), Handler)
    log("info", "Starting web console", port=HTTP_PORT, db_path=DB_PATH)
    server.serve_forever()
    return 0


def print_manifest() -> None:
    sample = [{"name": "vm-example-01", "address": "10.0.0.11"}]
    print(
        "apiVersion: v1\nkind: PersistentVolumeClaim\nmetadata:\n  name: openstack-vm-recovery-data\nspec:\n"
        "  accessModes: [\"ReadWriteOnce\"]\n  resources:\n    requests:\n      storage: 2Gi\n---\n"
        "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: openstack-vm-recovery-config\ndata:\n  targets.json: |\n"
        + "\n".join("    " + line for line in json.dumps(sample, indent=2, ensure_ascii=True).splitlines())
        + "\n---\napiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: openstack-vm-recovery-web\nspec:\n  replicas: 1\n"
        "  selector:\n    matchLabels:\n      app: openstack-vm-recovery-web\n  template:\n    metadata:\n      labels:\n        app: openstack-vm-recovery-web\n    spec:\n      containers:\n        - name: web\n"
        "          image: registry.example.com/opencloud/openstack-vm-recovery:0.3.0\n          command: [\"python\", \"/app/openstack_vm_recovery.py\", \"serve-web\"]\n          ports:\n            - containerPort: 9088\n"
        f"          env:\n            - name: DB_PATH\n              value: /data/openstack_vm_recovery.db\n            - name: VM_TARGETS_FILE\n              value: /config/targets.json\n            - name: FAILURE_THRESHOLD\n              value: \"{FAILURE_THRESHOLD}\"\n"
        "          volumeMounts:\n            - name: config\n              mountPath: /config\n              readOnly: true\n            - name: data\n              mountPath: /data\n"
        "      volumes:\n        - name: config\n          configMap:\n            name: openstack-vm-recovery-config\n        - name: data\n          persistentVolumeClaim:\n            claimName: openstack-vm-recovery-data\n---\n"
        "apiVersion: v1\nkind: Service\nmetadata:\n  name: openstack-vm-recovery-web\nspec:\n  selector:\n    app: openstack-vm-recovery-web\n  ports:\n    - name: http\n      port: 80\n      targetPort: 9088\n---\n"
        "apiVersion: batch/v1\nkind: CronJob\nmetadata:\n  name: openstack-vm-recovery\nspec:\n"
        f"  schedule: \"{CRON_SCHEDULE}\"\n  concurrencyPolicy: Forbid\n  jobTemplate:\n    spec:\n      template:\n        spec:\n          restartPolicy: Never\n          containers:\n            - name: recovery\n              image: registry.example.com/opencloud/openstack-vm-recovery:0.3.0\n              command: [\"python\", \"/app/openstack_vm_recovery.py\", \"run\"]\n              env:\n                - name: DB_PATH\n                  value: /data/openstack_vm_recovery.db\n                - name: VM_TARGETS_FILE\n                  value: /config/targets.json\n                - name: FAILURE_THRESHOLD\n                  value: \"{FAILURE_THRESHOLD}\"\n"
        "              volumeMounts:\n                - name: config\n                  mountPath: /config\n                  readOnly: true\n                - name: data\n                  mountPath: /data\n"
        "          volumes:\n            - name: config\n              configMap:\n                name: openstack-vm-recovery-config\n            - name: data\n              persistentVolumeClaim:\n                claimName: openstack-vm-recovery-data\n"
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run")
    sub.add_parser("serve-web")
    sub.add_parser("sync-targets")
    sub.add_parser("print-k8s-manifest")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.cmd == "run":
        return run_once()
    if args.cmd == "serve-web":
        return serve_web()
    if args.cmd == "sync-targets":
        ensure_db()
        sync_targets()
        return 0
    print_manifest()
    return 0


if __name__ == "__main__":
    sys.exit(main())
