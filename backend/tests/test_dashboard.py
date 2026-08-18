"""Dashboard aggregates and fleet analytics."""

from datetime import date, datetime, timedelta, timezone

from tests.conftest import API


def test_an_empty_fleet_reports_zeroes(client, manager_headers):
    body = client.get(f"{API}/dashboard", headers=manager_headers).json()
    assert body["total_vehicles"] == 0
    assert body["active_trips"] == 0
    assert body["distance_today_km"] == 0.0


def test_vehicle_counts_are_grouped_by_status(
    client, manager_headers, vehicle_payload
):
    for index in range(3):
        client.post(
            f"{API}/vehicles",
            json={**vehicle_payload, "registration_number": f"KA-0{index}-AA-000{index}"},
            headers=manager_headers,
        )
    listing = client.get(f"{API}/vehicles", headers=manager_headers).json()["items"]
    client.put(
        f"{API}/vehicles/{listing[0]['id']}",
        json={"status": "IN_MAINTENANCE"},
        headers=manager_headers,
    )
    client.post(f"{API}/vehicles/{listing[1]['id']}/deactivate", headers=manager_headers)

    body = client.get(f"{API}/dashboard", headers=manager_headers).json()
    assert body["total_vehicles"] == 3
    assert body["available_vehicles"] == 1
    assert body["vehicles_in_maintenance"] == 1
    assert body["inactive_vehicles"] == 1


def test_an_active_trip_moves_the_counters(client, manager_headers, driver_headers, trip):
    before = client.get(f"{API}/dashboard", headers=manager_headers).json()
    assert before["scheduled_trips"] == 1
    assert before["active_trips"] == 0

    client.post(
        f"{API}/trips/{trip['id']}/start",
        json={"start_odometer": 48250, "start_latitude": 12.9, "start_longitude": 77.5},
        headers=driver_headers,
    )

    after = client.get(f"{API}/dashboard", headers=manager_headers).json()
    assert after["active_trips"] == 1
    assert after["vehicles_on_trip"] == 1


def test_todays_distance_sums_completed_trips(
    client, manager_headers, driver_headers, trip
):
    client.post(
        f"{API}/trips/{trip['id']}/start",
        json={"start_odometer": 48250, "start_latitude": 12.9, "start_longitude": 77.5},
        headers=driver_headers,
    )
    client.post(
        f"{API}/trips/{trip['id']}/complete",
        json={
            "end_odometer": 48600,
            "end_latitude": 13.08,
            "end_longitude": 80.27,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=driver_headers,
    )

    body = client.get(f"{API}/dashboard", headers=manager_headers).json()
    assert body["completed_trips_today"] == 1
    assert body["distance_today_km"] == 350.0


def test_an_expiring_licence_is_flagged(client, manager_headers, db_session, driver):
    driver.license_expiry = date.today() + timedelta(days=7)
    db_session.commit()

    body = client.get(f"{API}/dashboard", headers=manager_headers).json()
    licences = [
        item for item in body["expiring_documents"] if item["document"] == "Driving licence"
    ]
    assert len(licences) == 1
    assert licences[0]["days_remaining"] == 7


def test_an_already_expired_document_stays_visible(
    client, manager_headers, db_session, driver
):
    driver.license_expiry = date.today() - timedelta(days=3)
    db_session.commit()

    body = client.get(f"{API}/dashboard", headers=manager_headers).json()
    licences = [
        item for item in body["expiring_documents"] if item["document"] == "Driving licence"
    ]
    assert licences[0]["days_remaining"] == -3


def test_analytics_reports_distance_and_cost_per_km(
    client, manager_headers, driver_headers, trip, vehicle
):
    client.post(
        f"{API}/trips/{trip['id']}/start",
        json={"start_odometer": 48250, "start_latitude": 12.9, "start_longitude": 77.5},
        headers=driver_headers,
    )
    client.post(
        f"{API}/trips/{trip['id']}/complete",
        json={"end_odometer": 48650, "end_latitude": 13.08, "end_longitude": 80.27},
        headers=driver_headers,
    )
    client.post(
        f"{API}/maintenance",
        json={
            "vehicle_id": vehicle["id"],
            "maintenance_type": "GENERAL_INSPECTION",
            "service_date": str(date.today()),
            "cost": 800,
            "odometer": 48650,
        },
        headers=manager_headers,
    )

    body = client.get(f"{API}/analytics?period_days=30", headers=manager_headers).json()
    assert body["total_distance_km"] == 400.0
    assert body["total_maintenance_cost"] == 800.0
    assert body["average_cost_per_km"] == 2.0


def test_driver_performance_counts_trips_and_incidents(
    client, manager_headers, driver_headers, driver, trip, vehicle
):
    client.post(
        f"{API}/trips/{trip['id']}/start",
        json={"start_odometer": 48250, "start_latitude": 12.9, "start_longitude": 77.5},
        headers=driver_headers,
    )
    client.post(
        f"{API}/trips/{trip['id']}/complete",
        json={"end_odometer": 48500, "end_latitude": 13.08, "end_longitude": 80.27},
        headers=driver_headers,
    )
    client.post(
        f"{API}/incidents",
        json={"vehicle_id": vehicle["id"], "title": "Cracked mirror", "severity": "LOW"},
        headers=driver_headers,
    )

    body = client.get(
        f"{API}/analytics/drivers/{driver.id}", headers=manager_headers
    ).json()
    assert body["completed_trips"] == 1
    assert body["total_distance_km"] == 250.0
    assert body["incidents_reported"] == 1
    assert body["average_trip_duration_minutes"] is not None


def test_the_dashboard_is_manager_only(client, driver_headers):
    assert client.get(f"{API}/dashboard", headers=driver_headers).status_code == 403
    assert client.get(f"{API}/analytics", headers=driver_headers).status_code == 403
