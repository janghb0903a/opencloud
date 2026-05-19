from __future__ import annotations

import os
import subprocess
from collections.abc import Iterable
from typing import Any

import httpx
import openstack

from .config import CloudConfig, resolve_ref
from .errors import DiagnosticError
from .policy import PolicyGuard
from .redaction import redact


class OpenStackClientFactory:
    def create(self, cloud: CloudConfig):
        clouds_file = resolve_ref(cloud.clouds_yaml_ref)
        old_config = os.environ.get("OS_CLIENT_CONFIG_FILE")
        if clouds_file:
            os.environ["OS_CLIENT_CONFIG_FILE"] = clouds_file
        try:
            return openstack.connect(cloud=cloud.cloud, region_name=cloud.region_name, interface=cloud.interface)
        except Exception as exc:  # pragma: no cover - integration path
            raise DiagnosticError("openstack_auth_failed", "Failed to create OpenStack SDK connection", {"cloud_id": cloud.cloud_id}) from exc
        finally:
            if old_config is None:
                os.environ.pop("OS_CLIENT_CONFIG_FILE", None)
            else:
                os.environ["OS_CLIENT_CONFIG_FILE"] = old_config


class RestClient:
    def __init__(self, conn: Any, timeout_seconds: int = 20):
        self.conn = conn
        self.timeout_seconds = timeout_seconds

    def get(self, service_type: str, path: str, microversion: str | None = None) -> dict[str, Any]:
        endpoint = self.conn.endpoint_for(service_type=service_type)
        token = self.conn.authorize()
        headers = {"X-Auth-Token": token}
        if microversion and service_type == "placement":
            headers["OpenStack-API-Version"] = f"placement {microversion}"
        try:
            with httpx.Client(timeout=self.timeout_seconds) as http:
                response = http.get(f"{endpoint.rstrip('/')}/{path.lstrip('/')}", headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            raise DiagnosticError("openstack_rest_error", f"OpenStack REST request failed for {service_type}") from exc


class SafeCliRunner:
    def __init__(self, policy: PolicyGuard, allowlist: dict[str, Any]):
        self.policy = policy
        self.allowlist = allowlist

    def run(self, argv: list[str], env: dict[str, str] | None = None) -> dict[str, Any]:
        self.policy.ensure_cli_allowed(argv, self.allowlist)
        try:
            completed = subprocess.run(
                argv,
                shell=False,
                env=env,
                text=True,
                capture_output=True,
                timeout=self.policy.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise DiagnosticError("cli_timeout", "OpenStack CLI fallback timed out") from exc
        stdout = (completed.stdout or "")[: self.policy.stdout_limit_bytes]
        stderr = (completed.stderr or "")[: self.policy.stdout_limit_bytes]
        return {"returncode": completed.returncode, "stdout": redact(stdout), "stderr": redact(stderr)}


def serialize(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): serialize(v) for k, v in obj.items() if not str(k).startswith("_")}
    if isinstance(obj, (list, tuple, set)):
        return [serialize(item) for item in obj]
    if hasattr(obj, "to_dict"):
        return serialize(obj.to_dict())
    if hasattr(obj, "__dict__"):
        return {key: serialize(value) for key, value in vars(obj).items() if not key.startswith("_")}
    return str(obj)


def limited(items: Iterable[Any], limit: int) -> list[Any]:
    result = []
    for item in items:
        result.append(serialize(item))
        if len(result) >= limit:
            break
    return result

