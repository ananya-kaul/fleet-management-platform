import SwiftUI

/// Small building blocks reused across screens.

/// A coloured capsule for a status enum.
struct StatusChip: View {
    let text: String
    let color: Color

    var body: some View {
        Text(text)
            .font(.caption2.weight(.semibold))
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(color.opacity(0.15), in: Capsule())
            .foregroundStyle(color)
    }
}

/// A labelled value row for detail screens.
struct DetailRow: View {
    let label: String
    let value: String

    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            Text(label)
                .foregroundStyle(.secondary)
            Spacer(minLength: 12)
            Text(value)
                .multilineTextAlignment(.trailing)
        }
    }
}

/// A single dashboard metric.
struct MetricTile: View {
    let title: String
    let value: String
    var systemImage: String = "circle"
    var tint: Color = .accentColor

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Label(title, systemImage: systemImage)
                .font(.caption)
                .foregroundStyle(.secondary)
                .labelStyle(.titleAndIcon)
            Text(value)
                .font(.title2.weight(.semibold))
                .foregroundStyle(tint)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 10))
    }
}

/// Shown when a list has loaded but has nothing in it.
struct EmptyStateView: View {
    let title: String
    var message: String? = nil
    var systemImage: String = "tray"

    var body: some View {
        ContentUnavailableView {
            Label(title, systemImage: systemImage)
        } description: {
            if let message { Text(message) }
        }
    }
}

/// Standard inline error with a retry affordance.
struct ErrorBanner: View {
    let message: String
    var retry: (() -> Void)?

    var body: some View {
        VStack(spacing: 12) {
            Label(message, systemImage: "exclamationmark.triangle")
                .font(.callout)
                .multilineTextAlignment(.center)
            if let retry {
                Button("Try again", action: retry)
                    .buttonStyle(.bordered)
            }
        }
        .frame(maxWidth: .infinity)
        .padding()
    }
}

// MARK: - Formatting helpers

enum Format {
    static func distance(_ km: Double?) -> String {
        guard let km else { return "—" }
        return String(format: "%.1f km", km)
    }

    static func odometer(_ km: Double?) -> String {
        guard let km else { return "—" }
        return String(format: "%.0f km", km)
    }

    static func currency(_ amount: Double) -> String {
        amount.formatted(.currency(code: "INR").precision(.fractionLength(0)))
    }

    static func dateTime(_ date: Date?) -> String {
        guard let date else { return "—" }
        return date.formatted(date: .abbreviated, time: .shortened)
    }

    static func day(_ date: Date?) -> String {
        guard let date else { return "—" }
        return date.formatted(date: .abbreviated, time: .omitted)
    }

    static func apiDay(_ date: Date) -> String {
        JSONCoding.dayFormatter.string(from: date)
    }
}
