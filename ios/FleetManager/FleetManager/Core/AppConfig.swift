import Foundation

/// Environment configuration.
///
/// The base URL is read from the `API_BASE_URL` Info.plist key when present so
/// TestFlight and production builds can point at different backends without a
/// code change, and falls back to the local development server.
enum AppConfig {
    static let apiBaseURL: URL = {
        if let raw = Bundle.main.object(forInfoDictionaryKey: "API_BASE_URL") as? String,
           let url = URL(string: raw), !raw.isEmpty {
            return url
        }
        #if targetEnvironment(simulator)
        return URL(string: "http://127.0.0.1:8000/api/v1")!
        #else
        // A device cannot reach the Mac's loopback address; override this with
        // your machine's LAN address or a deployed URL when testing on hardware.
        return URL(string: "http://127.0.0.1:8000/api/v1")!
        #endif
    }()

    static var webSocketURL: URL {
        var components = URLComponents(url: apiBaseURL, resolvingAgainstBaseURL: false)!
        components.scheme = components.scheme == "https" ? "wss" : "ws"
        components.path += "/ws/tracking"
        return components.url!
    }

    /// How often the driver app sends a position while a trip is running.
    static let locationPingInterval: TimeInterval = 15
}
