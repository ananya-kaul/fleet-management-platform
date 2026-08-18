# API reference

Base URL: `/api/v1` · Interactive docs: `/docs` (Swagger UI) and `/redoc`

All endpoints except `/auth/login`, `/auth/register`, `/auth/refresh`,
`/auth/forgot-password` and `/auth/reset-password` require:

```
Authorization: Bearer <access_token>
```

## Conventions

**Roles.** `M` = fleet manager only, `D` = driver only, `A` = any signed-in user.
Drivers are additionally scoped: `GET /trips` returns only their own trips, and
`GET /incidents` only their own reports.

**Pagination.** Collection endpoints accept `limit` (1–200, default 50) and
`offset`, and return an envelope:

```json
{ "items": [...], "total": 128, "limit": 50, "offset": 0 }
```

`total` is the count matching the filter, ignoring pagination.

**Errors.** Every failure returns the same shape, so clients branch on `code`
and show `detail`:

```json
{ "code": "vehicle_already_assigned", "detail": "Vehicle KA-01-AB-1234 is already assigned to driver 1 for an overlapping period" }
```

| Status | Meaning | Example `code` |
|---|---|---|
| 401 | Missing, invalid or expired token | `authentication_failed`, `token_expired` |
| 403 | Authenticated but not allowed | `permission_denied` |
| 404 | No such row | `not_found` |
| 409 | Violates a business invariant | `duplicate_registration`, `invalid_transition` |
| 422 | Failed field validation | `validation_error` |

## Authentication

| Method | Path | Role | Purpose |
|---|---|---|---|
| POST | `/auth/register` | – | Create an account, returns a token pair |
| POST | `/auth/login` | – | Sign in, returns a token pair |
| POST | `/auth/refresh` | – | Exchange a refresh token for a new access token |
| POST | `/auth/logout` | A | Client-side token disposal |
| GET | `/auth/me` | A | The signed-in user, with `driver_id` when linked |
| POST | `/auth/change-password` | A | Change with the current password |
| POST | `/auth/forgot-password` | – | Issue a 30-minute reset token |
| POST | `/auth/reset-password` | – | Consume a reset token |

```http
POST /api/v1/auth/login
{ "email": "manager@fleet.com", "password": "Manager@123" }

200 OK
{
  "access_token": "eyJ…", "refresh_token": "eyJ…", "token_type": "bearer",
  "user": { "id": 1, "email": "manager@fleet.com", "full_name": "Anita Desai",
            "role": "FLEET_MANAGER", "is_active": true, "driver_id": null }
}
```

## Vehicles

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/vehicles` | A | List; filters: `search`, `status`, `is_active` |
| POST | `/vehicles` | M | Create |
| GET | `/vehicles/{id}` | A | Detail |
| PUT | `/vehicles/{id}` | M | Partial update |
| POST | `/vehicles/{id}/deactivate` | M | Retire from service |
| POST | `/vehicles/{id}/activate` | M | Return to service |
| GET | `/vehicles/{id}/location` | A | Most recent GPS fix |

Status: `AVAILABLE` · `ON_TRIP` · `IN_MAINTENANCE` · `INACTIVE`.
`registration_number` is normalised to upper case with hyphens, so `ka 01 ab 1234`
and `KA-01-AB-1234` collide as duplicates (409 `duplicate_registration`).

## Drivers

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/drivers` | M | List; filters: `search`, `status` |
| POST | `/drivers` | M | Create, optionally with an app login |
| GET | `/drivers/me` | D | The caller's own driver profile |
| GET | `/drivers/{id}` | M | Detail, including the current vehicle |
| PUT | `/drivers/{id}` | M | Partial update |
| POST | `/drivers/{id}/status` | M | `?new_status=ACTIVE\|INACTIVE\|SUSPENDED` |
| GET | `/drivers/{id}/assignments` | M | Assignment history |

Passing `email` and `password` to `POST /drivers` provisions a `DRIVER` user in
the same transaction and links it. Deactivating a driver closes their open
assignments so the vehicle is released.

