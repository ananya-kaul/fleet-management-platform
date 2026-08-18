"""Populate the database with demo data.

Run with:  python -m app.seed

Idempotent: it exits early if a fleet manager already exists.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.core.logging import configure_logging, get_logger
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import (
    Driver,
    DriverStatus,
    FuelType,
    Incident,
    IncidentSeverity,
    IncidentStatus,
    Location,
    MaintenanceRecord,
    MaintenanceType,
    Trip,
    TripStatus,
    User,
    UserRole,
    Vehicle,
    VehicleAssignment,
    VehicleStatus,
    VehicleType,
)

configure_logging()
logger = get_logger(__name__)

MANAGER_EMAIL = "manager@fleet.com"
MANAGER_PASSWORD = "Manager@123"
DRIVER_PASSWORD = "Driver@123"

VEHICLE_SPECS = [
    ("KA-01-AB-1234", VehicleType.TRUCK, "Tata", "Ace Gold", 2022, FuelType.DIESEL, 48250),
    ("KA-02-CD-5678", VehicleType.VAN, "Mahindra", "Supro", 2021, FuelType.DIESEL, 72400),
    ("KA-03-EF-9012", VehicleType.TRUCK, "Ashok Leyland", "Dost+", 2023, FuelType.DIESEL, 21980),
    ("KA-04-GH-3456", VehicleType.CAR, "Maruti", "Dzire Tour", 2020, FuelType.PETROL, 96110),
    ("KA-05-IJ-7890", VehicleType.VAN, "Tata", "Winger", 2023, FuelType.CNG, 15600),
    ("KA-06-KL-2345", VehicleType.TRUCK, "Eicher", "Pro 2049", 2019, FuelType.DIESEL, 141300),
]

DRIVER_SPECS = [
    ("Rahul Sharma", "+919845012345", "KA0120180001234", 420),
    ("Priya Menon", "+919845098765", "KA0320190005678", 180),
    ("Imran Khan", "+919886011223", "KA0520200009012", 25),
    ("Sunita Rao", "+919845033445", "KA0220170003456", 600),
]

TRIP_SPECS = [
    ("Bangalore", "Chennai", 0, TripStatus.IN_PROGRESS),
    ("Bangalore", "Hyderabad", 1, TripStatus.SCHEDULED),
    ("Mysore", "Bangalore", 2, TripStatus.COMPLETED),
    ("Bangalore", "Mangalore", 3, TripStatus.COMPLETED),
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.scalar(select(User).where(User.email == MANAGER_EMAIL)):
            logger.info("Demo data already present - nothing to do")
            return

        now = datetime.now(timezone.utc)
        today = date.today()

        manager = User(
            email=MANAGER_EMAIL,
            hashed_password=hash_password(MANAGER_PASSWORD),
            full_name="Anita Desai",
            role=UserRole.FLEET_MANAGER,
        )
        db.add(manager)

        vehicles = []
        for index, (reg, vtype, make, model, year, fuel, mileage) in enumerate(VEHICLE_SPECS):
            vehicles.append(
                Vehicle(
                    registration_number=reg,
                    vehicle_type=vtype,
                    make=make,
                    model=model,
                    year=year,
                    fuel_type=fuel,
                    current_mileage=mileage,
                    status=VehicleStatus.AVAILABLE,
                    # Stagger expiries so the dashboard has something to warn about.
                    insurance_expiry=today + timedelta(days=[18, 120, 240, 9, 300, 65][index]),
                    registration_expiry=today + timedelta(days=[400, 95, 700, 210, 520, 40][index]),
                )
            )
        db.add_all(vehicles)
        db.flush()

        drivers = []
        for index, (name, phone, licence, licence_days) in enumerate(DRIVER_SPECS):
            login = User(
                email=f"driver{index + 1}@fleet.com",
                hashed_password=hash_password(DRIVER_PASSWORD),
                full_name=name,
                role=UserRole.DRIVER,
            )
            db.add(login)
            db.flush()
            drivers.append(
                Driver(
                    user_id=login.id,
                    name=name,
                    phone_number=phone,
                    license_number=licence,
                    license_expiry=today + timedelta(days=licence_days),
                    status=DriverStatus.ACTIVE,
                )
            )
        db.add_all(drivers)
        db.flush()

        # Rahul holds KA-01-AB-1234 for the window from the assignment brief.
        db.add_all(
            [
                VehicleAssignment(
                    vehicle_id=vehicles[index].id,
                    driver_id=drivers[index].id,
                    start_date=today - timedelta(days=2),
                    end_date=today + timedelta(days=7),
                )
                for index in range(len(drivers))
            ]
        )

        trips = []
        for index, (source, destination, vehicle_index, status) in enumerate(TRIP_SPECS):
            scheduled_start = now - timedelta(hours=6) + timedelta(days=index)
            trip = Trip(
                trip_code=f"TRP{1001 + index}",
                vehicle_id=vehicles[vehicle_index].id,
                driver_id=drivers[vehicle_index].id,
                source=source,
                destination=destination,
                scheduled_start=scheduled_start,
                scheduled_end=scheduled_start + timedelta(hours=8),
                status=status,
            )
            start_odo = float(vehicles[vehicle_index].current_mileage)

            if status in (TripStatus.STARTED, TripStatus.IN_PROGRESS):
                trip.actual_start = scheduled_start
                trip.start_odometer = start_odo
                trip.start_latitude, trip.start_longitude = 12.9716, 77.5946
                vehicles[vehicle_index].status = VehicleStatus.ON_TRIP

            if status == TripStatus.COMPLETED:
                distance = 145.0 + index * 60
                trip.actual_start = scheduled_start
                trip.actual_end = scheduled_start + timedelta(hours=5)
                trip.start_odometer = start_odo
                trip.end_odometer = start_odo + distance
                trip.distance_km = distance
                trip.start_latitude, trip.start_longitude = 12.2958, 76.6394
                trip.end_latitude, trip.end_longitude = 12.9716, 77.5946
                vehicles[vehicle_index].current_mileage = start_odo + distance

            trips.append(trip)
        db.add_all(trips)
        db.flush()

        # A short GPS breadcrumb trail for the in-progress trip.
        active_trip = trips[0]
        for step in range(12):
            db.add(
                Location(
                    vehicle_id=active_trip.vehicle_id,
                    trip_id=active_trip.id,
                    latitude=12.9716 - step * 0.11,
                    longitude=77.5946 + step * 0.19,
                    speed_kph=58 + (step % 5) * 4,
                    heading=135.0,
                    recorded_at=now - timedelta(minutes=(12 - step) * 10),
                )
            )

        db.add_all(
            [
                MaintenanceRecord(
                    vehicle_id=vehicles[0].id,
                    maintenance_type=MaintenanceType.OIL_CHANGE,
                    description="Engine oil and filter replacement",
                    service_date=today - timedelta(days=95),
                    cost=4200,
                    odometer=44100,
                    next_service_date=today + timedelta(days=5),
                    next_service_mileage=54100,
                ),
                MaintenanceRecord(
                    vehicle_id=vehicles[1].id,
                    maintenance_type=MaintenanceType.BRAKE_SERVICE,
                    description="Front brake pads replaced",
                    service_date=today - timedelta(days=40),
                    cost=7800,
                    odometer=70200,
                    next_service_date=today + timedelta(days=140),
                    next_service_mileage=71000,
                ),
                MaintenanceRecord(
                    vehicle_id=vehicles[5].id,
                    maintenance_type=MaintenanceType.TYRE_REPLACEMENT,
                    description="Four tyres replaced",
                    service_date=today - timedelta(days=12),
                    cost=32400,
                    odometer=140100,
                    next_service_date=today + timedelta(days=350),
                    next_service_mileage=180000,
                ),
            ]
        )

        db.add_all(
            [
                Incident(
                    vehicle_id=vehicles[0].id,
                    trip_id=active_trip.id,
                    reported_by_driver_id=drivers[0].id,
                    title="Warning light on the dashboard",
                    description="Engine temperature warning came on near Hosur.",
                    severity=IncidentSeverity.HIGH,
                    status=IncidentStatus.OPEN,
                    reported_at=now - timedelta(hours=2),
                ),
                Incident(
                    vehicle_id=vehicles[3].id,
                    reported_by_driver_id=drivers[3].id,
                    title="Air conditioning not cooling",
                    severity=IncidentSeverity.LOW,
                    status=IncidentStatus.IN_PROGRESS,
                    reported_at=now - timedelta(days=1),
                ),
            ]
        )

        db.commit()
        logger.info(
            "Seeded %d vehicles, %d drivers, %d trips",
            len(vehicles),
            len(drivers),
            len(trips),
        )
        logger.info("Fleet manager: %s / %s", MANAGER_EMAIL, MANAGER_PASSWORD)
        logger.info("Drivers: driver1@fleet.com … driver4@fleet.com / %s", DRIVER_PASSWORD)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
