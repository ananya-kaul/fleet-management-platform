from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import MaintenanceType

if TYPE_CHECKING:
    from app.models.vehicle import Vehicle


class MaintenanceRecord(Base, TimestampMixin):
    __tablename__ = "maintenance_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    maintenance_type: Mapped[MaintenanceType] = mapped_column(
        Enum(MaintenanceType, native_enum=False, length=30), nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    service_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    odometer: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    next_service_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    next_service_mileage: Mapped[Optional[float]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    performed_by: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="maintenance_records")
