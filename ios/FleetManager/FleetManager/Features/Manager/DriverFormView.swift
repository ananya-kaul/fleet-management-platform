import SwiftUI

struct DriverFormView: View {
    @Environment(Session.self) private var session
    @Environment(\.dismiss) private var dismiss

    var onSaved: () -> Void

    @State private var name = ""
    @State private var phone = ""
    @State private var licenseNumber = ""
    @State private var licenseExpiry = Calendar.current.date(
        byAdding: .year, value: 1, to: .now
    ) ?? .now
    @State private var createsLogin = true
    @State private var email = ""
    @State private var password = ""

    @State private var errorMessage: String?
    @State private var isSaving = false

    private var canSave: Bool {
        !name.trimmingCharacters(in: .whitespaces).isEmpty
            && phone.count >= 6
            && licenseNumber.count >= 4
            && (!createsLogin || (email.contains("@") && password.count >= 8))
            && !isSaving
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Driver") {
                    TextField("Full name", text: $name)
                    TextField("Phone number", text: $phone)
                        .keyboardType(.phonePad)
                    TextField("Licence number", text: $licenseNumber)
                        .textInputAutocapitalization(.characters)
                        .autocorrectionDisabled()
                    DatePicker("Licence expiry", selection: $licenseExpiry,
                               displayedComponents: .date)
                }

                Section {
                    Toggle("Create an app login", isOn: $createsLogin)
                    if createsLogin {
                        TextField("Email", text: $email)
                            .keyboardType(.emailAddress)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                        SecureField("Password (min 8 characters)", text: $password)
                    }
                } footer: {
                    Text("A login lets the driver sign in to see trips and report issues.")
                }

                if let errorMessage {
                    Section { Text(errorMessage).foregroundStyle(.red) }
                }
            }
            .navigationTitle("New driver")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { Task { await save() } }.disabled(!canSave)
                }
            }
        }
    }

    private func save() async {
        isSaving = true
        defer { isSaving = false }

        let payload = DriverPayload(
            name: name.trimmingCharacters(in: .whitespaces),
            phoneNumber: phone.trimmingCharacters(in: .whitespaces),
            licenseNumber: licenseNumber.trimmingCharacters(in: .whitespaces),
            licenseExpiry: Format.apiDay(licenseExpiry),
            email: createsLogin ? email.trimmingCharacters(in: .whitespaces) : nil,
            password: createsLogin ? password : nil
        )

        do {
            _ = try await session.api.createDriver(payload)
            onSaved()
            dismiss()
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}
