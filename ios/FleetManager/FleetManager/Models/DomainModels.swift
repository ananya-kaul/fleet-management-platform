import Foundation

/// Paged list envelope returned by the collection endpoints.
struct Page<Item: Decodable>: Decodable {
    let items: [Item]
    let total: Int
    let limit: Int
    let offset: Int
}

struct MessageResponse: Decodable {
    let detail: String
}

// MARK: - Auth

struct AuthUser: Codable, Identifiable, Equatable {
    let id: Int
    let email: String
    let fullName: String
    let role: UserRole
    let isActive: Bool
    let driverId: Int?

    enum CodingKeys: String, CodingKey {
        case id, email, role
        case fullName = "full_name"
        case isActive = "is_active"
        case driverId = "driver_id"
    }
}

struct TokenPair: Decodable {
    let accessToken: String
    let refreshToken: String
    let user: AuthUser

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case user
    }
}

struct AccessTokenResponse: Decodable {
    let accessToken: String
    enum CodingKeys: String, CodingKey { case accessToken = "access_token" }
}

// MARK: - Vehicle

struct Vehicle: Codable, Identifiable, Equatable, Hashable {
    let id: Int
    let registrationNumber: String
    let vehicleType: VehicleType
    let make: String
    let model: String
    let year: Int
    let fuelType: FuelType
    let currentMileage: Double
    let status: VehicleStatus
    let isActive: Bool
    let insuranceExpiry: Date?
    let registrationExpiry: Date?

    enum CodingKeys: String, CodingKey {
        case id, make, model, year, status
        case registrationNumber = "registration_number"
        case vehicleType = "vehicle_type"
        case fuelType = "fuel_type"
        case currentMileage = "current_mileage"
        case isActive = "is_active"
        case insuranceExpiry = "insurance_expiry"
        case registrationExpiry = "registration_expiry"
    }

    var displayName: String { "\(make) \(model)" }
}

/// Compact vehicle projection embedded in trips and assignments.
struct VehicleSummary: Codable, Identifiable, Equatable, Hashable {
    let id: Int
    let registrationNumber: String
    let make: String
    let model: String
    let status: VehicleStatus

    enum CodingKeys: String, CodingKey {
        case id, make, model, status
        case registrationNumber = "registration_number"
    }

    var displayName: String { "\(make) \(model)" }
}

// MARK: - Driver

struct Driver: Codable, Identifiable, Equatable, Hashable {
    let id: Int
    let name: String
    let phoneNumber: String
    let licenseNumber: String
    let licenseExpiry: Date
    let status: DriverStatus
    let userId: Int?
    let assignedVehicleId: Int?
    let assignedVehicleRegistration: String?

    enum CodingKeys: String, CodingKey {
        case id, name, status
        case phoneNumber = "phone_number"
        case licenseNumber = "license_number"
        case licenseExpiry = "license_expiry"
        case userId = "user_id"
        case assignedVehicleId = "assigned_vehicle_id"
        case assignedVehicleRegistration = "assigned_vehicle_registration"
    }
}

struct DriverSummary: Codable, Identifiable, Equatable, Hashable {
    let id: Int
    let name: String
    let phoneNumber: String
    let status: DriverStatus

    enum CodingKeys: String, CodingKey {
        case id, name, status
        case phoneNumber = "phone_number"
    }
}

// MARK: - Assignment

struct Assignment: Codable, Identifiable, Equatable {
    let id: Int
    let vehicleId: Int
    let driverId: Int
    let startDate: Date
    let endDate: Date?
    let isActive: Bool
    let notes: String?
    let vehicle: VehicleSummary?
    let driver: DriverSummary?

    enum CodingKeys: String, CodingKey {
        case id, notes, vehicle, driver
        case vehicleId = "vehicle_id"
        case driverId = "driver_id"
        case startDate = "start_date"
        case endDate = "end_date"
        case isActive = "is_active"
    }
}

// MARK: - Trip

struct Trip: Codable, Identifiable, Equatable, Hashable {
    let id: Int
    let tripCode: String
    let vehicleId: Int
    let driverId: Int
    let source: String
    let destination: String
    let scheduledStart: Date
    let scheduledEnd: Date
    let status: TripStatus
    let notes: String?

