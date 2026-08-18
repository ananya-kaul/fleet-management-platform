import SwiftUI

/// Add-vehicle sheet. Server-side conflicts (a duplicate registration) surface
/// inline rather than as an alert so the offending field stays on screen.
struct VehicleFormView: View {
    @Environment(Session.self) private var session
    @Environment(\.dismiss) private var dismiss

    var onSaved: () -> Void

    @State private var registration = ""
    @State private var vehicleType: VehicleType = .truck
    @State private var make = ""
    @State private var model = ""
    @State private var year = Calendar.current.component(.year, from: .now)
    @State private var fuelType: FuelType = .diesel
    @State private var mileage = ""
    @State private var hasInsuranceExpiry = false
    @State private var insuranceExpiry = Date.now
    @State private var hasRegistrationExpiry = false
    @State private var registrationExpiry = Date.now

    @State private var errorMessage: String?
    @State private var isSaving = false

    private var canSave: Bool {
        !registration.trimmingCharacters(in: .whitespaces).isEmpty
            && !make.trimmingCharacters(in: .whitespaces).isEmpty
            && !model.trimmingCharacters(in: .whitespaces).isEmpty
            && !isSaving
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Identity") {
                    TextField("Registration number", text: $registration)
                        .textInputAutocapitalization(.characters)
                        .autocorrectionDisabled()
                    Picker("Type", selection: $vehicleType) {
                        ForEach(VehicleType.allCases) { Text($0.label).tag($0) }
                    }
                }

                Section("Details") {
                    TextField("Make", text: $make)
                    TextField("Model", text: $model)
                    Stepper("Year: \(String(year))", value: $year, in: 1980...2100)
                    Picker("Fuel", selection: $fuelType) {
                        ForEach(FuelType.allCases) { Text($0.label).tag($0) }
                    }
                    TextField("Current odometer (km)", text: $mileage)
                        .keyboardType(.decimalPad)
                }

                Section("Documents") {
                    Toggle("Insurance expiry", isOn: $hasInsuranceExpiry)
                    if hasInsuranceExpiry {
                        DatePicker("Expires", selection: $insuranceExpiry,
                                   displayedComponents: .date)
                    }
                    Toggle("Registration expiry", isOn: $hasRegistrationExpiry)
                    if hasRegistrationExpiry {
                        DatePicker("Expires", selection: $registrationExpiry,
                                   displayedComponents: .date)
                    }
                }

                if let errorMessage {
                    Section { Text(errorMessage).foregroundStyle(.red) }
                }
            }
            .navigationTitle("New vehicle")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { Task { await save() } }
                        .disabled(!canSave)
                }
            }
            .overlay {
                if isSaving {
                    ProgressView().controlSize(.large)
                }
            }
        }
    }

    private func save() async {
        isSaving = true
        defer { isSaving = false }

        let payload = VehiclePayload(
            registrationNumber: registration.trimmingCharacters(in: .whitespaces),
            vehicleType: vehicleType,
            make: make.trimmingCharacters(in: .whitespaces),
            model: model.trimmingCharacters(in: .whitespaces),
            year: year,
            fuelType: fuelType,
            currentMileage: Double(mileage) ?? 0,
            insuranceExpiry: hasInsuranceExpiry ? Format.apiDay(insuranceExpiry) : nil,
            registrationExpiry: hasRegistrationExpiry ? Format.apiDay(registrationExpiry) : nil
        )

        do {
            _ = try await session.api.createVehicle(payload)
            onSaved()
            dismiss()
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}
