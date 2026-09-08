import 'package:flutter/material.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import 'dart:io';
import '../services/sync_queue.dart';
import '../models/listing_draft.dart';
import 'package:uuid/uuid.dart';
import 'pricing_screen.dart';

class RecordScreen extends StatefulWidget {
  final String imagePath;
  const RecordScreen({Key? key, required this.imagePath}) : super(key: key);

  @override
  State<RecordScreen> createState() => _RecordScreenState();
}

class _RecordScreenState extends State<RecordScreen> with SingleTickerProviderStateMixin {
  late final AudioRecorder _audioRecorder;
  bool _isRecording = false;
  late AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _audioRecorder = AudioRecorder();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1000),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _audioRecorder.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  Future<void> _toggleRecording() async {
    if (_isRecording) {
      final path = await _audioRecorder.stop();
      setState(() => _isRecording = false);
      
      if (path != null) {
        _saveAndEnqueue(path);
      }
    } else {
      if (await _audioRecorder.hasPermission()) {
        final dir = await getApplicationDocumentsDirectory();
        final path = '${dir.path}/audio_${DateTime.now().millisecondsSinceEpoch}.m4a';
        await _audioRecorder.start(const RecordConfig(encoder: AudioEncoder.aacLc), path: path);
        setState(() => _isRecording = true);
      }
    }
  }

  Future<void> _saveAndEnqueue(String audioPath) async {
    // Generate client ID
    final String clientId = const Uuid().v4();

    final draft = ListingDraft(
      id: clientId,
      imagePath: widget.imagePath,
      audioPath: audioPath,
      createdAt: DateTime.now(),
      isSynced: false,
    );

    await SyncQueueService.instance.enqueue(draft);

    // The draft is already saved and queued regardless of what happens next —
    // Day 3's offline guarantee doesn't depend on pricing succeeding. Pricing
    // itself needs a network round trip (Gemini + the model are server-side),
    // so PricingScreen shows its own offline/error state rather than this
    // screen trying to guard against that.
    if (mounted) {
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => PricingScreen(
            imagePath: widget.imagePath,
            audioPath: audioPath,
            clientId: clientId,
          ),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1F2937),
      body: Stack(
        children: [
          // Background Image (Blurred)
          Positioned.fill(
            child: Opacity(
              opacity: 0.4,
              child: Image.file(
                File(widget.imagePath),
                fit: BoxFit.cover,
              ),
            ),
          ),
          
          // Back Button
          Positioned(
            top: 50,
            left: 20,
            child: IconButton(
              icon: const Icon(Icons.arrow_back, color: Colors.white, size: 32),
              onPressed: () => Navigator.pop(context),
            ),
          ),

          // Main Content
          Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Text(
                  'Describe the craft',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 16),
                const Text(
                  'What material is it? What size?',
                  style: TextStyle(
                    color: Colors.white70,
                    fontSize: 16,
                  ),
                ),
                const SizedBox(height: 60),
                
                // Record Button with Pulse
                GestureDetector(
                  onTap: _toggleRecording,
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      if (_isRecording)
                        ScaleTransition(
                          scale: Tween(begin: 1.0, end: 1.5).animate(_pulseController),
                          child: Container(
                            width: 100,
                            height: 100,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: Colors.red.withOpacity(0.3),
                            ),
                          ),
                        ),
                      Container(
                        width: 80,
                        height: 80,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: _isRecording ? Colors.red : Colors.white,
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.2),
                              blurRadius: 10,
                              offset: const Offset(0, 5),
                            )
                          ],
                        ),
                        child: Icon(
                          _isRecording ? Icons.stop : Icons.mic,
                          color: _isRecording ? Colors.white : const Color(0xFF4F46E5),
                          size: 40,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
