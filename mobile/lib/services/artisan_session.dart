// Local onboarding state (Day 5) — thin wrapper over LocalDb.settings so
// callers don't spell out key names. Mirrors, but does not replace, the
// backend's own Artisan.verified — this is a local cache of it, refreshed
// whenever verify_otp succeeds.

import 'local_db.dart';

class ArtisanSession {
  static const _kArtisanId = 'artisan_id';
  static const _kPhone = 'artisan_phone';
  static const _kLanguage = 'artisan_language';
  static const _kVerified = 'artisan_verified';

  static Future<bool> isOnboarded() async {
    return await LocalDb.instance.getSetting(_kArtisanId) != null;
  }

  static Future<void> save({
    required String artisanId,
    required String phone,
    required String language,
    required bool verified,
  }) async {
    await LocalDb.instance.setSetting(_kArtisanId, artisanId);
    await LocalDb.instance.setSetting(_kPhone, phone);
    await LocalDb.instance.setSetting(_kLanguage, language);
    await LocalDb.instance.setSetting(_kVerified, verified ? '1' : '0');
  }

  static Future<void> setVerified(bool verified) async {
    await LocalDb.instance.setSetting(_kVerified, verified ? '1' : '0');
  }

  static Future<String?> get artisanId => LocalDb.instance.getSetting(_kArtisanId);
  static Future<String?> get phone => LocalDb.instance.getSetting(_kPhone);
  static Future<String?> get language => LocalDb.instance.getSetting(_kLanguage);
  static Future<bool> get isVerified async =>
      (await LocalDb.instance.getSetting(_kVerified)) == '1';
}
