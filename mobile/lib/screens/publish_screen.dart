// Publish step, reached from PricingScreen's result view. Not in the 6-screen
// wireframe set directly, but built to the same three rules: nothing essential
// text-only, every text block has a speaker, no screen offers more than two
// real choices — so stock type is exactly two tiles, and verification (if
// still deferred) is a single OTP detour before publishing rather than a
// blocking step earlier in the flow (decision: deferred verification). (Day 5)
//
// Price confirm/edit step (Day 6): PricingScreen's number is a suggestion, not
// a quote — the wireframe itself says the floor "warns without seizing her
// decision" and the band is shown as "never a single false-precision number".
// Until this step existed, "List for sale" published at the exact suggested
// number with no way to change it, which quietly contradicted that. Prefilled
// with the suggestion so doing nothing still works; going below the floor (if
// known) shows a plain warning and nothing more — never blocks, matching
// floor.py's own design.
import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import '../services/artisan_session.dart';
import '../services/listings_client.dart';
import '../widgets/numeric_keypad.dart';
import 'home_screen.dart';
import 'onboarding/otp_screen.dart';
import 'rename_listing_screen.dart';

const _accent = Color(0xFF4F46E5);

class PublishScreen extends StatefulWidget {
  final String clientId;
  final String category;
  final String material;
  final String sizeClass;
  final String titleEn;
  final String titleHi;
  final String descriptionEn;
  final String descriptionHi;
  final double priceInr;
  final double? bandLowInr;
  final double? bandHighInr;
  final double? floorInr; // null when the floor itself is unknown (material/size unconfirmed)
  final String lang;

  const PublishScreen({
    Key? key,
    required this.clientId,
    required this.category,
    required this.material,
    required this.sizeClass,
    required this.titleEn,
    required this.titleHi,
    required this.descriptionEn,
    required this.descriptionHi,
    required this.priceInr,
    this.bandLowInr,
    this.bandHighInr,
    this.floorInr,
    this.lang = 'hi',
  }) : super(key: key);

  @override
  State<PublishScreen> createState() => _PublishScreenState();
}

// priceUnit (Day 7, roadmap "per-piece vs per-set → ask"): after a batch
// count, is the price she set for each piece or for all of them together?
enum _Step { checkingVerification, priceConfirm, stockType, batchCount, priceUnit, publishing, done, error }

class _PublishScreenState extends State<PublishScreen> {
  final FlutterTts _tts = FlutterTts();
  _Step _step = _Step.checkingVerification;
  String? _stockType;
  String _countDigits = '';
  int _batchCount = 1;
  late String _priceDigits;
  late String _titleEn;
  late String _titleHi;
  String? _error;
  String? _listingUrl;

  double get _finalPrice => double.tryParse(_priceDigits) ?? widget.priceInr;
  bool get _belowFloor => widget.floorInr != null && _priceDigits.isNotEmpty && _finalPrice < widget.floorInr!;

  @override
  void initState() {
    super.initState();
    _tts.setLanguage('hi-IN');
    _priceDigits = widget.priceInr.round().toString();
    _titleEn = widget.titleEn;
    _titleHi = widget.titleHi;
    _checkVerification();
  }

  Future<void> _editName() async {
    final result = await Navigator.push<Map<String, dynamic>>(
      context,
      MaterialPageRoute(builder: (_) => RenameListingScreen(
        initialTitleEn: _titleEn, initialTitleHi: _titleHi, lang: widget.lang,
      )),
    );
    if (result != null && mounted) {
      setState(() {
        _titleEn = result['title_en'] as String;
        _titleHi = result['title_hi'] as String;
      });
    }
  }

  @override
  void dispose() {
    _tts.stop();
    super.dispose();
  }

