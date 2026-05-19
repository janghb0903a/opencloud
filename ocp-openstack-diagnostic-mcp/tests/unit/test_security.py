from __future__ import annotations

from ocp_openstack_diagnostic_mcp.policy import PolicyGuard
from ocp_openstack_diagnostic_mcp.redaction import redact


def test_unknown_cloud_rejected(service):
    response = service.cloud_get("unknown")
    assert response["error"]["code"] == "unknown_cloud"


def test_secret_redaction():
    payload = {
        "password": "pw",
        "application_credential_secret": "secret",
        "headers": {"X-Auth-Token": "token"},
        "log": "Authorization: Bearer abc123",
    }
    redacted = redact(payload)
    assert redacted["password"] == "[REDACTED]"
    assert redacted["application_credential_secret"] == "[REDACTED]"
    assert redacted["headers"]["X-Auth-Token"] == "[REDACTED]"
    assert "abc123" not in redacted["log"]


def test_forbidden_operation():
    guard = PolicyGuard({})
    try:
        guard.ensure_read_only_operation("server.delete")
    except Exception as exc:
        assert getattr(exc, "code") == "forbidden_operation"
    else:
        raise AssertionError("expected forbidden operation")


def test_cli_command_denylist(runtime_config):
    guard = PolicyGuard(runtime_config.policies)
    try:
        guard.ensure_cli_allowed(["openstack", "server", "delete", "vm1"], runtime_config.cli_allowlist)
    except Exception as exc:
        assert getattr(exc, "code") == "forbidden_cli_command"
    else:
        raise AssertionError("expected forbidden CLI command")


def test_no_k8s_mcp_imports_in_source():
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[2] / "src"
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.py"))
    assert "ocp_k8s_diagnostic_mcp" not in source

