import SwiftUI

struct ProfileView: View {
    @Environment(Session.self) private var session

    @State private var isChangingPassword = false
    @State private var isConfirmingSignOut = false

    var body: some View {
        List {
            if let user = session.currentUser {
                Section("Account") {
                    DetailRow(label: "Name", value: user.fullName)
                    DetailRow(label: "Email", value: user.email)
                    DetailRow(label: "Role", value: user.role.label)
                }
            }

            Section("Security") {
                Button("Change password") { isChangingPassword = true }
            }

            Section {
                Button("Sign out", role: .destructive) { isConfirmingSignOut = true }
            }

            Section("About") {
                DetailRow(label: "Server", value: AppConfig.apiBaseURL.absoluteString)
                DetailRow(
                    label: "Version",
                    value: Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString")
                        as? String ?? "1.0"
                )
            }
        }
        .navigationTitle("Profile")
        .sheet(isPresented: $isChangingPassword) { ChangePasswordView() }
        // An alert rather than a confirmationDialog: on iPhone SwiftUI can render
        // a dialog as a popover anchored to the attached view, which pins it to
        // the top of the screen over the navigation title and drops the cancel
        // button. An alert is always a centred modal with both actions intact.
        .alert("Sign out?", isPresented: $isConfirmingSignOut) {
            Button("Cancel", role: .cancel) {}
            Button("Sign out", role: .destructive) { Task { await session.signOut() } }
        } message: {
            Text("You will need to sign in again to see your trips.")
        }
    }
}

struct ChangePasswordView: View {
    @Environment(Session.self) private var session
    @Environment(\.dismiss) private var dismiss

    @State private var current = ""
    @State private var updated = ""
    @State private var confirmation = ""
    @State private var errorMessage: String?
    @State private var isSaving = false

    private var canSave: Bool {
        !current.isEmpty && updated.count >= 8 && updated == confirmation && !isSaving
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    SecureField("Current password", text: $current)
                    SecureField("New password", text: $updated)
                    SecureField("Confirm new password", text: $confirmation)
                } footer: {
                    if !confirmation.isEmpty, updated != confirmation {
                        Text("The new passwords do not match.").foregroundStyle(.red)
                    } else if let errorMessage {
                        Text(errorMessage).foregroundStyle(.red)
                    }
                }
            }
            .navigationTitle("Change password")
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
        do {
            try await session.api.changePassword(current: current, new: updated)
            dismiss()
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}
