// Talks to backend/app/api/offers.py. (Day 5; sign-in token Day 7 — the offer
// inbox and buyer contacts are "only in her view".)

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'api_base.dart';
import 'artisan_session.dart';

class OffersClient {
  static String get baseUrl => apiBaseUrl;

  static Future<List<Map<String, dynamic>>> listPending(String artisanId) async {
    final res = await http.get(Uri.parse('$baseUrl/offers?artisan_id=$artisanId'),
        headers: await ArtisanSession.authHeaders());
    throwIfSignedOut(res.statusCode);
    if (res.statusCode != 200) throw Exception('offers request failed: ${res.statusCode}');
    return List<Map<String, dynamic>>.from(jsonDecode(res.body));
  }

  /// Returns {'buyer_name', 'buyer_contact'} on success. Throws on 409 —
  /// stock ran out between the list refresh and this tap (the double-accept
  /// case another buyer already won), which the caller must show plainly
  /// rather than retry silently.
  static Future<Map<String, dynamic>> accept(int offerId) async {
    final res = await http.post(Uri.parse('$baseUrl/offers/$offerId/accept'),
        headers: await ArtisanSession.authHeaders());
    throwIfSignedOut(res.statusCode);
    if (res.statusCode != 200) {
      String detail = 'accept failed: ${res.statusCode}';
      try {
        detail = jsonDecode(res.body)['detail'] ?? detail;
      } catch (_) {}
      throw Exception(detail);
    }
    return jsonDecode(res.body);
  }

  static Future<void> decline(int offerId) async {
    final res = await http.post(Uri.parse('$baseUrl/offers/$offerId/decline'),
        headers: await ArtisanSession.authHeaders());
    throwIfSignedOut(res.statusCode);
    if (res.statusCode != 200) throw Exception('decline failed: ${res.statusCode}');
  }
}
