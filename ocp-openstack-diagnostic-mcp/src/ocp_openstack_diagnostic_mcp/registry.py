from __future__ import annotations

from .config import CloudConfig, RuntimeConfig
from .errors import DiagnosticError


class CloudRegistry:
    def __init__(self, config: RuntimeConfig):
        self._clouds = config.clouds

    @property
    def cloud_ids(self) -> set[str]:
        return set(self._clouds)

    def get(self, cloud_id: str) -> CloudConfig:
        if cloud_id not in self._clouds:
            raise DiagnosticError("unknown_cloud", f"cloud_id is not allowed: {cloud_id}", {"cloud_id": cloud_id})
        return self._clouds[cloud_id]

