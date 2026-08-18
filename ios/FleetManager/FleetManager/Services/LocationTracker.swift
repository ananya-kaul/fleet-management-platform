import CoreLocation
import Foundation
import Observation

/// Sends the driver's position to the backend while a trip is running.
///
/// Design notes:
/// - `allowsBackgroundLocationUpdates` is deliberately left off. Turning it on
///   requires the background-location entitlement and an App Store
///   justification; the assignment only calls for periodic updates, so the app
///   tracks in the foreground and flushes anything buffered on return.
/// - Pings that fail to upload are queued and retried through the batch
///   endpoint, so a tunnel or a dead zone does not punch a hole in the trail.
@Observable
@MainActor
final class LocationTracker: NSObject {
    private(set) var authorizationStatus: CLAuthorizationStatus
    private(set) var lastLocation: CLLocation?
    private(set) var pendingCount = 0
    private(set) var lastError: String?
    private(set) var isTracking = false

    private let manager = CLLocationManager()
    private var api: FleetAPI?
    private var vehicleId: Int?
    private var tripId: Int?
    private var lastSentAt: Date?
    /// Pings that could not be uploaded yet, oldest first.
    private var buffer: [LocationPayload] = []

    override init() {
        authorizationStatus = manager.authorizationStatus
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyNearestTenMeters
        // Only report movement of 25 m or more; a parked lorry should not
        // generate a ping every second.
        manager.distanceFilter = 25
    }

    var isAuthorized: Bool {
        authorizationStatus == .authorizedWhenInUse || authorizationStatus == .authorizedAlways
    }

    func requestPermission() {
        manager.requestWhenInUseAuthorization()
    }

    func startTracking(api: FleetAPI, vehicleId: Int, tripId: Int) {
        self.api = api
        self.vehicleId = vehicleId
        self.tripId = tripId

        guard isAuthorized else {
            requestPermission()
            return
        }

        isTracking = true
        manager.startUpdatingLocation()
    }

    func stopTracking() {
        isTracking = false
        manager.stopUpdatingLocation()
        Task { await flushBuffer() }
    }

    /// A one-shot reading for the start/complete forms, which need coordinates
    /// even before continuous tracking begins.
    func currentCoordinate() -> CLLocationCoordinate2D? {
        lastLocation?.coordinate ?? manager.location?.coordinate
    }

    // MARK: - Upload

    private func handle(_ location: CLLocation) {
        lastLocation = location

        // CoreLocation fires far more often than the backend needs; throttle to
        // the configured interval.
        if let lastSentAt, Date.now.timeIntervalSince(lastSentAt) < AppConfig.locationPingInterval {
            return
        }
        guard let vehicleId, let tripId else { return }
        lastSentAt = .now

        let payload = LocationPayload(
            vehicleId: vehicleId,
            tripId: tripId,
            latitude: location.coordinate.latitude,
            longitude: location.coordinate.longitude,
            speedKph: location.speed >= 0 ? location.speed * 3.6 : nil,
            heading: location.course >= 0 ? location.course : nil,
            accuracyM: location.horizontalAccuracy,
            recordedAt: location.timestamp
        )

        Task { await send(payload) }
    }

    private func send(_ payload: LocationPayload) async {
        guard let api else { return }

        // Anything already queued goes first so the trail stays in order.
        if !buffer.isEmpty {
            buffer.append(payload)
            pendingCount = buffer.count
            await flushBuffer()
            return
        }

        do {
            _ = try await api.sendLocation(payload)
            lastError = nil
        } catch {
            buffer.append(payload)
            pendingCount = buffer.count
            lastError = "Buffered \(buffer.count) position(s) - will retry."
        }
    }

    private func flushBuffer() async {
        guard let api, !buffer.isEmpty else { return }
        let batch = buffer

        do {
            _ = try await api.sendLocations(batch)
            buffer.removeAll()
            pendingCount = 0
            lastError = nil
        } catch {
            // Keep the buffer for the next attempt, but do not let it grow
            // without bound on a long outage.
            if buffer.count > 500 {
                buffer.removeFirst(buffer.count - 500)
            }
            pendingCount = buffer.count
        }
    }
}

extension LocationTracker: CLLocationManagerDelegate {
    nonisolated func locationManager(
        _ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]
    ) {
        guard let latest = locations.last else { return }
        Task { @MainActor in handle(latest) }
    }

    nonisolated func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        let status = manager.authorizationStatus
        Task { @MainActor in
            authorizationStatus = status
            if isAuthorized, isTracking {
                manager.startUpdatingLocation()
            }
        }
    }

    nonisolated func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        Task { @MainActor in
            // A transient "unknown location" is normal indoors; only surface
            // the errors a driver can act on.
            if (error as? CLError)?.code != .locationUnknown {
                lastError = error.localizedDescription
            }
        }
    }
}
