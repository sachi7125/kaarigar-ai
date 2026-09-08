// Talks to backend/app/api/storefront.py. (Day 6)

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'api_base.dart';

class StorefrontClient {
  static String get baseUrl => apiBaseUrl;

  static Future<Map<String, dynamic>> recordMakerStory({
    required String artisanId,
    required String audioPath,
    required String lang,
  }) async {
    final request = http.MultipartRequest('POST', Uri.parse('$baseUrl/storefront/maker_story'));
    request.fields['artisan_id'] = artisanId;
    request.fields['lang'] = lang;
    request.files.add(await http.MultipartFile.fromPath('audio', audioPath));

    final response = await request.send();
    if (response.statusCode != 200) {
      throw Exception('maker_story request failed: ${response.statusCode}');
    }
    return jsonDecode(await response.stream.bytesToString());
  }

  static Future<Map<String, dynamic>> getStorefront(String artisanId) async {
    final res = await http.get(Uri.parse('$baseUrl/storefront/$artisanId'));
    if (res.statusCode != 200) throw Exception('storefront request failed: ${res.statusCode}');
    return jsonDecode(res.body);
  }

  static Future<Map<String, dynamic>> getDashboard(String artisanId) async {
    final res = await http.get(Uri.parse('$baseUrl/storefront/$artisanId/dashboard'));
    if (res.statusCode != 200) throw Exception('dashboard request failed: ${res.statusCode}');
    return jsonDecode(res.body);
  }

  static Future<Map<String, dynamic>> getDigestPreview(String artisanId) async {
    final res = await http.get(Uri.parse('$baseUrl/storefront/$artisanId/digest_preview'));
    if (res.statusCode != 200) throw Exception('digest_preview request failed: ${res.statusCode}');
    return jsonDecode(res.body);
  }

  /// True if this is a new follow, false if she was already following.
  static Future<bool> follow({required String artisanId, required String email}) async {
    final res = await http.post(
      Uri.parse('$baseUrl/storefront/follow'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'artisan_id': artisanId, 'email': email}),
    );
    if (res.statusCode != 200) throw Exception('follow request failed: ${res.statusCode}');
    return jsonDecode(res.body)['status'] == 'following';
  }

  // The permanent public storefront URL (kaarigar.in/s/<id>) is computed
  // server-side with the real url_base (config.yaml) and comes back from
  // getStorefront()['storefront_url'] — not reconstructed here, so mobile
  // never has to know that config value.
  static String qrImageUrl(String artisanId) => '$baseUrl/storefront/$artisanId/qr';
}
