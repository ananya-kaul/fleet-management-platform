import SwiftUI

/// Switches between the launch state, sign-in, and the role-appropriate home.
struct RootView: View {
    @Environment(Session.self) private var session

    var body: some View {
        Group {
            switch session.state {
            case .loading:
                ProgressView("Loading…")
            case .signedOut:
                LoginView()
            case .signedIn(let user):
                if user.role == .fleetManager {
                    ManagerTabView()
                } else {
                    DriverTabView()
                }
            }
        }
        .animation(.default, value: session.state)
    }
}
