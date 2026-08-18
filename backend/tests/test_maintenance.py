"""Maintenance records and the due-for-service rule."""

from datetime import date, timedelta

from tests.conftest import API


def _record(vehicle_id, **overrides):
    payload = {
        "vehicle_id": vehicle_id,
        "maintenance_type": "OIL_CHANGE",
        "description": "Engine oil and filter replacement",
        "service_date": str(date.today() - timedelta(days=30)),
        "cost": 4200,
        "odometer": 45000,
        "next_service_date": str(date.today() + timedelta(days=150)),
        "next_service_mileage": 55000,
    }
    payload.update(overrides)
    return payload


def test_create_a_maintenance_record(client, manager_headers, vehicle):
    response = client.post(
        f"{API}/maintenance", json=_record(vehicle["id"]), headers=manager_headers
    )
    assert response.status_code == 201
    body = response.json()
    assert body["maintenance_type"] == "OIL_CHANGE"
    assert body["cost"] == 4200


def test_a_record_can_move_the_vehicle_into_maintenance(
    client, manager_headers, vehicle
):
    client.post(
        f"{API}/maintenance",
        json=_record(vehicle["id"], set_vehicle_in_maintenance=True),
        headers=manager_headers,
    )
    response = client.get(f"{API}/vehicles/{vehicle['id']}", headers=manager_headers)
    assert response.json()["status"] == "IN_MAINTENANCE"


def test_a_higher_service_odometer_updates_the_vehicle_mileage(
    client, manager_headers, vehicle
):
    client.post(
        f"{API}/maintenance", json=_record(vehicle["id"], odometer=60000), headers=manager_headers
    )
    response = client.get(f"{API}/vehicles/{vehicle['id']}", headers=manager_headers)
    assert response.json()["current_mileage"] == 60000


def test_a_vehicle_is_due_when_the_next_service_date_is_near(
    client, manager_headers, vehicle
):
    client.post(
        f"{API}/maintenance",
        json=_record(vehicle["id"], next_service_date=str(date.today() + timedelta(days=3))),
        headers=manager_headers,
    )
    due = client.get(f"{API}/maintenance/due", headers=manager_headers).json()
    assert len(due) == 1
    assert due[0]["vehicle_id"] == vehicle["id"]
    assert due[0]["due_date"] is not None


def test_a_vehicle_is_due_when_the_odometer_passes_the_service_mileage(
    client, manager_headers, vehicle
):
    client.post(
        f"{API}/maintenance",
        json=_record(
            vehicle["id"],
            odometer=48000,
            next_service_date=str(date.today() + timedelta(days=300)),
            next_service_mileage=47000,
        ),
        headers=manager_headers,
    )
    due = client.get(f"{API}/maintenance/due", headers=manager_headers).json()
    assert len(due) == 1
    assert due[0]["due_mileage"] == 47000


def test_a_recently_serviced_vehicle_is_not_due(client, manager_headers, vehicle):
    client.post(
        f"{API}/maintenance",
        json=_record(
            vehicle["id"],
            next_service_date=str(date.today() + timedelta(days=300)),
            next_service_mileage=999999,
        ),
        headers=manager_headers,
    )
    assert client.get(f"{API}/maintenance/due", headers=manager_headers).json() == []


def test_only_the_latest_record_decides_whether_a_vehicle_is_due(
    client, manager_headers, vehicle
):
    """An old overdue record must not keep a freshly serviced vehicle on the list."""
    client.post(
        f"{API}/maintenance",
        json=_record(
            vehicle["id"],
            service_date=str(date.today() - timedelta(days=200)),
            next_service_date=str(date.today() - timedelta(days=100)),
            next_service_mileage=None,
        ),
        headers=manager_headers,
    )
    client.post(
        f"{API}/maintenance",
        json=_record(
            vehicle["id"],
            service_date=str(date.today() - timedelta(days=2)),
            next_service_date=str(date.today() + timedelta(days=300)),
            next_service_mileage=999999,
        ),
        headers=manager_headers,
    )
    assert client.get(f"{API}/maintenance/due", headers=manager_headers).json() == []


def test_history_is_filtered_by_vehicle(
    client, manager_headers, vehicle, vehicle_payload
):
    second = client.post(
        f"{API}/vehicles",
        json={**vehicle_payload, "registration_number": "KA-04-GH-3456"},
        headers=manager_headers,
    ).json()

    client.post(f"{API}/maintenance", json=_record(vehicle["id"]), headers=manager_headers)
    client.post(f"{API}/maintenance", json=_record(second["id"]), headers=manager_headers)
    client.post(
        f"{API}/maintenance",
        json=_record(second["id"], maintenance_type="BRAKE_SERVICE"),
        headers=manager_headers,
    )

    response = client.get(
        f"{API}/maintenance?vehicle_id={second['id']}", headers=manager_headers
    )
    assert response.json()["total"] == 2


def test_update_a_maintenance_record(client, manager_headers, vehicle):
    created = client.post(
        f"{API}/maintenance", json=_record(vehicle["id"]), headers=manager_headers
    ).json()

    response = client.put(
        f"{API}/maintenance/{created['id']}",
        json={"cost": 5100, "performed_by": "Sharma Motors"},
        headers=manager_headers,
    )
    assert response.status_code == 200
    assert response.json()["cost"] == 5100
    assert response.json()["performed_by"] == "Sharma Motors"


def test_a_record_for_an_unknown_vehicle_is_rejected(client, manager_headers):
    response = client.post(f"{API}/maintenance", json=_record(9999), headers=manager_headers)
    assert response.status_code == 404


def test_negative_cost_is_rejected(client, manager_headers, vehicle):
    response = client.post(
        f"{API}/maintenance", json=_record(vehicle["id"], cost=-100), headers=manager_headers
    )
    assert response.status_code == 422


def test_drivers_cannot_create_maintenance_records(client, driver_headers, vehicle):
    response = client.post(
        f"{API}/maintenance", json=_record(vehicle["id"]), headers=driver_headers
    )
    assert response.status_code == 403


def test_due_vehicles_are_counted_on_the_dashboard(client, manager_headers, vehicle):
    client.post(
        f"{API}/maintenance",
        json=_record(vehicle["id"], next_service_date=str(date.today() + timedelta(days=2))),
        headers=manager_headers,
    )
    dashboard = client.get(f"{API}/dashboard", headers=manager_headers).json()
    assert dashboard["maintenance_due_count"] == 1