    let actualStart: Date?
    let startLatitude: Double?
    let startLongitude: Double?
    let startOdometer: Double?

    let actualEnd: Date?
    let endLatitude: Double?
    let endLongitude: Double?
    let endOdometer: Double?

    let distanceKm: Double?
    let cancellationReason: String?

    let vehicle: VehicleSummary?
    let driver: DriverSummary?

    enum CodingKeys: String, CodingKey {
        case id, source, destination, status, notes, vehicle, driver
        case tripCode = "trip_code"
        case vehicleId = "vehicle_id"
        case driverId = "driver_id"
        case scheduledStart = "scheduled_start"
        case scheduledEnd = "scheduled_end"
        case actualStart = "actual_start"
        case startLatitude = "start_latitude"
        case startLongitude = "start_longitude"
        case startOdometer = "start_odometer"
        case actualEnd = "actual_end"
        case endLatitude = "end_latitude"
        case endLongitude = "end_longitude"
        case endOdometer = "end_odometer"
        case distanceKm = "distance_km"
        case cancellationReason = "cancellation_reason"
    }

    var route: String { "\(source) → \(destination)" }
}

// MARK: - Location

struct TrackPoint: Codable, Identifiable, Equatable {
    let id: Int
    let vehicleId: Int
    let tripId: Int?
    let latitude: Double
    let longitude: Double
    let speedKph: Double?
    let heading: Double?
    let accuracyM: Double?
    let recordedAt: Date

    enum CodingKeys: String, CodingKey {
        case id, latitude, longitude, heading
        case vehicleId = "vehicle_id"
        case tripId = "trip_id"
        case speedKph = "speed_kph"
        case accuracyM = "accuracy_m"
        case recordedAt = "recorded_at"
    }
}

// MARK: - Maintenance

struct MaintenanceRecord: Codable, Identifiable, Equatable {
    let id: Int
    let vehicleId: Int
    let maintenanceType: MaintenanceType
    let description: String?
    let serviceDate: Date
    let cost: Double
    let odometer: Double
    let nextServiceDate: Date?
    let nextServiceMileage: Double?
    let performedBy: String?
    let vehicle: VehicleSummary?

    enum CodingKeys: String, CodingKey {
        case id, description, cost, odometer, vehicle
        case vehicleId = "vehicle_id"
        case maintenanceType = "maintenance_type"
        case serviceDate = "service_date"
        case nextServiceDate = "next_service_date"
        case nextServiceMileage = "next_service_mileage"
        case performedBy = "performed_by"
    }
}

struct MaintenanceDueItem: Codable, Identifiable, Equatable {
    let vehicleId: Int
    let registrationNumber: String
    let reason: String
    let dueDate: Date?
    let dueMileage: Double?

    var id: String { "\(vehicleId)-\(reason)" }

    enum CodingKeys: String, CodingKey {
        case reason
        case vehicleId = "vehicle_id"
        case registrationNumber = "registration_number"
        case dueDate = "due_date"
        case dueMileage = "due_mileage"
    }
}

// MARK: - Incident

struct Incident: Codable, Identifiable, Equatable {
    let id: Int
    let vehicleId: Int
    let tripId: Int?
    let reportedByDriverId: Int?
    let assignedToUserId: Int?
    let title: String
    let description: String?
    let severity: IncidentSeverity
    let status: IncidentStatus
    let resolutionNotes: String?
    let reportedAt: Date
    let resolvedAt: Date?
    let vehicle: VehicleSummary?
    let reportedBy: DriverSummary?

    enum CodingKeys: String, CodingKey {
        case id, title, description, severity, status, vehicle
        case vehicleId = "vehicle_id"
        case tripId = "trip_id"
        case reportedByDriverId = "reported_by_driver_id"
        case assignedToUserId = "assigned_to_user_id"
        case resolutionNotes = "resolution_notes"
        case reportedAt = "reported_at"
        case resolvedAt = "resolved_at"
        case reportedBy = "reported_by"
    }
}

// MARK: - Notification

struct AppNotification: Codable, Identifiable, Equatable {
    let id: Int
    let category: NotificationCategory
    let title: String
    let body: String
    let isRead: Bool
    let reference: String?
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id, category, title, body, reference
        case isRead = "is_read"
        case createdAt = "created_at"
    }
}

