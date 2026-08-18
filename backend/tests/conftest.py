"""Test fixtures.

Each test runs against a fresh in-memory SQLite database so cases stay
independent and the suite needs no external services.
"""

import os
from datetime import date, datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-used-in-production")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Driver, DriverStatus, User, UserRole

API = "/api/v1"


@pytest.fixture
def db_session():
    # StaticPool keeps one connection alive so ":memory:" survives across the
    # request handlers within a single test.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def manager(db_session) -> User:
    user = User(
        email="manager@test.com",
        hashed_password=hash_password("Manager@123"),
        full_name="Test Manager",
        role=UserRole.FLEET_MANAGER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def driver_user(db_session) -> User:
    user = User(
        email="driver@test.com",
        hashed_password=hash_password("Driver@123"),
        full_name="Test Driver",
        role=UserRole.DRIVER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def driver(db_session, driver_user) -> Driver:
    profile = Driver(
        user_id=driver_user.id,
        name="Rahul Sharma",
        phone_number="+919845012345",
        license_number="KA0120180001234",
        license_expiry=date.today() + timedelta(days=365),
        status=DriverStatus.ACTIVE,
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


def _auth_headers(client, email: str, password: str) -> dict[str, str]:
    response = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def manager_headers(client, manager) -> dict[str, str]:
    return _auth_headers(client, "manager@test.com", "Manager@123")


@pytest.fixture
def driver_headers(client, driver) -> dict[str, str]:
    return _auth_headers(client, "driver@test.com", "Driver@123")


@pytest.fixture
def vehicle_payload() -> dict:
    return {
        "registration_number": "KA-01-AB-1234",
        "vehicle_type": "TRUCK",
        "make": "Tata",
        "model": "Ace Gold",
        "year": 2022,
        "fuel_type": "DIESEL",
        "current_mileage": 48250,
        "insurance_expiry": str(date.today() + timedelta(days=200)),
        "registration_expiry": str(date.today() + timedelta(days=400)),
    }


@pytest.fixture
def vehicle(client, manager_headers, vehicle_payload) -> dict:
    response = client.post(f"{API}/vehicles", json=vehicle_payload, headers=manager_headers)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def second_driver(db_session) -> Driver:
    profile = Driver(
        name="Priya Menon",
        phone_number="+919845098765",
        license_number="KA0320190005678",
        license_expiry=date.today() + timedelta(days=365),
        status=DriverStatus.ACTIVE,
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


@pytest.fixture
def trip(client, manager_headers, vehicle, driver) -> dict:
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    response = client.post(
        f"{API}/trips",
        json={
            "vehicle_id": vehicle["id"],
            "driver_id": driver.id,
            "source": "Bangalore",
            "destination": "Chennai",
            "scheduled_start": start.isoformat(),
            "scheduled_end": (start + timedelta(hours=8)).isoformat(),
        },
        headers=manager_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()
