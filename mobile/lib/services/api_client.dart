// Talks to FastAPI. Shows queued state when offline. (Day 3)

import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';
import 'api_base.dart';

class ApiClient {
  static String get baseUrl => apiBaseUrl;

  static Future<bool> syncDraft({
    required String clientId,
    required String imagePath,
    required String audioPath,
  }) async {
    try {
      var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/sync'));
      request.fields['client_id'] = clientId;

      request.files.add(await http.MultipartFile.fromPath('image', imagePath));
      request.files.add(await http.MultipartFile.fromPath('audio', audioPath));

      var response = await request.send();
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('Sync failed: $e');
      return false;
    }
  }
}
