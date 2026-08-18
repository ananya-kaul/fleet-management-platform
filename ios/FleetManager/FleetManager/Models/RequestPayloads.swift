import Foundation

/// Request bodies. Kept separate from the read models so that optional/required
/// differences between what the API accepts and what it returns stay explicit.

struct LoginPayload: Encodable {
    let email: String
    let password: String
}

struct RefreshPayload: Encodable {
    let refreshToken: String
    enum CodingKeys: String, CodingKey { case refreshToken = "refresh_token" }
}

struct ChangePasswordPayload: Encodable {
    let currentPassword: String
    let newPassword: String

    enum CodingKeys: String, CodingKey {
        case currentPassword = "current_password"
        case newPassword = "new_password"
    }
}

struct VehiclePayload: Encodable {
    var registrationNumber: String
    var vehicleType: VehicleType
    var make: String
    var model: String
    var year: Int
    var fuelType: FuelType
    var currentMileage: Double
    var insuranceExpiry: String?
    var registrationExpiry: String?

    enum CodingKeys: String, CodingKey {
        case make, model, year
        case registrationNumber = "registration_number"
        case vehicleType = "vehicle_type"
        case fuelType = "fuel_type"
        case currentMileage = "current_mileage"
        case insuranceExpiry = "insurance_expiry"
        case registrationExpiry = "registration_expiry"
    }
}

struct VehicleUpdatePayload: Encodable {
    var make: String?
    var model: String?
    var currentMileage: Double?
    var status: VehicleStatus?
    var insuranceExpiry: String?
    var registrationExpiry: String?

    enum CodingKeys: String, CodingKey {
        case make, model, status
        case currentMileage = "current_mileage"
        case insuranceExpiry = "insurance_expiry"
        case registrationExpiry = "registration_expiry"
    }
}

struct DriverPayload: Encodable {
    var name: String
    var phoneNumber: String
    var licenseNumber: String
    var licenseExpiry: String
    var email: String?
    var password: String?

    enum CodingKeys: String, CodingKey {
        case name, email, password
        case phoneNumber = "phone_number"
        case licenseNumber = "license_number"
        case licenseExpiry = "license_expiry"
    }
}

struct AssignmentPayload: Encodable {
    let vehicleId: Int
    let driverId: Int
    let startDate: String
    let endDate: String?
    var notes: String?

    enum CodingKeys: String, CodingKey {
        case notes
        case vehicleId = "vehicle_id"
        case driverId = "driver_id"
        case startDate = "start_date"
        case endDate = "end_date"
    }
}

struct TripPayload: Encodable {
    let vehicleId: Int
    let driverId: Int
    let source: String
    let destination: String
    let scheduledStart: Date
    let scheduledEnd: Date
    var notes: String?

    enum CodingKeys: String, CodingKey {
        case source, destination, notes
        case vehicleId = "vehicle_id"
        case driverId = "driver_id"
        case scheduledStart = "scheduled_start"
        case scheduledEnd = "scheduled_end"
    }
}

struct TripStartPayload: Encodable {
    let startOdometer: Double
    let startLatitude: Double
    let startLongitude: Double

    enum CodingKeys: String, CodingKey {
        case startOdometer = "start_odometer"
        case startLatitude = "start_latitude"
        case startLongitude = "start_longitude"
    }
}

struct TripCompletePayload: Encodable {
    let endOdometer: Double
    let endLatitude: Double
    let endLongitude: Double

    enum CodingKeys: String, CodingKey {
        case endOdometer = "end_odometer"
        case endLatitude = "end_latitude"
        case endLongitude = "end_longitude"
    }
}

struct TripStatusPayload: Encodable {
    let status: TripStatus
    var reason: String?
}

struct LocationPayload: Encodable, Equatable {
    let vehicleId: Int
    let tripId: Int?
    let latitude: Double
    let longitude: Double
    let speedKph: Double?
    let heading: Double?
    let accuracyM: Double?
    let recordedAt: Date

    enum CodingKeys: String, CodingKey {
        case latitude, longitude, heading
        case vehicleId = "vehicle_id"
        case tripId = "trip_id"
        case speedKph = "speed_kph"
        case accuracyM = "accuracy_m"
        case recordedAt = "recorded_at"
    }
}

struct LocationBatchPayload: Encodable {
    let locations: [LocationPayload]
}

struct MaintenancePayload: Encodable {
    let vehicleId: Int
    let maintenanceType: MaintenanceType
    var description: String?
    let serviceDate: String
    let cost: Double
    let odometer: Double
    var nextServiceDate: String?
    var nextServiceMileage: Double?
    var performedBy: String?
    var setVehicleInMaintenance: Bool

    enum CodingKeys: String, CodingKey {
        case description, cost, odometer
        case vehicleId = "vehicle_id"
        case maintenanceType = "maintenance_type"
        case serviceDate = "service_date"
        case nextServiceDate = "next_service_date"
        case nextServiceMileage = "next_service_mileage"
        case performedBy = "performed_by"
        case setVehicleInMaintenance = "set_vehicle_in_maintenance"
    }
}

struct IncidentPayload: Encodable {
    let vehicleId: Int
    var tripId: Int?
    let title: String
    var description: String?
    let severity: IncidentSeverity

    enum CodingKeys: String, CodingKey {
        case title, description, severity
        case vehicleId = "vehicle_id"
        case tripId = "trip_id"
    }
}

struct IncidentUpdatePayload: Encodable {
    var status: IncidentStatus?
    var severity: IncidentSeverity?
    var resolutionNotes: String?

    enum CodingKeys: String, CodingKey {
        case status, severity
        case resolutionNotes = "resolution_notes"
    }
}

struct DeviceTokenPayload: Encodable {
    let token: String
    let platform: String
}
