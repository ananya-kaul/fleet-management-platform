# Walkthrough: what's happening, how, and why

A guide to the whole system for someone who has to explain or defend it. Every
section answers three things: **what** the piece does, **how** it works, and
**why it was built this way rather than the obvious alternative**.

---

## 1. The shape of the whole thing

### What

Three moving parts:

1. A **FastAPI backend** that owns all the rules and all the data.
2. A **relational database** (PostgreSQL in production, SQLite in development).
3. A **native iOS app** that is two apps in one bundle — a manager experience and
   a driver experience — chosen at sign-in by the user's role.

### How

The app never decides anything important. It collects input, sends it, and
renders what comes back. Every rule that matters — can this vehicle be assigned,
can this trip be completed, how far did it travel — is decided by the server.

### Why this way

**Why not put rules in the app?** Because the app is the least trustworthy place
in the system. It can be an old version the user has not updated, or a modified
build. If the app computed trip distance, the number would only be as reliable
as the phone that produced it. Rules on the server are enforced for every client,
now and in future.

**Why one app for two roles instead of two apps?** They share the entire
foundation — auth, networking, models, error handling. Two targets would mean
duplicating that or building a shared framework, which is more structure than
this problem needs. `RootView` switches on `user.role`, and the two role trees
never see each other's screens.

---

## 2. Backend layering

### What

Four layers, each depending only on the one beneath:

```
routes/     HTTP: paths, status codes, auth guards, pagination
schemas/    Validation: what a valid request even looks like
services/   Business rules: the decisions
models/     Persistence: tables and relationships
```

### How

A route handler is deliberately boring. Here is the whole of trip completion:

```python
@router.post("/{trip_id}/complete", response_model=TripRead)
def complete_trip(trip_id: int, payload: TripCompleteRequest,
                  db: DbSession, user: CurrentUser) -> TripRead:
    trip = trip_service.get_trip(db, trip_id)
    _assert_can_act_on(db, user, trip)
    return TripRead.model_validate(trip_service.complete_trip(db, trip_id, payload))
```

It fetches, checks permission, delegates, and shapes the response. The rules —
is this transition legal, is the odometer sane, what is the distance, does the
vehicle go back to `AVAILABLE`, who gets notified — are all in
`trip_service.complete_trip`.

### Why this way

**Why separate services from routes at all?** Two reasons. First, testability: a
service function takes a session and returns a model, so a rule can be tested
without an HTTP client, a token, or a route. Second, reuse: `complete_trip` is
called by one route today, but a scheduled job or an admin command would call the
same function and get the same rules.

**Why not "fat models" (rules as methods on the SQLAlchemy class)?** It works for
rules about one row. It breaks down as soon as a rule spans tables — completing a
trip touches the trip, the vehicle, and notifications. Putting that on `Trip`
makes the model know about half the schema. Services keep models as data.

**Why not a repository layer between services and models?** It would be a layer
that mostly forwards. SQLAlchemy's `Session` is already the abstraction over the
database, and the project is not swapping SQLAlchemy out. An extra indirection
with no decision in it is cost without benefit.

---

## 3. Authentication

### What

Email/password sign-in returning two JWTs: a short-lived **access token** (1
hour) sent with every request, and a long-lived **refresh token** (30 days) used
only to mint new access tokens. Two roles: `FLEET_MANAGER` and `DRIVER`.

### How

Passwords are hashed with **bcrypt** and never stored or logged in plaintext.
Tokens are signed with HS256 and carry `sub` (user id), `type`, `iat` and `exp`.

The role check is a FastAPI dependency, so it is declared in the signature rather
than written as a guard clause:

```python
def require_fleet_manager(user: CurrentUser) -> User:
    if user.role != UserRole.FLEET_MANAGER:
        raise PermissionDeniedError("This action requires the fleet manager role")
    return user

FleetManager = Annotated[User, Depends(require_fleet_manager)]

# usage - the guard is part of the type
def create_vehicle(payload: VehicleCreate, db: DbSession, _: FleetManager): ...
```

On the client, `APIClient` sees a 401, calls `refreshAccessToken()` once,
rebuilds the request with the new token, and retries. Only if the refresh also
fails does the user get logged out.

### Why this way

