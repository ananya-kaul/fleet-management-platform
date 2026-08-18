from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import TripStatus

if TYPE_CHECKING:
    from app.models.driver import Driver
    from app.models.incident import Incident
    from app.models.location import Location
    from app.models.vehicle import Vehicle


class Trip(Base, TimestampMixin):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_code: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False
    )
    driver_id: Mapped[int] = mapped_column(
        ForeignKey("drivers.id", ondelete="RESTRICT"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(160), nullable=False)
    destination: Mapped[str] = mapped_column(String(160), nullable=False)
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[TripStatus] = mapped_column(
        Enum(TripStatus, native_enum=False, length=20),
        default=TripStatus.SCHEDULED,
        nullable=False,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Recorded when the driver starts the trip.
    actual_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    start_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    start_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    start_odometer: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)

    # Recorded when the driver completes the trip.
    actual_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    end_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    end_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    end_odometer: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)

    # Derived on completion: end_odometer - start_odometer.
    distance_km: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="trips")
    driver: Mapped["Driver"] = relationship(back_populates="trips")
    locations: Mapped[list["Location"]] = relationship(
        back_populates="trip", cascade="all, delete-orphan"
    )
    incidents: Mapped[list["Incident"]] = relationship(back_populates="trip")

    @property
    def is_active(self) -> bool:
        return self.status in (TripStatus.STARTED, TripStatus.IN_PROGRESS)
