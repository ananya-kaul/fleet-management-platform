import SwiftUI

struct MyTripsView: View {
    @Environment(Session.self) private var session

    @State private var trips: [Trip] = []
    @State private var errorMessage: String?
    @State private var isLoading = false

    private var activeTrip: Trip? { trips.first { $0.status.isActive } }
    private var upcoming: [Trip] { trips.filter { $0.status == .scheduled } }
    private var past: [Trip] {
        trips.filter { $0.status == .completed || $0.status == .cancelled }
    }

    var body: some View {
        NavigationStack {
            Group {
                if trips.isEmpty, isLoading {
                    ProgressView()
                } else if let errorMessage, trips.isEmpty {
                    ErrorBanner(message: errorMessage) { Task { await load() } }
                } else if trips.isEmpty {
                    EmptyStateView(title: "No trips assigned",
                                   message: "Your fleet manager will assign trips to you here.",
                                   systemImage: "list.bullet.rectangle")
                } else {
                    List {
                        if let activeTrip {
                            Section("In progress") {
                                NavigationLink {
                                    DriverTripDetailView(tripId: activeTrip.id) {
                                        Task { await load() }
                                    }
                                } label: {
                                    TripRow(trip: activeTrip)
                                }
                            }
                        }

                        if !upcoming.isEmpty {
                            Section("Upcoming") {
                                ForEach(upcoming) { trip in
                                    NavigationLink {
                                        DriverTripDetailView(tripId: trip.id) {
                                            Task { await load() }
                                        }
                                    } label: {
                                        TripRow(trip: trip)
                                    }
                                }
                            }
                        }

                        if !past.isEmpty {
                            Section("History") {
                                ForEach(past) { trip in
                                    NavigationLink {
                                        DriverTripDetailView(tripId: trip.id) {
                                            Task { await load() }
                                        }
                                    } label: {
                                        TripRow(trip: trip)
                                    }
                                }
                            }
                        }
                    }
                }
            }
            .navigationTitle("My trips")
            .refreshable { await load() }
        }
        .task { await load() }
    }

    private func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            trips = try await session.api.trips().items
            errorMessage = nil
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}
