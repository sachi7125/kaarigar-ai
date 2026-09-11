// Screen 1b · phone number entry — numeric keypad next, digits only, no
// letters (wireframe). Registers the artisan UNVERIFIED — verification is
// deferred to publish-time (see decisions.md / onboarding.py). (Day 5)
import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import '../../services/onboarding_client.dart';
import '../../services/artisan_session.dart';
import '../../widgets/numeric_keypad.dart';
import '../home_screen.dart';
import 'otp_screen.dart';

const _accent = Color(0xFF4F46E5);

const _promptByLang = {
  'hi': 'अपना फ़ोन नंबर डालिए',
  'bn': 'আপনার ফোন নম্বর লিখুন',
  'ta': 'உங்கள் தொலைபேசி எண்ணை உள்ளிடவும்',
  'mr': 'तुमचा फोन नंबर टाका',
};
const _ttsLocaleByLang = {'hi': 'hi-IN', 'bn': 'bn-IN', 'ta': 'ta-IN', 'mr': 'mr-IN'};

class PhoneScreen extends StatefulWidget {
  final String language;
  const PhoneScreen({Key? key, required this.language}) : super(key: key);

  @override
  State<PhoneScreen> createState() => _PhoneScreenState();
}

class _PhoneScreenState extends State<PhoneScreen> {
  final FlutterTts _tts = FlutterTts();
  String _digits = '';
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _speakPrompt();
  }

  Future<void> _speakPrompt() async {
    await _tts.setLanguage(_ttsLocaleByLang[widget.language] ?? 'hi-IN');
    await _tts.speak(_promptByLang[widget.language] ?? _promptByLang['hi']!);
  }

  Future<void> _submit() async {
    if (_digits.length != 10 || _submitting) return;
    setState(() { _submitting = true; _error = null; });
    final phone = '+91$_digits';
    try {
      final result = await OnboardingClient.register(phone: phone, language: widget.language);
      final token = result['auth_token'] as String?;
      await ArtisanSession.save(
        artisanId: result['artisan_id'], phone: phone,
        language: widget.language, verified: result['verified'] == true, authToken: token,
      );
      if (!mounted) return;
      if (token == null) {
        // This number already has a shop (Day 7): the phone must prove it's
        // hers with the OTP before the shop opens on it.
        final ok = await Navigator.push<bool>(
          context,
          MaterialPageRoute(builder: (_) => OtpScreen(phone: phone, language: widget.language)),
        );
        if (!mounted) return;
        if (ok != true) {
          setState(() {
            _error = 'इस नंबर की दुकान पहले से है — खोलने के लिए कोड डालिए।';
            _submitting = false;
          });
          return;
        }
      }
      Navigator.pushAndRemoveUntil(
        context, MaterialPageRoute(builder: (_) => const HomeScreen()), (route) => false,
      );
    } catch (e) {
      setState(() {
        _error = 'नेटवर्क समस्या — दोबारा कोशिश करें। (Network error, try again.)';
        _submitting = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF9FAFB),
      body: SafeArea(
        child: Column(
          children: [
            const Spacer(),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Text(_promptByLang[widget.language] ?? _promptByLang['hi']!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 18, color: Color(0xFF1F2937), fontWeight: FontWeight.w600)),
            ),
            const SizedBox(height: 20),
            Text(_digits.isEmpty ? '+91' : '+91 $_digits',
                style: const TextStyle(fontSize: 24, letterSpacing: 2, fontWeight: FontWeight.bold, color: _accent)),
            const SizedBox(height: 24),
            NumericKeypad(value: _digits, maxLength: 10, onChanged: (v) => setState(() => _digits = v)),
            const SizedBox(height: 16),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: Text(_error!, style: const TextStyle(color: Colors.red, fontSize: 13), textAlign: TextAlign.center),
              ),
            const Spacer(),
            Padding(
              padding: const EdgeInsets.all(24),
              child: SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _digits.length == 10 && !_submitting ? _submit : null,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _accent, foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  ),
                  child: _submitting
                      ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : const Icon(Icons.arrow_forward_rounded),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
