import SwiftUI

struct LoginView: View {
    @Environment(Session.self) private var session

    @State private var email = ""
    @State private var password = ""
    @FocusState private var focusedField: Field?

    private enum Field { case email, password }

    private var canSubmit: Bool {
        !email.trimmingCharacters(in: .whitespaces).isEmpty
            && password.count >= 8
            && !session.isSigningIn
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Email", text: $email)
                        .textContentType(.emailAddress)
                        .keyboardType(.emailAddress)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .focused($focusedField, equals: .email)
                        .submitLabel(.next)
                        .onSubmit { focusedField = .password }

                    SecureField("Password", text: $password)
                        .textContentType(.password)
                        .focused($focusedField, equals: .password)
                        .submitLabel(.go)
                        .onSubmit { if canSubmit { submit() } }
                } header: {
                    Text("Sign in")
                } footer: {
                    if let error = session.signInError {
                        Text(error).foregroundStyle(.red)
                    }
                }

                Section {
                    Button(action: submit) {
                        HStack {
                            Spacer()
                            if session.isSigningIn {
                                ProgressView()
                            } else {
                                Text("Sign in").fontWeight(.semibold)
                            }
                            Spacer()
                        }
                    }
                    .disabled(!canSubmit)
                }

                Section("Demo accounts") {
                    Button("Fleet manager") {
                        fill(email: "manager@fleet.com", password: "Manager@123")
                    }
                    Button("Driver") {
                        fill(email: "driver1@fleet.com", password: "Driver@123")
                    }
                }
                .font(.callout)
            }
            .navigationTitle("Fleet Manager")
            .onChange(of: email) { session.clearSignInError() }
            .onChange(of: password) { session.clearSignInError() }
        }
    }

    private func fill(email: String, password: String) {
        self.email = email
        self.password = password
    }

    private func submit() {
        focusedField = nil
        Task { await session.signIn(email: email, password: password) }
    }
}
