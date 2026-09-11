// OTP verification — reached from the publish step (deferred verification:
// she can capture/record/price unverified; this is the one gate before
// PUBLISH). No SMS provider is configured (backend docstring, decisions.md),
// so the OTP is spoken aloud immediately by the app rather than arriving via
// text — an honest prototype substitute for a real SMS integration. (Day 5)
import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import '../../services/onboarding_client.dart';
import '../../services/artisan_session.dart';
import '../../widgets/numeric_keypad.dart';

const _accent = Color(0xFF4F46E5);

class OtpScreen extends StatefulWidget {
  final String phone;
  final String language;
  const OtpScreen({Key? key, required this.phone, required this.language}) : super(key: key);

  @override
  State<OtpScreen> createState() => _OtpScreenState();
}

class _OtpScreenState extends State<OtpScreen> {
  final FlutterTts _tts = FlutterTts();
  String _digits = '';
  bool _sending = true;
  bool _verifying = false;
  String? _error;

  static const _ttsLocaleByLang = {'hi': 'hi-IN', 'bn': 'bn-IN', 'ta': 'ta-IN', 'mr': 'mr-IN'};

  @override
  void initState() {
    super.initState();
    _sendAndSpeak();
  }

  Future<void> _sendAndSpeak() async {
    await _tts.setLanguage(_ttsLocaleByLang[widget.language] ?? 'hi-IN');
    try {
      final otp = await OnboardingClient.sendOtp(widget.phone);
      if (!mounted) return;
      setState(() => _sending = false);
      final spoken = otp.split('').join(' '); // digit-by-digit is clearer aloud
      await _tts.speak(spoken);
    } catch (e) {
      if (!mounted) return;
      setState(() { _sending = false; _error = 'OTP नहीं भेजा जा सका — नेटवर्क जांचें।'; });
    }
  }

  Future<void> _replay() async {
    final otp = await OnboardingClient.sendOtp(widget.phone);
    await _tts.speak(otp.split('').join(' '));
  }

  Future<void> _verify() async {
    if (_digits.length != 4 || _verifying) return;
    setState(() { _verifying = true; _error = null; });
    try {
      final token = await OnboardingClient.verifyOtp(phone: widget.phone, otp: _digits);
      if (token != null) {
        await ArtisanSession.setAuthToken(token);
        await ArtisanSession.setVerified(true);
        if (mounted) Navigator.pop(context, true);
      } else {
        setState(() { _error = 'गलत कोड — फिर कोशिश करें।'; _verifying = false; _digits = ''; });
      }
    } catch (e) {
      setState(() { _error = 'नेटवर्क समस्या — दोबारा कोशिश करें।'; _verifying = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF9FAFB),
      appBar: AppBar(
        backgroundColor: Colors.transparent, elevation: 0, foregroundColor: const Color(0xFF1F2937),
        title: const Text('Verify your number'),
      ),
      body: SafeArea(
        child: _sending
            ? const Center(child: CircularProgressIndicator(color: _accent))
            : Column(
                children: [
                  const SizedBox(height: 20),
                  IconButton(
                    icon: const Icon(Icons.volume_up_rounded, color: _accent, size: 36),
                    onPressed: _replay,
                    tooltip: 'फिर सुनिए',
                  ),
                  const Text('कोड फिर सुनने के लिए टैप करें', style: TextStyle(color: Color(0xFF6B7280), fontSize: 13)),
                  const SizedBox(height: 28),
                  DigitDots(entered: _digits.length, total: 4),
                  const SizedBox(height: 28),
                  NumericKeypad(value: _digits, maxLength: 4, onChanged: (v) => setState(() => _digits = v)),
                  if (_error != null) ...[
                    const SizedBox(height: 12),
                    Text(_error!, style: const TextStyle(color: Colors.red, fontSize: 13)),
                  ],
                  const Spacer(),
                  Padding(
                    padding: const EdgeInsets.all(24),
                    child: SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: _digits.length == 4 && !_verifying ? _verify : null,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: _accent, foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                        ),
                        child: _verifying
                            ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                            : const Text('Verify', style: TextStyle(fontWeight: FontWeight.bold)),
                      ),
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}
