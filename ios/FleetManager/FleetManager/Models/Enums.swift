import SwiftUI

/// Enums mirror the backend's string enums exactly.
/// `CaseIterable` drives the pickers; the colours drive the status chips.

enum UserRole: String, Codable, CaseIterable, Identifiable {
    case fleetManager = "FLEET_MANAGER"
    case driver = "DRIVER"

    var id: String { rawValue }
    var label: String { self == .fleetManager ? "Fleet Manager" : "Driver" }
}

enum VehicleStatus: String, Codable, CaseIterable, Identifiable {
    case available = "AVAILABLE"
    case onTrip = "ON_TRIP"
    case inMaintenance = "IN_MAINTENANCE"
    case inactive = "INACTIVE"

    var id: String { rawValue }

    var label: String {
        switch self {
        case .available: "Available"
        case .onTrip: "On trip"
        case .inMaintenance: "In maintenance"
        case .inactive: "Inactive"
        }
    }

    var color: Color {
        switch self {
        case .available: .green
        case .onTrip: .blue
        case .inMaintenance: .orange
        case .inactive: .secondary
        }
    }
}

enum VehicleType: String, Codable, CaseIterable, Identifiable {
    case truck = "TRUCK", van = "VAN", car = "CAR", bike = "BIKE", bus = "BUS"
    var id: String { rawValue }
    var label: String { rawValue.capitalized }
}

enum FuelType: String, Codable, CaseIterable, Identifiable {
    case petrol = "PETROL", diesel = "DIESEL", cng = "CNG"
    case electric = "ELECTRIC", hybrid = "HYBRID"

    var id: String { rawValue }
    var label: String { self == .cng ? "CNG" : rawValue.capitalized }
}

enum DriverStatus: String, Codable, CaseIterable, Identifiable {
    case active = "ACTIVE", inactive = "INACTIVE", suspended = "SUSPENDED"

    var id: String { rawValue }
    var label: String { rawValue.capitalized }

    var color: Color {
        switch self {
        case .active: .green
        case .inactive: .secondary
        case .suspended: .red
        }
    }
}

enum TripStatus: String, Codable, CaseIterable, Identifiable {
    case scheduled = "SCHEDULED"
    case started = "STARTED"
    case inProgress = "IN_PROGRESS"
    case completed = "COMPLETED"
    case cancelled = "CANCELLED"

    var id: String { rawValue }

    var label: String {
        switch self {
        case .scheduled: "Scheduled"
        case .started: "Started"
        case .inProgress: "In progress"
        case .completed: "Completed"
        case .cancelled: "Cancelled"
        }
    }

    var color: Color {
        switch self {
        case .scheduled: .orange
        case .started, .inProgress: .blue
        case .completed: .green
        case .cancelled: .secondary
        }
    }

    var isActive: Bool { self == .started || self == .inProgress }
}

enum IncidentSeverity: String, Codable, CaseIterable, Identifiable {
    case low = "LOW", medium = "MEDIUM", high = "HIGH", critical = "CRITICAL"

    var id: String { rawValue }
    var label: String { rawValue.capitalized }

    var color: Color {
        switch self {
        case .low: .secondary
        case .medium: .yellow
        case .high: .orange
        case .critical: .red
        }
    }
}

enum IncidentStatus: String, Codable, CaseIterable, Identifiable {
    case open = "OPEN", inProgress = "IN_PROGRESS", resolved = "RESOLVED"

    var id: String { rawValue }
    var label: String { self == .inProgress ? "In progress" : rawValue.capitalized }

    var color: Color {
        switch self {
        case .open: .red
        case .inProgress: .orange
        case .resolved: .green
        }
    }
}

enum MaintenanceType: String, Codable, CaseIterable, Identifiable {
    case oilChange = "OIL_CHANGE"
    case brakeService = "BRAKE_SERVICE"
    case tyreReplacement = "TYRE_REPLACEMENT"
    case engineService = "ENGINE_SERVICE"
    case generalInspection = "GENERAL_INSPECTION"
    case other = "OTHER"

    var id: String { rawValue }

    var label: String {
        switch self {
        case .oilChange: "Oil change"
        case .brakeService: "Brake service"
        case .tyreReplacement: "Tyre replacement"
        case .engineService: "Engine service"
        case .generalInspection: "General inspection"
        case .other: "Other"
        }
    }
}

enum NotificationCategory: String, Codable {
    case maintenanceDue = "MAINTENANCE_DUE"
    case insuranceExpiry = "INSURANCE_EXPIRY"
    case licenseExpiry = "LICENSE_EXPIRY"
    case tripAssigned = "TRIP_ASSIGNED"
    case tripCompleted = "TRIP_COMPLETED"
    case incidentReported = "INCIDENT_REPORTED"

    var iconName: String {
        switch self {
        case .maintenanceDue: "wrench.and.screwdriver"
        case .insuranceExpiry, .licenseExpiry: "calendar.badge.exclamationmark"
        case .tripAssigned: "arrow.triangle.turn.up.right.circle"
        case .tripCompleted: "checkmark.circle"
        case .incidentReported: "exclamationmark.triangle"
        }
    }
}
