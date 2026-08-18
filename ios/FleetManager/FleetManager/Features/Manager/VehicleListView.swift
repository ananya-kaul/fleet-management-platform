import SwiftUI

@Observable
@MainActor
final class VehicleListViewModel {
    var vehicles: [Vehicle] = []
    var search = ""
    var statusFilter: VehicleStatus?
    var errorMessage: String?
    var isLoading = false

    func load(api: FleetAPI) async {
        isLoading = true
        defer { isLoading = false }
        do {
            vehicles = try await api.vehicles(search: search, status: statusFilter).items
            errorMessage = nil
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

struct VehicleListView: View {
    @Environment(Session.self) private var session
    @State private var model = VehicleListViewModel()
    @State private var isPresentingForm = false

    var body: some View {
        NavigationStack {
            Group {
                if model.vehicles.isEmpty, model.isLoading {
                    ProgressView()
                } else if let error = model.errorMessage, model.vehicles.isEmpty {
                    ErrorBanner(message: error) { Task { await model.load(api: session.api) } }
                } else if model.vehicles.isEmpty {
                    EmptyStateView(
                        title: "No vehicles",
                        message: "Add the first vehicle with the + button.",
                        systemImage: "truck.box"
                    )
                } else {
                    List(model.vehicles) { vehicle in
                        NavigationLink {
                            VehicleDetailView(vehicleId: vehicle.id)
                        } label: {
                            VehicleRow(vehicle: vehicle)
                        }
                    }
                    .listStyle(.plain)
                }
            }
            .navigationTitle("Vehicles")
            .searchable(text: $model.search, prompt: "Registration, make or model")
            .onSubmit(of: .search) { Task { await model.load(api: session.api) } }
            .onChange(of: model.search) { _, newValue in
                if newValue.isEmpty { Task { await model.load(api: session.api) } }
            }
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Menu {
                        Button("All") {
                            model.statusFilter = nil
                            Task { await model.load(api: session.api) }
                        }
                        ForEach(VehicleStatus.allCases) { status in
                            Button(status.label) {
                                model.statusFilter = status
                                Task { await model.load(api: session.api) }
                            }
                        }
                    } label: {
                        Label("Filter", systemImage: model.statusFilter == nil
                              ? "line.3.horizontal.decrease.circle"
                              : "line.3.horizontal.decrease.circle.fill")
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button { isPresentingForm = true } label: {
                        Label("Add vehicle", systemImage: "plus")
                    }
                }
            }
            .refreshable { await model.load(api: session.api) }
            .sheet(isPresented: $isPresentingForm) {
                VehicleFormView { Task { await model.load(api: session.api) } }
            }
        }
        .task { await model.load(api: session.api) }
    }
}

struct VehicleRow: View {
    let vehicle: Vehicle

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 3) {
                Text(vehicle.registrationNumber).font(.headline)
                Text("\(vehicle.displayName) · \(vehicle.year.description)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            StatusChip(text: vehicle.status.label, color: vehicle.status.color)
        }
        .padding(.vertical, 2)
    }
}
