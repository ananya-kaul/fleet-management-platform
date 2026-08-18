import SwiftUI

struct ReportIssueView: View {
    @Environment(Session.self) private var session
    @Environment(\.dismiss) private var dismiss

    let vehicleId: Int
    var tripId: Int?

    @State private var title = ""
    @State private var details = ""
    @State private var severity: IncidentSeverity = .medium
    @State private var errorMessage: String?
    @State private var isSaving = false

    private var canSubmit: Bool {
        title.trimmingCharacters(in: .whitespaces).count >= 3 && !isSaving
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("What is wrong?") {
                    TextField("Short summary", text: $title)
                    TextField("Details", text: $details, axis: .vertical)
                        .lineLimit(3...6)
                }

                Section("How serious is it?") {
                    Picker("Severity", selection: $severity) {
                        ForEach(IncidentSeverity.allCases) { Text($0.label).tag($0) }
                    }
                    .pickerStyle(.segmented)
                }

                if let errorMessage {
                    Section { Text(errorMessage).foregroundStyle(.red) }
                }
            }
            .navigationTitle("Report an issue")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Send") { Task { await submit() } }.disabled(!canSubmit)
                }
            }
        }
    }

    private func submit() async {
        isSaving = true
        defer { isSaving = false }
        do {
            _ = try await session.api.reportIncident(
                IncidentPayload(
                    vehicleId: vehicleId,
                    tripId: tripId,
                    title: title.trimmingCharacters(in: .whitespaces),
                    description: details.isEmpty ? nil : details,
                    severity: severity
                )
            )
            dismiss()
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}
