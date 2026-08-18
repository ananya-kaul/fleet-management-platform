import MapKit
import SwiftUI

/// Live fleet map.
///
/// Positions are seeded from `GET /locations/latest` and then kept current by
/// the `/ws/tracking` WebSocket, so a moving vehicle updates without polling.
struct FleetMapView: View {
    @Environment(Session.self) private var session

    @State private var positions: [Int: TrackPoint] = [:]
    @State private var registrations: [Int: String] = [:]
    @State private var socket = TrackingSocket()
    @State private var errorMessage: String?

    private var markers: [TrackPoint] {
        positions.values.sorted { $0.vehicleId < $1.vehicleId }
    }

    var body: some View {
        Group {
            if markers.isEmpty {
                EmptyStateView(
                    title: "No positions yet",
                    message: "Vehicle positions appear here once a driver starts a trip.",
                    systemImage: "map"
                )
            } else {
                Map(initialPosition: .region(region)) {
                    ForEach(markers) { point in
                        Marker(
                            registrations[point.vehicleId] ?? "Vehicle \(point.vehicleId)",
                            systemImage: "truck.box.fill",
                            coordinate: CLLocationCoordinate2D(
                                latitude: point.latitude, longitude: point.longitude
                            )
                        )
                        .tint(.blue)
                    }
                }
            }
        }
        .navigationTitle("Live map")
        .navigationBarTitleDisplayMode(.inline)
        .overlay(alignment: .bottom) {
            HStack(spacing: 6) {
                Circle()
                    .fill(socket.isConnected ? .green : .secondary)
                    .frame(width: 8, height: 8)
                Text(socket.isConnected ? "Live" : "Not connected")
                    .font(.caption)
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(.thinMaterial, in: Capsule())
            .padding(.bottom, 12)
        }
        .task {
            await loadInitialPositions()
            socket.connect { update in
                positions[update.vehicleId] = update.point
                registrations[update.vehicleId] = update.registrationNumber
            }
        }
        .onDisappear { socket.disconnect() }
    }

    private func loadInitialPositions() async {
        do {
            let points = try await session.api.fleetPositions()
            positions = Dictionary(uniqueKeysWithValues: points.map { ($0.vehicleId, $0) })

            let vehicles = try await session.api.vehicles().items
            registrations = Dictionary(
                uniqueKeysWithValues: vehicles.map { ($0.id, $0.registrationNumber) }
            )
            errorMessage = nil
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private var region: MKCoordinateRegion {
        let coordinates = markers.map {
            CLLocationCoordinate2D(latitude: $0.latitude, longitude: $0.longitude)
        }
        guard !coordinates.isEmpty else {
            return MKCoordinateRegion(
                center: CLLocationCoordinate2D(latitude: 12.9716, longitude: 77.5946),
                span: MKCoordinateSpan(latitudeDelta: 2, longitudeDelta: 2)
            )
        }

        let latitudes = coordinates.map(\.latitude)
        let longitudes = coordinates.map(\.longitude)
        let minLat = latitudes.min()!, maxLat = latitudes.max()!
        let minLon = longitudes.min()!, maxLon = longitudes.max()!

        return MKCoordinateRegion(
            center: CLLocationCoordinate2D(
                latitude: (minLat + maxLat) / 2, longitude: (minLon + maxLon) / 2
            ),
            span: MKCoordinateSpan(
                latitudeDelta: max((maxLat - minLat) * 1.5, 0.2),
                longitudeDelta: max((maxLon - minLon) * 1.5, 0.2)
            )
        )
    }
}