**Why JWT instead of server-side sessions?** A session means shared server state
— sticky sessions or a shared store — which is a scaling constraint added for no
gain here. A JWT is verified with a signature check and no database round trip.
Mobile clients also have nowhere natural to keep a cookie jar.

**Why two tokens instead of one long-lived one?** A single 30-day token that
leaks is valid for 30 days. Splitting them means a leaked access token is useless
within the hour, while the user still is not asked to log in daily. It is the
standard trade between exposure window and friction.

**Why the retry-once-on-401 in the client?** Without it, every user gets kicked
to the login screen an hour into using the app. The refresh happens invisibly.
The retry is capped at one attempt so a genuinely dead session cannot loop.

**Why bcrypt and not SHA-256?** SHA-256 is built to be fast, which is exactly
wrong for passwords — fast means fast to brute-force. bcrypt is deliberately slow
and salts every hash, so identical passwords produce different stored values and
rainbow tables do not apply.

**Why not passlib, the usual wrapper?** It is an extra layer over bcrypt, and its
bcrypt-4.x version detection has a well-known breakage. Calling `bcrypt` directly
is two functions — `hashpw` and `checkpw` — and one fewer dependency to have
break.

**Why does a login for an unknown email still run a hash comparison?** If it
returned immediately, a wrong email would answer measurably faster than a wrong
password, and that timing difference reveals which addresses are registered. The
dummy comparison keeps both paths similar in cost.

---

## 4. The assignment overlap rule

This is the rule the brief calls out explicitly: *the system must prevent
assigning the same vehicle to two drivers simultaneously.*

### What

An assignment ties a vehicle to a driver over `[start_date, end_date]`, where a
null end means open ended. Two active assignments for the same vehicle may not
overlap; nor may two for the same driver.

### How

The naive approach is a stack of comparisons: does the new range start inside the
old one, end inside it, contain it, sit inside it? Four cases, easy to get wrong.

The compact form asks the opposite question. Two ranges overlap **unless** one
finishes before the other starts:

```
overlap  ⟺  existing.start <= new.end  AND  existing.end >= new.start
```

with null treated as infinity on that side. In SQL:

```python
stmt = select(VehicleAssignment).where(
    column == entity_id,
    VehicleAssignment.is_active.is_(True),
)
if end is not None:
    stmt = stmt.where(VehicleAssignment.start_date <= end)
stmt = stmt.where(
    or_(VehicleAssignment.end_date.is_(None),
        VehicleAssignment.end_date >= start)
)
```

One query, run once for the vehicle and once for the driver.

### Why this way

**Why the negative formulation?** It collapses all four positional cases into two
comparisons. Fewer branches means fewer places to be wrong, and it is the
standard interval-intersection test rather than something invented here.

**Why does the boundary day count as a conflict?** A range ending 25 Aug and one
starting 25 Aug both include that day, so the vehicle would be double-booked for
it. Inclusive ranges are what a dispatcher means by "17th to the 25th". This is
explicitly tested.

**Why check the driver as well as the vehicle?** The brief only names the vehicle
case, but one driver holding two vehicles at once is the same error viewed from
the other end. Both produce distinct error codes so the UI can say which.

**Why not enforce it with a database constraint?** PostgreSQL could do it with an
exclusion constraint over a `daterange`. Two reasons not to: it would not work on
SQLite, so local development and the test suite would diverge from production;
and a constraint violation surfaces as an opaque integrity error rather than
"Vehicle KA-01-AB-1234 is already assigned to driver 1 for an overlapping
period". Under heavy concurrent writes the constraint would be the safer belt to
add alongside — see the race-condition note in §11.

---

## 5. The trip state machine

### What

A trip moves through `SCHEDULED → STARTED → IN_PROGRESS → COMPLETED`, with
`CANCELLED` reachable from any non-terminal state. Anything else is refused.

### How

The transitions are data, not control flow:

```python
ALLOWED_TRANSITIONS: dict[TripStatus, set[TripStatus]] = {
    TripStatus.SCHEDULED:   {TripStatus.STARTED, TripStatus.CANCELLED},
    TripStatus.STARTED:     {TripStatus.IN_PROGRESS, TripStatus.COMPLETED,
                             TripStatus.CANCELLED},
    TripStatus.IN_PROGRESS: {TripStatus.COMPLETED, TripStatus.CANCELLED},
    TripStatus.COMPLETED:   set(),
    TripStatus.CANCELLED:   set(),
}
```

