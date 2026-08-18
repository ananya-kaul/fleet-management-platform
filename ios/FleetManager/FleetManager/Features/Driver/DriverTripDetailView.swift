import SwiftUI

/// The driver's view of one trip: the pre-trip briefing, the start and complete
/// actions, live tracking status while it runs, and a route to reporting an issue.
struct DriverTripDetailView: View {
    @Environment(Session.self) private var session
    @Environment(LocationTracker.self) private var tracker

    let tripId: Int
    var onChange: () -> Void

    @State private var trip: Trip?
    @State private var errorMessage: String?
    @State private var actionError: String?
    @State private var isPresentingStart = false
    @State private var isPresentingComplete = false
    @State private var isPresentingIssue = false
    @State private var isWorking = false

    var body: some View {
        Group {
            if let trip {
                List {
                    Section("Trip") {
                        DetailRow(label: "Code", value: trip.tripCode)
                        DetailRow(label: "From", value: trip.source)
                        DetailRow(label: "To", value: trip.destination)
                        HStack {
                            Text("Status").foregroundStyle(.secondary)
                            Spacer()
                            StatusChip(text: trip.status.label, color: trip.status.color)
                        }
                    }

                    Section("Vehicle") {
                        DetailRow(label: "Registration",
                                  value: trip.vehicle?.registrationNumber ?? "—")
                        DetailRow(label: "Model", value: trip.vehicle?.displayName ?? "—")
                    }

                    Section("Schedule") {
                        DetailRow(label: "Scheduled start",
                                  value: Format.dateTime(trip.scheduledStart))
                        DetailRow(label: "Scheduled end",
                                  value: Format.dateTime(trip.scheduledEnd))
                    }

                    if trip.startOdometer != nil {
                        Section("Progress") {
                            DetailRow(label: "Started", value: Format.dateTime(trip.actualStart))
                            DetailRow(label: "Start odometer",
                                      value: Format.odometer(trip.startOdometer))
                            if trip.status == .completed {
                                DetailRow(label: "Finished",
                                          value: Format.dateTime(trip.actualEnd))
                                DetailRow(label: "End odometer",
                                          value: Format.odometer(trip.endOdometer))
                                DetailRow(label: "Distance",
                                          value: Format.distance(trip.distanceKm))
                            }
                        }
                    }

                    if trip.status.isActive {
                        Section("Live tracking") {
                            HStack {
                                Circle()
                                    .fill(tracker.isTracking ? .green : .orange)
                                    .frame(width: 8, height: 8)
                                Text(tracker.isTracking
                                     ? "Sending your position"
                                     : "Tracking paused")
                                    .font(.subheadline)
                            }
                            if let location = tracker.lastLocation {
                                DetailRow(
                                    label: "Last fix",
                                    value: String(format: "%.4f, %.4f",
                                                  location.coordinate.latitude,
                                                  location.coordinate.longitude)
                                )
                            }
                            if tracker.pendingCount > 0 {
                                DetailRow(label: "Queued offline",
                                          value: "\(tracker.pendingCount)")
                            }
                            if !tracker.isAuthorized {
                                Button("Allow location access") {
                                    tracker.requestPermission()
                                }
                            }
                        }
                    }

                    Section {
                        actionButtons(for: trip)
                    } footer: {
                        if let actionError { Text(actionError).foregroundStyle(.red) }
                    }
                    .disabled(isWorking)
                }
            } else if let errorMessage {
                ErrorBanner(message: errorMessage) { Task { await load() } }
            } else {
                ProgressView()
            }
        }
        .navigationTitle(trip?.tripCode ?? "Trip")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
        .sheet(isPresented: $isPresentingStart) {
            if let trip {
                OdometerEntryView(
                    title: "Start trip",
                    prompt: "Enter the odometer reading before you set off.",
                    defaultValue: trip.startOdometer
                ) { reading in
                    await start(trip: trip, odometer: reading)
                }
            }
        }
        .sheet(isPresented: $isPresentingComplete) {
            if let trip {
                OdometerEntryView(
                    title: "Complete trip",
                    prompt: "Enter the odometer reading at your destination.",
                    defaultValue: trip.startOdometer,
                    minimum: trip.startOdometer
                ) { reading in
                    await complete(trip: trip, odometer: reading)
                }
            }
        }
        .sheet(isPresented: $isPresentingIssue) {
            if let trip {
                ReportIssueView(vehicleId: trip.vehicleId, tripId: trip.id)
            }
        }
    }

