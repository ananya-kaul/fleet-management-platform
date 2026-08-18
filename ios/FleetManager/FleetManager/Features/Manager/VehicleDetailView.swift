import SwiftUI

struct VehicleDetailView: View {
    @Environment(Session.self) private var session
    let vehicleId: Int

    @State private var vehicle: Vehicle?
    @State private var maintenance: [MaintenanceRecord] = []
    @State private var errorMessage: String?
    @State private var actionError: String?
    @State private var isWorking = false

    var body: some View {
        Group {
            if let vehicle {
                List {
                    Section("Vehicle") {
                        DetailRow(label: "Registration", value: vehicle.registrationNumber)
                        DetailRow(label: "Type", value: vehicle.vehicleType.label)
                        DetailRow(label: "Make", value: vehicle.make)
                        DetailRow(label: "Model", value: vehicle.model)
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

                    Section("Documents") {
                        DetailRow(label: "Insurance expiry",
                                  value: Format.day(vehicle.insuranceExpiry))
                        DetailRow(label: "Registration expiry",
                                  value: Format.day(vehicle.registrationExpiry))
                    }

                    Section("Maintenance history") {
                        if maintenance.isEmpty {
                            Text("No records yet").foregroundStyle(.secondary)
                        } else {
                            ForEach(maintenance) { record in
                                VStack(alignment: .leading, spacing: 3) {
                                    Text(record.maintenanceType.label)
                                        .font(.subheadline.weight(.medium))
                                    Text("\(Format.day(record.serviceDate)) · \(Format.currency(record.cost))")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }
                    }

                    Section {
                        if vehicle.isActive {
                            Button("Deactivate vehicle", role: .destructive) {
                                Task { await setActive(false) }
                            }
                        } else {
                            Button("Reactivate vehicle") {
                                Task { await setActive(true) }
                            }
                        }
                    } footer: {
                        if let actionError {
                            Text(actionError).foregroundStyle(.red)
                        }
                    }
                    .disabled(isWorking)
                }
            } else if let errorMessage {
                ErrorBanner(message: errorMessage) { Task { await load() } }
            } else {
                ProgressView()
            }
        }
        .navigationTitle(vehicle?.registrationNumber ?? "Vehicle")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private func load() async {
        do {
            async let detail = session.api.vehicle(id: vehicleId)
            async let history = session.api.maintenance(vehicleId: vehicleId)
            vehicle = try await detail
            maintenance = try await history.items
            errorMessage = nil
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func setActive(_ active: Bool) async {
        isWorking = true
        defer { isWorking = false }
        do {
            vehicle = active
                ? try await session.api.activateVehicle(id: vehicleId)
                : try await session.api.deactivateVehicle(id: vehicleId)
            actionError = nil
        } catch {
            actionError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}
