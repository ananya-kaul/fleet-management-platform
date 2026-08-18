"""Root API router - every versioned route is mounted here."""

from fastapi import APIRouter

from app.api.routes import (
    assignments,
    auth,
    dashboard,
    drivers,
    incidents,
    locations,
    maintenance,
    notifications,
    trips,
    vehicles,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(vehicles.router)
api_router.include_router(drivers.router)
api_router.include_router(assignments.router)
api_router.include_router(trips.router)
api_router.include_router(locations.router)
api_router.include_router(maintenance.router)
api_router.include_router(incidents.router)
api_router.include_router(notifications.router)
api_router.include_router(dashboard.router)
