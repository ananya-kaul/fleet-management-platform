"""Trip state transitions and the odometer-derived distance."""

from datetime import datetime, timedelta, timezone

from tests.conftest import API


def _start(client, trip_id, headers, odometer=48250):
    return client.post(
        f"{API}/trips/{trip_id}/start",
        json={
            "start_odometer": odometer,
            "start_latitude": 12.9716,
            "start_longitude": 77.5946,
        },
        headers=headers,
    )


def _complete(client, trip_id, headers, odometer=48600):
    return client.post(
        f"{API}/trips/{trip_id}/complete",
        json={
            "end_odometer": odometer,
            "end_latitude": 13.0827,
            "end_longitude": 80.2707,
        },
        headers=headers,
    )


def test_create_trip_assigns_a_trip_code(client, trip):
    assert trip["trip_code"].startswith("TRP")
    assert trip["status"] == "SCHEDULED"


def test_create_trip_rejects_an_end_before_the_start(
    client, manager_headers, vehicle, driver
):
    start = datetime.now(timezone.utc) + timedelta(hours=4)
    response = client.post(
        f"{API}/trips",
        json={
            "vehicle_id": vehicle["id"],
            "driver_id": driver.id,
            "source": "Bangalore",
            "destination": "Chennai",
            "scheduled_start": start.isoformat(),
            "scheduled_end": (start - timedelta(hours=1)).isoformat(),
        },
        headers=manager_headers,
    )
    assert response.status_code == 422