Every mutation calls `assert_transition_allowed(current, target)` before touching
anything.

### Why this way

**Why a table instead of `if` statements?** Scattered conditionals drift. When
the rules live in one dict, the legal transitions are *readable* — you can see
the whole machine at a glance — and adding a state is one edit rather than a hunt
through handlers.

**Why is `STARTED → COMPLETED` allowed without passing through `IN_PROGRESS`?**
`IN_PROGRESS` is a courtesy signal from the driver, not a required step. On a
short run a driver may never tap it, and refusing to close their trip for that
would be the system being pedantic about its own bookkeeping.

**Why are `COMPLETED` and `CANCELLED` terminal?** A completed trip has a recorded
distance that feeds analytics and the dashboard. Reopening it would silently
change historical totals. Corrections should be a new record, not a mutation of
the old one.

**Why do `/start` and `/complete` have dedicated endpoints instead of just using
`/status`?** Because they are not status changes — they capture data. Starting
records a time, a position and an odometer reading; completing records those and
derives the distance. Squeezing that into a generic status endpoint would mean a
body whose required fields depend on the target value. `/status` explicitly
refuses `STARTED` and `COMPLETED` and points at the right endpoint.

---

## 6. Distance calculation

### What

`distance_km = end_odometer − start_odometer`, exactly as the brief specifies.

### How

On completion the service checks a start reading exists, rejects an end reading
below it, computes the difference, stores it on the trip, and advances the
vehicle's odometer.

```python
if payload.end_odometer < float(trip.start_odometer):
    raise ValidationError("Ending odometer cannot be lower than the starting odometer")

trip.distance_km = payload.end_odometer - float(trip.start_odometer)
vehicle.current_mileage = max(float(vehicle.current_mileage), payload.end_odometer)
```

### Why this way

**Why not compute it from the GPS trail instead?** GPS distance is the more
interesting number, but it is not what the brief asks for, and it is less
trustworthy: pings drop in tunnels, drift in cities, and the sum of straight
lines between samples understates real road distance. The odometer is the
vehicle's own record. The GPS trail is kept anyway and drawn on the map — it
answers "where did it go", while the odometer answers "how far".

**Why store `distance_km` when it is derivable?** The dashboard sums today's
distance across trips. With a stored column that is one `SUM`. Derived, it is a
per-row subtraction the database cannot index or aggregate as cheaply. It is only
written once, at completion, so it cannot drift from its inputs.

**Why `max()` on the vehicle odometer?** Trips can be completed out of order, and
a maintenance record may already have logged a higher reading. An odometer only
moves forward; `max` encodes that rather than trusting whichever write lands
last.

---

## 7. GPS tracking

### What

While a trip is active the driver's phone reports its position; managers see
vehicles move on a live map.

### How

Four pieces:

1. **Sampling.** `CLLocationManager` with `distanceFilter = 25` metres, so a
   parked vehicle stops producing updates.
2. **Throttling.** Even when moving, at most one upload every 15 seconds.
3. **Buffering.** A failed upload is queued; the queue is flushed through
   `POST /locations/batch` on the next success, oldest first.
4. **Broadcast.** The server writes the row and publishes `location.updated` to
   every WebSocket on `/ws/tracking`; the manager's map applies it in place.

### Why this way

**Why throttle at all — why not send every fix?** CoreLocation can fire several
times a second. At that rate one lorry on an eight-hour run would generate tens
of thousands of rows and drain the battery, for a map that only needs to be
roughly current. Fifteen seconds is about 250 metres at highway speed: precise
enough to watch, cheap enough to keep.

**Why the 25 m distance filter as well as the time throttle?** They solve
different problems. The distance filter stops the OS waking the app for a
stationary vehicle; the time throttle limits uploads for a moving one. Together:
no traffic when parked, bounded traffic when driving.

**Why buffer instead of dropping failures?** Lorries drive through tunnels and
dead zones — exactly where you most want to know where they were. Dropping means
a permanent hole in the trail. Buffering means the timing is late but the record
is complete. The buffer is capped at 500 entries so a multi-hour outage cannot
grow it without bound.

**Why a WebSocket rather than polling?** Polling every few seconds is a request
per client per interval whether or not anything moved, and it is still late by up
to one interval. A socket is one connection that carries data only when there is
data. The map goes from "refreshes eventually" to "moves".

