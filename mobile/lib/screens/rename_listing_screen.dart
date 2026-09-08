// Rename a listing's name — before publish (from PublishScreen) or after
// (from DashboardScreen). Raised by the user directly ("allow user to edit
// name of the listing before listing and also after"), with an explicit
// choice on how: a big mic button (speak the new name, transcribed the same
// way material/maker-story are — consistent with the rest of the app, no
// keyboard anywhere else) PLUS a plain text field as an alternative, since
// the user asked for both rather than picking one. (Day 6)
import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import '../services/listings_client.dart';

const _accent = Color(0xFF4F46E5);

class RenameListingScreen extends StatefulWidget {
  final String initialTitleEn;
  final String initialTitleHi;
  final String lang;
  // If set, this screen saves directly to that published listing. If null,
  // it just returns the chosen {title_en, title_hi} for the caller (the
  // pre-publish flow) to hold locally until the actual publish call.
  final String? listingId;

  const RenameListingScreen({
    Key? key,
    required this.initialTitleEn,
    required this.initialTitleHi,
    this.lang = 'hi',
    this.listingId,
  }) : super(key: key);

  @override
  State<RenameListingScreen> createState() => _RenameListingScreenState();
}

class _RenameListingScreenState extends State<RenameListingScreen> {
  final FlutterTts _tts = FlutterTts();
  final AudioRecorder _recorder = AudioRecorder();
  final TextEditingController _textController = TextEditingController();
  late String _titleEn;
  late String _titleHi;
  bool _isRecording = false;
  bool _isTranscribing = false;
  bool _isSaving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _titleEn = widget.initialTitleEn;
    _titleHi = widget.initialTitleHi;
    _textController.text = _titleHi.isNotEmpty ? _titleHi : _titleEn;
    _tts.setLanguage('hi-IN');
  }

  @override
  void dispose() {
    _tts.stop();
    _recorder.dispose();
    _textController.dispose();
    super.dispose();
  }

  Future<void> _toggleRecording() async {
    if (_isRecording) {
      final path = await _recorder.stop();
      setState(() { _isRecording = false; _isTranscribing = true; });
      if (path != null) await _submitVoice(path);
      setState(() => _isTranscribing = false);
    } else if (await _recorder.hasPermission()) {
      final dir = await getApplicationDocumentsDirectory();
      final path = '${dir.path}/rename_${DateTime.now().millisecondsSinceEpoch}.m4a';
      await _recorder.start(const RecordConfig(encoder: AudioEncoder.aacLc), path: path);
      setState(() => _isRecording = true);
    }
  }

  Future<void> _submitVoice(String audioPath) async {
    try {
      final result = await ListingsClient.renameByVoice(audioPath: audioPath, lang: widget.lang);
      final newEn = result['title_en'] as String? ?? _titleEn;
      final newHi = result['title_hi'] as String? ?? _titleHi;
      if (!mounted) return;
      setState(() {
        _titleEn = newEn;
        _titleHi = newHi.isNotEmpty ? newHi : newEn;
        _textController.text = _titleHi;
      });
      await _tts.speak(_titleHi);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = '$e');
    }
  }

  Future<void> _save() async {
    // Whatever's in the text field wins — it's the last thing she touched,
    // whether that came from typing or from the voice result pre-filling it.
    final typed = _textController.text.trim();
    final titleHi = typed.isNotEmpty ? typed : _titleHi;
    final titleEn = typed.isNotEmpty ? typed : _titleEn;
    if (widget.listingId == null) {
      Navigator.pop(context, {'title_en': titleEn, 'title_hi': titleHi});
      return;
    }
    setState(() { _isSaving = true; _error = null; });
    try {
      await ListingsClient.renameListing(
        listingId: widget.listingId!, titleEn: titleEn, titleHi: titleHi);
      if (!mounted) return;
      Navigator.pop(context, {'title_en': titleEn, 'title_hi': titleHi});
    } catch (e) {
      if (!mounted) return;
      setState(() { _isSaving = false; _error = '$e'; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF3F4F6),
      appBar: AppBar(
        backgroundColor: Colors.transparent, elevation: 0, foregroundColor: const Color(0xFF1F2937),
        title: const Text('Rename', style: TextStyle(fontWeight: FontWeight.bold)),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 12),
              const Text('नाम बदलें', textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600, color: Color(0xFF1F2937))),
              const SizedBox(height: 28),
              Center(
                child: GestureDetector(
                  onTap: _isTranscribing ? null : _toggleRecording,
                  child: Container(
                    width: 80, height: 80,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: _isRecording ? Colors.red : _accent,
                      boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.15), blurRadius: 12, offset: const Offset(0, 4))],
                    ),
                    child: _isTranscribing
                        ? const Padding(
                            padding: EdgeInsets.all(24),
                            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 3),
                          )
                        : Icon(_isRecording ? Icons.stop : Icons.mic, color: Colors.white, size: 34),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Center(
                child: Text(
                  _isTranscribing ? 'सुना जा रहा है...' : (_isRecording ? 'बोलिए... (टैप करें रोकने के लिए)' : 'नया नाम बोलने के लिए टैप करें'),
                  style: const TextStyle(color: Color(0xFF9CA3AF), fontSize: 13),
                ),
              ),
              const SizedBox(height: 32),
              const Row(children: [
                Expanded(child: Divider()),
                Padding(padding: EdgeInsets.symmetric(horizontal: 12), child: Text('या', style: TextStyle(color: Color(0xFF9CA3AF)))),
                Expanded(child: Divider()),
              ]),
              const SizedBox(height: 16),
              const Text('टाइप करें', style: TextStyle(fontSize: 13, color: Color(0xFF374151), fontWeight: FontWeight.w500)),
              const SizedBox(height: 8),
              TextField(
                controller: _textController,
                decoration: InputDecoration(
                  filled: true, fillColor: Colors.white,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                ),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(_error!, style: const TextStyle(color: Colors.red, fontSize: 13)),
              ],
              const Spacer(),
              ElevatedButton(
                onPressed: _isSaving ? null : _save,
                style: ElevatedButton.styleFrom(
                  backgroundColor: _accent, foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                ),
                child: _isSaving
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                    : const Text('सुरक्षित करें', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
