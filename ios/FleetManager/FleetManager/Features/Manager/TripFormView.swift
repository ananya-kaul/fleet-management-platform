import SwiftUI

struct TripFormView: View {
    @Environment(Session.self) private var session
    @Environment(\.dismiss) private var dismiss

    var onSaved: () -> Void

    @State private var vehicles: [Vehicle] = []
    @State private var drivers: [Driver] = []
    @State private var vehicleId: Int?
    @State private var driverId: Int?
    @State private var source = ""
    @State private var destination = ""
    @State private var scheduledStart = Date.now.addingTimeInterval(3600)
    @State private var scheduledEnd = Date.now.addingTimeInterval(3600 * 9)
    @State private var notes = ""

    @State private var errorMessage: String?
    @State private var isSaving = false

    private var canSave: Bool {
        vehicleId != nil && driverId != nil
            && source.trimmingCharacters(in: .whitespaces).count >= 2
            && destination.trimmingCharacters(in: .whitespaces).count >= 2
            && scheduledEnd > scheduledStart
            && !isSaving
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Route") {
                    TextField("From", text: $source)
                    TextField("To", text: $destination)
                }

                Section("Allocation") {
                    Picker("Vehicle", selection: $vehicleId) {
                        Text("Select…").tag(Int?.none)
                        ForEach(vehicles.filter { $0.isActive && $0.status != .inMaintenance }) { vehicle in
                            Text(vehicle.registrationNumber).tag(Int?.some(vehicle.id))
                        }
                    }
                    Picker("Driver", selection: $driverId) {
                        Text("Select…").tag(Int?.none)
                        ForEach(drivers.filter { $0.status == .active }) { driver in
                            Text(driver.name).tag(Int?.some(driver.id))
                        }
                    }
                }

                Section("Schedule") {
                    DatePicker("Starts", selection: $scheduledStart)
                    DatePicker("Ends", selection: $scheduledEnd, in: scheduledStart...)
                }

                Section("Notes") {
                    TextField("Optional", text: $notes, axis: .vertical)
                        .lineLimit(2...4)
                }

                if let errorMessage {
                    Section { Text(errorMessage).foregroundStyle(.red) }
                }
            }
            .navigationTitle("New trip")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Create") { Task { await save() } }.disabled(!canSave)
                }
            }
            .task {
                vehicles = (try? await session.api.vehicles().items) ?? []
                drivers = (try? await session.api.drivers().items) ?? []
            }
        }
    }

    private func save() async {
        guard let vehicleId, let driverId else { return }
        isSaving = true
        defer { isSaving = false }

        do {
            _ = try await session.api.createTrip(
                TripPayload(
                    vehicleId: vehicleId,
                    driverId: driverId,
                    source: source.trimmingCharacters(in: .whitespaces),
                    destination: destination.trimmingCharacters(in: .whitespaces),
                    scheduledStart: scheduledStart,
                    scheduledEnd: scheduledEnd,
                    notes: notes.isEmpty ? nil : notes
                )
            )
            onSaved()
            dismiss()
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}
