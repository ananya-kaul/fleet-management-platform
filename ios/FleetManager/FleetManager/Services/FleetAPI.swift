import Foundation

/// One typed facade over every endpoint the app uses.
///
/// Views never build paths or query items themselves - they call a method here,
/// which keeps the REST surface in one place and makes it trivial to see what
/// the app actually consumes.
struct FleetAPI {
    let client: APIClient

    // MARK: - Auth

    func login(email: String, password: String) async throws -> TokenPair {
        try await client.send(
            "auth/login",
            method: .post,
            body: LoginPayload(email: email, password: password),
            authenticated: false
        )
    }

    func refresh(token: String) async throws -> AccessTokenResponse {
        try await client.send(
            "auth/refresh",
            method: .post,
            body: RefreshPayload(refreshToken: token),
            authenticated: false
        )
    }

    func currentUser() async throws -> AuthUser {
        try await client.send("auth/me")
    }

    func logout() async throws {
        let _: MessageResponse = try await client.send("auth/logout", method: .post)
    }

    func changePassword(current: String, new: String) async throws {
        let _: MessageResponse = try await client.send(
            "auth/change-password",
            method: .post,
            body: ChangePasswordPayload(currentPassword: current, newPassword: new)
        )
    }

    // MARK: - Vehicles

    func vehicles(
        search: String? = nil,
        status: VehicleStatus? = nil,
        limit: Int = 100
    ) async throws -> Page<Vehicle> {
        var query = [URLQueryItem(name: "limit", value: String(limit))]
        if let search, !search.isEmpty { query.append(.init(name: "search", value: search)) }
        if let status { query.append(.init(name: "status", value: status.rawValue)) }
        return try await client.send("vehicles", query: query)
    }

    func vehicle(id: Int) async throws -> Vehicle {
        try await client.send("vehicles/\(id)")
    }

    func createVehicle(_ payload: VehiclePayload) async throws -> Vehicle {
        try await client.send("vehicles", method: .post, body: payload)
    }

    func updateVehicle(id: Int, _ payload: VehicleUpdatePayload) async throws -> Vehicle {
        try await client.send("vehicles/\(id)", method: .put, body: payload)
    }

    func deactivateVehicle(id: Int) async throws -> Vehicle {
        try await client.send("vehicles/\(id)/deactivate", method: .post)
    }

    func activateVehicle(id: Int) async throws -> Vehicle {
        try await client.send("vehicles/\(id)/activate", method: .post)
    }

    func latestLocation(vehicleId: Int) async throws -> TrackPoint {
        try await client.send("vehicles/\(vehicleId)/location")
    }

    func fleetPositions() async throws -> [TrackPoint] {
        try await client.send("locations/latest")
    }

    // MARK: - Drivers

    func drivers(search: String? = nil, limit: Int = 100) async throws -> Page<Driver> {
        var query = [URLQueryItem(name: "limit", value: String(limit))]
        if let search, !search.isEmpty { query.append(.init(name: "search", value: search)) }
        return try await client.send("drivers", query: query)
    }

    func driver(id: Int) async throws -> Driver {
        try await client.send("drivers/\(id)")
    }

    func myDriverProfile() async throws -> Driver {
        try await client.send("drivers/me")
    }

    func createDriver(_ payload: DriverPayload) async throws -> Driver {
        try await client.send("drivers", method: .post, body: payload)
    }

    func setDriverStatus(id: Int, status: DriverStatus) async throws -> Driver {
        try await client.send(
            "drivers/\(id)/status",
            method: .post,
            query: [URLQueryItem(name: "new_status", value: status.rawValue)]
        )
    }

    func driverAssignments(id: Int) async throws -> [Assignment] {
        try await client.send("drivers/\(id)/assignments")
    }

    // MARK: - Assignments

    func assignments(activeOnly: Bool = false) async throws -> Page<Assignment> {
        try await client.send(
            "assignments",
            query: [
                URLQueryItem(name: "limit", value: "100"),
                URLQueryItem(name: "active_only", value: activeOnly ? "true" : "false"),
            ]
        )
    }

    func createAssignment(_ payload: AssignmentPayload) async throws -> Assignment {
        try await client.send("assignments", method: .post, body: payload)
    }