## Assignments

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/assignments` | M | List; filters: `vehicle_id`, `driver_id`, `active_only` |
| POST | `/assignments` | M | Assign a vehicle to a driver for a period |
| POST | `/assignments/{id}/end` | M | Close early; optional `?end_date=` |

`end_date: null` means open ended. Creation returns 409 when the range overlaps
an existing active assignment for either the vehicle
(`vehicle_already_assigned`) or the driver (`driver_already_assigned`), and also
rejects inactive vehicles, inactive drivers, and licences that expire before the
assignment starts.

## Trips

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/trips` | A | List; drivers see only their own |
| POST | `/trips` | M | Schedule |
| GET | `/trips/{id}` | A | Detail |
| PUT | `/trips/{id}` | M | Edit — only while `SCHEDULED` |
| POST | `/trips/{id}/start` | A | Record start time, location, odometer |
| POST | `/trips/{id}/complete` | A | Record end, compute distance |
| POST | `/trips/{id}/status` | A | Other transitions (`IN_PROGRESS`, `CANCELLED`) |
| GET | `/trips/{id}/track` | A | Ordered GPS trail |

Legal transitions — anything else is 409 `invalid_transition`:

```
SCHEDULED   → STARTED | CANCELLED
STARTED     → IN_PROGRESS | COMPLETED | CANCELLED
IN_PROGRESS → COMPLETED | CANCELLED
COMPLETED   → (terminal)
CANCELLED   → (terminal)
```

Starting a trip flips the vehicle to `ON_TRIP`; completing or cancelling
releases it to `AVAILABLE`. On completion the server sets
`distance_km = end_odometer − start_odometer` and rejects an end reading below
the start (422).

```http
POST /api/v1/trips/2/complete
{ "end_odometer": 72963.5, "end_latitude": 17.385, "end_longitude": 78.4867 }

200 OK
{ "trip_code": "TRP1002", "status": "COMPLETED",
  "start_odometer": 72400.0, "end_odometer": 72963.5, "distance_km": 563.5, … }
```

## Tracking

| Method | Path | Role | Purpose |
|---|---|---|---|
| POST | `/locations` | A | One GPS ping |
| POST | `/locations/batch` | A | Up to 500 pings (offline flush) |
| GET | `/locations/latest` | M | One most-recent position per vehicle |
| WS | `/ws/tracking` | – | Live `location.updated` broadcast |

A ping carrying `trip_id` is rejected unless that trip is `STARTED` or
`IN_PROGRESS` and belongs to the same vehicle. Socket frames:

```json
{ "event": "location.updated",
  "data": { "vehicle_id": 2, "registration_number": "KA-02-CD-5678", "trip_id": 2,
            "latitude": 12.57, "longitude": 78.09, "speed_kph": 62.0,
            "heading": 135.0, "recorded_at": "2026-08-18T10:52:03.114Z" } }
```

## Maintenance

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/maintenance` | A | History; filter `vehicle_id` |
| POST | `/maintenance` | M | Record a service |
| GET | `/maintenance/due` | A | Vehicles due for service |
| GET | `/maintenance/{id}` | A | Detail |
| PUT | `/maintenance/{id}` | M | Update |

A vehicle is *due* when its **latest** record has a `next_service_date` inside
the window (default 14 days) or a `next_service_mileage` the odometer has
already passed. Only the latest record counts, so a freshly serviced vehicle
does not stay flagged by an old overdue row.

## Incidents

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/incidents` | A | List; drivers see only their own |
| POST | `/incidents` | A | Report an issue |
| GET | `/incidents/{id}` | A | Detail |
| PUT | `/incidents/{id}` | M | Triage: status, severity, assignee, notes |

Status `OPEN → IN_PROGRESS → RESOLVED`; a resolved incident cannot be reopened
(409). Reporting notifies every active fleet manager.

## Notifications

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/notifications` | A | List; `?unread_only=true` |
| POST | `/notifications/{id}/read` | A | Mark one read |
| POST | `/notifications/read-all` | A | Mark all read |
| POST | `/notifications/devices` | A | Register a push token |
| DELETE | `/notifications/devices/{token}` | A | Unregister |

Generated on trip assignment, trip completion and incident reports.

## Dashboard and analytics

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/dashboard` | M | Fleet counters, maintenance due, expiring documents, recent incidents |
| GET | `/analytics` | M | Utilisation and cost per km; `?period_days=` (default 30) |
| GET | `/analytics/drivers/{id}` | M | One driver's performance |

## System

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness probe (not under `/api/v1`) |
| GET | `/openapi.json` | Machine-readable schema for the whole API |
