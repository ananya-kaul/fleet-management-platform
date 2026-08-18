from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, Enum, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import FuelType, VehicleStatus, VehicleType

if TYPE_CHECKING:
    from app.models.assignment import VehicleAssignment
    from app.models.incident import Incident
    from app.models.location import Location
    from app.models.maintenance import MaintenanceRecord
    from app.models.trip import Trip


class Vehicle(Base, TimestampMixin):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    registration_number: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    vehicle_type: Mapped[VehicleType] = mapped_column(
        Enum(VehicleType, native_enum=False, length=20), nullable=False
    )
    make: Mapped[str] = mapped_column(String(60), nullable=False)
    model: Mapped[str] = mapped_column(String(60), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    fuel_type: Mapped[FuelType] = mapped_column(
        Enum(FuelType, native_enum=False, length=20), nullable=False
    )
    current_mileage: Mapped[float] = mapped_column(
        Numeric(12, 2), default=0, nullable=False
    )
    status: Mapped[VehicleStatus] = mapped_column(
        Enum(VehicleStatus, native_enum=False, length=20),
        default=VehicleStatus.AVAILABLE,
        nullable=False,
        index=True,
    )
    insurance_expiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    registration_expiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    assignments: Mapped[list["VehicleAssignment"]] = relationship(
        back_populates="vehicle", cascade="all, delete-orphan"
    )
    trips: Mapped[list["Trip"]] = relationship(back_populates="vehicle")
    locations: Mapped[list["Location"]] = relationship(
        back_populates="vehicle", cascade="all, delete-orphan"
    )
    maintenance_records: Mapped[list["MaintenanceRecord"]] = relationship(
        back_populates="vehicle", cascade="all, delete-orphan"
    )
    incidents: Mapped[list["Incident"]] = relationship(back_populates="vehicle")

    @property
    def display_name(self) -> str:
        return f"{self.make} {self.model} ({self.registration_number})"