**Why in-process broadcast instead of Redis?** For one instance a set of
connections in memory is exactly right, and Redis would be infrastructure for a
problem that does not exist yet. It is a genuine limitation at multi-worker
scale, documented in the README, and the fix is confined to
`ConnectionManager.broadcast` because nothing else knows how the fan-out works.

**Why is tracking foreground-only?** Background location requires the
`UIBackgroundModes` entitlement and an App Store review justification, and it is
one of the most scrutinised permissions Apple grants. The brief asks for periodic
updates during a trip, which the foreground satisfies. The buffer means
backgrounding the app delays uploads rather than losing them.

---

## 8. Maintenance due detection

### What

`GET /maintenance/due` lists vehicles needing service.

### How

Two independent triggers, evaluated against a vehicle's **most recent** record:

- **By date** — `next_service_date` falls within the window (default 14 days).
- **By mileage** — the odometer has passed `next_service_mileage`.

```python
latest = db.scalar(
    select(MaintenanceRecord)
    .where(MaintenanceRecord.vehicle_id == vehicle.id)
    .order_by(MaintenanceRecord.service_date.desc(), MaintenanceRecord.id.desc())
)
```

### Why this way

**Why only the latest record?** Because otherwise a vehicle serviced yesterday
stays flagged forever by an overdue row from last year. "Due" is a statement
about the vehicle's current condition, and only the newest record describes that.
There is a test for exactly this.

**Why both date and mileage?** They catch different vehicles. A van doing 200 km
a day hits its service mileage long before the calendar date; a spare that sits
in the yard hits the date having barely moved. Either alone misses half the
fleet.

**Why report the reason as text?** A manager seeing "KA-02 is due" asks *why*.
`"Odometer 72400 km has passed the 71000 km service point"` answers it without a
second query, and it is the same string in the API, the dashboard and the list.

**Why a window rather than only overdue?** Maintenance needs booking. A list that
only shows vehicles already overdue is a list of things that are already a
problem.

---

## 9. The iOS networking layer

### What

One `APIClient` actor with a single `send` method, and a `FleetAPI` facade with
one typed method per endpoint.

### How

`send` builds the request, attaches the bearer token, performs it, retries once
after a token refresh on a 401, maps the status code onto a typed `APIError`, and
decodes. Views never touch URLs:

```swift
func trips(status: TripStatus? = nil, activeOnly: Bool = false) async throws -> Page<Trip> {
    var query = [URLQueryItem(name: "limit", value: "100"),
                 URLQueryItem(name: "active_only", value: activeOnly ? "true" : "false")]
    if let status { query.append(.init(name: "status_filter", value: status.rawValue)) }
    return try await client.send("trips", query: query)
}
```

### Why this way

**Why one `send` rather than a method per verb?** Every request does the same six
things. Writing them once means auth, refresh, error mapping and decoding cannot
be inconsistent between endpoints — a class of bug that simply cannot occur.

**Why an `actor`?** The client holds mutable state (the token provider reference)
and is called concurrently from many screens. An actor serialises that access, so
data races are prevented by the compiler rather than by convention.

**Why a `FleetAPI` facade over raw `send` calls in views?** It puts the entire
REST surface in one readable file — you can see exactly what the app consumes —
and it means a path or parameter change is one edit, not a search through
screens. It also keeps views honest: a view that cannot build a URL cannot
quietly invent an endpoint.

**Why `URLSession` and not Alamofire?** Alamofire existed because pre-async
`URLSession` was painful. With async/await, the ~150 lines in `APIClient` cover
everything this app needs. A dependency should earn its place; here it would not.

**Why typed `APIError` cases instead of passing `Error` around?** So the UI can
branch. A 409 conflict shows the server's message beside the field the user just
filled in; a 401 signs them out; a network failure offers retry. With an untyped
error every failure becomes the same generic alert.

**Why a custom date decoder?** The API emits timestamps in several shapes — with
and without fractional seconds, with and without a timezone offset (SQLite does
not preserve one) — plus plain `yyyy-MM-dd` for expiry dates. A single
`ISO8601` strategy rejects at least one of those, and the failure mode is an
entire screen showing an error because one field would not parse. The decoder
tries each format in turn. This is exactly the sort of thing that looks like
over-engineering until it costs an afternoon.

