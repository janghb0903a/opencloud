from __future__ import annotations


def test_linked_k8s_and_recommended_tools(service):
    response = service.nova_diagnose_no_valid_host("test-mgmt-02")
    assert response["linked_k8s"]["mcp_server"] == "ocp-k8s-diagnostic-mcp"
    assert response["linked_k8s"]["cluster_id"] == "test-mgmt-02"
    assert response["recommended_next_tools"][0]["tool"] == "k8s.get_pods"
    assert response["recommended_next_tools"][0]["arguments"]["cluster_id"] == "test-mgmt-02"

