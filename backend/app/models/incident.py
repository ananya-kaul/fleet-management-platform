from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import IncidentSeverity, IncidentStatus

if TYPE_CHECKING:
    from app.models.driver import Driver
    from app.models.trip import Trip
    from app.models.user import User
    from app.models.vehicle import Vehicle


class Incident(Base, TimestampMixin):
    """A vehicle issue reported by a driver and triaged by a fleet manager."""

    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trip_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("trips.id", ondelete="SET NULL"), nullable=True
    )
    reported_by_driver_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True
    )
    assigned_to_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    severity: Mapped[IncidentSeverity] = mapped_column(
        Enum(IncidentSeverity, native_enum=False, length=20), nullable=False
    )
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, native_enum=False, length=20),
        default=IncidentStatus.OPEN,
        nullable=False,
        index=True,
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    vehicle: Mapped["Vehicle"] = relationship(back_populates="incidents")
    trip: Mapped[Optional["Trip"]] = relationship(back_populates="incidents")
    reported_by: Mapped[Optional["Driver"]] = relationship(back_populates="incidents")
    assigned_to: Mapped[Optional["User"]] = relationship()
