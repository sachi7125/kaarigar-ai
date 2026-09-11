// Local onboarding state (Day 5) — thin wrapper over LocalDb.settings so
// callers don't spell out key names. Mirrors, but does not replace, the
// backend's own Artisan.verified — this is a local cache of it, refreshed
// whenever verify_otp succeeds.
//
// Day 7: also holds the sign-in token the backend issued to this phone
// (backend/app/auth.py), sent with every artisan-only request.

import 'local_db.dart';

class ArtisanSession {
  static const _kArtisanId = 'artisan_id';
  static const _kPhone = 'artisan_phone';
  static const _kLanguage = 'artisan_language';
  static const _kVerified = 'artisan_verified';
  static const _kAuthToken = 'artisan_auth_token';

  /// Onboarded = this phone knows her shop AND holds its sign-in token. A phone
  /// set up before Day 7 has no token, so it goes through the number and OTP
  /// screens once more; the same shop comes back.
  static Future<bool> isOnboarded() async {
    return await LocalDb.instance.getSetting(_kArtisanId) != null &&
        await LocalDb.instance.getSetting(_kAuthToken) != null;
  }

  static Future<void> save({
    required String artisanId,
    required String phone,
    required String language,
    required bool verified,
    String? authToken,
  }) async {
    await LocalDb.instance.setSetting(_kArtisanId, artisanId);
    await LocalDb.instance.setSetting(_kPhone, phone);
    await LocalDb.instance.setSetting(_kLanguage, language);
    await LocalDb.instance.setSetting(_kVerified, verified ? '1' : '0');
    if (authToken != null) await setAuthToken(authToken);
  }

  static Future<void> setVerified(bool verified) async {
    await LocalDb.instance.setSetting(_kVerified, verified ? '1' : '0');
  }

  static Future<void> setAuthToken(String token) async {
    await LocalDb.instance.setSetting(_kAuthToken, token);
  }

  /// Header map for artisan-only requests; empty if this phone has no token
  /// (the server then answers 401 and the screen offers to verify again).
  static Future<Map<String, String>> authHeaders() async {
    final token = await LocalDb.instance.getSetting(_kAuthToken);
    return token == null ? {} : {'Authorization': 'Bearer $token'};
  }

  static Future<String?> get artisanId => LocalDb.instance.getSetting(_kArtisanId);
  static Future<String?> get phone => LocalDb.instance.getSetting(_kPhone);
  static Future<String?> get language => LocalDb.instance.getSetting(_kLanguage);
  static Future<bool> get isVerified async =>
      (await LocalDb.instance.getSetting(_kVerified)) == '1';
}