// MARK: - Dashboard

struct ExpiringDocument: Codable, Identifiable, Equatable {
    let vehicleId: Int?
    let driverId: Int?
    let subject: String
    let document: String
    let expiresOn: Date
    let daysRemaining: Int

    var id: String { "\(subject)-\(document)" }

    enum CodingKeys: String, CodingKey {
        case subject, document
        case vehicleId = "vehicle_id"
        case driverId = "driver_id"
        case expiresOn = "expires_on"
        case daysRemaining = "days_remaining"
    }
}

struct DashboardSnapshot: Codable, Equatable {
    let totalVehicles: Int
    let availableVehicles: Int
    let vehiclesOnTrip: Int
    let vehiclesInMaintenance: Int
    let inactiveVehicles: Int
    let totalDrivers: Int
    let activeDrivers: Int
    let activeTrips: Int
    let scheduledTrips: Int
    let completedTripsToday: Int
    let distanceTodayKm: Double
    let maintenanceDueCount: Int
    let expiringDocumentsCount: Int
    let openIncidents: Int
    let maintenanceDue: [MaintenanceDueItem]
    let expiringDocuments: [ExpiringDocument]
    let recentIncidents: [Incident]

    enum CodingKeys: String, CodingKey {
        case totalVehicles = "total_vehicles"
        case availableVehicles = "available_vehicles"
        case vehiclesOnTrip = "vehicles_on_trip"
        case vehiclesInMaintenance = "vehicles_in_maintenance"
        case inactiveVehicles = "inactive_vehicles"
        case totalDrivers = "total_drivers"
        case activeDrivers = "active_drivers"
        case activeTrips = "active_trips"
        case scheduledTrips = "scheduled_trips"
        case completedTripsToday = "completed_trips_today"
        case distanceTodayKm = "distance_today_km"
        case maintenanceDueCount = "maintenance_due_count"
        case expiringDocumentsCount = "expiring_documents_count"
        case openIncidents = "open_incidents"
        case maintenanceDue = "maintenance_due"
        case expiringDocuments = "expiring_documents"
        case recentIncidents = "recent_incidents"
    }
}

// MARK: - Analytics

struct VehicleUtilisation: Codable, Identifiable, Equatable {
    let vehicleId: Int
    let registrationNumber: String
    let totalTrips: Int
    let totalDistanceKm: Double
    let maintenanceCost: Double
    let costPerKm: Double?
    let daysOnTrip: Int

    var id: Int { vehicleId }

    enum CodingKeys: String, CodingKey {
        case vehicleId = "vehicle_id"
        case registrationNumber = "registration_number"
        case totalTrips = "total_trips"
        case totalDistanceKm = "total_distance_km"
        case maintenanceCost = "maintenance_cost"
        case costPerKm = "cost_per_km"
        case daysOnTrip = "days_on_trip"
    }
}

struct DriverPerformance: Codable, Identifiable, Equatable {
    let driverId: Int
    let name: String
    let totalTrips: Int
    let completedTrips: Int
    let totalDistanceKm: Double
    let averageTripDurationMinutes: Double?
    let incidentsReported: Int

    var id: Int { driverId }

    enum CodingKeys: String, CodingKey {
        case name
        case driverId = "driver_id"
        case totalTrips = "total_trips"
        case completedTrips = "completed_trips"
        case totalDistanceKm = "total_distance_km"
        case averageTripDurationMinutes = "average_trip_duration_minutes"
        case incidentsReported = "incidents_reported"
    }
}

struct FleetAnalytics: Codable, Equatable {
    let periodDays: Int
    let totalDistanceKm: Double
    let totalMaintenanceCost: Double
    let averageCostPerKm: Double?
    let vehicles: [VehicleUtilisation]
    let drivers: [DriverPerformance]

    enum CodingKeys: String, CodingKey {
        case vehicles, drivers
        case periodDays = "period_days"
        case totalDistanceKm = "total_distance_km"
        case totalMaintenanceCost = "total_maintenance_cost"
        case averageCostPerKm = "average_cost_per_km"
    }
}
