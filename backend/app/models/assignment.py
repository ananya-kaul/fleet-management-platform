from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.driver import Driver
    from app.models.vehicle import Vehicle


class VehicleAssignment(Base, TimestampMixin):
    """A driver holding a vehicle for a closed or open-ended date range."""

    __tablename__ = "vehicle_assignments"
    __table_args__ = (
        Index("ix_assignment_vehicle_active", "vehicle_id", "is_active"),
        Index("ix_assignment_driver_active", "driver_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False
    )
    driver_id: Mapped[int] = mapped_column(
        ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    # A null end_date means the assignment is open ended.
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="assignments")
    driver: Mapped["Driver"] = relationship(back_populates="assignments")

    def overlaps(self, start: date, end: date | None) -> bool:
        """Two ranges overlap unless one finishes strictly before the other starts."""
        own_end = self.end_date
        if own_end is not None and own_end < start:
            return False
        if end is not None and self.start_date > end:
            return False
        return True
