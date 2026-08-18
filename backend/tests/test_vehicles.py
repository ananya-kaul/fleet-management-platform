"""Vehicle creation, update, search and the duplicate-registration guard."""

from datetime import date, timedelta

from tests.conftest import API


def test_create_vehicle(client, manager_headers, vehicle_payload):
    response = client.post(f"{API}/vehicles", json=vehicle_payload, headers=manager_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["registration_number"] == "KA-01-AB-1234"
    assert body["status"] == "AVAILABLE"
    assert body["is_active"] is True


def test_duplicate_registration_is_rejected(client, manager_headers, vehicle_payload, vehicle):
    response = client.post(f"{API}/vehicles", json=vehicle_payload, headers=manager_headers)
    assert response.status_code == 409
    assert response.json()["code"] == "duplicate_registration"


def test_duplicate_registration_is_caught_across_formatting(
    client, manager_headers, vehicle_payload, vehicle
):
    """Registrations are normalised, so spacing and case cannot smuggle a duplicate in."""
    variant = {**vehicle_payload, "registration_number": "ka 01 ab 1234"}
    response = client.post(f"{API}/vehicles", json=variant, headers=manager_headers)
    assert response.status_code == 409


def test_create_vehicle_rejects_invalid_year(client, manager_headers, vehicle_payload):
    response = client.post(
        f"{API}/vehicles", json={**vehicle_payload, "year": 1800}, headers=manager_headers
    )
    assert response.status_code == 422


def test_create_vehicle_rejects_unknown_fuel_type(client, manager_headers, vehicle_payload):
    response = client.post(
        f"{API}/vehicles",
        json={**vehicle_payload, "fuel_type": "PLUTONIUM"},
        headers=manager_headers,
    )
    assert response.status_code == 422


def test_update_vehicle(client, manager_headers, vehicle):
    response = client.put(
        f"{API}/vehicles/{vehicle['id']}",
        json={"current_mileage": 50000, "status": "IN_MAINTENANCE"},
        headers=manager_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_mileage"] == 50000
    assert body["status"] == "IN_MAINTENANCE"


def test_update_unknown_vehicle_returns_404(client, manager_headers):
    response = client.put(
        f"{API}/vehicles/9999", json={"make": "Ghost"}, headers=manager_headers
    )
    assert response.status_code == 404


def test_deactivate_vehicle(client, manager_headers, vehicle):
    response = client.post(
        f"{API}/vehicles/{vehicle['id']}/deactivate", headers=manager_headers
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert response.json()["status"] == "INACTIVE"


def test_reactivate_vehicle_returns_it_to_available(client, manager_headers, vehicle):
    client.post(f"{API}/vehicles/{vehicle['id']}/deactivate", headers=manager_headers)
    response = client.post(f"{API}/vehicles/{vehicle['id']}/activate", headers=manager_headers)
    assert response.json()["status"] == "AVAILABLE"


def test_search_filters_by_registration_and_make(client, manager_headers, vehicle_payload):
    client.post(f"{API}/vehicles", json=vehicle_payload, headers=manager_headers)
    client.post(
        f"{API}/vehicles",
        json={
            **vehicle_payload,
            "registration_number": "KA-02-CD-5678",
            "make": "Mahindra",
        },
        headers=manager_headers,
    )

    assert client.get(f"{API}/vehicles?search=mahindra", headers=manager_headers).json()["total"] == 1
    assert client.get(f"{API}/vehicles?search=KA-01", headers=manager_headers).json()["total"] == 1
    assert client.get(f"{API}/vehicles?search=KA-", headers=manager_headers).json()["total"] == 2


def test_filter_by_status(client, manager_headers, vehicle):
    client.put(
        f"{API}/vehicles/{vehicle['id']}",
        json={"status": "IN_MAINTENANCE"},
        headers=manager_headers,
    )
    available = client.get(f"{API}/vehicles?status=AVAILABLE", headers=manager_headers)
    in_maintenance = client.get(f"{API}/vehicles?status=IN_MAINTENANCE", headers=manager_headers)
    assert available.json()["total"] == 0
    assert in_maintenance.json()["total"] == 1


def test_pagination_reports_total_independently_of_the_page(
    client, manager_headers, vehicle_payload
):
    for index in range(5):
        client.post(
            f"{API}/vehicles",
            json={**vehicle_payload, "registration_number": f"KA-1{index}-XY-000{index}"},
            headers=manager_headers,
        )

    page = client.get(f"{API}/vehicles?limit=2&offset=0", headers=manager_headers).json()
    assert len(page["items"]) == 2
    assert page["total"] == 5


def test_driver_can_read_but_not_write_vehicles(
    client, driver_headers, manager_headers, vehicle, vehicle_payload
):
    assert client.get(f"{API}/vehicles", headers=driver_headers).status_code == 200
    assert (
        client.post(
            f"{API}/vehicles",
            json={**vehicle_payload, "registration_number": "KA-77-ZZ-7777"},
            headers=driver_headers,
        ).status_code
        == 403
    )


def test_expiring_documents_surface_on_the_dashboard(
    client, manager_headers, vehicle_payload
):
    soon = str(date.today() + timedelta(days=5))
    client.post(
        f"{API}/vehicles",
        json={**vehicle_payload, "insurance_expiry": soon},
        headers=manager_headers,
    )
    dashboard = client.get(f"{API}/dashboard", headers=manager_headers).json()
    assert dashboard["expiring_documents_count"] >= 1
    assert any(
        item["document"] == "Insurance" for item in dashboard["expiring_documents"]
    )
