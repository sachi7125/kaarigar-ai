// Screen 5 · SOMEBODY WANTS TO BUY IT (wireframe): fixed fields — price,
// quantity, date — nothing to translate to act on it. "Two buttons. A number
// she can read. Nothing else." Accept/decline work by voice (same yes/no
// classifier the Day-4 attribute confirm loop and Day-2 readback gate use)
// with the two on-screen buttons as the always-available fallback. (Day 5)
import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import '../services/artisan_session.dart';
import '../services/offers_client.dart';
import '../services/pricing_client.dart';

const _accent = Color(0xFF4F46E5);
// Copied verbatim from pipelines/voice/readback.py's hi._PHRASE['unclear'] — same
// wording as PricingScreen's retry so an unclear answer sounds consistent app-wide.
const _unclearRetryPhrase = 'समझ नहीं आया। कृपया हाँ या नहीं बोलिए।';

class OffersScreen extends StatefulWidget {
  const OffersScreen({Key? key}) : super(key: key);

  @override
  State<OffersScreen> createState() => _OffersScreenState();
}

class _OffersScreenState extends State<OffersScreen> {
  final FlutterTts _tts = FlutterTts();
  final AudioRecorder _recorder = AudioRecorder();
  List<Map<String, dynamic>> _offers = [];
  bool _loading = true;
  String? _error;
  int? _busyOfferId; // offer currently being voice-answered or acted on
  bool _isRecording = false;
  // Guards against the phone's own speaker bleeding into the mic recording if
  // she taps the mic before the spoken offer/prompt finishes — see the same
  // fix and its cause in pricing_screen.dart.
  bool _ttsSpeaking = false;

  @override
  void initState() {
    super.initState();
    _tts.setLanguage('hi-IN');
    _tts.awaitSpeakCompletion(true);
    _load();
  }

