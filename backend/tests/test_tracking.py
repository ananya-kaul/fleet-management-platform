"""GPS ping storage and retrieval."""

from datetime import datetime, timedelta, timezone

from tests.conftest import API


def _ping(vehicle_id, trip_id=None, lat=12.9716, lon=77.5946, **extra):
    payload = {"vehicle_id": vehicle_id, "latitude": lat, "longitude": lon, **extra}
    if trip_id is not None:
        payload["trip_id"] = trip_id
    return payload


def _start_trip(client, headers, trip_id):
    return client.post(
        f"{API}/trips/{trip_id}/start",
        json={"start_odometer": 48250, "start_latitude": 12.97, "start_longitude": 77.59},
        headers=headers,
    )


def test_store_and_read_back_a_location(client, driver_headers, vehicle):
    response = client.post(
        f"{API}/locations",
        json=_ping(vehicle["id"], speed_kph=62.5, heading=135.0),
        headers=driver_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["latitude"] == 12.9716
    assert body["speed_kph"] == 62.5
    assert body["recorded_at"] is not None


def test_latest_location_returns_the_most_recent_ping(client, driver_headers, vehicle):
    now = datetime.now(timezone.utc)
    for minutes, lat in ((30, 12.10), (20, 12.20), (5, 12.90)):
        client.post(
            f"{API}/locations",
            json=_ping(
                vehicle["id"],
                lat=lat,
                recorded_at=(now - timedelta(minutes=minutes)).isoformat(),
            ),
            headers=driver_headers,
        )

    response = client.get(f"{API}/vehicles/{vehicle['id']}/location", headers=driver_headers)
    assert response.status_code == 200
    assert response.json()["latitude"] == 12.90


def test_latest_location_is_404_when_nothing_was_recorded(client, driver_headers, vehicle):
    response = client.get(f"{API}/vehicles/{vehicle['id']}/location", headers=driver_headers)
    assert response.status_code == 404


def test_out_of_range_coordinates_are_rejected(client, driver_headers, vehicle):
    assert (
        client.post(
            f"{API}/locations", json=_ping(vehicle["id"], lat=91.0), headers=driver_headers
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"{API}/locations", json=_ping(vehicle["id"], lon=181.0), headers=driver_headers
        ).status_code
        == 422
    )


def test_ping_for_an_unknown_vehicle_is_rejected(client, driver_headers):
    response = client.post(f"{API}/locations", json=_ping(9999), headers=driver_headers)
    assert response.status_code == 404


def test_pings_attach_to_an_active_trip_and_form_a_track(client, driver_headers, trip):
    _start_trip(client, driver_headers, trip["id"])

    now = datetime.now(timezone.utc)
    for index in range(5):
        response = client.post(
            f"{API}/locations",
            json=_ping(
                trip["vehicle_id"],
                trip_id=trip["id"],
                lat=12.97 - index * 0.1,
                recorded_at=(now + timedelta(minutes=index)).isoformat(),
            ),
            headers=driver_headers,
        )
        assert response.status_code == 201

    track = client.get(f"{API}/trips/{trip['id']}/track", headers=driver_headers)
    assert track.status_code == 200
    points = track.json()
    assert len(points) == 5
    # The track is returned in chronological order.
    assert points[0]["latitude"] > points[-1]["latitude"]


def test_ping_against_a_trip_that_has_not_started_is_rejected(
    client, driver_headers, trip
):
    response = client.post(
        f"{API}/locations",
        json=_ping(trip["vehicle_id"], trip_id=trip["id"]),
        headers=driver_headers,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "trip_not_active"


def test_ping_rejects_a_trip_vehicle_mismatch(
    client, manager_headers, driver_headers, trip, vehicle_payload
):
    _start_trip(client, driver_headers, trip["id"])
    other = client.post(
        f"{API}/vehicles",
        json={**vehicle_payload, "registration_number": "KA-09-ZZ-9999"},
        headers=manager_headers,
    ).json()

    response = client.post(
        f"{API}/locations",
        json=_ping(other["id"], trip_id=trip["id"]),
        headers=driver_headers,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "trip_vehicle_mismatch"


def test_batch_upload_persists_every_ping(client, driver_headers, trip):
    """Mirrors the offline-buffer flush from the mobile client."""
    _start_trip(client, driver_headers, trip["id"])
    now = datetime.now(timezone.utc)

    response = client.post(
        f"{API}/locations/batch",
        json={
            "locations": [
                _ping(
                    trip["vehicle_id"],
                    trip_id=trip["id"],
                    lat=12.9 - index * 0.05,
                    recorded_at=(now + timedelta(seconds=index * 30)).isoformat(),
                )
                for index in range(8)
            ]
        },
        headers=driver_headers,
    )
    assert response.status_code == 201
    assert len(response.json()) == 8

    track = client.get(f"{API}/trips/{trip['id']}/track", headers=driver_headers).json()
    assert len(track) == 8


def test_fleet_map_returns_one_position_per_vehicle(
    client, manager_headers, driver_headers, vehicle, vehicle_payload
):
    second = client.post(
        f"{API}/vehicles",
        json={**vehicle_payload, "registration_number": "KA-08-YY-8888"},
        headers=manager_headers,
    ).json()

    for vehicle_id in (vehicle["id"], vehicle["id"], second["id"]):
        client.post(f"{API}/locations", json=_ping(vehicle_id), headers=driver_headers)

    response = client.get(f"{API}/locations/latest", headers=manager_headers)
    assert response.status_code == 200
    assert len({row["vehicle_id"] for row in response.json()}) == 2


def test_the_fleet_map_is_manager_only(client, driver_headers):
    assert client.get(f"{API}/locations/latest", headers=driver_headers).status_code == 403


def test_the_tracking_socket_accepts_a_connection(client):
    with client.websocket_connect(f"{API}/ws/tracking") as socket:
        assert socket is not None
