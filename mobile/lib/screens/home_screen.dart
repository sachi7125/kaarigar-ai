import 'package:flutter/material.dart';
import '../services/local_db.dart';
import '../services/sync_queue.dart';
import '../models/listing_draft.dart';
import 'capture_screen.dart';
import 'offers_screen.dart';
import 'dashboard_screen.dart';
import 'settings_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({Key? key}) : super(key: key);

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<ListingDraft> _drafts = [];

  @override
  void initState() {
    super.initState();
    _loadDrafts();
    // enqueue() doesn't await the network sync, so a draft can flip to
    // "Synced" seconds after this screen last loaded — listen instead of
    // relying on the one-shot reload after returning from CaptureScreen.
    SyncQueueService.instance.queueVersion.addListener(_loadDrafts);
  }

  @override
  void dispose() {
    SyncQueueService.instance.queueVersion.removeListener(_loadDrafts);
    super.dispose();
  }

  Future<void> _loadDrafts() async {
    final drafts = await LocalDb.instance.getAllDrafts();
    setState(() {
      _drafts = drafts;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF3F4F6),
      appBar: AppBar(
        elevation: 0,
        backgroundColor: Colors.transparent,
        title: const Text(
          'KaarigarAI',
          style: TextStyle(
            color: Color(0xFF1F2937),
            fontWeight: FontWeight.w800,
            fontSize: 24,
            letterSpacing: -0.5,
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.storefront_outlined, color: Color(0xFF4B5563)),
            tooltip: 'My Shop',
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const DashboardScreen())),
          ),
          IconButton(
            icon: const Icon(Icons.local_offer_outlined, color: Color(0xFF4B5563)),
            tooltip: 'Offers',
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const OffersScreen())),
          ),
          IconButton(
            icon: const Icon(Icons.settings_outlined, color: Color(0xFF4B5563)),
            tooltip: 'Settings',
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SettingsScreen())),
          )
        ],
      ),
      body: _drafts.isEmpty
          ? _buildEmptyState()
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _drafts.length,
              itemBuilder: (context, index) {
                final draft = _drafts[index];
                return _buildDraftCard(draft);
              },
            ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          await Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const CaptureScreen()),
          );
          _loadDrafts(); // Refresh when returning
        },
        backgroundColor: const Color(0xFF4F46E5),
        elevation: 4,
        icon: const Icon(Icons.camera_alt, color: Colors.white),
        label: const Text(
          'New Listing',
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: Colors.white,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.05),
                  blurRadius: 20,
                  offset: const Offset(0, 10),
                )
              ],
            ),
            child: const Icon(Icons.inventory_2_outlined, size: 64, color: Color(0xFF9CA3AF)),
          ),
          const SizedBox(height: 24),
          const Text(
            'No listings yet',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: Color(0xFF374151),
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Tap the button below to capture a craft.',
            style: TextStyle(
              color: Color(0xFF6B7280),
              fontSize: 16,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDraftCard(ListingDraft draft) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.03),
            blurRadius: 10,
            offset: const Offset(0, 4),
          )
        ],
      ),
      child: ListTile(
        contentPadding: const EdgeInsets.all(16),
        leading: Container(
          width: 60,
          height: 60,
          decoration: BoxDecoration(
            color: const Color(0xFFF3F4F6),
            borderRadius: BorderRadius.circular(12),
          ),
          child: const Icon(Icons.image_outlined, color: Color(0xFF9CA3AF)),
        ),
        title: Text(
          'Draft ${draft.id.substring(0, 6)}',
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 8.0),
          child: Row(
            children: [
              Icon(
                draft.isSynced ? Icons.cloud_done : Icons.cloud_upload_outlined,
                size: 16,
                color: draft.isSynced ? Colors.green : const Color(0xFFF59E0B),
              ),
              const SizedBox(width: 4),
              Text(
                draft.isSynced ? 'Synced' : 'Pending Sync',
                style: TextStyle(
                  color: draft.isSynced ? Colors.green : const Color(0xFFF59E0B),
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}