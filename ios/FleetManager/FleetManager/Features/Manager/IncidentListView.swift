import SwiftUI

struct IncidentListView: View {
    @Environment(Session.self) private var session

    @State private var incidents: [Incident] = []
    @State private var statusFilter: IncidentStatus?
    @State private var errorMessage: String?
    @State private var isLoading = false

    var body: some View {
        Group {
            if incidents.isEmpty, isLoading {
                ProgressView()
            } else if let errorMessage, incidents.isEmpty {
                ErrorBanner(message: errorMessage) { Task { await load() } }
            } else if incidents.isEmpty {
                EmptyStateView(title: "No incidents",
                               message: "Issues reported by drivers appear here.",
                               systemImage: "checkmark.shield")
            } else {
                List(incidents) { incident in
                    NavigationLink {
                        IncidentDetailView(incident: incident) { Task { await load() } }
                    } label: {
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text(incident.title).font(.headline)
                                Spacer()
                                StatusChip(text: incident.severity.label,
                                           color: incident.severity.color)
                            }
                            HStack(spacing: 6) {
                                Text(incident.vehicle?.registrationNumber ?? "—")
                                Text("·")
                                Text(Format.dateTime(incident.reportedAt))
                            }
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            StatusChip(text: incident.status.label, color: incident.status.color)
                        }
                        .padding(.vertical, 2)
                    }
                }
                .listStyle(.plain)
            }
        }
        .navigationTitle("Incidents")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Menu {
                    Button("All") { statusFilter = nil; Task { await load() } }
                    ForEach(IncidentStatus.allCases) { status in
                        Button(status.label) { statusFilter = status; Task { await load() } }
                    }
                } label: {
                    Label("Filter", systemImage: "line.3.horizontal.decrease.circle")
                }
            }
        }
        .refreshable { await load() }
        .task { await load() }
    }

    private func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            incidents = try await session.api.incidents(status: statusFilter).items
            errorMessage = nil
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

struct IncidentDetailView: View {
    @Environment(Session.self) private var session
    @State var incident: Incident
    var onChange: () -> Void

    @State private var resolutionNotes = ""
    @State private var errorMessage: String?
    @State private var isWorking = false

    var body: some View {
        List {
            Section("Issue") {
                DetailRow(label: "Title", value: incident.title)
                if let description = incident.description {
                    DetailRow(label: "Details", value: description)
                }
                HStack {
                    Text("Severity").foregroundStyle(.secondary)
                    Spacer()
                    StatusChip(text: incident.severity.label, color: incident.severity.color)
                }
                HStack {
                    Text("Status").foregroundStyle(.secondary)
                    Spacer()
                    StatusChip(text: incident.status.label, color: incident.status.color)
                }
                DetailRow(label: "Vehicle",
                          value: incident.vehicle?.registrationNumber ?? "—")
                DetailRow(label: "Reported by", value: incident.reportedBy?.name ?? "—")
                DetailRow(label: "Reported at", value: Format.dateTime(incident.reportedAt))
            }

            if incident.status != .resolved {
                Section("Resolution") {
                    TextField("Notes", text: $resolutionNotes, axis: .vertical)
                        .lineLimit(2...4)

                    if incident.status == .open {
                        Button("Start work") { Task { await update(status: .inProgress) } }
                    }
                    Button("Mark resolved") { Task { await update(status: .resolved) } }
                }
                .disabled(isWorking)
            } else {
                Section("Resolved") {
                    DetailRow(label: "Resolved at", value: Format.dateTime(incident.resolvedAt))
                    if let notes = incident.resolutionNotes {
                        Text(notes)
                    }
                }
            }

            if let errorMessage {
                Section { Text(errorMessage).foregroundStyle(.red) }
            }
        }
        .navigationTitle("Incident")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func update(status: IncidentStatus) async {
        isWorking = true
        defer { isWorking = false }
        do {
            incident = try await session.api.updateIncident(
                id: incident.id,
                IncidentUpdatePayload(
                    status: status,
                    resolutionNotes: resolutionNotes.isEmpty ? nil : resolutionNotes
                )
            )
            errorMessage = nil
            onChange()
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}
