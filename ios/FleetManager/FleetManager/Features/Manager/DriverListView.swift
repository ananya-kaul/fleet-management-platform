import SwiftUI

struct DriverListView: View {
    @Environment(Session.self) private var session

    @State private var drivers: [Driver] = []
    @State private var search = ""
    @State private var errorMessage: String?
    @State private var isLoading = false
    @State private var isPresentingForm = false

    var body: some View {
        Group {
            if drivers.isEmpty, isLoading {
                ProgressView()
            } else if let errorMessage, drivers.isEmpty {
                ErrorBanner(message: errorMessage) { Task { await load() } }
            } else if drivers.isEmpty {
                EmptyStateView(title: "No drivers",
                               message: "Add a driver with the + button.",
                               systemImage: "person.2")
            } else {
                List(drivers) { driver in
                    NavigationLink {
                        DriverDetailView(driver: driver, onChange: { Task { await load() } })
                    } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 3) {
                                Text(driver.name).font(.headline)
                                Text(driver.assignedVehicleRegistration ?? "No vehicle assigned")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                            StatusChip(text: driver.status.label, color: driver.status.color)
                        }
                    }
                }
                .listStyle(.plain)
            }
        }
        .navigationTitle("Drivers")
        .searchable(text: $search, prompt: "Name, phone or licence")
        .onSubmit(of: .search) { Task { await load() } }
        .onChange(of: search) { _, value in if value.isEmpty { Task { await load() } } }
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { isPresentingForm = true } label: {
                    Label("Add driver", systemImage: "plus")
                }
            }
        }
        .refreshable { await load() }
        .sheet(isPresented: $isPresentingForm) {
            DriverFormView { Task { await load() } }
        }
        .task { await load() }
    }

    private func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            drivers = try await session.api.drivers(search: search).items
            errorMessage = nil
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

struct DriverDetailView: View {
    @Environment(Session.self) private var session
    let driver: Driver
    var onChange: () -> Void

    @State private var history: [Assignment] = []
    @State private var performance: DriverPerformance?
    @State private var actionError: String?

    var body: some View {
        List {
            Section("Driver") {
                DetailRow(label: "Name", value: driver.name)
                DetailRow(label: "Phone", value: driver.phoneNumber)
                DetailRow(label: "Licence", value: driver.licenseNumber)
                DetailRow(label: "Licence expiry", value: Format.day(driver.licenseExpiry))
                HStack {
                    Text("Status").foregroundStyle(.secondary)
                    Spacer()
                    StatusChip(text: driver.status.label, color: driver.status.color)
                }
                DetailRow(label: "Assigned vehicle",
                          value: driver.assignedVehicleRegistration ?? "—")
            }

            if let performance {
                Section("Last 30 days") {
                    DetailRow(label: "Trips", value: "\(performance.totalTrips)")
                    DetailRow(label: "Completed", value: "\(performance.completedTrips)")
                    DetailRow(label: "Distance",
                              value: Format.distance(performance.totalDistanceKm))
                    DetailRow(label: "Incidents reported",
                              value: "\(performance.incidentsReported)")
                }
            }

            Section("Assignment history") {
                if history.isEmpty {
                    Text("No assignments yet").foregroundStyle(.secondary)
                } else {
                    ForEach(history) { assignment in
                        VStack(alignment: .leading, spacing: 3) {
                            Text(assignment.vehicle?.registrationNumber ?? "Vehicle \(assignment.vehicleId)")
                                .font(.subheadline.weight(.medium))
                            Text("\(Format.day(assignment.startDate)) – \(assignment.endDate.map(Format.day) ?? "open")")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }

            Section {
                if driver.status == .active {
                    Button("Deactivate driver", role: .destructive) {
                        Task { await setStatus(.inactive) }
                    }
                } else {
                    Button("Reactivate driver") { Task { await setStatus(.active) } }
                }
            } footer: {
                if let actionError { Text(actionError).foregroundStyle(.red) }
            }
        }
        .navigationTitle(driver.name)
        .navigationBarTitleDisplayMode(.inline)
        .task {
            history = (try? await session.api.driverAssignments(id: driver.id)) ?? []
        }
    }

    private func setStatus(_ status: DriverStatus) async {
        do {
            _ = try await session.api.setDriverStatus(id: driver.id, status: status)
            actionError = nil
            onChange()
        } catch {
            actionError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}
