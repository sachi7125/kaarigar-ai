// Screen 1 · FIRST RUN — CHOOSE A LANGUAGE (wireframe).
// No language list is read — the script glyph on each tile is recognition,
// not reading. Each tile speaks its own name when touched. Language stays
// changeable later (Day 6+ settings — out of scope today). (Day 5)
import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'phone_screen.dart';

const _accent = Color(0xFF4F46E5);

class _Lang {
  final String code;
  final String glyph;
  final String spokenName;
  final String ttsLocale;
  const _Lang(this.code, this.glyph, this.spokenName, this.ttsLocale);
}

const _languages = [
  _Lang('hi', 'हिं', 'हिन्दी', 'hi-IN'),
  _Lang('bn', 'বাং', 'বাংলা', 'bn-IN'),
  _Lang('ta', 'தமி', 'தமிழ்', 'ta-IN'),
  _Lang('mr', 'मरा', 'मराठी', 'mr-IN'),
];

class LanguageScreen extends StatefulWidget {
  const LanguageScreen({Key? key}) : super(key: key);

  @override
  State<LanguageScreen> createState() => _LanguageScreenState();
}

class _LanguageScreenState extends State<LanguageScreen> {
  final FlutterTts _tts = FlutterTts();
  bool _navigating = false;

  @override
  void dispose() {
    _tts.stop();
    super.dispose();
  }

  Future<void> _selectLanguage(_Lang lang) async {
    if (_navigating) return;
    setState(() => _navigating = true);
    await _tts.setLanguage(lang.ttsLocale);
    await _tts.speak(lang.spokenName);
    await Future.delayed(const Duration(milliseconds: 1100));
    if (!mounted) return;
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (_) => PhoneScreen(language: lang.code)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF9FAFB),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Spacer(),
              const Icon(Icons.volume_up_rounded, color: _accent, size: 40),
              const SizedBox(height: 12),
              const Text('KaarigarAI', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Color(0xFF1F2937))),
              const SizedBox(height: 40),
              GridView.count(
                shrinkWrap: true,
                crossAxisCount: 2,
                mainAxisSpacing: 16,
                crossAxisSpacing: 16,
                childAspectRatio: 1.3,
                children: _languages.map((lang) {
                  return Material(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(20),
                    elevation: 2,
                    child: InkWell(
                      borderRadius: BorderRadius.circular(20),
                      onTap: () => _selectLanguage(lang),
                      child: Center(
                        child: Text(lang.glyph,
                            style: const TextStyle(fontSize: 34, fontWeight: FontWeight.w600, color: Color(0xFF1F2937))),
                      ),
                    ),
                  );
                }).toList(),
              ),
              const Spacer(),
              if (_navigating) const CircularProgressIndicator(color: _accent),
              const SizedBox(height: 12),
            ],
          ),
        ),
      ),
    );
  }
}
