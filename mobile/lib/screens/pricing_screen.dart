// Day 4 exit gate, on screen: photo + voice -> price band with a plain explanation,
// no cost question asked, the floor visibly refusing an underpriced suggestion, and
// the rate's date + source on screen. Comparables are shown BEFORE the model number
// (roadmap requirement) — see _ResultView below.
//
// Pricing needs Gemini + the XGBoost model, both server-side, so unlike capture
// (Day 3) there is no offline path here — a network failure shows a plain "not
// available offline yet" message rather than blocking or crashing. The draft itself
// has already been saved and queued by RecordScreen before this screen ever opens,
// so Day 3's offline guarantee is untouched by this screen failing.
//
// 0-2 spoken, attribute-only confirmations happen here for real: flutter_tts speaks
// the question (phrasing copied verbatim from pipelines/pricing/attributes.py's
// _PHRASE so the same words are used whether the confirm loop runs server-side or
// here), the artisan answers by voice, and the answer is classified server-side via
// the same primitive the Day-2 read-back gate uses. A "no" clears the field rather
// than re-asking a different guess — never fabricate a second guess.
import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import '../models/pricing_result.dart';
import '../services/pricing_client.dart';
import 'publish_screen.dart';

enum _Stage { loading, confirming, quoting, result, offline, error }

const _materialConfirmTemplate = 'मैंने सुना: सामग्री {v}। क्या यह सही है? हाँ या नहीं बोलिए।';
const _sizeConfirmTemplate = 'मैंने अंदाज़ा लगाया: यह आकार में {v} है। क्या यह सही है? हाँ या नहीं बोलिए।';
const _sizeWords = {'small': 'छोटे', 'medium': 'मध्यम', 'large': 'बड़े'};
// Copied verbatim from pipelines/voice/readback.py's hi._PHRASE['unclear'] so an
// unclear confirm answer sounds the same whether the retry happens here or in the
// original Day-2 readback gate.
const _unclearRetryPhrase = 'समझ नहीं आया। कृपया हाँ या नहीं बोलिए।';
// Matches config.yaml's readback.max_confirm_attempts — the same bound the Day-2
// readback gate uses, so a genuinely unclear answer gets one real second try
// before the field is dropped rather than silently clearing on the first mumble.
const _maxConfirmAttempts = 2;
const _accent = Color(0xFF4F46E5);

class PricingScreen extends StatefulWidget {
  final String imagePath;
  final String audioPath;
  final String clientId;
  final String lang;

  const PricingScreen({
    Key? key,
    required this.imagePath,
    required this.audioPath,
    required this.clientId,
    this.lang = 'hi',
  }) : super(key: key);

  @override
  State<PricingScreen> createState() => _PricingScreenState();
}

class _PricingScreenState extends State<PricingScreen> {
  _Stage _stage = _Stage.loading;
  String? _error;

  AttributeSuggestion? _attrs;
  String _material = '';
  String _materialSource = 'none';
  String _sizeClass = '';
  double? _sizeScore;
  Quote? _quote;

  // A definite "yes" keeps the field's value but must still stop _confirmNext()
  // from asking about it again — without these, "material source is voice"
  // stays true forever after being confirmed, re-asking the same question in an
  // infinite loop (a real bug, only surfaced once a genuine spoken "yes" landed
  // on a real device — the emulator's fake mic never produced one).
  bool _materialConfirmed = false;
  bool _sizeConfirmed = false;
  // True while the confirm question is still being spoken. On a real phone
  // (unlike the emulator's fake mic) tapping the mic before this finishes lets
  // the phone's own speaker output bleed into the recording — a real answer clip
  // came back as "क्या यी सही है? हा या नहीं बोली? यस", the tail of the question
  // plus her answer concatenated. Recording is blocked until TTS completes.
  bool _ttsSpeaking = false;

  String? _confirmingField; // "material" | "size"
  String _question = '';
  int _confirmAttempts = 0; // attempts used on the CURRENT field's question
  bool _isRecordingAnswer = false;
  bool _isSubmittingAnswer = false;

  final FlutterTts _tts = FlutterTts();
  final AudioRecorder _recorder = AudioRecorder();

