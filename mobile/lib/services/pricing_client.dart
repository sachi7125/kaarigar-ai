// Talks to backend/app/api/pricing.py. Requires connectivity — unlike capture and
// the offline queue (Day 3), pricing needs Gemini + the XGBoost model, both
// server-side, so there is no offline path here. Callers must handle failure by
// telling her the estimate isn't available right now, never by blocking capture
// itself (that guarantee stays Day 3's). (Day 4)

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'api_base.dart';
import '../models/pricing_result.dart';

class PricingClient {
  static String get baseUrl => apiBaseUrl;

  static Future<AttributeSuggestion> fetchAttributes({
    required String imagePath,
    required String audioPath,
    required String lang,
  }) async {
    final request = http.MultipartRequest('POST', Uri.parse('$baseUrl/pricing/attributes'));
    request.fields['lang'] = lang;
    request.files.add(await http.MultipartFile.fromPath('image', imagePath));
    request.files.add(await http.MultipartFile.fromPath('audio', audioPath));

    final response = await request.send();
    if (response.statusCode != 200) {
      throw Exception('attributes request failed: ${response.statusCode}');
    }
    final body = await response.stream.bytesToString();
    return AttributeSuggestion.fromJson(jsonDecode(body));
  }

  /// True/false/null (null = unclear — caller should re-ask or give up).
  static Future<bool?> classifyAnswer({
    required String audioPath,
    required String lang,
  }) async {
    final request = http.MultipartRequest('POST', Uri.parse('$baseUrl/pricing/classify_answer'));
    request.fields['lang'] = lang;
    request.files.add(await http.MultipartFile.fromPath('audio', audioPath));

    final response = await request.send();
    if (response.statusCode != 200) {
      throw Exception('classify_answer request failed: ${response.statusCode}');
    }
    final body = jsonDecode(await response.stream.bytesToString());
    return body['answer'] as bool?;
  }

  static Future<Quote> getQuote({
    required String category,
    required String material,
    required String sizeClass,
    double? sizeScore,
    String region = 'unknown',
    int? month,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/pricing/quote'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'category': category,
        'material': material,
        'size_class': sizeClass,
        'size_score': sizeScore,
        'region': region,
        'month': month,
      }),
    );
    if (response.statusCode != 200) {
      throw Exception('quote request failed: ${response.statusCode}');
    }
    return Quote.fromJson(jsonDecode(response.body));
  }
}
