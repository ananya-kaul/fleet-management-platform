import SwiftUI

@main
struct FleetManagerApp: App {
    @State private var session = Session()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(session)
                .task { await session.bootstrap() }
        }
    }
}
