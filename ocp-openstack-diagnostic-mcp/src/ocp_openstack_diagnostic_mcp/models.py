from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CloudInput(BaseModel):
    cloud_id: str


class ProjectInput(CloudInput):
    project_id: str | None = None
    project_name: str | None = None


class ServerInput(CloudInput):
    server_id: str


class HostInput(CloudInput):
    host: str


class HypervisorInput(CloudInput):
    hypervisor_id: str


class NetworkInput(CloudInput):
    network_id: str | None = None


class PortInput(CloudInput):
    port_id: str


class RouterInput(CloudInput):
    router_id: str


class FloatingIPInput(CloudInput):
    floatingip_id: str


class VolumeInput(CloudInput):
    volume_id: str


class ImageInput(CloudInput):
    image_id: str


class ResourceProviderInput(CloudInput):
    resource_provider_id: str


class ListInput(CloudInput):
    limit: int | None = Field(default=200, ge=1, le=500)


class RunbookSearchInput(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=25)


class RunbookGetInput(BaseModel):
    runbook_id: str


class DiagnosticResponse(BaseModel):
    cloud_id: str
    context_used: dict[str, Any] = Field(default_factory=dict)
    data_sources: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    result: dict[str, Any] = Field(default_factory=dict)
    linked_k8s: dict[str, Any] | None = None
    recommended_next_tools: list[dict[str, Any]] = Field(default_factory=list)
    trace_id: str | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)

