from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.trip import Trip
    from app.models.vehicle import Vehicle


class Location(Base):
    """A single GPS ping sent by the driver app during an active trip."""

    __tablename__ = "locations"
    __table_args__ = (
        Index("ix_location_vehicle_recorded", "vehicle_id", "recorded_at"),
        Index("ix_location_trip_recorded", "trip_id", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False
    )
    trip_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("trips.id", ondelete="CASCADE"), nullable=True
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    speed_kph: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    heading: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    accuracy_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    vehicle: Mapped["Vehicle"] = relationship(back_populates="locations")
    trip: Mapped[Optional["Trip"]] = relationship(back_populates="locations")
