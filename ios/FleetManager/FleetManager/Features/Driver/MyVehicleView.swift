import SwiftUI

/// The vehicle currently assigned to the signed-in driver, plus a shortcut to
/// report a problem with it.
struct MyVehicleView: View {
    @Environment(Session.self) private var session

    @State private var profile: Driver?
    @State private var vehicle: Vehicle?
    @State private var myIncidents: [Incident] = []
    @State private var errorMessage: String?
    @State private var isLoading = false
    @State private var isPresentingIssue = false

    var body: some View {
        Group {
            if isLoading, profile == nil {
                ProgressView()
            } else if let errorMessage, profile == nil {
                ErrorBanner(message: errorMessage) { Task { await load() } }
            } else if let vehicle {
                List {
                    Section("Assigned vehicle") {
                        DetailRow(label: "Registration", value: vehicle.registrationNumber)
                        DetailRow(label: "Model", value: vehicle.displayName)
                        DetailRow(label: "Year", value: String(vehicle.year))
                        DetailRow(label: "Fuel", value: vehicle.fuelType.label)
                        DetailRow(label: "Odometer",
                                  value: Format.odometer(vehicle.currentMileage))
                        HStack {
                            Text("Status").foregroundStyle(.secondary)
                            Spacer()
                            StatusChip(text: vehicle.status.label, color: vehicle.status.color)
                        }
                    }

                    Section {
                        Button("Report an issue") { isPresentingIssue = true }
                    }

                    Section("My reports") {
                        if myIncidents.isEmpty {
                            Text("You have not reported any issues.")
                                .foregroundStyle(.secondary)
                        } else {
                            ForEach(myIncidents) { incident in
                                VStack(alignment: .leading, spacing: 3) {
                                    Text(incident.title).font(.subheadline)
                                    HStack {
                                        StatusChip(text: incident.status.label,
                                                   color: incident.status.color)
                                        Text(Format.dateTime(incident.reportedAt))
                                            .font(.caption2)
                                            .foregroundStyle(.secondary)
                                    }
                                }
                            }
                        }
                    }
                }
            } else {
                EmptyStateView(
                    title: "No vehicle assigned",
                    message: "Your fleet manager has not assigned a vehicle to you yet.",
                    systemImage: "truck.box"
                )
            }
        }
        .navigationTitle("My vehicle")
        .refreshable { await load() }
        .task { await load() }
        .sheet(isPresented: $isPresentingIssue) {
            if let vehicle {
                ReportIssueView(vehicleId: vehicle.id)
            }
        }
    }

    private func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let driver = try await session.api.myDriverProfile()
            profile = driver
            if let vehicleId = driver.assignedVehicleId {
                vehicle = try await session.api.vehicle(id: vehicleId)
            } else {
                vehicle = nil
            }
            myIncidents = (try? await session.api.incidents().items) ?? []
            errorMessage = nil
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}