  Future<void> _checkVerification() async {
    final verified = await ArtisanSession.isVerified;
    if (verified) {
      await _enterPriceConfirm();
      return;
    }
    final phone = await ArtisanSession.phone;
    final language = await ArtisanSession.language ?? 'hi';
    if (!mounted) return;
    final result = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => OtpScreen(phone: phone ?? '', language: language)),
    );
    if (!mounted) return;
    if (result == true) {
      await _enterPriceConfirm();
    } else {
      Navigator.pop(context); // she backed out of verification — don't force it
    }
  }

  Future<void> _enterPriceConfirm() async {
    setState(() => _step = _Step.priceConfirm);
    final rounded = widget.priceInr.round();
    await _tts.speak('सुझाई गई कीमत $rounded रुपये है। बदलने के लिए नंबर दबाएं, या आगे बढ़ने के लिए नीचे दबाएं।');
  }

  Future<void> _chooseStockType(String type) async {
    setState(() => _stockType = type);
    if (type == 'unique') {
      await _publish(1);
    } else {
      setState(() => _step = _Step.batchCount);
    }
  }

  Future<void> _enterPriceUnit(int count) async {
    setState(() { _batchCount = count; _step = _Step.priceUnit; });
    await _tts.speak('${_finalPrice.round()} रुपये — यह एक पीस की कीमत है, या सभी $count की एक साथ?');
  }

  Future<void> _publish(int totalCount, {String priceUnit = 'piece'}) async {
    setState(() { _step = _Step.publishing; _error = null; });
    try {
      final artisanId = await ArtisanSession.artisanId;
      final result = await ListingsClient.publish(
        artisanId: artisanId ?? '',
        clientId: widget.clientId,
        category: widget.category,
        material: widget.material,
        sizeClass: widget.sizeClass,
        titleEn: _titleEn,
        titleHi: _titleHi,
        descriptionEn: widget.descriptionEn,
        descriptionHi: widget.descriptionHi,
        priceInr: _finalPrice,
        bandLowInr: widget.bandLowInr,
        bandHighInr: widget.bandHighInr,
        stockType: _stockType ?? 'unique',
        totalCount: totalCount,
        priceUnit: priceUnit,
      );
      if (!mounted) return;
      setState(() {
        _listingUrl = result['url'] as String?;
        _step = _Step.done;
      });
      await _tts.setLanguage('hi-IN');
      await _tts.speak('आपकी लिस्टिंग तैयार है।');
    } catch (e) {
      if (!mounted) return;
      setState(() { _step = _Step.error; _error = '$e'; });
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
        title: const Text('List for sale', style: TextStyle(fontWeight: FontWeight.bold)),
      ),
      body: SafeArea(child: _body()),
    );
  }

  Widget _body() {
    switch (_step) {
      case _Step.checkingVerification:
        return const Center(child: CircularProgressIndicator(color: _accent));
      case _Step.priceConfirm:
        return _priceConfirmView();
      case _Step.stockType:
        return _stockTypeView();
      case _Step.batchCount:
        return _batchCountView();
      case _Step.priceUnit:
        return _priceUnitView();
      case _Step.publishing:
        return const Center(child: CircularProgressIndicator(color: _accent));
      case _Step.done:
        return _doneView();
      case _Step.error:
        return _errorView();
    }
  }

  Widget _priceConfirmView() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
              child: Row(
                children: [
                  Expanded(
                    child: Text(_titleHi.isNotEmpty ? _titleHi : _titleEn,
                        style: const TextStyle(fontSize: 14, color: Color(0xFF1F2937), fontWeight: FontWeight.w500),
                        maxLines: 1, overflow: TextOverflow.ellipsis),
                  ),
                  TextButton(onPressed: _editName, child: const Text('नाम बदलें')),
                ],
              ),
            ),
            const SizedBox(height: 20),
            const Text('आप किस कीमत पर बेचना चाहती हैं?',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600, color: Color(0xFF1F2937))),
            const SizedBox(height: 6),
            const Text('सुझाई गई कीमत पहले से भरी है — चाहें तो बदल दीजिए',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 13, color: Color(0xFF9CA3AF))),
            const SizedBox(height: 20),
            Text(_priceDigits.isEmpty ? '—' : '₹$_priceDigits',
                style: const TextStyle(fontSize: 36, fontWeight: FontWeight.bold, color: _accent)),
            if (_belowFloor) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFFBEB),
                  border: Border.all(color: const Color(0xFFF59E0B)),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  'यह सामग्री और समय की लागत (₹${widget.floorInr!.round()}) से कम है — फिर भी आप इस कीमत पर बेच सकती हैं',
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 12, color: Color(0xFF92400E)),
                ),
              ),
            ],
            const SizedBox(height: 20),
            NumericKeypad(value: _priceDigits, maxLength: 7, onChanged: (v) => setState(() => _priceDigits = v)),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _priceDigits.isNotEmpty && int.parse(_priceDigits) > 0
                    ? () => setState(() => _step = _Step.stockType)
                    : null,
                style: ElevatedButton.styleFrom(
                  backgroundColor: _accent, foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                ),
                child: const Text('आगे बढ़ें', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _stockTypeView() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('क्या यह एक ही चीज़ है, या आपके पास कई हैं?',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600, color: Color(0xFF1F2937))),
            const SizedBox(height: 32),
            Row(
              children: [
                Expanded(child: _tile('एक ही', Icons.looks_one_rounded, () => _chooseStockType('unique'))),
                const SizedBox(width: 16),
                Expanded(child: _tile('कई हैं', Icons.inventory_2_rounded, () => _chooseStockType('batch'))),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _tile(String label, IconData icon, VoidCallback onTap) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(20),
      elevation: 2,
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onTap,
        child: Container(
          height: 140,
          alignment: Alignment.center,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 40, color: _accent),
              const SizedBox(height: 12),
              Text(label, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Color(0xFF1F2937))),
            ],
          ),
        ),
      ),
    );
  }

  Widget _batchCountView() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('कितने हैं?', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600, color: Color(0xFF1F2937))),
            const SizedBox(height: 20),
            Text(_countDigits.isEmpty ? '—' : _countDigits,
                style: const TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: _accent)),
            const SizedBox(height: 20),
            NumericKeypad(value: _countDigits, maxLength: 3, onChanged: (v) => setState(() => _countDigits = v)),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _countDigits.isNotEmpty && int.parse(_countDigits) > 0
                    ? () => _enterPriceUnit(int.parse(_countDigits))
                    : null,
                style: ElevatedButton.styleFrom(
                  backgroundColor: _accent, foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                ),
                child: const Text('List for sale', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _priceUnitView() {
    final price = _finalPrice.round();
    // The floor is per piece; for a set the comparison is against all of them.
    final setFloor = widget.floorInr == null ? null : widget.floorInr! * _batchCount;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('₹$price किसकी कीमत है?',
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600, color: Color(0xFF1F2937))),
            const SizedBox(height: 32),
            Row(
              children: [
                Expanded(child: _tile('हर एक पीस का', Icons.looks_one_rounded,
                    () => _publish(_batchCount, priceUnit: 'piece'))),
                const SizedBox(width: 16),
                Expanded(child: _tile('सभी $_batchCount का', Icons.inventory_2_rounded,
                    () => _publish(_batchCount, priceUnit: 'set'))),
              ],
            ),
            if (setFloor != null && _finalPrice < setFloor) ...[
              const SizedBox(height: 16),
              Text(
                'अगर ₹$price सभी $_batchCount का है, तो यह उनकी लागत (लगभग ₹${setFloor.round()}) से कम है',
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 12, color: Color(0xFF92400E)),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _doneView() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.check_circle_rounded, size: 64, color: Color(0xFF16A34A)),
            const SizedBox(height: 20),
            const Text('लिस्टिंग तैयार है!', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Color(0xFF1F2937))),
            const SizedBox(height: 12),
            if (_listingUrl != null)
              Text(_listingUrl!, style: const TextStyle(fontSize: 14, color: Color(0xFF6B7280))),
            const SizedBox(height: 28),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () => Navigator.of(context).pushAndRemoveUntil(
                  MaterialPageRoute(builder: (_) => const HomeScreen()), (r) => false,
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: _accent, foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: const Text('Back to Home', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ),
          ],
        ),
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
            Text('लिस्ट नहीं हो सका। ($_error)', textAlign: TextAlign.center,
                style: const TextStyle(color: Color(0xFF6B7280), fontSize: 14)),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: () => setState(() => _step = _Step.stockType),
              style: ElevatedButton.styleFrom(backgroundColor: _accent, foregroundColor: Colors.white),
              child: const Text('फिर कोशिश करें'),
            ),
          ],
        ),
      ),
    );
  }
}
