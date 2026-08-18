import SwiftUI

struct TripListView: View {
    @Environment(Session.self) private var session

    @State private var trips: [Trip] = []
    @State private var statusFilter: TripStatus?
    @State private var errorMessage: String?
    @State private var isLoading = false
    @State private var isPresentingForm = false

    var body: some View {
        NavigationStack {
            Group {
                if trips.isEmpty, isLoading {
                    ProgressView()
                } else if let errorMessage, trips.isEmpty {
                    ErrorBanner(message: errorMessage) { Task { await load() } }
                } else if trips.isEmpty {
                    EmptyStateView(title: "No trips",
                                   message: "Create a trip with the + button.",
                                   systemImage: "arrow.triangle.turn.up.right.circle")
                } else {
                    List(trips) { trip in
                        NavigationLink {
                            TripDetailView(tripId: trip.id, onChange: { Task { await load() } })
                        } label: {
                            TripRow(trip: trip)
                        }
                    }
                    .listStyle(.plain)
                }
            }
            .navigationTitle("Trips")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Menu {
                        Button("All") { statusFilter = nil; Task { await load() } }
                        ForEach(TripStatus.allCases) { status in
                            Button(status.label) { statusFilter = status; Task { await load() } }
                        }
                    } label: {
                        Label("Filter", systemImage: statusFilter == nil
                              ? "line.3.horizontal.decrease.circle"
                              : "line.3.horizontal.decrease.circle.fill")
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button { isPresentingForm = true } label: {
                        Label("New trip", systemImage: "plus")
                    }
                }
            }
            .refreshable { await load() }
            .sheet(isPresented: $isPresentingForm) {
                TripFormView { Task { await load() } }
            }
        }
        .task { await load() }
    }

    private func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            trips = try await session.api.trips(status: statusFilter).items
            errorMessage = nil
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

struct TripRow: View {
    let trip: Trip

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(trip.tripCode).font(.headline)
                Spacer()
                StatusChip(text: trip.status.label, color: trip.status.color)
            }
            Text(trip.route).font(.subheadline)
            HStack(spacing: 6) {
                Text(trip.vehicle?.registrationNumber ?? "—")
                Text("·")
                Text(trip.driver?.name ?? "—")
            }
            .font(.caption)
            .foregroundStyle(.secondary)
        }
        .padding(.vertical, 2)
    }
}
