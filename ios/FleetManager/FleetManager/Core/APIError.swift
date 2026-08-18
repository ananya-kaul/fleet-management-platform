import Foundation

/// The error envelope the backend returns: `{"code": "...", "detail": "..."}`.
struct APIErrorBody: Decodable {
    let code: String
    let detail: String
}

enum APIError: LocalizedError, Equatable {
    case unauthorized
    case forbidden(String)
    case notFound(String)
    case conflict(code: String, message: String)
    case validation(String)
    case server(status: Int, message: String)
    case network(String)
    case decoding(String)

    var errorDescription: String? {
        switch self {
        case .unauthorized:
            return "Your session has expired. Please sign in again."
        case .forbidden(let message), .notFound(let message), .validation(let message):
            return message
        case .conflict(_, let message):
            return message
        case .server(let status, let message):
            return message.isEmpty ? "The server returned an error (\(status))." : message
        case .network(let message):
            return message
        case .decoding:
            return "The server sent a response the app could not read."
        }
    }

    /// True when signing in again might fix it.
    var requiresReauthentication: Bool {
        self == .unauthorized
    }
}
