// Talks to backend/app/api/listings.py. (Day 5, share card + export bundle Day 6)

import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'api_base.dart';

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
  }) async {
    final res = await http.post(
      Uri.parse('$baseUrl/listings'),
      headers: {'Content-Type': 'application/json'},
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
      }),
    );
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

  /// Downloads the share-card PNG for a listing to a local temp file and
  /// returns its path — the caller hands that to the OS share sheet
  /// (`share_plus`) so "forward it on WhatsApp" (wireframe/architecture doc)
  /// is a real share, not just a preview.
  static Future<String> downloadShareCard(String listingId) async {
    final res = await http.get(Uri.parse('$baseUrl/listings/$listingId/share_card'));
    if (res.statusCode != 200) throw Exception('share_card request failed: ${res.statusCode}');
    final dir = await getApplicationDocumentsDirectory();
    final path = '${dir.path}/share_card_$listingId.png';
    await File(path).writeAsBytes(res.bodyBytes);
    return path;
  }

  /// Downloads the export-bundle spreadsheet (GeM/ONDC/Amazon Karigar/ODOP-
  /// style catalog data, decision D1) to a local temp file and returns its
  /// path.
  static Future<String> downloadExportBundle(String listingId) async {
    final res = await http.get(Uri.parse('$baseUrl/listings/$listingId/export_bundle'));
    if (res.statusCode != 200) throw Exception('export_bundle request failed: ${res.statusCode}');
    final dir = await getApplicationDocumentsDirectory();
    final path = '${dir.path}/kaarigar_export_$listingId.xlsx';
    await File(path).writeAsBytes(res.bodyBytes);
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
    request.fields['lang'] = lang;
    request.files.add(await http.MultipartFile.fromPath('audio', audioPath));
    final response = await request.send();
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
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'title_en': titleEn, 'title_hi': titleHi}),
    );
    if (res.statusCode != 200) {
      String detail = 'rename failed: ${res.statusCode}';
      try {
        detail = jsonDecode(res.body)['detail'] ?? detail;
      } catch (_) {}
      throw Exception(detail);
    }
  }
}
