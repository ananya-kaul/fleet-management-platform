import Foundation

enum HTTPMethod: String {
    case get = "GET", post = "POST", put = "PUT", delete = "DELETE"
}

/// Supplies the bearer token and is told when the server rejects it.
protocol TokenProviding: AnyObject, Sendable {
    func currentAccessToken() async -> String?
    /// Attempts a refresh. Returns the new access token, or nil if the session is dead.
    func refreshAccessToken() async -> String?
    func handleSessionExpired() async
}

/// Thin async wrapper over URLSession.
///
/// Kept deliberately small: one `send` path that builds the request, attaches
/// auth, maps the status code onto `APIError`, and retries once after a token
/// refresh so an expired access token does not surface as a logout.
actor APIClient {
    private let baseURL: URL
    private let session: URLSession
    weak var tokenProvider: TokenProviding?

    init(baseURL: URL = AppConfig.apiBaseURL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
    }

    func setTokenProvider(_ provider: TokenProviding?) {
        tokenProvider = provider
    }

    // MARK: - Request building

    private func makeRequest(
        path: String,
        method: HTTPMethod,
        query: [URLQueryItem],
        body: Data?,
        token: String?
    ) throws -> URLRequest {
        var components = URLComponents(
            url: baseURL.appendingPathComponent(path),
            resolvingAgainstBaseURL: false
        )!
        if !query.isEmpty { components.queryItems = query }

        guard let url = components.url else {
            throw APIError.network("Could not build a URL for \(path)")
        }

        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue
        request.timeoutInterval = 30
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body {
            request.httpBody = body
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        if let token {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return request
    }

    // MARK: - Sending

    @discardableResult
    func send<Response: Decodable>(
        _ path: String,
        method: HTTPMethod = .get,
        query: [URLQueryItem] = [],
        body: (any Encodable)? = nil,
        authenticated: Bool = true,
        as type: Response.Type = Response.self
    ) async throws -> Response {
        let payload: Data? = try body.map { value in
            do { return try JSONCoding.encoder.encode(value) }
            catch { throw APIError.decoding("Could not encode the request body") }
        }

        var token = authenticated ? await tokenProvider?.currentAccessToken() : nil
        var request = try makeRequest(
            path: path, method: method, query: query, body: payload, token: token
        )

        var (data, response) = try await perform(request)

        // A 401 on an authenticated call means the access token aged out; try one
        // refresh before surfacing it to the user as a logout.
        if response.statusCode == 401, authenticated, token != nil {
            if let refreshed = await tokenProvider?.refreshAccessToken() {
                token = refreshed
                request = try makeRequest(
                    path: path, method: method, query: query, body: payload, token: refreshed
                )
                (data, response) = try await perform(request)
            }
        }

        guard (200..<300).contains(response.statusCode) else {
            let error = Self.mapError(status: response.statusCode, data: data)
            if error.requiresReauthentication, authenticated {
                await tokenProvider?.handleSessionExpired()
            }
            throw error
        }

        if Response.self == EmptyResponse.self {
            return EmptyResponse() as! Response
        }

        do {
            return try JSONCoding.decoder.decode(Response.self, from: data)
        } catch {
            throw APIError.decoding(String(describing: error))
        }
    }

    private func perform(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        do {
            let (data, response) = try await session.data(for: request)
            guard let http = response as? HTTPURLResponse else {
                throw APIError.network("The server sent an unexpected response.")
            }
            return (data, http)
        } catch let error as APIError {
            throw error
        } catch let error as URLError {
            switch error.code {
            case .notConnectedToInternet, .networkConnectionLost:
                throw APIError.network("You appear to be offline.")
            case .timedOut:
                throw APIError.network("The request timed out.")
            case .cannotConnectToHost, .cannotFindHost:
                throw APIError.network("Could not reach the server. Is the backend running?")
            default:
                throw APIError.network(error.localizedDescription)
            }
        } catch {
            throw APIError.network(error.localizedDescription)
        }
    }

    private static func mapError(status: Int, data: Data) -> APIError {
        let body = try? JSONCoding.decoder.decode(APIErrorBody.self, from: data)
        let message = body?.detail ?? "Something went wrong."

        switch status {
        case 401: return .unauthorized
        case 403: return .forbidden(message)
        case 404: return .notFound(message)
        case 409: return .conflict(code: body?.code ?? "conflict", message: message)
        case 422: return .validation(message)
        default:  return .server(status: status, message: message)
        }
    }
}

/// Placeholder for endpoints whose body we do not care about.
struct EmptyResponse: Decodable {}