    func endAssignment(id: Int) async throws -> Assignment {
        try await client.send("assignments/\(id)/end", method: .post)
    }

    // MARK: - Trips

    func trips(status: TripStatus? = nil, activeOnly: Bool = false) async throws -> Page<Trip> {
        var query = [
            URLQueryItem(name: "limit", value: "100"),
            URLQueryItem(name: "active_only", value: activeOnly ? "true" : "false"),
        ]
        if let status { query.append(.init(name: "status_filter", value: status.rawValue)) }
        return try await client.send("trips", query: query)
    }

    func trip(id: Int) async throws -> Trip {
        try await client.send("trips/\(id)")
    }

    func createTrip(_ payload: TripPayload) async throws -> Trip {
        try await client.send("trips", method: .post, body: payload)
    }

    func startTrip(id: Int, _ payload: TripStartPayload) async throws -> Trip {
        try await client.send("trips/\(id)/start", method: .post, body: payload)
    }

    func completeTrip(id: Int, _ payload: TripCompletePayload) async throws -> Trip {
        try await client.send("trips/\(id)/complete", method: .post, body: payload)
    }

    func setTripStatus(id: Int, status: TripStatus, reason: String? = nil) async throws -> Trip {
        try await client.send(
            "trips/\(id)/status",
            method: .post,
            body: TripStatusPayload(status: status, reason: reason)
        )
    }

    func tripTrack(id: Int) async throws -> [TrackPoint] {
        try await client.send("trips/\(id)/track")
    }

    // MARK: - Locations

    func sendLocation(_ payload: LocationPayload) async throws -> TrackPoint {
        try await client.send("locations", method: .post, body: payload)
    }

    func sendLocations(_ payloads: [LocationPayload]) async throws -> [TrackPoint] {
        try await client.send(
            "locations/batch",
            method: .post,
            body: LocationBatchPayload(locations: payloads)
        )
    }

    // MARK: - Maintenance

    func maintenance(vehicleId: Int? = nil) async throws -> Page<MaintenanceRecord> {
        var query = [URLQueryItem(name: "limit", value: "100")]
        if let vehicleId { query.append(.init(name: "vehicle_id", value: String(vehicleId))) }
        return try await client.send("maintenance", query: query)
    }

    func createMaintenance(_ payload: MaintenancePayload) async throws -> MaintenanceRecord {
        try await client.send("maintenance", method: .post, body: payload)
    }

    func maintenanceDue() async throws -> [MaintenanceDueItem] {
        try await client.send("maintenance/due")
    }

    // MARK: - Incidents

    func incidents(status: IncidentStatus? = nil) async throws -> Page<Incident> {
        var query = [URLQueryItem(name: "limit", value: "100")]
        if let status { query.append(.init(name: "status_filter", value: status.rawValue)) }
        return try await client.send("incidents", query: query)
    }

    func reportIncident(_ payload: IncidentPayload) async throws -> Incident {
        try await client.send("incidents", method: .post, body: payload)
    }

    func updateIncident(id: Int, _ payload: IncidentUpdatePayload) async throws -> Incident {
        try await client.send("incidents/\(id)", method: .put, body: payload)
    }

    // MARK: - Notifications

    func notifications() async throws -> [AppNotification] {
        try await client.send("notifications")
    }

    func markNotificationRead(id: Int) async throws -> AppNotification {
        try await client.send("notifications/\(id)/read", method: .post)
    }

    func markAllNotificationsRead() async throws {
        let _: MessageResponse = try await client.send("notifications/read-all", method: .post)
    }

    func registerDevice(token: String) async throws {
        let _: MessageResponse = try await client.send(
            "notifications/devices",
            method: .post,
            body: DeviceTokenPayload(token: token, platform: "ios")
        )
    }

    // MARK: - Dashboard

    func dashboard() async throws -> DashboardSnapshot {
        try await client.send("dashboard")
    }

    func analytics(periodDays: Int = 30) async throws -> FleetAnalytics {
        try await client.send(
            "analytics",
            query: [URLQueryItem(name: "period_days", value: String(periodDays))]
        )
    }
}