  @override
  void initState() {
    super.initState();
    _tts.setLanguage('hi-IN');
    _tts.awaitSpeakCompletion(true); // so `await _tts.speak(...)` actually waits
    _start();
  }

  @override
  void dispose() {
    _tts.stop();
    _recorder.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    try {
      final attrs = await PricingClient.fetchAttributes(
        imagePath: widget.imagePath,
        audioPath: widget.audioPath,
        lang: widget.lang,
      );
      if (!mounted) return;
      setState(() {
        _attrs = attrs;
        _material = attrs.material;
        _materialSource = attrs.materialSource;
        _sizeClass = attrs.sizeClass;
        _sizeScore = attrs.sizeScore;
      });
      await _confirmNext();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _stage = _Stage.offline;
        _error = '$e';
      });
    }
  }

  // Confirms material first (only if voice found one), then size (always, since
  // vision's guess is genuinely rough) — never more than these two, never about
  // price or cost.
  Future<void> _confirmNext() async {
    if (_material.isNotEmpty && _materialSource == 'voice' && !_materialConfirmed) {
      await _askConfirm('material', _materialConfirmTemplate.replaceFirst('{v}', _material));
      return;
    }
    if (_sizeClass.isNotEmpty && !_sizeConfirmed) {
      final word = _sizeWords[_sizeClass] ?? _sizeClass;
      await _askConfirm('size', _sizeConfirmTemplate.replaceFirst('{v}', word));
      return;
    }
    await _fetchQuote();
  }

  Future<void> _askConfirm(String field, String question) async {
    setState(() {
      _confirmingField = field;
      _question = question;
      _confirmAttempts = 0;
      _stage = _Stage.confirming;
      _ttsSpeaking = true;
    });
    await _tts.speak(question);
    if (mounted) setState(() => _ttsSpeaking = false);
  }

  Future<void> _retryConfirm() async {
    setState(() {
      _question = _unclearRetryPhrase;
      _ttsSpeaking = true;
    });
    await _tts.speak(_unclearRetryPhrase);
    if (mounted) setState(() => _ttsSpeaking = false);
  }

  Future<void> _toggleAnswerRecording() async {
    if (_ttsSpeaking) return; // don't record over the question still being spoken
    if (_isRecordingAnswer) {
      final path = await _recorder.stop();
      setState(() => _isRecordingAnswer = false);
      if (path != null) await _submitAnswer(path);
    } else {
      if (await _recorder.hasPermission()) {
        final dir = await getApplicationDocumentsDirectory();
        final path = '${dir.path}/confirm_${DateTime.now().millisecondsSinceEpoch}.m4a';
        await _recorder.start(const RecordConfig(encoder: AudioEncoder.aacLc), path: path);
        setState(() => _isRecordingAnswer = true);
      }
    }
  }

  Future<void> _submitAnswer(String answerAudioPath) async {
    setState(() => _isSubmittingAnswer = true);
    bool? verdict;
    try {
      verdict = await PricingClient.classifyAnswer(audioPath: answerAudioPath, lang: widget.lang);
    } catch (_) {
      verdict = null; // network hiccup mid-confirm -> treat like "unclear", don't crash
    }

    if (verdict == null && _confirmAttempts + 1 < _maxConfirmAttempts) {
      // Genuinely unclear (not a definite "no") and a retry is still available —
      // re-ask the same question rather than silently dropping a possibly-correct
      // vision/voice reading over one noisy recording. Matches the Day-2 readback
      // gate's own max_confirm_attempts bound; a definite "no" below still clears
      // the field immediately since there's nothing ambiguous to retry.
      setState(() {
        _confirmAttempts += 1;
        _isSubmittingAnswer = false;
      });
      await _retryConfirm();
      return;
    }

    if (verdict == true) {
      // Confirmed — keep the value but mark it settled so _confirmNext() moves
      // on instead of asking the same question again.
      setState(() {
        if (_confirmingField == 'material') {
          _materialConfirmed = true;
        } else {
          _sizeConfirmed = true;
        }
      });
    } else {
      // "no", or "unclear" after exhausting retries — clear the field, never
      // guess again (matches attributes.py's suggest_attributes: a rejected
      // vision/voice reading is never reused for anything downstream).
      setState(() {
        if (_confirmingField == 'material') {
          _material = '';
          _materialSource = 'unconfirmed';
        } else {
          _sizeClass = '';
          _sizeScore = null;
        }
      });
    }
    setState(() => _isSubmittingAnswer = false);
    await _confirmNext();
  }

  Future<void> _fetchQuote() async {
    setState(() => _stage = _Stage.quoting);
    try {
      final quote = await PricingClient.getQuote(
        category: _attrs?.category ?? '',
        material: _material,
        sizeClass: _sizeClass,
        sizeScore: _sizeScore,
        region: 'unknown', // Day 5's onboarding hasn't captured her location yet
        month: DateTime.now().month,
      );
      if (!mounted) return;
      setState(() {
        _quote = quote;
        _stage = _Stage.result;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _stage = _Stage.error;
        _error = '$e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF3F4F6),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        foregroundColor: const Color(0xFF1F2937),
        title: const Text('Price Estimate', style: TextStyle(fontWeight: FontWeight.bold)),
      ),
      body: SafeArea(child: _buildBody()),
    );
  }

  Widget _buildBody() {
    switch (_stage) {
      case _Stage.loading:
        return _loadingView('फोटो और आवाज़ का विश्लेषण हो रहा है...');
      case _Stage.confirming:
        return _confirmView();
      case _Stage.quoting:
        return _loadingView('कीमत का अनुमान लगाया जा रहा है...');
      case _Stage.result:
        return _ResultView(
          quote: _quote!,
          category: _attrs?.category ?? '',
          material: _material,
          sizeClass: _sizeClass,
          clientId: widget.clientId,
          titleEn: _attrs?.titleEn ?? '',
          titleHi: _attrs?.titleHi ?? '',
          descriptionEn: _attrs?.descriptionEn ?? '',
          descriptionHi: _attrs?.descriptionHi ?? '',
          lang: widget.lang,
        );
      case _Stage.offline:
        return _messageView(
          icon: Icons.wifi_off_rounded,
          title: 'अभी उपलब्ध नहीं',
          body: 'इंटरनेट के बिना कीमत का अनुमान नहीं मिल सकता। ड्राफ्ट सुरक्षित है और सिंक होने पर कीमत दिखेगी।\n\n'
              '(No internet — price estimate isn\'t available offline. Your draft is saved and queued; the estimate will be ready once you\'re online.)',
        );
      case _Stage.error:
        return _messageView(
          icon: Icons.error_outline_rounded,
          title: 'कुछ गलत हुआ',
          body: 'कीमत का अनुमान नहीं मिल सका। ($_error)',
        );
    }
  }

  Widget _loadingView(String text) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const CircularProgressIndicator(color: _accent),
          const SizedBox(height: 20),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 32),
            child: Text(text, textAlign: TextAlign.center, style: const TextStyle(color: Color(0xFF6B7280), fontSize: 15)),
          ),
        ],
      ),
    );
  }

  Widget _messageView({required IconData icon, required String title, required String body}) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 56, color: const Color(0xFF9CA3AF)),
            const SizedBox(height: 20),
            Text(title, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Color(0xFF374151))),
            const SizedBox(height: 8),
            Text(body, textAlign: TextAlign.center, style: const TextStyle(color: Color(0xFF6B7280), fontSize: 14, height: 1.5)),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => Navigator.of(context).popUntil((r) => r.isFirst),
              style: ElevatedButton.styleFrom(backgroundColor: _accent, foregroundColor: Colors.white),
              child: const Text('Back to Home'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _confirmView() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.record_voice_over_rounded, size: 48, color: _accent),
            const SizedBox(height: 20),
            Text(_question, textAlign: TextAlign.center, style: const TextStyle(fontSize: 17, height: 1.5, color: Color(0xFF1F2937))),
            const SizedBox(height: 36),
            if (_isSubmittingAnswer)
              const CircularProgressIndicator(color: _accent)
            else
              GestureDetector(
                onTap: _toggleAnswerRecording,
                child: Container(
                  width: 72,
                  height: 72,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: _ttsSpeaking
                        ? const Color(0xFFC7C9F5)
                        : (_isRecordingAnswer ? Colors.red : _accent),
                    boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.15), blurRadius: 12, offset: const Offset(0, 4))],
                  ),
                  child: Icon(_isRecordingAnswer ? Icons.stop : Icons.mic, color: Colors.white, size: 32),
                ),
              ),
            const SizedBox(height: 16),
            Text(
              _ttsSpeaking
                  ? 'सुनिए...'
                  : (_isRecordingAnswer ? 'बोलिए... (टैप करें रोकने के लिए)' : 'हाँ या नहीं बोलने के लिए टैप करें'),
              style: const TextStyle(color: Color(0xFF9CA3AF), fontSize: 13),
            ),
          ],
        ),
      ),
    );
  }
}

