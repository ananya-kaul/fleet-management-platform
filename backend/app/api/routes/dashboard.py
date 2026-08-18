from fastapi import APIRouter, Query
from typing import Annotated

from app.api.deps import DbSession, FleetManager
from app.schemas.analytics import DriverPerformance, FleetAnalytics
from app.schemas.dashboard import DashboardResponse
from app.services import analytics_service, dashboard_service

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(db: DbSession, _: FleetManager) -> DashboardResponse:
    return dashboard_service.build_dashboard(db)


@router.get("/analytics", response_model=FleetAnalytics)
def analytics(
    db: DbSession,
    _: FleetManager,
    period_days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> FleetAnalytics:
    return analytics_service.build_analytics(db, period_days=period_days)


@router.get("/analytics/drivers/{driver_id}", response_model=DriverPerformance)
def driver_analytics(
    driver_id: int,
    db: DbSession,
    _: FleetManager,
    period_days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> DriverPerformance:
    return analytics_service.driver_performance(db, driver_id, period_days=period_days)
