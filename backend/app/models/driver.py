from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import DriverStatus

if TYPE_CHECKING:
    from app.models.assignment import VehicleAssignment
    from app.models.incident import Incident
    from app.models.trip import Trip
    from app.models.user import User


class Driver(Base, TimestampMixin):
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    license_number: Mapped[str] = mapped_column(
        String(40), unique=True, index=True, nullable=False
    )
    license_expiry: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[DriverStatus] = mapped_column(
        Enum(DriverStatus, native_enum=False, length=20),
        default=DriverStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    user: Mapped[Optional["User"]] = relationship(back_populates="driver")
    assignments: Mapped[list["VehicleAssignment"]] = relationship(
        back_populates="driver", cascade="all, delete-orphan"
    )
    trips: Mapped[list["Trip"]] = relationship(back_populates="driver")
    incidents: Mapped[list["Incident"]] = relationship(back_populates="reported_by")
