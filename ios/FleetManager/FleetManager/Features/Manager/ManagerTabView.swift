import SwiftUI

/// Fleet manager home. Four tabs keep the primary work one tap away; the
/// lower-traffic screens live behind "More".
struct ManagerTabView: View {
    var body: some View {
        TabView {
            DashboardView()
                .tabItem { Label("Dashboard", systemImage: "chart.bar.doc.horizontal") }

            VehicleListView()
                .tabItem { Label("Vehicles", systemImage: "truck.box") }

            TripListView()
                .tabItem { Label("Trips", systemImage: "arrow.triangle.turn.up.right.circle") }

            MoreView()
                .tabItem { Label("More", systemImage: "ellipsis.circle") }
        }
    }
}

struct MoreView: View {
    var body: some View {
        NavigationStack {
            List {
                Section("Fleet") {
                    NavigationLink { DriverListView() } label: {
                        Label("Drivers", systemImage: "person.2")
                    }
                    NavigationLink { AssignmentListView() } label: {
                        Label("Assignments", systemImage: "link")
                    }
                    NavigationLink { FleetMapView() } label: {
                        Label("Live map", systemImage: "map")
                    }
                }

                Section("Operations") {
                    NavigationLink { MaintenanceListView() } label: {
                        Label("Maintenance", systemImage: "wrench.and.screwdriver")
                    }
                    NavigationLink { IncidentListView() } label: {
                        Label("Incidents", systemImage: "exclamationmark.triangle")
                    }
                    NavigationLink { AnalyticsView() } label: {
                        Label("Analytics", systemImage: "chart.xyaxis.line")
                    }
                }

                Section("Account") {
                    NavigationLink { NotificationListView() } label: {
                        Label("Notifications", systemImage: "bell")
                    }
                    NavigationLink { ProfileView() } label: {
                        Label("Profile", systemImage: "person.crop.circle")
                    }
                }
            }
            .navigationTitle("More")
        }
    }
}
