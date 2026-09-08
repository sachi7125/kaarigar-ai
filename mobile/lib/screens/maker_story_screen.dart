// Maker story — a short voice note about herself or her craft, turned into a
// bilingual bio for the top of her storefront (roadmap: "maker story
// pipeline (reuses Day-2 voice pipeline)"). Not in the 6-screen wireframe set
// (storefront itself isn't wireframed), but built to the same rules: TTS
// prompts and reads the result back, a single mic button, re-recordable any
// time rather than a one-shot gate — a bio isn't a publish-time commitment
// the way a listing's price is. (Day 6)
import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import '../services/artisan_session.dart';
import '../services/storefront_client.dart';

const _accent = Color(0xFF4F46E5);

class MakerStoryScreen extends StatefulWidget {
  const MakerStoryScreen({Key? key}) : super(key: key);

  @override
  State<MakerStoryScreen> createState() => _MakerStoryScreenState();
}

enum _Stage { prompt, recording, submitting, result, error }

class _MakerStoryScreenState extends State<MakerStoryScreen> {
  final FlutterTts _tts = FlutterTts();
  final AudioRecorder _recorder = AudioRecorder();
  _Stage _stage = _Stage.prompt;
  bool _ttsSpeaking = false;
  String? _textEn;
  String? _textHi;
  String? _error;
  String _lang = 'hi';

  @override
  void initState() {
    super.initState();
    _tts.awaitSpeakCompletion(true);
    _init();
  }

  @override
  void dispose() {
    _tts.stop();
    _recorder.dispose();
    super.dispose();
  }

  Future<void> _init() async {
    _lang = await ArtisanSession.language ?? 'hi';
    await _tts.setLanguage(_ttsLocale(_lang));
    setState(() => _ttsSpeaking = true);
    await _tts.speak(_promptText(_lang));
    if (mounted) setState(() => _ttsSpeaking = false);
  }

  String _ttsLocale(String lang) =>
      const {'hi': 'hi-IN', 'bn': 'bn-IN', 'ta': 'ta-IN', 'mr': 'mr-IN'}[lang] ?? 'hi-IN';

  String _promptText(String lang) => const {
        'hi': 'अपने बारे में या अपने हुनर के बारे में कुछ बोलिए। यह आपकी दुकान के पन्ने पर सबसे ऊपर दिखेगा।',
        'bn': 'নিজের সম্পর্কে বা আপনার শিল্প সম্পর্কে কিছু বলুন।',
        'ta': 'உங்களைப் பற்றி அல்லது உங்கள் கைவினைப் பற்றி பேசுங்கள்.',
        'mr': 'स्वतःबद्दल किंवा तुमच्या कलेबद्दल थोडं बोला.',
      }[lang] ??
      'अपने बारे में या अपने हुनर के बारे में कुछ बोलिए।';

  Future<void> _toggleRecording() async {
    if (_ttsSpeaking) return;
    if (_stage == _Stage.recording) {
      final path = await _recorder.stop();
      setState(() => _stage = _Stage.submitting);
      if (path != null) {
        await _submit(path);
      } else {
        setState(() => _stage = _Stage.prompt);
      }
    } else if (await _recorder.hasPermission()) {
      final dir = await getApplicationDocumentsDirectory();
      final path = '${dir.path}/maker_story_${DateTime.now().millisecondsSinceEpoch}.m4a';
      await _recorder.start(const RecordConfig(encoder: AudioEncoder.aacLc), path: path);
      setState(() => _stage = _Stage.recording);
    }
  }

  Future<void> _submit(String audioPath) async {
    try {
      final artisanId = await ArtisanSession.artisanId;
      final result = await StorefrontClient.recordMakerStory(
        artisanId: artisanId ?? '', audioPath: audioPath, lang: _lang,
      );
      if (!mounted) return;
      setState(() {
        _textEn = result['text_en'] as String?;
        _textHi = result['text_hi'] as String?;
        _stage = _Stage.result;
      });
      if (_textHi != null && _textHi!.isNotEmpty) {
        setState(() => _ttsSpeaking = true);
        await _tts.speak(_textHi!);
        if (mounted) setState(() => _ttsSpeaking = false);
      }
    } catch (e) {
      if (!mounted) return;
      setState(() { _stage = _Stage.error; _error = '$e'; });
    }
  }

