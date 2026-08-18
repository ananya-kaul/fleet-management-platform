import SwiftUI

struct AssignmentListView: View {
    @Environment(Session.self) private var session

    @State private var assignments: [Assignment] = []
    @State private var errorMessage: String?
    @State private var isLoading = false
    @State private var isPresentingForm = false

    var body: some View {
        Group {
            if assignments.isEmpty, isLoading {
                ProgressView()
            } else if let errorMessage, assignments.isEmpty {
                ErrorBanner(message: errorMessage) { Task { await load() } }
            } else if assignments.isEmpty {
                EmptyStateView(title: "No assignments",
                               message: "Assign a vehicle to a driver with the + button.",
                               systemImage: "link")
            } else {
                List {
                    ForEach(assignments) { assignment in
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text(assignment.vehicle?.registrationNumber
                                     ?? "Vehicle \(assignment.vehicleId)")
                                    .font(.headline)
                                Spacer()
                                StatusChip(text: assignment.isActive ? "Active" : "Ended",
                                           color: assignment.isActive ? .green : .secondary)
                            }
                            Text(assignment.driver?.name ?? "Driver \(assignment.driverId)")
                                .font(.subheadline)
                            Text("\(Format.day(assignment.startDate)) – \(assignment.endDate.map(Format.day) ?? "open ended")")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .swipeActions {
                            if assignment.isActive {
                                Button("End") { Task { await end(assignment) } }
                                    .tint(.orange)
                            }
                        }
                    }
                }
                .listStyle(.plain)
            }
        }
        .navigationTitle("Assignments")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { isPresentingForm = true } label: {
                    Label("New assignment", systemImage: "plus")
                }
            }
        }
        .refreshable { await load() }
        .sheet(isPresented: $isPresentingForm) {
            AssignmentFormView { Task { await load() } }
        }
        .task { await load() }
    }

    private func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            assignments = try await session.api.assignments().items
            errorMessage = nil
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func end(_ assignment: Assignment) async {
        _ = try? await session.api.endAssignment(id: assignment.id)
        await load()
    }
}

/// Creating an assignment is the screen most likely to hit a server-side
/// conflict (the vehicle or driver is already booked), so the failure message
/// is shown in place rather than dismissing the sheet.
struct AssignmentFormView: View {
    @Environment(Session.self) private var session
    @Environment(\.dismiss) private var dismiss

    var onSaved: () -> Void

    @State private var vehicles: [Vehicle] = []
    @State private var drivers: [Driver] = []
    @State private var vehicleId: Int?
    @State private var driverId: Int?
    @State private var startDate = Date.now
    @State private var hasEndDate = true
    @State private var endDate = Calendar.current.date(byAdding: .day, value: 7, to: .now) ?? .now

    @State private var errorMessage: String?
    @State private var isSaving = false

    var body: some View {
        NavigationStack {
            Form {
                Section("Vehicle") {
                    Picker("Vehicle", selection: $vehicleId) {
                        Text("Select…").tag(Int?.none)
                        ForEach(vehicles.filter(\.isActive)) { vehicle in
                            Text(vehicle.registrationNumber).tag(Int?.some(vehicle.id))
                        }
                    }
                }

                Section("Driver") {
                    Picker("Driver", selection: $driverId) {
                        Text("Select…").tag(Int?.none)
                        ForEach(drivers.filter { $0.status == .active }) { driver in
                            Text(driver.name).tag(Int?.some(driver.id))
                        }
                    }
                }

                Section("Period") {
                    DatePicker("Starts", selection: $startDate, displayedComponents: .date)
                    Toggle("Has an end date", isOn: $hasEndDate)
                    if hasEndDate {
                        DatePicker("Ends", selection: $endDate, in: startDate...,
                                   displayedComponents: .date)
                    }
                }

                if let errorMessage {
                    Section { Text(errorMessage).foregroundStyle(.red) }
                }
            }
            .navigationTitle("Assign vehicle")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Assign") { Task { await save() } }
                        .disabled(vehicleId == nil || driverId == nil || isSaving)
                }
            }
            .task { await loadPickers() }
        }
    }

    private func loadPickers() async {
        vehicles = (try? await session.api.vehicles().items) ?? []
        drivers = (try? await session.api.drivers().items) ?? []
    }

    private func save() async {
        guard let vehicleId, let driverId else { return }
        isSaving = true
        defer { isSaving = false }

        do {
            _ = try await session.api.createAssignment(
                AssignmentPayload(
                    vehicleId: vehicleId,
                    driverId: driverId,
                    startDate: Format.apiDay(startDate),
                    endDate: hasEndDate ? Format.apiDay(endDate) : nil
                )
            )
            onSaved()
            dismiss()
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}