class _ResultView extends StatelessWidget {
  final Quote quote;
  final String category;
  final String material;
  final String sizeClass;
  final String clientId;
  final String titleEn;
  final String titleHi;
  final String descriptionEn;
  final String descriptionHi;
  final String lang;

  const _ResultView({
    required this.quote,
    required this.category,
    required this.material,
    required this.sizeClass,
    required this.clientId,
    required this.titleEn,
    required this.titleHi,
    required this.descriptionEn,
    required this.descriptionHi,
    required this.lang,
  });

  String _fmt(double v) => '₹${v.round()}';

  @override
  Widget build(BuildContext context) {
    final band = quote.band;
    final floor = quote.floor;
    final suggested = quote.suggested;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('$category${material.isNotEmpty ? " · $material" : ""}${sizeClass.isNotEmpty ? " · $sizeClass" : ""}',
              style: const TextStyle(fontSize: 13, color: Color(0xFF6B7280), fontWeight: FontWeight.w500)),
          const SizedBox(height: 16),

          // Comparables shown BEFORE the model number (roadmap requirement).
          if (band.comparables.isNotEmpty) ...[
            const Text('Similar listings', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Color(0xFF1F2937))),
            const SizedBox(height: 8),
            _card(
              child: Column(
                children: band.comparables
                    .map((c) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 6),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Expanded(
                                child: Text('${c.material} · ${c.size} · ${c.region}',
                                    style: const TextStyle(fontSize: 13, color: Color(0xFF4B5563))),
                              ),
                              Text(_fmt(c.priceInr), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                            ],
                          ),
                        ))
                    .toList(),
              ),
            ),
            const SizedBox(height: 20),
          ],

          const Text('Price band', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Color(0xFF1F2937))),
          const SizedBox(height: 8),
          _card(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('${_fmt(band.bandLowInr)} – ${_fmt(band.bandHighInr)}',
                        style: const TextStyle(fontSize: 15, color: Color(0xFF4B5563))),
                    if (band.confidence == 'low')
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(color: const Color(0xFFFEF3C7), borderRadius: BorderRadius.circular(6)),
                        child: const Text('Low confidence', style: TextStyle(fontSize: 11, color: Color(0xFF92400E), fontWeight: FontWeight.w600)),
                      ),
                  ],
                ),
                if (band.confidence == 'low' && band.confidenceReason.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(_plainReason(band.confidenceReason), style: const TextStyle(fontSize: 12, color: Color(0xFF9CA3AF))),
                ],
                if (band.seasonalMultiplier != 1.0) ...[
                  const SizedBox(height: 6),
                  Text('Seasonal adjustment: ×${band.seasonalMultiplier.toStringAsFixed(2)}',
                      style: const TextStyle(fontSize: 12, color: Color(0xFF4B5563))),
                ],
              ],
            ),
          ),
          const SizedBox(height: 20),

          const Text('Suggested price', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Color(0xFF1F2937))),
          const SizedBox(height: 8),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: suggested.basedOn == 'floor' ? const Color(0xFFFFFBEB) : _accent,
              borderRadius: BorderRadius.circular(16),
              border: suggested.basedOn == 'floor' ? Border.all(color: const Color(0xFFF59E0B)) : null,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _fmt(suggested.valueInr),
                  style: TextStyle(
                    fontSize: 32,
                    fontWeight: FontWeight.bold,
                    color: suggested.basedOn == 'floor' ? const Color(0xFF92400E) : Colors.white,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  suggested.note,
                  style: TextStyle(
                    fontSize: 13,
                    color: suggested.basedOn == 'floor' ? const Color(0xFF92400E) : Colors.white.withOpacity(0.9),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          const Text('Fair-price floor', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Color(0xFF1F2937))),
          const SizedBox(height: 8),
          _card(
            child: floor.known
                ? Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _row('Material cost', _fmt(floor.materialCost.costInr)),
                      _row('Your time (${floor.labourHours.toStringAsFixed(1)}h)', _fmt(floor.labourCostInr)),
                      const Divider(height: 20),
                      _row('Floor', _fmt(floor.floorInr), bold: true),
                      const SizedBox(height: 10),
                      Text(
                        'Rate: ₹${floor.materialCost.rateInrPerKg.toStringAsFixed(0)}/kg · '
                        'dated ${floor.materialCost.rateDate} · ${floor.materialCost.rateSource}',
                        style: const TextStyle(fontSize: 11, color: Color(0xFF9CA3AF)),
                      ),
                      const SizedBox(height: 4),
                      const Text(
                        'This is a floor, not a rule — you can list below it if you choose.',
                        style: TextStyle(fontSize: 11, color: Color(0xFF9CA3AF), fontStyle: FontStyle.italic),
                      ),
                    ],
                  )
                : const Text('Floor unknown — material or size wasn\'t confirmed.',
                    style: TextStyle(fontSize: 13, color: Color(0xFF6B7280))),
          ),
          const SizedBox(height: 20),

          const Text('Why this price', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Color(0xFF1F2937))),
          const SizedBox(height: 8),
          _card(
            child: Column(
              children: [
                _bar('Material', quote.explain.materialInr),
                _bar('Demand (category/size/season)', quote.explain.demandInr),
                _bar('Region', quote.explain.regionInr),
              ],
            ),
          ),
          const SizedBox(height: 24),

          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () => Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => PublishScreen(
                    clientId: clientId,
                    category: category,
                    material: material,
                    sizeClass: sizeClass,
                    titleEn: titleEn,
                    titleHi: titleHi,
                    descriptionEn: descriptionEn,
                    descriptionHi: descriptionHi,
                    priceInr: suggested.valueInr,
                    bandLowInr: band.bandLowInr,
                    bandHighInr: band.bandHighInr,
                    floorInr: quote.floor.known ? quote.floor.floorInr : null,
                    lang: lang,
                  ),
                ),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF16A34A),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: const Text('List for sale', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ),
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: () => Navigator.of(context).popUntil((r) => r.isFirst),
              style: OutlinedButton.styleFrom(
                foregroundColor: const Color(0xFF4B5563),
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: const Text('Not now'),
            ),
          ),
          const SizedBox(height: 12),
        ],
      ),
    );
  }

  String _plainReason(String reason) {
    if (reason.contains('unseen')) {
      return 'This exact combination hasn\'t been seen before, so the range is wider than usual.';
    }
    return reason;
  }

  Widget _row(String label, String value, {bool bold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(fontSize: 13, color: const Color(0xFF4B5563), fontWeight: bold ? FontWeight.bold : FontWeight.normal)),
          Text(value, style: TextStyle(fontSize: 13, fontWeight: bold ? FontWeight.bold : FontWeight.w500)),
        ],
      ),
    );
  }

  Widget _bar(String label, double value) {
    final isPositive = value >= 0;
    final width = (value.abs() / 20).clamp(4.0, 120.0);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          SizedBox(width: 150, child: Text(label, style: const TextStyle(fontSize: 12, color: Color(0xFF6B7280)))),
          Expanded(
            child: Align(
              alignment: isPositive ? Alignment.centerLeft : Alignment.centerRight,
              child: Container(
                height: 10,
                width: width,
                decoration: BoxDecoration(
                  color: isPositive ? _accent : const Color(0xFFF59E0B),
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          SizedBox(
            width: 50,
            child: Text('${isPositive ? '+' : ''}₹${value.round()}',
                textAlign: TextAlign.right, style: const TextStyle(fontSize: 11, color: Color(0xFF9CA3AF))),
          ),
        ],
      ),
    );
  }

  Widget _card({required Widget child}) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 10, offset: const Offset(0, 4))],
      ),
      child: child,
    );
  }
}