def test_double_booking_a_vehicle_is_rejected(
    client, manager_headers, vehicle, driver, second_driver, trip
):
    response = client.post(
        f"{API}/trips",
        json={
            "vehicle_id": vehicle["id"],
            "driver_id": second_driver.id,
            "source": "Bangalore",
            "destination": "Mysore",
            "scheduled_start": trip["scheduled_start"],
            "scheduled_end": trip["scheduled_end"],
        },
        headers=manager_headers,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "trip_schedule_conflict"


def test_start_trip_records_time_location_and_odometer(client, driver_headers, trip):
    response = _start(client, trip["id"], driver_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "STARTED"
    assert body["start_odometer"] == 48250
    assert body["start_latitude"] == 12.9716
    assert body["actual_start"] is not None


def test_starting_a_trip_puts_the_vehicle_on_trip(client, driver_headers, trip, vehicle):
    _start(client, trip["id"], driver_headers)
    response = client.get(f"{API}/vehicles/{vehicle['id']}", headers=driver_headers)
    assert response.json()["status"] == "ON_TRIP"


def test_a_trip_cannot_be_started_twice(client, driver_headers, trip):
    _start(client, trip["id"], driver_headers)
    response = _start(client, trip["id"], driver_headers)
    assert response.status_code == 409
    assert response.json()["code"] == "invalid_transition"


def test_scheduled_trip_cannot_jump_straight_to_completed(client, driver_headers, trip):
    response = _complete(client, trip["id"], driver_headers)
    assert response.status_code == 409
    assert response.json()["code"] == "invalid_transition"


def test_full_lifecycle_scheduled_started_in_progress_completed(
    client, driver_headers, trip
):
    assert _start(client, trip["id"], driver_headers).json()["status"] == "STARTED"

    in_progress = client.post(
        f"{API}/trips/{trip['id']}/status",
        json={"status": "IN_PROGRESS"},
        headers=driver_headers,
    )
    assert in_progress.json()["status"] == "IN_PROGRESS"

    assert _complete(client, trip["id"], driver_headers).json()["status"] == "COMPLETED"


def test_distance_is_the_odometer_difference(client, driver_headers, trip):
    _start(client, trip["id"], driver_headers, odometer=48250)
    response = _complete(client, trip["id"], driver_headers, odometer=48597.5)
    assert response.json()["distance_km"] == 347.5


def test_end_odometer_below_start_is_rejected(client, driver_headers, trip):
    _start(client, trip["id"], driver_headers, odometer=48250)
    response = _complete(client, trip["id"], driver_headers, odometer=48000)
    assert response.status_code == 422


def test_completing_a_trip_frees_the_vehicle_and_updates_mileage(
    client, driver_headers, trip, vehicle
):
    _start(client, trip["id"], driver_headers, odometer=48250)
    _complete(client, trip["id"], driver_headers, odometer=48600)

    response = client.get(f"{API}/vehicles/{vehicle['id']}", headers=driver_headers)
    body = response.json()
    assert body["status"] == "AVAILABLE"
    assert body["current_mileage"] == 48600


def test_a_completed_trip_is_terminal(client, driver_headers, trip):
    _start(client, trip["id"], driver_headers)
    _complete(client, trip["id"], driver_headers)

    response = client.post(
        f"{API}/trips/{trip['id']}/status",
        json={"status": "CANCELLED"},
        headers=driver_headers,
    )
    assert response.status_code == 409


def test_cancelling_a_scheduled_trip(client, manager_headers, trip):
    response = client.post(
        f"{API}/trips/{trip['id']}/status",
        json={"status": "CANCELLED", "reason": "Customer postponed"},
        headers=manager_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert response.json()["cancellation_reason"] == "Customer postponed"


def test_cancelling_a_started_trip_releases_the_vehicle(
    client, manager_headers, driver_headers, trip, vehicle
):
    _start(client, trip["id"], driver_headers)
    client.post(
        f"{API}/trips/{trip['id']}/status",
        json={"status": "CANCELLED", "reason": "Breakdown"},
        headers=manager_headers,
    )
    response = client.get(f"{API}/vehicles/{vehicle['id']}", headers=manager_headers)
    assert response.json()["status"] == "AVAILABLE"


def test_status_endpoint_refuses_to_shortcut_start(client, driver_headers, trip):
    response = client.post(
        f"{API}/trips/{trip['id']}/status",
        json={"status": "STARTED"},
        headers=driver_headers,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "use_dedicated_endpoint"


def test_a_driver_cannot_start_someone_elses_trip(
    client, db_session, manager_headers, driver_headers, vehicle, second_driver
):
    start = datetime.now(timezone.utc) + timedelta(days=3)
    other_trip = client.post(
        f"{API}/trips",
        json={
            "vehicle_id": vehicle["id"],
            "driver_id": second_driver.id,
            "source": "Mysore",
            "destination": "Bangalore",
            "scheduled_start": start.isoformat(),
            "scheduled_end": (start + timedelta(hours=4)).isoformat(),
        },
        headers=manager_headers,
    ).json()

    response = _start(client, other_trip["id"], driver_headers)
    assert response.status_code == 403


def test_a_scheduled_trip_can_be_edited_but_a_started_one_cannot(
    client, manager_headers, driver_headers, trip
):
    edited = client.put(
        f"{API}/trips/{trip['id']}",
        json={"destination": "Coimbatore"},
        headers=manager_headers,
    )
    assert edited.status_code == 200
    assert edited.json()["destination"] == "Coimbatore"

    _start(client, trip["id"], driver_headers)
    locked = client.put(
        f"{API}/trips/{trip['id']}", json={"destination": "Salem"}, headers=manager_headers
    )
    assert locked.status_code == 409


def test_trip_on_an_inactive_vehicle_is_rejected(
    client, manager_headers, vehicle, driver
):
    client.post(f"{API}/vehicles/{vehicle['id']}/deactivate", headers=manager_headers)
    start = datetime.now(timezone.utc) + timedelta(days=1)
    response = client.post(
        f"{API}/trips",
        json={
            "vehicle_id": vehicle["id"],
            "driver_id": driver.id,
            "source": "Bangalore",
            "destination": "Chennai",
            "scheduled_start": start.isoformat(),
            "scheduled_end": (start + timedelta(hours=2)).isoformat(),
        },
        headers=manager_headers,
    )
    assert response.status_code == 409


def test_creating_a_trip_notifies_the_driver(client, driver_headers, trip):
    response = client.get(f"{API}/notifications", headers=driver_headers)
    assert response.status_code == 200
    categories = [item["category"] for item in response.json()]
    assert "TRIP_ASSIGNED" in categories


def test_completing_a_trip_notifies_the_fleet_manager(
    client, manager_headers, driver_headers, trip
):
    _start(client, trip["id"], driver_headers)
    _complete(client, trip["id"], driver_headers)

    response = client.get(f"{API}/notifications", headers=manager_headers)
    categories = [item["category"] for item in response.json()]
    assert "TRIP_COMPLETED" in categories
