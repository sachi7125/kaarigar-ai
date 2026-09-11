// Shared backend host resolution for every API client. (Day 4)

// Default: the phone's OWN localhost:8000 — a real Android device reaches the
// Mac through `adb reverse tcp:8000 tcp:8000`, the emulator the same way, and
// the iOS Simulator shares the host's network. Day 7: for the Wi-Fi demo with
// no cable, build with the Mac's address instead (scripts/run_server.sh lan
// prints it):
//   flutter run --dart-define=KAARIGAR_API=http://192.168.1.5:8000/api
const String _apiOverride = String.fromEnvironment('KAARIGAR_API');

String get apiBaseUrl => _apiOverride.isNotEmpty ? _apiOverride : 'http://localhost:8000/api';

/// Thrown by the API clients on HTTP 401 (Day 7): this phone's sign-in token is
/// missing, or it was replaced because her number was verified on another
/// phone. Screens catch it and offer to verify the number again.
class SignInRequired implements Exception {
  @override
  String toString() => 'इस फ़ोन पर नंबर फिर से पक्का करना होगा।';
}

void throwIfSignedOut(int statusCode) {
  if (statusCode == 401) throw SignInRequired();
}
