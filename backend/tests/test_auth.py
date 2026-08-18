"""Authentication, session handling and role-based access control."""

from tests.conftest import API


def test_register_returns_tokens_and_profile(client):
    response = client.post(
        f"{API}/auth/register",
        json={
            "email": "New.Manager@Test.com",
            "password": "Str0ngPass!",
            "full_name": "New Manager",
            "role": "FLEET_MANAGER",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["access_token"] and body["refresh_token"]
    # Emails are normalised to lower case on the way in.
    assert body["user"]["email"] == "new.manager@test.com"
    assert body["user"]["role"] == "FLEET_MANAGER"


def test_register_rejects_duplicate_email(client, manager):
    response = client.post(
        f"{API}/auth/register",
        json={
            "email": "manager@test.com",
            "password": "Str0ngPass!",
            "full_name": "Impostor",
        },
    )
    assert response.status_code == 409
    assert response.json()["code"] == "email_taken"


def test_register_rejects_short_password(client):
    response = client.post(
        f"{API}/auth/register",
        json={"email": "a@b.com", "password": "short", "full_name": "Someone"},
    )
    assert response.status_code == 422


def test_login_succeeds_with_valid_credentials(client, manager):
    response = client.post(
        f"{API}/auth/login",
        json={"email": "manager@test.com", "password": "Manager@123"},
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_login_rejects_wrong_password(client, manager):
    response = client.post(
        f"{API}/auth/login",
        json={"email": "manager@test.com", "password": "WrongPassword1"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "authentication_failed"


def test_login_rejects_unknown_email(client):
    response = client.post(
        f"{API}/auth/login", json={"email": "nobody@test.com", "password": "Whatever123"}
    )
    assert response.status_code == 401


def test_login_rejects_deactivated_account(client, db_session, manager):
    manager.is_active = False
    db_session.commit()

    response = client.post(
        f"{API}/auth/login",
        json={"email": "manager@test.com", "password": "Manager@123"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "account_disabled"


def test_me_returns_the_authenticated_user(client, manager_headers):
    response = client.get(f"{API}/auth/me", headers=manager_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "manager@test.com"


def test_me_links_the_driver_profile(client, driver_headers, driver):
    response = client.get(f"{API}/auth/me", headers=driver_headers)
    assert response.status_code == 200
    assert response.json()["driver_id"] == driver.id


def test_protected_route_rejects_missing_token(client):
    assert client.get(f"{API}/vehicles").status_code == 401


def test_protected_route_rejects_malformed_token(client):
    response = client.get(
        f"{API}/vehicles", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_refresh_token_issues_a_new_access_token(client, manager):
    login = client.post(
        f"{API}/auth/login",
        json={"email": "manager@test.com", "password": "Manager@123"},
    ).json()

    response = client.post(
        f"{API}/auth/refresh", json={"refresh_token": login["refresh_token"]}
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_access_token_is_rejected_by_the_refresh_endpoint(client, manager):
    login = client.post(
        f"{API}/auth/login",
        json={"email": "manager@test.com", "password": "Manager@123"},
    ).json()

    response = client.post(
        f"{API}/auth/refresh", json={"refresh_token": login["access_token"]}
    )
    assert response.status_code == 401


def test_change_password_then_login_with_the_new_one(client, manager, manager_headers):
    changed = client.post(
        f"{API}/auth/change-password",
        json={"current_password": "Manager@123", "new_password": "BrandNew@456"},
        headers=manager_headers,
    )
    assert changed.status_code == 200

    assert (
        client.post(
            f"{API}/auth/login",
            json={"email": "manager@test.com", "password": "Manager@123"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            f"{API}/auth/login",
            json={"email": "manager@test.com", "password": "BrandNew@456"},
        ).status_code
        == 200
    )


def test_change_password_rejects_wrong_current_password(client, manager_headers):
    response = client.post(
        f"{API}/auth/change-password",
        json={"current_password": "NotMyPassword1", "new_password": "BrandNew@456"},
        headers=manager_headers,
    )
    assert response.status_code == 401


def test_password_reset_round_trip(client, manager):
    token = client.post(
        f"{API}/auth/forgot-password", json={"email": "manager@test.com"}
    ).json()["reset_token"]

    reset = client.post(
        f"{API}/auth/reset-password",
        json={"reset_token": token, "new_password": "Recovered@789"},
    )
    assert reset.status_code == 200
    assert (
        client.post(
            f"{API}/auth/login",
            json={"email": "manager@test.com", "password": "Recovered@789"},
        ).status_code
        == 200
    )


def test_driver_cannot_reach_manager_only_routes(client, driver_headers):
    assert client.get(f"{API}/drivers", headers=driver_headers).status_code == 403
    assert client.get(f"{API}/dashboard", headers=driver_headers).status_code == 403


def test_manager_can_reach_manager_only_routes(client, manager_headers):
    assert client.get(f"{API}/drivers", headers=manager_headers).status_code == 200
    assert client.get(f"{API}/dashboard", headers=manager_headers).status_code == 200
