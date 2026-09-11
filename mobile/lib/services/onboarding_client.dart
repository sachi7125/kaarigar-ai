// Talks to backend/app/api/onboarding.py. (Day 5)

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'api_base.dart';

class OnboardingClient {
  static String get baseUrl => apiBaseUrl;

  static Future<Map<String, dynamic>> register({
    required String phone,
    required String language,
  }) async {
    final res = await http.post(Uri.parse('$baseUrl/onboarding/register'),
        body: {'phone': phone, 'language': language});
    if (res.statusCode != 200) throw Exception('register failed: ${res.statusCode}');
    return jsonDecode(res.body);
  }

  /// Returns the OTP itself — no SMS provider is configured (see the backend's
  /// own docstring); the app speaks it aloud immediately instead, simulating
  /// what "OTP read aloud" looks like once a real SMS integration exists.
  static Future<String> sendOtp(String phone) async {
    final res = await http.post(Uri.parse('$baseUrl/onboarding/send_otp'), body: {'phone': phone});
    if (res.statusCode != 200) throw Exception('send_otp failed: ${res.statusCode}');
    return jsonDecode(res.body)['otp'] as String;
  }

  /// The phone's new sign-in token on success (Day 7), null on a wrong or
  /// expired code.
  static Future<String?> verifyOtp({required String phone, required String otp}) async {
    final res = await http.post(Uri.parse('$baseUrl/onboarding/verify_otp'),
        body: {'phone': phone, 'otp': otp});
    if (res.statusCode != 200) return null;
    final body = jsonDecode(res.body);
    return body['verified'] == true ? body['auth_token'] as String? : null;
  }
}
