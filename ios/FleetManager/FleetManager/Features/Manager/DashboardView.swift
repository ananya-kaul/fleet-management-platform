import SwiftUI

@Observable
@MainActor
final class DashboardViewModel {
    var snapshot: DashboardSnapshot?
    var errorMessage: String?
    var isLoading = false

    func load(api: FleetAPI) async {
        isLoading = true
        defer { isLoading = false }
        do {
            snapshot = try await api.dashboard()
            errorMessage = nil
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

struct DashboardView: View {
    @Environment(Session.self) private var session
    @State private var model = DashboardViewModel()

    private let columns = [GridItem(.adaptive(minimum: 150), spacing: 12)]

    var body: some View {
        NavigationStack {
            Group {
                if let snapshot = model.snapshot {
                    content(for: snapshot)
                } else if model.isLoading {
                    ProgressView()
                } else if let error = model.errorMessage {
                    ErrorBanner(message: error) {
                        Task { await model.load(api: session.api) }
                    }
                } else {
                    EmptyStateView(title: "No data yet")
                }
            }
            .navigationTitle("Fleet overview")
            .refreshable { await model.load(api: session.api) }
        }
        .task { await model.load(api: session.api) }
    }

    @ViewBuilder
    private func content(for snapshot: DashboardSnapshot) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                LazyVGrid(columns: columns, spacing: 12) {
                    MetricTile(title: "Total vehicles", value: "\(snapshot.totalVehicles)",
                               systemImage: "truck.box", tint: .primary)
                    MetricTile(title: "Available", value: "\(snapshot.availableVehicles)",
                               systemImage: "checkmark.circle", tint: .green)
                    MetricTile(title: "On trip", value: "\(snapshot.vehiclesOnTrip)",
                               systemImage: "location.fill", tint: .blue)
                    MetricTile(title: "In maintenance", value: "\(snapshot.vehiclesInMaintenance)",
                               systemImage: "wrench.and.screwdriver", tint: .orange)
                    MetricTile(title: "Inactive", value: "\(snapshot.inactiveVehicles)",
                               systemImage: "pause.circle", tint: .secondary)
                    MetricTile(title: "Active trips", value: "\(snapshot.activeTrips)",
                               systemImage: "arrow.triangle.turn.up.right.circle", tint: .blue)
                    MetricTile(title: "Today's distance",
                               value: Format.distance(snapshot.distanceTodayKm),
                               systemImage: "road.lanes", tint: .primary)
                    MetricTile(title: "Maintenance due", value: "\(snapshot.maintenanceDueCount)",
                               systemImage: "exclamationmark.triangle", tint: .orange)
                    MetricTile(title: "Expiring documents",
                               value: "\(snapshot.expiringDocumentsCount)",
                               systemImage: "calendar.badge.exclamationmark", tint: .red)
                    MetricTile(title: "Open incidents", value: "\(snapshot.openIncidents)",
                               systemImage: "bolt.trianglebadge.exclamationmark", tint: .red)
                }

                if !snapshot.maintenanceDue.isEmpty {
                    section("Maintenance due") {
                        ForEach(snapshot.maintenanceDue) { item in
                            VStack(alignment: .leading, spacing: 2) {
                                Text(item.registrationNumber).font(.subheadline.weight(.medium))
                                Text(item.reason)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }
                }

                if !snapshot.expiringDocuments.isEmpty {
                    section("Expiring documents") {
                        ForEach(snapshot.expiringDocuments) { item in
                            HStack {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text("\(item.subject) · \(item.document)")
                                        .font(.subheadline)
                                    Text(Format.day(item.expiresOn))
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                                Spacer()
                                StatusChip(
                                    text: item.daysRemaining < 0
                                        ? "Expired"
                                        : "\(item.daysRemaining) days",
                                    color: item.daysRemaining < 0 ? .red : .orange
                                )
                            }
                        }
                    }
                }

                if !snapshot.recentIncidents.isEmpty {
                    section("Recent incidents") {
                        ForEach(snapshot.recentIncidents) { incident in
                            HStack {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(incident.title).font(.subheadline)
                                    Text(incident.vehicle?.registrationNumber ?? "—")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                                Spacer()
                                StatusChip(text: incident.severity.label,
                                           color: incident.severity.color)
                            }
                        }
                    }
                }
            }
            .padding()
        }
    }

    @ViewBuilder
    private func section<Content: View>(
        _ title: String, @ViewBuilder content: () -> Content
    ) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title).font(.headline)
            VStack(spacing: 10) { content() }
                .padding(12)
                .background(Color(.secondarySystemBackground),
                            in: RoundedRectangle(cornerRadius: 10))
        }
    }
}
