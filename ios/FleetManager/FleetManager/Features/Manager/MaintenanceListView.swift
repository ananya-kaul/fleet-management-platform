import SwiftUI

struct MaintenanceListView: View {
    @Environment(Session.self) private var session

    @State private var records: [MaintenanceRecord] = []
    @State private var due: [MaintenanceDueItem] = []
    @State private var errorMessage: String?
    @State private var isLoading = false
    @State private var isPresentingForm = false

    var body: some View {
        Group {
            if records.isEmpty, due.isEmpty, isLoading {
                ProgressView()
            } else if let errorMessage, records.isEmpty {
                ErrorBanner(message: errorMessage) { Task { await load() } }
            } else {
                List {
                    if !due.isEmpty {
                        Section("Due for service") {
                            ForEach(due) { item in
                                VStack(alignment: .leading, spacing: 3) {
                                    Text(item.registrationNumber)
                                        .font(.subheadline.weight(.medium))
                                    Text(item.reason)
                                        .font(.caption)
                                        .foregroundStyle(.orange)
                                }
                            }
                        }
                    }

                    Section("History") {
                        if records.isEmpty {
                            Text("No records yet").foregroundStyle(.secondary)
                        } else {
                            ForEach(records) { record in
                                VStack(alignment: .leading, spacing: 4) {
                                    HStack {
                                        Text(record.vehicle?.registrationNumber ?? "—")
                                            .font(.headline)
                                        Spacer()
                                        Text(Format.currency(record.cost))
                                            .font(.subheadline)
                                    }
                                    Text(record.maintenanceType.label).font(.subheadline)
                                    Text("\(Format.day(record.serviceDate)) · \(Format.odometer(record.odometer))")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                    if let next = record.nextServiceDate {
                                        Text("Next service: \(Format.day(next))")
                                            .font(.caption)
                                            .foregroundStyle(.secondary)
                                    }
                                }
                                .padding(.vertical, 2)
                            }
                        }
                    }
                }
            }
        }
        .navigationTitle("Maintenance")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { isPresentingForm = true } label: {
                    Label("New record", systemImage: "plus")
                }
            }
        }
        .refreshable { await load() }
        .sheet(isPresented: $isPresentingForm) {
            MaintenanceFormView { Task { await load() } }
        }
        .task { await load() }
    }

    private func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            records = try await session.api.maintenance().items
            due = (try? await session.api.maintenanceDue()) ?? []
            errorMessage = nil
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

struct MaintenanceFormView: View {
    @Environment(Session.self) private var session
    @Environment(\.dismiss) private var dismiss

    var onSaved: () -> Void

    @State private var vehicles: [Vehicle] = []
    @State private var vehicleId: Int?
    @State private var type: MaintenanceType = .oilChange
    @State private var details = ""
    @State private var serviceDate = Date.now
    @State private var cost = ""
    @State private var odometer = ""
    @State private var hasNextDate = true
    @State private var nextServiceDate = Calendar.current.date(
        byAdding: .month, value: 6, to: .now
    ) ?? .now
    @State private var nextServiceMileage = ""
    @State private var performedBy = ""
    @State private var setInMaintenance = false

    @State private var errorMessage: String?
    @State private var isSaving = false

    private var canSave: Bool {
        vehicleId != nil && Double(odometer) != nil && !isSaving
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Vehicle") {
                    Picker("Vehicle", selection: $vehicleId) {
                        Text("Select…").tag(Int?.none)
                        ForEach(vehicles) { vehicle in
                            Text(vehicle.registrationNumber).tag(Int?.some(vehicle.id))
                        }
                    }
                    Picker("Type", selection: $type) {
                        ForEach(MaintenanceType.allCases) { Text($0.label).tag($0) }
                    }
                }

                Section("Service") {
                    TextField("Description", text: $details, axis: .vertical)
                        .lineLimit(2...4)
                    DatePicker("Date", selection: $serviceDate, displayedComponents: .date)
                    TextField("Cost", text: $cost).keyboardType(.decimalPad)
                    TextField("Odometer (km)", text: $odometer).keyboardType(.decimalPad)
                    TextField("Performed by", text: $performedBy)
                }

                Section("Next service") {
                    Toggle("Schedule next service", isOn: $hasNextDate)
                    if hasNextDate {
                        DatePicker("Due", selection: $nextServiceDate,
                                   displayedComponents: .date)
                    }
                    TextField("Due at odometer (km)", text: $nextServiceMileage)
                        .keyboardType(.decimalPad)
                }

                Section {
                    Toggle("Move the vehicle into maintenance", isOn: $setInMaintenance)
                }

                if let errorMessage {
                    Section { Text(errorMessage).foregroundStyle(.red) }
                }
            }
            .navigationTitle("New record")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { Task { await save() } }.disabled(!canSave)
                }
            }
            .task { vehicles = (try? await session.api.vehicles().items) ?? [] }
        }
    }

    private func save() async {
        guard let vehicleId, let odometerValue = Double(odometer) else { return }
        isSaving = true
        defer { isSaving = false }

        do {
            _ = try await session.api.createMaintenance(
                MaintenancePayload(
                    vehicleId: vehicleId,
                    maintenanceType: type,
                    description: details.isEmpty ? nil : details,
                    serviceDate: Format.apiDay(serviceDate),
                    cost: Double(cost) ?? 0,
                    odometer: odometerValue,
                    nextServiceDate: hasNextDate ? Format.apiDay(nextServiceDate) : nil,
                    nextServiceMileage: Double(nextServiceMileage),
                    performedBy: performedBy.isEmpty ? nil : performedBy,
                    setVehicleInMaintenance: setInMaintenance
                )
            )
            onSaved()
            dismiss()
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}
