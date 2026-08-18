import SwiftUI

struct NotificationListView: View {
    @Environment(Session.self) private var session

    @State private var notifications: [AppNotification] = []
    @State private var errorMessage: String?
    @State private var isLoading = false

    var body: some View {
        Group {
            if notifications.isEmpty, isLoading {
                ProgressView()
            } else if let errorMessage, notifications.isEmpty {
                ErrorBanner(message: errorMessage) { Task { await load() } }
            } else if notifications.isEmpty {
                EmptyStateView(title: "No notifications",
                               message: "Alerts about trips, maintenance and incidents land here.",
                               systemImage: "bell.slash")
            } else {
                List(notifications) { item in
                    HStack(alignment: .top, spacing: 12) {
                        Image(systemName: item.category.iconName)
                            .foregroundStyle(item.isRead ? Color.secondary : Color.accentColor)
                            .frame(width: 24)
                        VStack(alignment: .leading, spacing: 3) {
                            Text(item.title)
                                .font(.subheadline.weight(item.isRead ? .regular : .semibold))
                            Text(item.body)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            Text(Format.dateTime(item.createdAt))
                                .font(.caption2)
                                .foregroundStyle(.tertiary)
                        }
                    }
                    .padding(.vertical, 2)
                    .contentShape(Rectangle())
                    .onTapGesture {
                        Task {
                            _ = try? await session.api.markNotificationRead(id: item.id)
                            await load()
                        }
                    }
                }
                .listStyle(.plain)
            }
        }
        .navigationTitle("Notifications")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button("Mark all read") {
                    Task {
                        try? await session.api.markAllNotificationsRead()
                        await load()
                    }
                }
                .disabled(notifications.allSatisfy(\.isRead))
            }
        }
        .refreshable { await load() }
        .task { await load() }
    }

    private func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            notifications = try await session.api.notifications()
            errorMessage = nil
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}
