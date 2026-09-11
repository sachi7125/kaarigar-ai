// Talks to backend/app/api/listings.py. (Day 5, share card + export bundle Day 6,
// per-marketplace exports + sign-in token Day 7)

import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'api_base.dart';
import 'artisan_session.dart';

class ListingsClient {
  static String get baseUrl => apiBaseUrl;

  /// Throws with the server's detail message on failure (e.g. 403 when the
  /// artisan isn't verified yet) so the caller can show it as-is.
  static Future<Map<String, dynamic>> publish({
    required String artisanId,
    required String clientId,
    required String category,
    required String material,
    required String sizeClass,
    required String titleEn,
    required String titleHi,
    required String descriptionEn,
    required String descriptionHi,
    required double priceInr,
    double? bandLowInr,
    double? bandHighInr,
    required String stockType,
    required int totalCount,
    String priceUnit = 'piece', // 'piece' | 'set' — a set is all totalCount pieces at priceInr
  }) async {
    final res = await http.post(
      Uri.parse('$baseUrl/listings'),
      headers: {'Content-Type': 'application/json', ...await ArtisanSession.authHeaders()},
      body: jsonEncode({
        'artisan_id': artisanId,
        'client_id': clientId,
        'category': category,
        'material': material,
        'size_class': sizeClass,
        'title_en': titleEn,
        'title_hi': titleHi,
        'description_en': descriptionEn,
        'description_hi': descriptionHi,
        'price_inr': priceInr,
        'band_low_inr': bandLowInr,
        'band_high_inr': bandHighInr,
        'stock_type': stockType,
        'total_count': totalCount,
        'price_unit': priceUnit,
      }),
    );
    throwIfSignedOut(res.statusCode);
    if (res.statusCode != 200) {
      String detail = 'publish failed: ${res.statusCode}';
      try {
        detail = jsonDecode(res.body)['detail'] ?? detail;
      } catch (_) {}
      throw Exception(detail);
    }
    return jsonDecode(res.body);
  }

  static Future<List<Map<String, dynamic>>> listForArtisan(String artisanId) async {
    final res = await http.get(Uri.parse('$baseUrl/listings?artisan_id=$artisanId'));
    if (res.statusCode != 200) throw Exception('listings request failed: ${res.statusCode}');
    return List<Map<String, dynamic>>.from(jsonDecode(res.body));
  }

  /// Downloads the share-card PNG for a listing to the app's cache folder and
  /// returns its path — the caller hands that to the OS share sheet
  /// (`share_plus`) so "forward it on WhatsApp" (wireframe/architecture doc)
  /// is a real share, not just a preview.
  static Future<String> downloadShareCard(String listingId) async {
    final res = await http.get(Uri.parse('$baseUrl/listings/$listingId/share_card'));
    if (res.statusCode != 200) throw Exception('share_card request failed: ${res.statusCode}');
    return _saveToCache('share_card_$listingId.png', res.bodyBytes);
  }

  /// The marketplaces a listing can be exported for: [{id, name, format}].
  static Future<List<Map<String, dynamic>>> exportMarketplaces() async {
    final res = await http.get(Uri.parse('$baseUrl/exports/marketplaces'));
    if (res.statusCode != 200) throw Exception('marketplaces request failed: ${res.statusCode}');
    return List<Map<String, dynamic>>.from(jsonDecode(res.body));
  }

  /// One listing in one marketplace's format (Day 7). The server builds the
  /// file only now, on this tap; the phone keeps it in its cache folder (which
  /// Android clears on its own), not in her documents, and overwrites it on
  /// the next export of the same listing.
  static Future<String> downloadExport(String listingId, String marketplace) async {
    final res = await http.get(Uri.parse('$baseUrl/listings/$listingId/export/$marketplace'));
    if (res.statusCode != 200) throw Exception('export request failed: ${res.statusCode}');
    final match = RegExp(r'filename="([^"]+)"').firstMatch(res.headers['content-disposition'] ?? '');
    final name = match?.group(1) ?? 'kaarigar_${marketplace}_$listingId';
    return _saveToCache(name, res.bodyBytes);
  }

  static Future<String> _saveToCache(String name, List<int> bytes) async {
    final dir = await getTemporaryDirectory();
    final path = '${dir.path}/$name';
    await File(path).writeAsBytes(bytes);
    return path;
  }

  /// A short voice note -> a bilingual title suggestion (transcribed,
  /// glossary-corrected, same describe() pipeline a listing already goes
  /// through) — for renaming before or after publish. Never writes anything
  /// itself; the caller decides whether to hold the result locally
  /// (pre-publish) or send it via [renameListing] (post-publish).
  static Future<Map<String, dynamic>> renameByVoice({
    required String audioPath,
    required String lang,
  }) async {
    final request = http.MultipartRequest('POST', Uri.parse('$baseUrl/listings/rename_by_voice'));
    request.headers.addAll(await ArtisanSession.authHeaders());
    request.fields['lang'] = lang;
    request.files.add(await http.MultipartFile.fromPath('audio', audioPath));
    final response = await request.send();
    throwIfSignedOut(response.statusCode);
    if (response.statusCode != 200) {
      throw Exception('rename_by_voice request failed: ${response.statusCode}');
    }
    return jsonDecode(await response.stream.bytesToString());
  }

  /// Renames an already-published listing.
  static Future<void> renameListing({
    required String listingId,
    required String titleEn,
    required String titleHi,
  }) async {
    final res = await http.patch(
      Uri.parse('$baseUrl/listings/$listingId'),
      headers: {'Content-Type': 'application/json', ...await ArtisanSession.authHeaders()},
      body: jsonEncode({'title_en': titleEn, 'title_hi': titleHi}),
    );
    throwIfSignedOut(res.statusCode);
    if (res.statusCode != 200) {
      String detail = 'rename failed: ${res.statusCode}';
      try {
        detail = jsonDecode(res.body)['detail'] ?? detail;
      } catch (_) {}
      throw Exception(detail);
    }
  }
}
