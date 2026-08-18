from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LocationCreate(BaseModel):
    vehicle_id: int
    trip_id: int | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    speed_kph: float | None = Field(default=None, ge=0)
    heading: float | None = Field(default=None, ge=0, lt=360)
    accuracy_m: float | None = Field(default=None, ge=0)
    recorded_at: datetime | None = None


class LocationBatchCreate(BaseModel):
    """Used by the mobile clients to flush pings buffered while offline."""

    locations: list[LocationCreate] = Field(min_length=1, max_length=500)


class LocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_id: int
    trip_id: int | None
    latitude: float
    longitude: float
    speed_kph: float | None
    heading: float | None
    accuracy_m: float | None
    recorded_at: datetime
