// Dashboard (roadmap, ○ stretch item folded in here since the data it needs
// — listings/offers/earning/stock/followers — is the same data the mandatory
// storefront items already produce) + the mandatory Day-6 exit-gate pieces:
// stall QR (opens the permanent storefront URL), maker story entry point,
// and per-listing share card / export actions. Icon-driven per the
// roadmap ("icon-driven dashboard"), numbers are real aggregates from
// backend/app/api/storefront.py's dashboard endpoint, never placeholders.
//
// Day 7: exports are per marketplace (Amazon, Flipkart, GeM, ONDC), built
// only when she picks one; a no-offers-for-a-week card lists reasons read off
// her own data; a scheme card appears when her craft maps to one; both can be
// read aloud. Earnings need this phone's sign-in token — if it was replaced,
// the screen offers to verify the number again instead of showing an error.
import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:share_plus/share_plus.dart';
import '../services/api_base.dart';
import '../services/artisan_session.dart';
import '../services/storefront_client.dart';
import '../services/listings_client.dart';
import 'maker_story_screen.dart';
import 'onboarding/otp_screen.dart';
import 'rename_listing_screen.dart';

const _accent = Color(0xFF4F46E5);

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({Key? key}) : super(key: key);

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final FlutterTts _tts = FlutterTts();
  bool _loading = true;
  bool _signedOut = false;
  String? _error;
  String? _artisanId;
  Map<String, dynamic>? _dashboard;
  Map<String, dynamic>? _storefront;
  List<Map<String, dynamic>> _schemeCards = [];
  final Set<String> _busyListingActions = {};

  @override
  void initState() {
    super.initState();
    _tts.setLanguage('hi-IN');
    _load();
  }

  @override
  void dispose() {
    _tts.stop();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; _signedOut = false; });
    try {
      final artisanId = await ArtisanSession.artisanId;
      if (artisanId == null) throw Exception('not onboarded');
      final dashboard = await StorefrontClient.getDashboard(artisanId);
      final storefront = await StorefrontClient.getStorefront(artisanId);
      var schemes = <Map<String, dynamic>>[];
      try {
        schemes = await StorefrontClient.getSchemes(artisanId);
      } catch (_) {
        // an optional card; never keeps her shop from opening
      }
      if (!mounted) return;
      setState(() {
        _artisanId = artisanId;
        _dashboard = dashboard;
        _storefront = storefront;
        _schemeCards = schemes;
        _loading = false;
      });
    } on SignInRequired {
      if (!mounted) return;
      setState(() { _loading = false; _signedOut = true; });
    } catch (e) {
      if (!mounted) return;
      setState(() { _loading = false; _error = '$e'; });
    }
  }

  Future<void> _verifyAgain() async {
    final phone = await ArtisanSession.phone;
    final language = await ArtisanSession.language ?? 'hi';
    if (!mounted || phone == null) return;
    final ok = await Navigator.push<bool>(
      context, MaterialPageRoute(builder: (_) => OtpScreen(phone: phone, language: language)));
    if (ok == true) _load();
  }

  Future<void> _speak(String text) async {
    await _tts.stop();
    await _tts.speak(text);
  }

  void _showMessage(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  Future<void> _shareStorefront() async {
    final url = _storefront?['storefront_url'] as String?;
    if (url == null) return;
    await Share.share('मेरी दुकान देखिए — $url');
  }

  Future<void> _shareListing(String listingId) async {
    setState(() => _busyListingActions.add('share_$listingId'));
    try {
      final path = await ListingsClient.downloadShareCard(listingId);
      await Share.shareXFiles([XFile(path)]);
    } catch (e) {
      _showMessage('शेयर कार्ड नहीं बन सका — फिर कोशिश करें।');
    } finally {
      if (mounted) setState(() => _busyListingActions.remove('share_$listingId'));
    }
  }

  Future<void> _exportListing(String listingId) async {
    List<Map<String, dynamic>> marketplaces;
    try {
      marketplaces = await ListingsClient.exportMarketplaces();
    } catch (_) {
      _showMessage('एक्सपोर्ट की सूची नहीं मिली — फिर कोशिश करें।');
      return;
    }
    if (!mounted) return;
    final choice = await showModalBottomSheet<String>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(20, 20, 20, 2),
              child: Text('किस बाज़ार के लिए फ़ाइल बनाएँ?',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF1F2937))),
            ),
            const Padding(
              padding: EdgeInsets.fromLTRB(20, 0, 20, 8),
              child: Text('फ़ाइल अभी बनेगी — फिर भेज दीजिए या सहेज लीजिए।',
                  style: TextStyle(fontSize: 12, color: Color(0xFF9CA3AF))),
            ),
            ...marketplaces.map((m) => ListTile(
                  leading: Icon(
                    m['format'] == 'json' ? Icons.data_object_rounded : Icons.table_chart_rounded,
                    color: _accent,
                  ),
                  title: Text(m['name'] as String),
                  subtitle: Text(m['format'] == 'json' ? 'JSON file' : 'Excel file'),
                  onTap: () => Navigator.pop(ctx, m['id'] as String),
                )),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
    if (choice == null || !mounted) return;
    setState(() => _busyListingActions.add('export_$listingId'));
    try {
      final path = await ListingsClient.downloadExport(listingId, choice);
      await Share.shareXFiles([XFile(path)]);
    } catch (e) {
      _showMessage('एक्सपोर्ट फ़ाइल नहीं बन सकी — फिर कोशिश करें।');
    } finally {
      if (mounted) setState(() => _busyListingActions.remove('export_$listingId'));
    }
  }

  Future<void> _renameListing(String listingId, String titleEn, String titleHi) async {
    final lang = await ArtisanSession.language ?? 'hi';
    if (!mounted) return;
    final result = await Navigator.push<Map<String, dynamic>>(
      context,
      MaterialPageRoute(builder: (_) => RenameListingScreen(
        listingId: listingId, initialTitleEn: titleEn, initialTitleHi: titleHi, lang: lang,
      )),
    );
    if (result != null) _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF3F4F6),
      appBar: AppBar(
        backgroundColor: Colors.transparent, elevation: 0, foregroundColor: const Color(0xFF1F2937),
        title: const Text('My Shop', style: TextStyle(fontWeight: FontWeight.bold)),
      ),
      body: SafeArea(child: _body()),
    );
  }

  Widget _body() {
    if (_loading) return const Center(child: CircularProgressIndicator(color: _accent));
    if (_signedOut) {
      return _messageView(
        'यह फ़ोन अब आपकी दुकान से जुड़ा नहीं है — शायद नंबर किसी और फ़ोन पर पक्का किया गया। '
        'दुकान खोलने के लिए अपना नंबर फिर से पक्का कीजिए।',
        'नंबर पक्का करें', _verifyAgain,
      );
    }
    if (_error != null) {
      return _messageView('लोड नहीं हो सका। ($_error)', 'फिर कोशिश करें', _load);
    }

    final d = _dashboard!;
    final listings = (_storefront?['listings'] as List?) ?? [];
    final nudge = d['nudge'] as Map<String, dynamic>?;

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12, crossAxisSpacing: 12, childAspectRatio: 1.6,
            children: [
              _statTile(Icons.storefront_rounded, '${d['listings_count']}', 'Listings'),
              _statTile(Icons.local_offer_rounded, '${d['pending_offers_count']}', 'Pending offers'),
              _statTile(Icons.payments_rounded, '₹${(d['total_earning_inr'] as num).round()}', 'Total earned'),
              _statTile(Icons.inventory_2_rounded, '${d['remaining_stock_total']}', 'In stock'),
              _statTile(Icons.favorite_rounded, '${d['follower_count']}', 'Followers'),
              _statTile(Icons.verified_rounded, '${d['sold_out_count']}', 'Sold out'),
            ],
          ),
          if (nudge != null) ...[
            const SizedBox(height: 20),
            _nudgeCard(nudge),
          ],
          const SizedBox(height: 20),
          _makerStoryCard(),
          const SizedBox(height: 20),
          _qrCard(),
          for (final card in _schemeCards) ...[
            const SizedBox(height: 20),
            _schemeCard(card),
          ],
          const SizedBox(height: 20),
          const Text('Your listings', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Color(0xFF1F2937))),
          const SizedBox(height: 10),
          if (listings.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 16),
              child: Text('अभी कोई लिस्टिंग नहीं है।', style: TextStyle(color: Color(0xFF9CA3AF))),
            )
          else
            ...listings.map((l) => _listingRow(l as Map<String, dynamic>)),
        ],
      ),
    );
  }

  Widget _messageView(String text, String buttonLabel, VoidCallback onPressed) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(text, textAlign: TextAlign.center, style: const TextStyle(color: Color(0xFF6B7280))),
            const SizedBox(height: 16),
            ElevatedButton(onPressed: onPressed, child: Text(buttonLabel)),
          ],
        ),
      ),
    );
  }

  BoxDecoration _cardDecoration() => BoxDecoration(
        color: Colors.white, borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 10, offset: const Offset(0, 4))],
      );

  Widget _statTile(IconData icon, String value, String label) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white, borderRadius: BorderRadius.circular(14),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 8, offset: const Offset(0, 3))],
      ),
      child: Row(
        children: [
          Icon(icon, color: _accent, size: 26),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF1F2937))),
                Text(label, style: const TextStyle(fontSize: 11, color: Color(0xFF9CA3AF))),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _speakerButton(String text, Color color) {
    return IconButton(
      icon: Icon(Icons.volume_up_rounded, color: color),
      tooltip: 'सुनिए',
      onPressed: () => _speak(text),
    );
  }

  Widget _nudgeCard(Map<String, dynamic> nudge) {
    final reasons = (nudge['reasons'] as List).cast<Map<String, dynamic>>();
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 8, 8, 16),
      decoration: BoxDecoration(
        color: const Color(0xFFFFFBEB),
        border: Border.all(color: const Color(0xFFF59E0B)),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.lightbulb_outline_rounded, color: Color(0xFFB45309)),
              const SizedBox(width: 10),
              Expanded(
                child: Text(nudge['heading_hi'] as String,
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Color(0xFF92400E))),
              ),
              _speakerButton(nudge['spoken_hi'] as String, const Color(0xFFB45309)),
            ],
          ),
          ...reasons.map((r) => Padding(
                padding: const EdgeInsets.only(top: 6, right: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('•  ', style: TextStyle(color: Color(0xFF92400E))),
                    Expanded(
                      child: Text(r['text_hi'] as String,
                          style: const TextStyle(fontSize: 13, color: Color(0xFF78350F))),
                    ),
                  ],
                ),
              )),
        ],
      ),
    );
  }

  Widget _schemeCard(Map<String, dynamic> card) {
    final benefits = (card['benefits_hi'] as List).cast<String>();
    final sources = (card['sources'] as List).cast<String>();
    final sourceHost = sources.isEmpty ? '' : Uri.parse(sources.first).host;
    return Container(
      padding: const EdgeInsets.fromLTRB(18, 8, 8, 18),
      decoration: _cardDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.account_balance_rounded, color: _accent, size: 26),
              const SizedBox(width: 12),
              Expanded(
                child: Text(card['name_hi'] as String,
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Color(0xFF1F2937))),
              ),
              _speakerButton(card['spoken_hi'] as String, _accent),
            ],
          ),
          Padding(
            padding: const EdgeInsets.only(right: 10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(card['fit_hi'] as String, style: const TextStyle(fontSize: 13, color: Color(0xFF374151))),
                const SizedBox(height: 8),
                ...benefits.map((b) => Padding(
                      padding: const EdgeInsets.only(bottom: 4),
                      child: Text('•  $b', style: const TextStyle(fontSize: 12.5, color: Color(0xFF374151))),
                    )),
                const SizedBox(height: 6),
                Text(card['how_to_apply_hi'] as String,
                    style: const TextStyle(fontSize: 12, color: Color(0xFF6B7280))),
                const SizedBox(height: 6),
                Text('जानकारी ${card['checked_on']} को $sourceHost से जाँची गई',
                    style: const TextStyle(fontSize: 11, color: Color(0xFF9CA3AF))),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _makerStoryCard() {
    final hasStory = _storefront?['has_maker_story'] == true;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: _cardDecoration(),
      child: Row(
        children: [
          const Icon(Icons.auto_stories_rounded, color: _accent, size: 28),
          const SizedBox(width: 14),
          Expanded(
            child: Text(
              hasStory
                  ? (_storefront?['maker_story_text_hi'] as String? ?? '')
                  : 'अपनी कहानी अभी तक रिकॉर्ड नहीं की है',
              maxLines: 2, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 13, color: Color(0xFF374151)),
            ),
          ),
          TextButton(
            onPressed: () async {
              final saved = await Navigator.push<bool>(
                context, MaterialPageRoute(builder: (_) => const MakerStoryScreen()));
              if (saved == true) _load();
            },
            child: Text(hasStory ? 'Edit' : 'Record'),
          ),
        ],
      ),
    );
  }

  Widget _qrCard() {
    if (_artisanId == null) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: _cardDecoration(),
      child: Column(
        children: [
          const Text('Stall QR', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Color(0xFF1F2937))),
          const SizedBox(height: 4),
          const Text('Print this — it opens your storefront, months later too.',
              textAlign: TextAlign.center, style: TextStyle(fontSize: 12, color: Color(0xFF9CA3AF))),
          const SizedBox(height: 14),
          ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: Image.network(
              StorefrontClient.qrImageUrl(_artisanId!),
              width: 160, height: 160,
              errorBuilder: (_, __, ___) => const SizedBox(
                width: 160, height: 160,
                child: Center(child: Icon(Icons.qr_code_2_rounded, size: 48, color: Color(0xFFD1D5DB))),
              ),
            ),
          ),
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: _shareStorefront,
              icon: const Icon(Icons.share_rounded, size: 18),
              label: const Text('Share my shop link'),
              style: OutlinedButton.styleFrom(foregroundColor: _accent),
            ),
          ),
        ],
      ),
    );
  }

  Widget _listingRow(Map<String, dynamic> l) {
    final id = l['id'] as String;
    final sharing = _busyListingActions.contains('share_$id');
    final exporting = _busyListingActions.contains('export_$id');
    final setNote = l['price_unit'] == 'set' ? ' · ${l['pack_size']} का सेट' : '';
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white, borderRadius: BorderRadius.circular(14),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 8, offset: const Offset(0, 3))],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(l['title_en'] as String,
                    style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
                    maxLines: 1, overflow: TextOverflow.ellipsis),
              ),
              GestureDetector(
                onTap: () => _renameListing(id, l['title_en'] as String, l['title_hi'] as String),
                child: const Padding(
                  padding: EdgeInsets.only(left: 8),
                  child: Icon(Icons.edit_outlined, size: 18, color: Color(0xFF9CA3AF)),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text('₹${(l['price_inr'] as num).round()}$setNote · ${l['status']}',
              style: const TextStyle(fontSize: 12, color: Color(0xFF6B7280))),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: sharing ? null : () => _shareListing(id),
                  icon: sharing
                      ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.share_rounded, size: 16),
                  label: const Text('Share', style: TextStyle(fontSize: 13)),
                  style: OutlinedButton.styleFrom(foregroundColor: _accent, padding: const EdgeInsets.symmetric(vertical: 8)),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: exporting ? null : () => _exportListing(id),
                  icon: exporting
                      ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.description_rounded, size: 16),
                  label: const Text('Export', style: TextStyle(fontSize: 13)),
                  style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFF4B5563), padding: const EdgeInsets.symmetric(vertical: 8)),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