    @ViewBuilder
    private func actionButtons(for trip: Trip) -> some View {
        switch trip.status {
        case .scheduled:
            Button("Start trip") { isPresentingStart = true }
                .fontWeight(.semibold)
        case .started:
            Button("Mark in progress") { Task { await setStatus(.inProgress) } }
            Button("Complete trip") { isPresentingComplete = true }
                .fontWeight(.semibold)
            Button("Report an issue") { isPresentingIssue = true }
        case .inProgress:
            Button("Complete trip") { isPresentingComplete = true }
                .fontWeight(.semibold)
            Button("Report an issue") { isPresentingIssue = true }
        case .completed, .cancelled:
            Text("This trip is closed.").foregroundStyle(.secondary)
        }
    }

    private func load() async {
        do {
            let loaded = try await session.api.trip(id: tripId)
            trip = loaded
            errorMessage = nil

            // Resume tracking if the app was relaunched mid-trip.
            if loaded.status.isActive, !tracker.isTracking {
                tracker.startTracking(
                    api: session.api, vehicleId: loaded.vehicleId, tripId: loaded.id
                )
            }
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func start(trip: Trip, odometer: Double) async {
        isWorking = true
        defer { isWorking = false }

        let coordinate = tracker.currentCoordinate()
        do {
            let updated = try await session.api.startTrip(
                id: trip.id,
                TripStartPayload(
                    startOdometer: odometer,
                    startLatitude: coordinate?.latitude ?? 0,
                    startLongitude: coordinate?.longitude ?? 0
                )
            )
            self.trip = updated
            actionError = nil
            tracker.startTracking(
                api: session.api, vehicleId: updated.vehicleId, tripId: updated.id
            )
            onChange()
        } catch {
            actionError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func complete(trip: Trip, odometer: Double) async {
        isWorking = true
        defer { isWorking = false }

        let coordinate = tracker.currentCoordinate()
        do {
            let updated = try await session.api.completeTrip(
                id: trip.id,
                TripCompletePayload(
                    endOdometer: odometer,
                    endLatitude: coordinate?.latitude ?? 0,
                    endLongitude: coordinate?.longitude ?? 0
                )
            )
            self.trip = updated
            actionError = nil
            tracker.stopTracking()
            onChange()
        } catch {
            actionError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func setStatus(_ status: TripStatus) async {
        isWorking = true
        defer { isWorking = false }
        do {
            trip = try await session.api.setTripStatus(id: tripId, status: status)
            actionError = nil
            onChange()
        } catch {
            actionError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

/// Shared odometer prompt for the start and complete actions.
struct OdometerEntryView: View {
    @Environment(\.dismiss) private var dismiss

    let title: String
    let prompt: String
    var defaultValue: Double?
    var minimum: Double?
    let onConfirm: (Double) async -> Void

    @State private var reading = ""
    @State private var isSaving = false

    private var parsed: Double? { Double(reading) }

    private var validationMessage: String? {
        guard let parsed else { return nil }
        if let minimum, parsed < minimum {
            return "Must be at least \(Format.odometer(minimum)) - the reading at the start."
        }
        return nil
    }

    private var canConfirm: Bool {
        parsed != nil && validationMessage == nil && !isSaving
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Odometer (km)", text: $reading)
                        .keyboardType(.decimalPad)
                } header: {
                    Text(prompt)
                } footer: {
                    if let validationMessage {
                        Text(validationMessage).foregroundStyle(.red)
                    }
                }
            }
            .navigationTitle(title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Confirm") {
                        guard let parsed else { return }
                        Task {
                            isSaving = true
                            await onConfirm(parsed)
                            isSaving = false
                            dismiss()
                        }
                    }
                    .disabled(!canConfirm)
                }
            }
            .onAppear {
                if reading.isEmpty, let defaultValue {
                    reading = String(format: "%.0f", defaultValue)
                }
            }
        }
    }
}
