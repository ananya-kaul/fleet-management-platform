import MapKit
import SwiftUI

struct TripDetailView: View {
    @Environment(Session.self) private var session
    let tripId: Int
    var onChange: () -> Void

    @State private var trip: Trip?
    @State private var track: [TrackPoint] = []
    @State private var errorMessage: String?
    @State private var actionError: String?
    @State private var isCancelling = false

    var body: some View {
        Group {
            if let trip {
                List {
                    Section("Trip") {
                        DetailRow(label: "Code", value: trip.tripCode)
                        DetailRow(label: "From", value: trip.source)
                        DetailRow(label: "To", value: trip.destination)
                        HStack {
                            Text("Status").foregroundStyle(.secondary)
                            Spacer()
                            StatusChip(text: trip.status.label, color: trip.status.color)
                        }
                        DetailRow(label: "Vehicle",
                                  value: trip.vehicle?.registrationNumber ?? "—")
                        DetailRow(label: "Driver", value: trip.driver?.name ?? "—")
                    }

                    Section("Schedule") {
                        DetailRow(label: "Scheduled start",
                                  value: Format.dateTime(trip.scheduledStart))
                        DetailRow(label: "Scheduled end",
                                  value: Format.dateTime(trip.scheduledEnd))
                        DetailRow(label: "Actual start", value: Format.dateTime(trip.actualStart))
                        DetailRow(label: "Actual end", value: Format.dateTime(trip.actualEnd))
                    }

                    Section("Odometer") {
                        DetailRow(label: "Start", value: Format.odometer(trip.startOdometer))
                        DetailRow(label: "End", value: Format.odometer(trip.endOdometer))
                        DetailRow(label: "Distance travelled",
                                  value: Format.distance(trip.distanceKm))
                    }

                    if !track.isEmpty {
                        Section("Route") {
                            TripRouteMap(points: track)
                                .frame(height: 220)
                                .listRowInsets(EdgeInsets())
                        }
                    }

                    if let reason = trip.cancellationReason {
                        Section("Cancellation") { Text(reason) }
                    }

                    if trip.status == .scheduled || trip.status.isActive {
                        Section {
                            Button("Cancel trip", role: .destructive) {
                                Task { await cancel() }
                            }
                            .disabled(isCancelling)
                        } footer: {
                            if let actionError { Text(actionError).foregroundStyle(.red) }
                        }
                    }
                }
            } else if let errorMessage {
                ErrorBanner(message: errorMessage) { Task { await load() } }
            } else {
                ProgressView()
            }
        }
        .navigationTitle(trip?.tripCode ?? "Trip")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private func load() async {
        do {
            trip = try await session.api.trip(id: tripId)
            track = (try? await session.api.tripTrack(id: tripId)) ?? []
            errorMessage = nil
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func cancel() async {
        isCancelling = true
        defer { isCancelling = false }
        do {
            trip = try await session.api.setTripStatus(
                id: tripId, status: .cancelled, reason: "Cancelled by the fleet manager"
            )
            actionError = nil
            onChange()
        } catch {
            actionError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

/// Draws the recorded breadcrumb trail. Uses MapKit's SwiftUI `Map`, so there
/// is no third-party dependency and no API key to manage.
struct TripRouteMap: View {
    let points: [TrackPoint]

    private var coordinates: [CLLocationCoordinate2D] {
        points.map { CLLocationCoordinate2D(latitude: $0.latitude, longitude: $0.longitude) }
    }

    var body: some View {
        Map(initialPosition: .region(region)) {
            if let first = coordinates.first {
                Marker("Start", systemImage: "flag", coordinate: first)
                    .tint(.green)
            }
            if coordinates.count > 1, let last = coordinates.last {
                Marker("Latest", systemImage: "location.fill", coordinate: last)
                    .tint(.blue)
            }
            MapPolyline(coordinates: coordinates)
                .stroke(.blue, lineWidth: 4)
        }
    }

    /// A region that contains every point, with a little padding so the markers
    /// are not flush against the edge.
    private var region: MKCoordinateRegion {
        guard !coordinates.isEmpty else {
            return MKCoordinateRegion(
                center: CLLocationCoordinate2D(latitude: 12.9716, longitude: 77.5946),
                span: MKCoordinateSpan(latitudeDelta: 1, longitudeDelta: 1)
            )
        }

        let latitudes = coordinates.map(\.latitude)
        let longitudes = coordinates.map(\.longitude)
        let minLat = latitudes.min()!, maxLat = latitudes.max()!
        let minLon = longitudes.min()!, maxLon = longitudes.max()!

        return MKCoordinateRegion(
            center: CLLocationCoordinate2D(
                latitude: (minLat + maxLat) / 2,
                longitude: (minLon + maxLon) / 2
            ),
            span: MKCoordinateSpan(
                latitudeDelta: max((maxLat - minLat) * 1.4, 0.05),
                longitudeDelta: max((maxLon - minLon) * 1.4, 0.05)
            )
        )
    }
}
