"""Driver CRUD, optional login provisioning and assignment lookups."""

from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models import Driver, DriverStatus, User, UserRole, VehicleAssignment
from app.schemas.driver import DriverCreate, DriverUpdate


def get_driver(db: Session, driver_id: int) -> Driver:
    driver = db.get(Driver, driver_id)
    if driver is None:
        raise NotFoundError(f"Driver {driver_id} was not found")
    return driver


def get_driver_for_user(db: Session, user: User) -> Driver:
    driver = db.scalar(select(Driver).where(Driver.user_id == user.id))
    if driver is None:
        raise NotFoundError("No driver profile is linked to this account")
    return driver


def create_driver(db: Session, payload: DriverCreate) -> Driver:
    license_number = payload.license_number.strip().upper()
    if db.scalar(select(Driver).where(Driver.license_number == license_number)):
        raise ConflictError(
            f"A driver with licence {license_number} already exists",
            code="duplicate_license",
        )

    user_id = None
    if payload.email and payload.password:
        if db.scalar(select(User).where(User.email == payload.email.lower())):
            raise ConflictError(
                "An account with this email already exists", code="email_taken"
            )
        user = User(
            email=payload.email.lower(),
            hashed_password=hash_password(payload.password),
            full_name=payload.name.strip(),
            role=UserRole.DRIVER,
        )
        db.add(user)
        db.flush()
        user_id = user.id

    driver = Driver(
        name=payload.name.strip(),
        phone_number=payload.phone_number.strip(),
        license_number=license_number,
        license_expiry=payload.license_expiry,
        status=payload.status,
        user_id=user_id,
    )
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver


def update_driver(db: Session, driver_id: int, payload: DriverUpdate) -> Driver:
    driver = get_driver(db, driver_id)
    changes = payload.model_dump(exclude_unset=True)

    if "license_number" in changes and changes["license_number"]:
        license_number = changes["license_number"].strip().upper()
        clash = db.scalar(
            select(Driver).where(
                Driver.license_number == license_number, Driver.id != driver_id
            )
        )
        if clash is not None:
            raise ConflictError(
                f"A driver with licence {license_number} already exists",
                code="duplicate_license",
            )
        changes["license_number"] = license_number

    for field, value in changes.items():
        setattr(driver, field, value)

    db.commit()
    db.refresh(driver)
    return driver


def set_driver_status(db: Session, driver_id: int, status: DriverStatus) -> Driver:
    driver = get_driver(db, driver_id)
    driver.status = status
    if status != DriverStatus.ACTIVE:
        # Close any open assignments so the vehicle is released.
        for assignment in driver.assignments:
            if assignment.is_active:
                assignment.is_active = False
    db.commit()
    db.refresh(driver)
    return driver


def current_assignment(db: Session, driver_id: int, on: date | None = None) -> VehicleAssignment | None:
    today = on or date.today()
    return db.scalar(
        select(VehicleAssignment)
        .where(
            VehicleAssignment.driver_id == driver_id,
            VehicleAssignment.is_active.is_(True),
            VehicleAssignment.start_date <= today,
            or_(
                VehicleAssignment.end_date.is_(None),
                VehicleAssignment.end_date >= today,
            ),
        )
        .order_by(VehicleAssignment.start_date.desc())
    )


def list_drivers(
    db: Session,
    *,
    search: str | None = None,
    status: DriverStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Driver], int]:
    stmt = select(Driver)
    count_stmt = select(func.count()).select_from(Driver)

    filters = []
    if search:
        pattern = f"%{search.strip().lower()}%"
        filters.append(
            or_(
                func.lower(Driver.name).like(pattern),
                func.lower(Driver.license_number).like(pattern),
                Driver.phone_number.like(pattern),
            )
        )
    if status is not None:
        filters.append(Driver.status == status)

    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    total = db.scalar(count_stmt) or 0
    rows = list(db.scalars(stmt.order_by(Driver.name).limit(limit).offset(offset)))
    return rows, total