  Future<void> _recordAgain() async {
    setState(() { _stage = _Stage.prompt; _textEn = null; _textHi = null; });
    setState(() => _ttsSpeaking = true);
    await _tts.speak(_promptText(_lang));
    if (mounted) setState(() => _ttsSpeaking = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF3F4F6),
      appBar: AppBar(
        backgroundColor: Colors.transparent, elevation: 0, foregroundColor: const Color(0xFF1F2937),
        title: const Text('My Story', style: TextStyle(fontWeight: FontWeight.bold)),
      ),
      body: SafeArea(child: _body()),
    );
  }

  Widget _body() {
    switch (_stage) {
      case _Stage.prompt:
      case _Stage.recording:
        return _recordView();
      case _Stage.submitting:
        return const Center(child: CircularProgressIndicator(color: _accent));
      case _Stage.result:
        return _resultView();
      case _Stage.error:
        return _errorView();
    }
  }

  Widget _recordView() {
    final recording = _stage == _Stage.recording;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.auto_stories_rounded, size: 48, color: _accent),
            const SizedBox(height: 20),
            Text(_promptText(_lang), textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 17, height: 1.5, color: Color(0xFF1F2937))),
            const SizedBox(height: 36),
            GestureDetector(
              onTap: _toggleRecording,
              child: Container(
                width: 80, height: 80,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: _ttsSpeaking ? const Color(0xFFC7C9F5) : (recording ? Colors.red : _accent),
                  boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.15), blurRadius: 12, offset: const Offset(0, 4))],
                ),
                child: Icon(recording ? Icons.stop : Icons.mic, color: Colors.white, size: 34),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              _ttsSpeaking ? 'सुनिए...' : (recording ? 'बोलिए... (टैप करें रोकने के लिए)' : 'बोलने के लिए टैप करें'),
              style: const TextStyle(color: Color(0xFF9CA3AF), fontSize: 13),
            ),
          ],
        ),
      ),
    );
  }

  Widget _resultView() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 8),
          const Text('आपकी कहानी', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Color(0xFF1F2937))),
          const SizedBox(height: 12),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: Colors.white, borderRadius: BorderRadius.circular(14),
              boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 10, offset: const Offset(0, 4))],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(_textHi ?? '', style: const TextStyle(fontSize: 15, color: Color(0xFF1F2937), height: 1.5)),
                const SizedBox(height: 10),
                const Divider(),
                const SizedBox(height: 10),
                Text(_textEn ?? '', style: const TextStyle(fontSize: 13, color: Color(0xFF6B7280), height: 1.5)),
              ],
            ),
          ),
          const SizedBox(height: 28),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () => Navigator.pop(context, true),
              style: ElevatedButton.styleFrom(
                backgroundColor: _accent, foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: const Text('सुरक्षित करें', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ),
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: _recordAgain,
              style: OutlinedButton.styleFrom(
                foregroundColor: const Color(0xFF4B5563),
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: const Text('फिर से रिकॉर्ड करें'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _errorView() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline_rounded, size: 56, color: Color(0xFF9CA3AF)),
            const SizedBox(height: 16),
            Text('सुरक्षित नहीं हो सका। ($_error)', textAlign: TextAlign.center,
                style: const TextStyle(color: Color(0xFF6B7280), fontSize: 14)),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: _recordAgain,
              style: ElevatedButton.styleFrom(backgroundColor: _accent, foregroundColor: Colors.white),
              child: const Text('फिर कोशिश करें'),
            ),
          ],
        ),
      ),
    );
  }
}