  @override
  void dispose() {
    _tts.stop();
    _recorder.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final artisanId = await ArtisanSession.artisanId;
      final offers = await OffersClient.listPending(artisanId ?? '');
      if (!mounted) return;
      setState(() { _offers = offers; _loading = false; });
    } catch (e) {
      if (!mounted) return;
      setState(() { _loading = false; _error = '$e'; });
    }
  }

  Future<void> _speakOffer(Map<String, dynamic> offer) async {
    final price = (offer['price_inr'] as num).round();
    final qty = offer['quantity'] as int;
    final returning = offer['is_returning_buyer'] == true;
    final base = qty > 1
        ? '$qty चीज़ों के लिए $price रुपये की पेशकश।'
        : '$price रुपये की पेशकश।';
    // Returning-buyer flag spoken with the offer (roadmap) — a fact about
    // the buyer, not a recommendation; the accept/decline decision stays hers.
    final returningNote = returning ? ' यह खरीदार पहले भी आपसे खरीद चुका है।' : '';
    final text = '$base$returningNote स्वीकार करने के लिए हाँ बोलिए, नहीं तो नहीं बोलिए।';
    setState(() => _ttsSpeaking = true);
    await _tts.speak(text);
    if (mounted) setState(() => _ttsSpeaking = false);
  }

  Future<void> _toggleVoiceAnswer(Map<String, dynamic> offer) async {
    if (_ttsSpeaking) return; // don't record over the offer/prompt still being spoken
    final offerId = offer['id'] as int;
    if (_isRecording && _busyOfferId == offerId) {
      final path = await _recorder.stop();
      setState(() => _isRecording = false);
      if (path != null) await _classifyAndAct(offerId, path);
      return;
    }
    if (await _recorder.hasPermission()) {
      final dir = await getApplicationDocumentsDirectory();
      final path = '${dir.path}/offer_answer_${DateTime.now().millisecondsSinceEpoch}.m4a';
      await _recorder.start(const RecordConfig(encoder: AudioEncoder.aacLc), path: path);
      setState(() { _isRecording = true; _busyOfferId = offerId; });
    }
  }

  Future<void> _classifyAndAct(int offerId, String audioPath) async {
    setState(() => _busyOfferId = offerId);
    bool? verdict;
    try {
      verdict = await PricingClient.classifyAnswer(audioPath: audioPath, lang: 'hi');
    } catch (_) {
      verdict = null;
    }
    if (verdict == true) {
      await _accept(offerId);
    } else if (verdict == false) {
      await _decline(offerId);
    } else {
      // unclear — never guess; speak the same retry prompt the readback gate and
      // PricingScreen use, then let her retap the mic and speak again.
      setState(() { _busyOfferId = null; _ttsSpeaking = true; });
      await _tts.speak(_unclearRetryPhrase);
      if (mounted) setState(() => _ttsSpeaking = false);
    }
  }

  Future<void> _accept(int offerId) async {
    setState(() => _busyOfferId = offerId);
    try {
      final result = await OffersClient.accept(offerId);
      if (!mounted) return;
      await _tts.speak('स्वीकार कर लिया गया।');
      await showDialog(
        context: context,
        builder: (_) => AlertDialog(
          title: const Text('Accepted'),
          content: Text('Buyer: ${result['buyer_name']}\nContact: ${result['buyer_contact']}'),
          actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('OK'))],
        ),
      );
      await _load();
    } catch (e) {
      if (!mounted) return;
      setState(() => _busyOfferId = null);
      await _tts.speak('यह अब उपलब्ध नहीं है।');
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('यह अब उपलब्ध नहीं है — स्टॉक खत्म हो गया।')),
      );
      await _load(); // stock/offer state changed under us — refresh
    }
  }

  Future<void> _decline(int offerId) async {
    setState(() => _busyOfferId = offerId);
    try {
      await OffersClient.decline(offerId);
      await _load();
    } catch (e) {
      if (!mounted) return;
      setState(() => _busyOfferId = null);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('कुछ गलत हुआ — फिर कोशिश करें।')),
      );
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
        title: const Text('Offers', style: TextStyle(fontWeight: FontWeight.bold)),
      ),
      body: SafeArea(child: _body()),
    );
  }

  Widget _body() {
    if (_loading) return const Center(child: CircularProgressIndicator(color: _accent));
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text('कोई पेशकश लोड नहीं हो सकी। ($_error)', textAlign: TextAlign.center,
              style: const TextStyle(color: Color(0xFF6B7280))),
        ),
      );
    }
    if (_offers.isEmpty) {
      return const Center(
        child: Text('अभी कोई पेशकश नहीं है।', style: TextStyle(color: Color(0xFF6B7280), fontSize: 16)),
      );
    }
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _offers.length,
        itemBuilder: (context, i) => _offerCard(_offers[i]),
      ),
    );
  }

  Widget _offerCard(Map<String, dynamic> offer) {
    final offerId = offer['id'] as int;
    final price = (offer['price_inr'] as num).round();
    final qty = offer['quantity'] as int;
    final busy = _busyOfferId == offerId;
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 10, offset: const Offset(0, 4))],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(offer['listing_title'] ?? '',
                    style: const TextStyle(fontSize: 13, color: Color(0xFF6B7280))),
              ),
              if (offer['is_returning_buyer'] == true)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(color: const Color(0xFFD1FAE5), borderRadius: BorderRadius.circular(6)),
                  child: const Text('दोबारा खरीदार',
                      style: TextStyle(fontSize: 11, color: Color(0xFF065F46), fontWeight: FontWeight.w600)),
                ),
            ],
          ),
          const SizedBox(height: 6),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text('₹$price', style: const TextStyle(fontSize: 30, fontWeight: FontWeight.bold, color: _accent)),
              if (qty > 1) ...[
                const SizedBox(width: 10),
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text('× $qty', style: const TextStyle(fontSize: 16, color: Color(0xFF6B7280))),
                ),
              ],
              const Spacer(),
              IconButton(
                icon: const Icon(Icons.volume_up_rounded, color: _accent),
                onPressed: () => _speakOffer(offer),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (busy)
            const Center(child: CircularProgressIndicator(color: _accent))
          else
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _decline(offerId),
                    icon: const Icon(Icons.close_rounded, color: Colors.red),
                    label: const Text('Decline', style: TextStyle(color: Colors.red)),
                    style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: Colors.red),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _accept(offerId),
                    icon: const Icon(Icons.check_rounded),
                    label: const Text('Accept'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF16A34A),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                GestureDetector(
                  onTap: () => _toggleVoiceAnswer(offer),
                  child: CircleAvatar(
                    radius: 22,
                    backgroundColor: _ttsSpeaking
                        ? const Color(0xFFE5E7EB)
                        : (_isRecording && _busyOfferId == offerId ? Colors.red : const Color(0xFFF3F4F6)),
                    child: Icon(
                      _isRecording && _busyOfferId == offerId ? Icons.stop : Icons.mic,
                      color: _ttsSpeaking
                          ? const Color(0xFF9CA3AF)
                          : (_isRecording && _busyOfferId == offerId ? Colors.white : _accent),
                    ),
                  ),
                ),
              ],
            ),
        ],
      ),
    );
  }
}
