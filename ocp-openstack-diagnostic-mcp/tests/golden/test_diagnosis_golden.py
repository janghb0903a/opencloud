from __future__ import annotations


def reasons(response):
    return [item["reason"] for item in response["result"]["findings"]]


def test_no_valid_host_diagnosis(service):
    response = service.nova_diagnose_no_valid_host("test-mgmt-02")
    assert response["cloud_id"] == "test-mgmt-02"
    assert "NoObviousNoValidHostSignal" in reasons(response)


def test_vm_error_diagnosis(service):
    response = service.nova_diagnose_server("test-mgmt-02", "vm-error")
    assert "ServerError" in reasons(response)
    assert response["result"]["server"]["fault"]["message"] == "NoValidHost"


def test_vm_network_issue_diagnosis(service):
    response = service.neutron_diagnose_vm_network("test-mgmt-02", "vm-error")
    assert "PortsDownOrError" in reasons(response)


def test_volume_attach_failed_diagnosis(service):
    response = service.cinder_diagnose_attachment("test-mgmt-02", "vol-error")
    assert "VolumeError" in reasons(response)


def test_powerflex_backend_issue_diagnosis(service):
    response = service.cinder_diagnose_powerflex("test-mgmt-02")
    assert "CinderServiceDown" in reasons(response)
    assert "PowerFlexPoolLowCapacity" in reasons(response)

