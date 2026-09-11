// Settings — read-only view of who she is on this device: phone, language,
// verified status, plus a shortcut to re-record her maker story. (Day 7)
//
// Deliberately no "change language" tile: several screens (pricing, offers,
// publish) still hardcode Hindi TTS/text, so a live switch would be
// misleading. The current-language tile speaks the name aloud so she can
// confirm what the app thinks she picked at first-run. Full multi-language
// UI is a separate hardening pass (watchlist).
import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import '../services/artisan_session.dart';
import 'maker_story_screen.dart';

const _accent = Color(0xFF4F46E5);

// Same four languages the first-run screen offers, kept in sync deliberately
// (if that list changes, this one must change too).
const _langInfo = {
  'hi': {'glyph': 'हिं', 'name': 'हिन्दी', 'locale': 'hi-IN'},
  'bn': {'glyph': 'বাং', 'name': 'বাংলা', 'locale': 'bn-IN'},
  'ta': {'glyph': 'தமி', 'name': 'தமிழ்', 'locale': 'ta-IN'},
  'mr': {'glyph': 'मरा', 'name': 'मराठी', 'locale': 'mr-IN'},
};

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({Key? key}) : super(key: key);

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final FlutterTts _tts = FlutterTts();
  bool _loading = true;
  String? _phone;
  String? _lang;
  bool _verified = false;

  @override
  void initState() {
    super.initState();
    _tts.awaitSpeakCompletion(true);
    _load();
  }

  @override
  void dispose() {
    _tts.stop();
    super.dispose();
  }

  Future<void> _load() async {
    final phone = await ArtisanSession.phone;
    final lang = await ArtisanSession.language;
    final verified = await ArtisanSession.isVerified;
    if (!mounted) return;
    setState(() {
      _phone = phone;
      _lang = lang ?? 'hi';
      _verified = verified;
      _loading = false;
    });
  }

  Future<void> _speakPhone() async {
    if (_phone == null) return;
    // Read the digits one by one so a mishear is easy to spot — same reason
    // the OTP flow reads its number back digit-by-digit.
    final spoken = _phone!.split('').join(' ');
    await _tts.setLanguage(_langInfo[_lang]?['locale'] ?? 'hi-IN');
    await _tts.speak(spoken);
  }

  Future<void> _speakLanguageName() async {
    final info = _langInfo[_lang];
    if (info == null) return;
    await _tts.setLanguage(info['locale']!);
    await _tts.speak(info['name']!);
  }

  Future<void> _openMakerStory() async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const MakerStoryScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF3F4F6),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        foregroundColor: const Color(0xFF1F2937),
        title: const Text('Settings', style: TextStyle(fontWeight: FontWeight.bold)),
      ),
      body: SafeArea(
        child: _loading
            ? const Center(child: CircularProgressIndicator(color: _accent))
            : ListView(
                padding: const EdgeInsets.all(20),
                children: [
                  _phoneCard(),
                  const SizedBox(height: 16),
                  _languageCard(),
                  const SizedBox(height: 16),
                  _verifiedCard(),
                  const SizedBox(height: 24),
                  _makerStoryButton(),
                ],
              ),
      ),
    );
  }

  Widget _phoneCard() {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 10, offset: const Offset(0, 4))],
      ),
      child: Row(
        children: [
          const Icon(Icons.phone_rounded, color: _accent, size: 26),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('आपका नंबर', style: TextStyle(fontSize: 12, color: Color(0xFF9CA3AF))),
                const SizedBox(height: 2),
                Text(_phone ?? '—',
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF1F2937))),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.volume_up_rounded, color: _accent),
            onPressed: _speakPhone,
          ),
        ],
      ),
    );
  }

  Widget _languageCard() {
    final info = _langInfo[_lang] ?? _langInfo['hi']!;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 10, offset: const Offset(0, 4))],
      ),
      child: Row(
        children: [
          const Icon(Icons.language_rounded, color: _accent, size: 26),
          const SizedBox(width: 14),
          const Expanded(
            child: Text('आपकी भाषा', style: TextStyle(fontSize: 12, color: Color(0xFF9CA3AF))),
          ),
          IconButton(
            icon: const Icon(Icons.volume_up_rounded, color: _accent),
            onPressed: _speakLanguageName,
          ),
        ],
      ).let((row) => Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              row,
              const SizedBox(height: 14),
              Container(
                width: 110,
                padding: const EdgeInsets.symmetric(vertical: 16),
                decoration: BoxDecoration(
                  color: const Color(0xFFEEF2FF),
                  border: Border.all(color: _accent, width: 2),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Column(
                  children: [
                    Text(info['glyph']!,
                        style: const TextStyle(fontSize: 30, fontWeight: FontWeight.w600, color: Color(0xFF1F2937))),
                    const SizedBox(height: 4),
                    Text(info['name']!,
                        style: const TextStyle(fontSize: 13, color: Color(0xFF6B7280))),
                  ],
                ),
              ),
            ],
          )),
    );
  }

  Widget _verifiedCard() {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 10, offset: const Offset(0, 4))],
      ),
      child: Row(
        children: [
          Icon(
            _verified ? Icons.verified_rounded : Icons.info_outline_rounded,
            color: _verified ? const Color(0xFF16A34A) : const Color(0xFFF59E0B),
            size: 26,
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _verified ? 'सत्यापित' : 'सत्यापन बाकी है',
                  style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Color(0xFF1F2937)),
                ),
                const SizedBox(height: 2),
                Text(
                  _verified
                      ? 'आप अपनी लिस्टिंग पब्लिश कर सकती हैं'
                      : 'पब्लिश करने से पहले नंबर सत्यापित करना होगा',
                  style: const TextStyle(fontSize: 12, color: Color(0xFF6B7280)),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _makerStoryButton() {
    return SizedBox(
      width: double.infinity,
      child: OutlinedButton.icon(
        onPressed: _openMakerStory,
        icon: const Icon(Icons.auto_stories_rounded),
        label: const Text('अपनी कहानी बदलें'),
        style: OutlinedButton.styleFrom(
          foregroundColor: _accent,
          padding: const EdgeInsets.symmetric(vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          side: const BorderSide(color: _accent),
        ),
      ),
    );
  }
}

// Small extension so the language card can build a row-inside-a-column
// without a temporary variable — keeps the widget code declarative.
extension _Let<T> on T {
  R let<R>(R Function(T) f) => f(this);
}