// Shared backend host resolution for every API client. (Day 4)

// Every target — Android emulator, a real Android device over
// `adb reverse tcp:8000 tcp:8000`, and iOS Simulator (shares the host's
// network) — reaches the backend at its OWN localhost:8000. For the emulator
// specifically, `adb reverse` is equivalent to its usual 10.0.2.2 special
// alias, so one code path now covers all three instead of branching on
// platform; a real device over Wi-Fi (no USB/adb reverse) would still need
// the host's LAN IP instead.
String get apiBaseUrl => 'http://localhost:8000/api';
