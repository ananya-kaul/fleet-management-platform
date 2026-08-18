import SwiftUI

/// Driver home. Deliberately narrow: a driver only needs their trips, the
/// vehicle they are on, and a way to report a problem.
struct DriverTabView: View {
    @State private var tracker = LocationTracker()

    var body: some View {
        TabView {
            MyTripsView()
                .tabItem { Label("My trips", systemImage: "list.bullet.rectangle") }

            NavigationStack { MyVehicleView() }
                .tabItem { Label("My vehicle", systemImage: "truck.box") }

            NavigationStack { NotificationListView() }
                .tabItem { Label("Alerts", systemImage: "bell") }

            NavigationStack { ProfileView() }
                .tabItem { Label("Profile", systemImage: "person.crop.circle") }
        }
        .environment(tracker)
    }
}
