import Foundation
import Observation

/// Consumes the `/ws/tracking` broadcast feed.
///
/// URLSessionWebSocketTask is used directly - the payload is one small JSON
/// envelope, so a third-party socket library would be more moving parts than
/// the problem needs.
@Observable
@MainActor
final class TrackingSocket {
    struct Update {
        let vehicleId: Int
        let registrationNumber: String
        let point: TrackPoint
    }

    private(set) var isConnected = false

    private var task: URLSessionWebSocketTask?
    private var onUpdate: ((Update) -> Void)?

    func connect(onUpdate: @escaping (Update) -> Void) {
        guard task == nil else { return }
        self.onUpdate = onUpdate

        let socket = URLSession.shared.webSocketTask(with: AppConfig.webSocketURL)
        task = socket
        socket.resume()
        isConnected = true
        receive()
    }

    func disconnect() {
        task?.cancel(with: .goingAway, reason: nil)
        task = nil
        isConnected = false
    }

    private func receive() {
        task?.receive { [weak self] result in
            Task { @MainActor [weak self] in
                guard let self else { return }
                switch result {
                case .success(let message):
                    if case .string(let text) = message {
                        self.handle(text)
                    }
                    self.receive()  // re-arm for the next frame
                case .failure:
                    self.isConnected = false
                    self.task = nil
                }
            }
        }
    }

    private func handle(_ text: String) {
        struct Envelope: Decodable {
            let event: String
            let data: Payload

            struct Payload: Decodable {
                let vehicleId: Int
                let registrationNumber: String
                let tripId: Int?
                let latitude: Double
                let longitude: Double
                let speedKph: Double?
                let heading: Double?
                let recordedAt: Date

                enum CodingKeys: String, CodingKey {
                    case latitude, longitude, heading
                    case vehicleId = "vehicle_id"
                    case registrationNumber = "registration_number"
                    case tripId = "trip_id"
                    case speedKph = "speed_kph"
                    case recordedAt = "recorded_at"
                }
            }
        }

        guard let data = text.data(using: .utf8),
              let envelope = try? JSONCoding.decoder.decode(Envelope.self, from: data),
              envelope.event == "location.updated" else { return }

        let payload = envelope.data
        onUpdate?(
            Update(
                vehicleId: payload.vehicleId,
                registrationNumber: payload.registrationNumber,
                point: TrackPoint(
                    id: Int(payload.recordedAt.timeIntervalSince1970),
                    vehicleId: payload.vehicleId,
                    tripId: payload.tripId,
                    latitude: payload.latitude,
                    longitude: payload.longitude,
                    speedKph: payload.speedKph,
                    heading: payload.heading,
                    accuracyM: nil,
                    recordedAt: payload.recordedAt
                )
            )
        )
    }
}