---

## 10. iOS state management

### What

`Session` owns authentication. Screens use `@State` for simple local state and an
`@Observable` view model where there is real loading logic.

### How

`Session` is `@Observable` and `@MainActor`, injected once at the app root and
read via `@Environment`. It also implements `TokenProviding`, so `APIClient` can
ask for a token and report an expired one without knowing SwiftUI exists.
`RootView` switches on its state:

```swift
switch session.state {
case .loading:              ProgressView("Loading…")
case .signedOut:            LoginView()
case .signedIn(let user):   user.role == .fleetManager ? ManagerTabView() : DriverTabView()
}
```

### Why this way

**Why `@Observable` rather than `ObservableObject`/`@Published`?** `@Observable`
(iOS 17) drops the per-property `@Published` boilerplate and — the real win —
only invalidates views that actually read a changed property. With
`ObservableObject`, any change redraws every observer.

**Why is auth a single shared object instead of state passed down?** Because
almost everything depends on it, and it must have exactly one value. Threading it
through initialisers would touch every screen; two copies could disagree about
whether the user is signed in. Environment injection gives one instance any view
can read.

**Why does `Session` implement `TokenProviding` rather than `APIClient` holding
the token?** Two owners of the token would eventually disagree after a refresh.
The protocol inverts it: the client asks, the session answers. It also keeps
`APIClient` free of UI concerns, which is what makes it testable in isolation.

**Why not a view model for every screen?** A view model that only forwards calls
is ceremony, not architecture. Screens with real logic — the dashboard, the
vehicle list with search and filters — have one. A detail screen that loads a
record and displays it keeps its state in `@State`. Consistency for its own sake
costs more than it saves.

**Why the Keychain and not `UserDefaults`?** `UserDefaults` is a plist in the app
container, unencrypted. Tokens are credentials. The Keychain is the system store
for credentials, encrypted at rest and released after first unlock.

---

## 11. Testing

### What

122 tests, mapping onto the scenarios the brief lists.

### How

Every test gets a fresh in-memory SQLite database via a fixture, with FastAPI's
`get_db` dependency overridden to hand back that session:

```python
engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                       poolclass=StaticPool)
```

`StaticPool` is what makes `:memory:` work here — it keeps one connection alive,
so the schema created by the fixture is the schema the request handler sees.

Tests go through the HTTP layer, not the services directly, so each one exercises
routing, validation, auth and rules together.

### Why this way

**Why in-memory SQLite instead of a test PostgreSQL?** Because `git clone &&
pytest` should work with nothing running. A test database that needs Docker is a
test suite people skip. The trade — tests do not exercise Postgres-specific
behaviour — is acceptable because the code uses no Postgres-only features.

**Why a fresh database per test rather than transaction rollback?** Rollback is
faster, but shares one connection and gets confusing once the code under test
commits (which these services do). A fresh in-memory database is a few
milliseconds and removes an entire category of order-dependent flakiness.

**Why test through HTTP rather than calling services directly?** Because the
interesting bugs live between layers: a route that forgets a role guard, a schema
that rejects a legal payload, a status code that says 200 when it created
something. Testing the service alone would pass while the endpoint is broken.

**Why so many tests on assignments and trips specifically?** They hold the rules
the brief singles out, and they have the most edge cases — boundary days, open
ranges, illegal transitions. Test count should follow risk, not line count.

**What is deliberately not tested?** Concurrent double-booking. Overlap checks
read then write without a lock, so two simultaneous requests for the same vehicle
could both pass the check. Fixing it properly needs `SELECT … FOR UPDATE` or a
Postgres exclusion constraint. It is called out rather than papered over with a
test that would not actually catch it.

---

## 12. Error handling

### What

One error envelope everywhere:

```json
{ "code": "vehicle_already_assigned", "detail": "Vehicle KA-01-AB-1234 is already assigned to driver 1 for an overlapping period" }
```

### How

Services raise typed exceptions — `NotFoundError`, `ConflictError`,
`ValidationError`, `PermissionDeniedError` — each carrying an HTTP status and a
stable `code`. One handler in `main.py` renders them. A catch-all handler logs
unexpected exceptions with a stack trace and returns a generic 500. The iOS layer
maps status codes back onto a Swift `APIError` enum.

### Why this way

