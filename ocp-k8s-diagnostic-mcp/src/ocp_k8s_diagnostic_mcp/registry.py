from __future__ import annotations

from .config import ClusterConfig, RuntimeConfig
from .errors import DiagnosticError


class ClusterRegistry:
    def __init__(self, config: RuntimeConfig):
        self._clusters = config.clusters

    @property
    def allowed_cluster_ids(self) -> set[str]:
        return set(self._clusters)

    def get(self, cluster_id: str) -> ClusterConfig:
        if cluster_id not in self._clusters:
            raise DiagnosticError("unknown_cluster", f"cluster_id is not allowed: {cluster_id}", {"cluster_id": cluster_id})
        return self._clusters[cluster_id]

