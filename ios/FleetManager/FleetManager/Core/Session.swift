import Foundation
import Observation

/// Owns the authenticated session: tokens, the signed-in user, and the
/// sign-in/sign-out transitions the root view switches on.
///
/// It is also the app's `TokenProviding` implementation, so `APIClient` can ask
/// it for a token and tell it when one has expired without either type knowing
/// about SwiftUI.
@Observable
@MainActor
final class Session {
    enum State: Equatable {
        case loading
        case signedOut
        case signedIn(AuthUser)
    }

    private(set) var state: State = .loading
    private(set) var signInError: String?
    private(set) var isSigningIn = false

    let client: APIClient
    let api: FleetAPI

    private var accessToken: String?
    private var refreshToken: String?

    private enum Keys {
        static let access = "access_token"
        static let refresh = "refresh_token"
    }

    init(client: APIClient = APIClient()) {
        self.client = client
        self.api = FleetAPI(client: client)
    }

    var currentUser: AuthUser? {
        if case .signedIn(let user) = state { return user }
        return nil
    }

    var isFleetManager: Bool { currentUser?.role == .fleetManager }

    /// Called once at launch: wires the client to this session and restores any
    /// stored session by validating the token against /auth/me.
    func bootstrap() async {
        await client.setTokenProvider(self)

        accessToken = KeychainStore.read(Keys.access)
        refreshToken = KeychainStore.read(Keys.refresh)

        guard accessToken != nil else {
            state = .signedOut
            return
        }

        do {
            let user = try await api.currentUser()
            state = .signedIn(user)
        } catch {
            // The stored token is stale or the backend is unreachable; either way
            // the safe landing spot is the sign-in screen.
            clearTokens()
            state = .signedOut
        }
    }

    func signIn(email: String, password: String) async {
        isSigningIn = true
        signInError = nil
        defer { isSigningIn = false }

        do {
            let pair = try await api.login(email: email, password: password)
            store(access: pair.accessToken, refresh: pair.refreshToken)
            state = .signedIn(pair.user)
        } catch {
            signInError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    func signOut() async {
        // Best effort: the token is discarded locally whatever the server says.
        try? await api.logout()
        clearTokens()
        state = .signedOut
    }

    func clearSignInError() {
        signInError = nil
    }

    // MARK: - Token storage

    private func store(access: String, refresh: String) {
        accessToken = access
        refreshToken = refresh
        KeychainStore.save(access, for: Keys.access)
        KeychainStore.save(refresh, for: Keys.refresh)
    }

    private func clearTokens() {
        accessToken = nil
        refreshToken = nil
        KeychainStore.delete(Keys.access)
        KeychainStore.delete(Keys.refresh)
    }
}

extension Session: TokenProviding {
    nonisolated func currentAccessToken() async -> String? {
        await MainActor.run { accessToken }
    }

    nonisolated func refreshAccessToken() async -> String? {
        guard let refresh = await MainActor.run(body: { refreshToken }) else { return nil }

        do {
            let response = try await api.refresh(token: refresh)
            await MainActor.run {
                accessToken = response.accessToken
                KeychainStore.save(response.accessToken, for: Keys.access)
            }
            return response.accessToken
        } catch {
            return nil
        }
    }

    nonisolated func handleSessionExpired() async {
        await MainActor.run {
            clearTokens()
            state = .signedOut
        }
    }
}
