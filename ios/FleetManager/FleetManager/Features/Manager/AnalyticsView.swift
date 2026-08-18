import SwiftUI

struct AnalyticsView: View {
    @Environment(Session.self) private var session

    @State private var analytics: FleetAnalytics?
    @State private var periodDays = 30
    @State private var errorMessage: String?

    var body: some View {
        Group {
            if let analytics {
                List {
                    Section("Summary") {
                        DetailRow(label: "Distance",
                                  value: Format.distance(analytics.totalDistanceKm))
                        DetailRow(label: "Maintenance cost",
                                  value: Format.currency(analytics.totalMaintenanceCost))
                        DetailRow(
                            label: "Average cost per km",
                            value: analytics.averageCostPerKm.map {
                                Format.currency($0)
                            } ?? "—"
                        )
                    }

                    Section("Vehicle utilisation") {
                        if analytics.vehicles.isEmpty {
                            Text("No data").foregroundStyle(.secondary)
                        } else {
                            ForEach(analytics.vehicles) { row in
                                VStack(alignment: .leading, spacing: 3) {
                                    Text(row.registrationNumber)
                                        .font(.subheadline.weight(.medium))
                                    Text("\(row.totalTrips) trips · \(Format.distance(row.totalDistanceKm))")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }
                    }

                    Section("Driver performance") {
                        if analytics.drivers.isEmpty {
                            Text("No data").foregroundStyle(.secondary)
                        } else {
                            ForEach(analytics.drivers) { row in
                                VStack(alignment: .leading, spacing: 3) {
                                    Text(row.name).font(.subheadline.weight(.medium))
                                    Text("\(row.completedTrips) completed · \(Format.distance(row.totalDistanceKm)) · \(row.incidentsReported) incidents")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                }
            } else if let errorMessage {
                ErrorBanner(message: errorMessage) { Task { await load() } }
            } else {
                ProgressView()
            }
        }
        .navigationTitle("Analytics")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Menu {
                    ForEach([7, 30, 90], id: \.self) { days in
                        Button("Last \(days) days") {
                            periodDays = days
                            Task { await load() }
                        }
                    }
                } label: {
                    Text("\(periodDays)d")
                }
            }
        }
        .task { await load() }
    }

    private func load() async {
        do {
            analytics = try await session.api.analytics(periodDays: periodDays)
            errorMessage = nil
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}
