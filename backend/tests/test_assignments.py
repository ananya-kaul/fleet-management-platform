"""Vehicle-driver assignment conflict rules."""

from datetime import date, timedelta

from tests.conftest import API


def _payload(vehicle_id, driver_id, start_offset=0, end_offset=7):
    start = date.today() + timedelta(days=start_offset)
    return {
        "vehicle_id": vehicle_id,
        "driver_id": driver_id,
        "start_date": str(start),
        "end_date": str(start + timedelta(days=end_offset - start_offset)),
    }


def test_create_assignment(client, manager_headers, vehicle, driver):
    response = client.post(
        f"{API}/assignments", json=_payload(vehicle["id"], driver.id), headers=manager_headers
    )
    assert response.status_code == 201
    body = response.json()
    assert body["is_active"] is True
    assert body["vehicle"]["registration_number"] == "KA-01-AB-1234"


def test_same_vehicle_to_two_drivers_over_the_same_dates_is_rejected(
    client, manager_headers, vehicle, driver, second_driver
):
    client.post(
        f"{API}/assignments", json=_payload(vehicle["id"], driver.id), headers=manager_headers
    )
    response = client.post(
        f"{API}/assignments",
        json=_payload(vehicle["id"], second_driver.id),
        headers=manager_headers,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "vehicle_already_assigned"


def test_partially_overlapping_range_is_rejected(
    client, manager_headers, vehicle, driver, second_driver
):
    """17-25 Aug and 20-30 Aug share days, so the second assignment must fail."""
    client.post(
        f"{API}/assignments",
        json=_payload(vehicle["id"], driver.id, 0, 8),
        headers=manager_headers,
    )
    response = client.post(
        f"{API}/assignments",
        json=_payload(vehicle["id"], second_driver.id, 3, 13),
        headers=manager_headers,
    )
    assert response.status_code == 409


def test_non_overlapping_range_is_allowed(
    client, manager_headers, vehicle, driver, second_driver
):
    client.post(
        f"{API}/assignments",
        json=_payload(vehicle["id"], driver.id, 0, 5),
        headers=manager_headers,
    )
    response = client.post(
        f"{API}/assignments",
        json=_payload(vehicle["id"], second_driver.id, 6, 12),
        headers=manager_headers,
    )
    assert response.status_code == 201


def test_boundary_day_counts_as_an_overlap(
    client, manager_headers, vehicle, driver, second_driver
):
    """A range ending on day 5 and one starting on day 5 share that day."""
    client.post(
        f"{API}/assignments",
        json=_payload(vehicle["id"], driver.id, 0, 5),
        headers=manager_headers,
    )
    response = client.post(
        f"{API}/assignments",
        json=_payload(vehicle["id"], second_driver.id, 5, 10),
        headers=manager_headers,
    )
    assert response.status_code == 409


def test_open_ended_assignment_blocks_every_later_range(
    client, manager_headers, vehicle, driver, second_driver
):
    client.post(
        f"{API}/assignments",
        json={
            "vehicle_id": vehicle["id"],
            "driver_id": driver.id,
            "start_date": str(date.today()),
            "end_date": None,
        },
        headers=manager_headers,
    )
    response = client.post(
        f"{API}/assignments",
        json=_payload(vehicle["id"], second_driver.id, 300, 400),
        headers=manager_headers,
    )
    assert response.status_code == 409


def test_one_driver_cannot_hold_two_vehicles_at_once(
    client, manager_headers, manager, vehicle, vehicle_payload, driver
):
    second = client.post(
        f"{API}/vehicles",
        json={**vehicle_payload, "registration_number": "KA-02-CD-5678"},
        headers=manager_headers,
    ).json()

    client.post(
        f"{API}/assignments", json=_payload(vehicle["id"], driver.id), headers=manager_headers
    )
    response = client.post(
        f"{API}/assignments", json=_payload(second["id"], driver.id), headers=manager_headers
    )
    assert response.status_code == 409
    assert response.json()["code"] == "driver_already_assigned"


def test_ending_an_assignment_frees_the_vehicle(
    client, manager_headers, vehicle, driver, second_driver
):
    created = client.post(
        f"{API}/assignments", json=_payload(vehicle["id"], driver.id), headers=manager_headers
    ).json()

    ended = client.post(f"{API}/assignments/{created['id']}/end", headers=manager_headers)
    assert ended.status_code == 200
    assert ended.json()["is_active"] is False

    reassigned = client.post(
        f"{API}/assignments",
        json=_payload(vehicle["id"], second_driver.id),
        headers=manager_headers,
    )
    assert reassigned.status_code == 201


def test_assignment_requires_an_existing_vehicle(client, manager_headers, driver):
    response = client.post(
        f"{API}/assignments", json=_payload(9999, driver.id), headers=manager_headers
    )
    assert response.status_code == 404


def test_end_date_before_start_date_is_rejected(client, manager_headers, vehicle, driver):
    response = client.post(
        f"{API}/assignments",
        json={
            "vehicle_id": vehicle["id"],
            "driver_id": driver.id,
            "start_date": str(date.today() + timedelta(days=10)),
            "end_date": str(date.today()),
        },
        headers=manager_headers,
    )
    assert response.status_code == 422


def test_inactive_driver_cannot_be_assigned(
    client, manager_headers, db_session, vehicle, driver
):
    from app.models import DriverStatus

    driver.status = DriverStatus.INACTIVE
    db_session.commit()

    response = client.post(
        f"{API}/assignments", json=_payload(vehicle["id"], driver.id), headers=manager_headers
    )
    assert response.status_code == 409
    assert response.json()["code"] == "driver_inactive"


def test_inactive_vehicle_cannot_be_assigned(client, manager_headers, vehicle, driver):
    client.post(f"{API}/vehicles/{vehicle['id']}/deactivate", headers=manager_headers)
    response = client.post(
        f"{API}/assignments", json=_payload(vehicle["id"], driver.id), headers=manager_headers
    )
    assert response.status_code == 409
    assert response.json()["code"] == "vehicle_inactive"


def test_driver_with_an_expired_licence_cannot_be_assigned(
    client, manager_headers, db_session, vehicle, driver
):
    driver.license_expiry = date.today() - timedelta(days=1)
    db_session.commit()

    response = client.post(
        f"{API}/assignments", json=_payload(vehicle["id"], driver.id), headers=manager_headers
    )
    assert response.status_code == 409
    assert response.json()["code"] == "license_expired"


def test_drivers_only_route_is_closed_to_drivers(client, driver_headers):
    assert client.get(f"{API}/assignments", headers=driver_headers).status_code == 403
