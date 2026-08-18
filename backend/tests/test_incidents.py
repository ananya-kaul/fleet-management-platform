"""Driver issue reporting and fleet manager triage."""

from tests.conftest import API


def _issue(vehicle_id, **overrides):
    payload = {
        "vehicle_id": vehicle_id,
        "title": "Warning light on the dashboard",
        "description": "Engine temperature warning came on near Hosur.",
        "severity": "HIGH",
    }
    payload.update(overrides)
    return payload


def test_a_driver_can_report_an_issue(client, driver_headers, driver, vehicle):
    response = client.post(
        f"{API}/incidents", json=_issue(vehicle["id"]), headers=driver_headers
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "OPEN"
    assert body["severity"] == "HIGH"
    assert body["reported_by_driver_id"] == driver.id


def test_reporting_an_issue_notifies_the_fleet_manager(
    client, manager_headers, driver_headers, vehicle
):
    client.post(f"{API}/incidents", json=_issue(vehicle["id"]), headers=driver_headers)
    notifications = client.get(f"{API}/notifications", headers=manager_headers).json()
    assert any(item["category"] == "INCIDENT_REPORTED" for item in notifications)


def test_an_issue_can_be_tied_to_a_trip(client, driver_headers, trip):
    client.post(
        f"{API}/trips/{trip['id']}/start",
        json={"start_odometer": 48250, "start_latitude": 12.9, "start_longitude": 77.5},
        headers=driver_headers,
    )
    response = client.post(
        f"{API}/incidents",
        json=_issue(trip["vehicle_id"], trip_id=trip["id"]),
        headers=driver_headers,
    )
    assert response.status_code == 201
    assert response.json()["trip_id"] == trip["id"]


def test_a_trip_belonging_to_another_vehicle_is_rejected(
    client, manager_headers, driver_headers, trip, vehicle_payload
):
    other = client.post(
        f"{API}/vehicles",
        json={**vehicle_payload, "registration_number": "KA-06-KL-2345"},
        headers=manager_headers,
    ).json()

    response = client.post(
        f"{API}/incidents",
        json=_issue(other["id"], trip_id=trip["id"]),
        headers=driver_headers,
    )
    assert response.status_code == 409


def test_a_manager_can_assign_and_resolve_an_incident(
    client, manager_headers, driver_headers, manager, vehicle
):
    created = client.post(
        f"{API}/incidents", json=_issue(vehicle["id"]), headers=driver_headers
    ).json()

    assigned = client.put(
        f"{API}/incidents/{created['id']}",
        json={"status": "IN_PROGRESS", "assigned_to_user_id": manager.id},
        headers=manager_headers,
    )
    assert assigned.json()["status"] == "IN_PROGRESS"
    assert assigned.json()["assigned_to_user_id"] == manager.id

    resolved = client.put(
        f"{API}/incidents/{created['id']}",
        json={"status": "RESOLVED", "resolution_notes": "Coolant topped up"},
        headers=manager_headers,
    )
    assert resolved.json()["status"] == "RESOLVED"
    assert resolved.json()["resolved_at"] is not None


def test_a_resolved_incident_cannot_be_reopened(
    client, manager_headers, driver_headers, vehicle
):
    created = client.post(
        f"{API}/incidents", json=_issue(vehicle["id"]), headers=driver_headers
    ).json()
    client.put(
        f"{API}/incidents/{created['id']}", json={"status": "RESOLVED"}, headers=manager_headers
    )

    response = client.put(
        f"{API}/incidents/{created['id']}", json={"status": "OPEN"}, headers=manager_headers
    )
    assert response.status_code == 409


def test_incidents_can_be_filtered_by_status(client, manager_headers, driver_headers, vehicle):
    first = client.post(
        f"{API}/incidents", json=_issue(vehicle["id"]), headers=driver_headers
    ).json()
    client.post(
        f"{API}/incidents",
        json=_issue(vehicle["id"], title="Brake noise", severity="MEDIUM"),
        headers=driver_headers,
    )
    client.put(
        f"{API}/incidents/{first['id']}", json={"status": "RESOLVED"}, headers=manager_headers
    )

    open_only = client.get(f"{API}/incidents?status_filter=OPEN", headers=manager_headers)
    assert open_only.json()["total"] == 1


def test_a_driver_only_sees_their_own_reports(
    client, db_session, manager_headers, driver_headers, driver, second_driver, vehicle
):
    client.post(f"{API}/incidents", json=_issue(vehicle["id"]), headers=driver_headers)

    from datetime import datetime, timezone

    from app.models import Incident, IncidentSeverity

    db_session.add(
        Incident(
            vehicle_id=vehicle["id"],
            reported_by_driver_id=second_driver.id,
            title="Someone else's report",
            severity=IncidentSeverity.LOW,
            reported_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    assert client.get(f"{API}/incidents", headers=driver_headers).json()["total"] == 1
    assert client.get(f"{API}/incidents", headers=manager_headers).json()["total"] == 2


def test_a_driver_cannot_triage_an_incident(client, driver_headers, vehicle):
    created = client.post(
        f"{API}/incidents", json=_issue(vehicle["id"]), headers=driver_headers
    ).json()
    response = client.put(
        f"{API}/incidents/{created['id']}", json={"status": "RESOLVED"}, headers=driver_headers
    )
    assert response.status_code == 403


def test_an_unknown_severity_is_rejected(client, driver_headers, vehicle):
    response = client.post(
        f"{API}/incidents", json=_issue(vehicle["id"], severity="APOCALYPTIC"),
        headers=driver_headers,
    )
    assert response.status_code == 422


def test_open_incidents_appear_on_the_dashboard(client, manager_headers, driver_headers, vehicle):
    client.post(f"{API}/incidents", json=_issue(vehicle["id"]), headers=driver_headers)
    dashboard = client.get(f"{API}/dashboard", headers=manager_headers).json()
    assert dashboard["open_incidents"] == 1
    assert len(dashboard["recent_incidents"]) == 1
