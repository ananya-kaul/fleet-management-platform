import Foundation

/// Shared JSON coders.
///
/// The API emits timestamps in several shapes depending on the column and the
/// database backing it: with or without fractional seconds, and with or without
/// a timezone offset (SQLite does not preserve one). A single ISO8601 strategy
/// rejects at least one of those, so the decoder tries each in turn.
enum JSONCoding {
    static let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .custom { decoder in
            let raw = try decoder.singleValueContainer().decode(String.self)
            if let date = parseDate(raw) { return date }
            throw DecodingError.dataCorrupted(
                .init(codingPath: decoder.codingPath,
                      debugDescription: "Unrecognised date format: \(raw)")
            )
        }
        return decoder
    }()

    static let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .custom { date, encoder in
            var container = encoder.singleValueContainer()
            try container.encode(isoFormatter.string(from: date))
        }
        return encoder
    }()

    /// ISO8601 with fractional seconds, always in UTC - what we send back.
    static let isoFormatter: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()

    private static let isoWithFraction: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()

    private static let isoPlain: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter
    }()

    /// Fallbacks for timestamps that carry no timezone, plus plain `yyyy-MM-dd`
    /// dates used by licence and insurance expiry fields.
    private static let fallbackFormats = [
        "yyyy-MM-dd'T'HH:mm:ss.SSSSSS",
        "yyyy-MM-dd'T'HH:mm:ss.SSS",
        "yyyy-MM-dd'T'HH:mm:ss",
        "yyyy-MM-dd",
    ]

    private static let fallbackFormatters: [DateFormatter] = fallbackFormats.map { format in
        let formatter = DateFormatter()
        formatter.dateFormat = format
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        return formatter
    }

    static func parseDate(_ raw: String) -> Date? {
        if let date = isoWithFraction.date(from: raw) { return date }
        if let date = isoPlain.date(from: raw) { return date }
        for formatter in fallbackFormatters {
            if let date = formatter.date(from: raw) { return date }
        }
        return nil
    }

    /// `yyyy-MM-dd`, the format the API expects for date-only fields.
    static let dayFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        return formatter
    }()
}