**Why typed exceptions instead of returning `(result, error)` tuples?** Because
the failure is usually detected several calls deep, and every intermediate caller
would have to forward it manually. Exceptions carry it to the boundary where it
becomes a response.

**Why not raise `HTTPException` directly in services?** That would make the
service layer depend on FastAPI. `trip_service` should be usable from a CLI
command or a background job. Domain exceptions keep the dependency pointing one
way: routes know about HTTP, services do not.

**Why a machine-readable `code` as well as `detail`?** So clients can branch
without string-matching English. `detail` is for humans and can be reworded or
translated; `code` is the contract.

**Why does the catch-all return a generic message?** An unhandled exception's
text can contain SQL fragments, file paths or column names. That is a disclosure
risk. The detail goes to the logs with a request id; the client gets "An
unexpected error occurred".

---

## 13. Database and migrations

### What

SQLAlchemy 2.0 models with Alembic migrations. PostgreSQL in production, SQLite
in development — one `DATABASE_URL` switches them.

### How

`alembic/env.py` reads the URL from application settings rather than
`alembic.ini`, so migrations and the app cannot end up pointed at different
databases. The Docker image runs `alembic upgrade head` before starting uvicorn.

### Why this way

**Why migrations instead of `create_all()`?** `create_all` creates missing
tables and does nothing about columns that changed. The first schema change after
launch would either need a manual `ALTER` or a dropped database. Migrations make
the schema versioned and reversible, which is what "database migrations" in the
brief's deliverables means.

**Why two databases at all — isn't that a risk?** It is a managed one. The code
uses no dialect-specific features, and the two places where the difference is
real are handled explicitly: SQLite needs `PRAGMA foreign_keys=ON` per connection
(without it, foreign keys are silently unenforced), and it cannot `ALTER COLUMN`,
so `render_as_batch` is enabled for it. The payoff is a suite that runs anywhere
with no services.

**Why `Enum(native_enum=False)`?** It stores enums as `VARCHAR` with a check
constraint instead of a real Postgres `ENUM` type. Postgres enums need an
`ALTER TYPE` migration to add a value and cannot easily drop one; a varchar
column takes a new value with an ordinary migration. It also behaves identically
on SQLite.

**Why run migrations at container start?** It removes the ordering mistake where
new code deploys against an old schema. The cost is that two instances starting
together both attempt it — Alembic takes a lock, so one waits.

---

## 14. Things a reviewer is likely to ask

**"Why FastAPI over Django?"** Django brings an ORM, admin, auth and migrations
in one box — genuinely useful, but it also brings conventions this project does
not need. FastAPI generates the OpenAPI spec from the same type hints that
validate the requests, so `/docs` cannot drift from the code. For an API-only
service consumed by a mobile client, that is the more relevant strength.

**"Why is the app iOS-only when the brief asks for a Kotlin subset?"** This was a
deliberate scoping decision, made explicitly rather than by omission, and it is
listed in Known limitations. The backend is client-agnostic — an Android client
would consume the same API with no server change.

**"How would this scale to 5,000 vehicles?"** Four things, in order of urgency:
(1) the `locations` table grows fastest — partition it by month and archive; (2)
the dashboard recomputes counters per request — cache or materialise them; (3)
the WebSocket hub needs Redis pub/sub to work across workers; (4) `/vehicles` is
paginated but the map fetches all positions — bound it by viewport.

**"What would you do differently with more time?"** Add the Postgres exclusion
constraint for assignment ranges to close the concurrency gap; wire real APNs
delivery; add a Redis-backed socket layer; and add XCTest coverage for the iOS
view models — the client is currently verified by decoding live API responses,
which is good evidence for the contract but not for view behaviour.

**"Is the API versioned?"** Yes — everything is under `/api/v1`. A breaking
change ships as `/api/v2` while v1 keeps serving apps that have not updated,
which matters because you cannot force an App Store update.

**"Why no `updated_at` on `locations`?"** It is append-only. A GPS ping is a
historical fact; it is never edited. Timestamp columns on immutable rows are
noise.

**"What happens if the driver's phone dies mid-trip?"** The trip stays
`IN_PROGRESS` and the vehicle stays `ON_TRIP`. The manager can cancel it, which
releases the vehicle. The driver can also complete it later — completion takes an
explicit odometer reading, so a late close still records the right distance.
