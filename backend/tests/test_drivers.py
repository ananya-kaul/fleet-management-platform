"""Driver CRUD and login provisioning."""

from datetime import date, timedelta

from tests.conftest import API


def _driver(**overrides):
    payload = {
        "name": "Imran Khan",
        "phone_number": "+919886011223",
        "license_number": "KA0520200009012",
        "license_expiry": str(date.today() + timedelta(days=400)),
    }
    payload.update(overrides)
    return payload


def test_create_a_driver(client, manager_headers):
    response = client.post(f"{API}/drivers", json=_driver(), headers=manager_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Imran Khan"
    assert body["status"] == "ACTIVE"
    assert body["user_id"] is None


def test_a_driver_can_be_created_with_a_login(client, manager_headers):
    response = client.post(
        f"{API}/drivers",
        json=_driver(email="imran@fleet.com", password="Driver@123"),
        headers=manager_headers,
    )
    assert response.status_code == 201
    assert response.json()["user_id"] is not None

    login = client.post(
        f"{API}/auth/login", json={"email": "imran@fleet.com", "password": "Driver@123"}
    )
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "DRIVER"


def test_duplicate_licence_numbers_are_rejected(client, manager_headers):
    client.post(f"{API}/drivers", json=_driver(), headers=manager_headers)
    response = client.post(
        f"{API}/drivers", json=_driver(name="Someone Else"), headers=manager_headers
    )
    assert response.status_code == 409
    assert response.json()["code"] == "duplicate_license"


def test_update_a_driver(client, manager_headers, driver):
    response = client.put(
        f"{API}/drivers/{driver.id}",
        json={"phone_number": "+919999999999"},
        headers=manager_headers,
    )
    assert response.status_code == 200
    assert response.json()["phone_number"] == "+919999999999"


def test_updating_to_a_taken_licence_is_rejected(client, manager_headers, driver):
    other = client.post(f"{API}/drivers", json=_driver(), headers=manager_headers).json()
    response = client.put(
        f"{API}/drivers/{other['id']}",
        json={"license_number": driver.license_number},
        headers=manager_headers,
    )
    assert response.status_code == 409


def test_deactivating_a_driver_closes_their_assignment(
    client, manager_headers, vehicle, driver, second_driver
):
    client.post(
        f"{API}/assignments",
        json={
            "vehicle_id": vehicle["id"],
            "driver_id": driver.id,
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=7)),
        },
        headers=manager_headers,
    )

    response = client.post(
        f"{API}/drivers/{driver.id}/status?new_status=INACTIVE", headers=manager_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVE"

    # The vehicle is free again once the assignment is closed.
    reassigned = client.post(
        f"{API}/assignments",
        json={
            "vehicle_id": vehicle["id"],
            "driver_id": second_driver.id,
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=7)),
        },
        headers=manager_headers,
    )
    assert reassigned.status_code == 201


def test_the_assigned_vehicle_shows_on_the_driver_record(
    client, manager_headers, vehicle, driver
):
    client.post(
        f"{API}/assignments",
        json={
            "vehicle_id": vehicle["id"],
            "driver_id": driver.id,
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=7)),
        },
        headers=manager_headers,
    )
    response = client.get(f"{API}/drivers/{driver.id}", headers=manager_headers)
    assert response.json()["assigned_vehicle_registration"] == "KA-01-AB-1234"


def test_a_driver_can_read_their_own_profile(client, driver_headers, driver):
    response = client.get(f"{API}/drivers/me", headers=driver_headers)
    assert response.status_code == 200
    assert response.json()["id"] == driver.id


def test_search_drivers_by_name(client, manager_headers, driver):
    client.post(f"{API}/drivers", json=_driver(), headers=manager_headers)
    response = client.get(f"{API}/drivers?search=imran", headers=manager_headers)
    assert response.json()["total"] == 1


def test_driver_history_lists_past_assignments(
    client, manager_headers, vehicle, driver
):
    created = client.post(
        f"{API}/assignments",
        json={
            "vehicle_id": vehicle["id"],
            "driver_id": driver.id,
            "start_date": str(date.today() - timedelta(days=30)),
            "end_date": str(date.today() - timedelta(days=20)),
        },
        headers=manager_headers,
    ).json()
    client.post(f"{API}/assignments/{created['id']}/end", headers=manager_headers)

    response = client.get(f"{API}/drivers/{driver.id}/assignments", headers=manager_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_an_unknown_driver_returns_404(client, manager_headers):
    assert client.get(f"{API}/drivers/9999", headers=manager_headers).status_code == 404
