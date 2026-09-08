import 'dart:async';
import 'dart:io';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:image/image.dart' as img;
import 'local_db.dart';
import 'api_client.dart';
import '../models/sync_task.dart';
import '../models/listing_draft.dart';

class SyncQueueService {
  static final SyncQueueService instance = SyncQueueService._init();

  // Bounds how many un-synced drafts can pile up offline; the oldest is
  // dropped (queue entry, draft row, and its files) once the cap is hit
  // so a long offline stretch can't grow storage unbounded.
  static const int maxQueueSize = 50;

  // Longest side an image is downscaled to before upload; the local draft
  // keeps the full-resolution original.
  static const int uploadMaxDimension = 1600;

  bool _isProcessing = false;
  late StreamSubscription<List<ConnectivityResult>> _connectivitySubscription;

  // `enqueue()` fires processQueue() without awaiting the network round trip
  // (deliberately, so capture isn't blocked on a slow/offline connection), so
  // a screen showing sync status can't just read it once after enqueueing —
  // it needs to know when a background sync actually finishes. Bumped once
  // per draft that changes state (synced, or a task dropped by the queue cap);
  // listen to it instead of polling.
  final ValueNotifier<int> queueVersion = ValueNotifier<int>(0);

  SyncQueueService._init() {
    _connectivitySubscription = Connectivity().onConnectivityChanged.listen((List<ConnectivityResult> results) {
      if (results.contains(ConnectivityResult.mobile) || results.contains(ConnectivityResult.wifi)) {
        processQueue();
      }
    });
  }

  void dispose() {
    _connectivitySubscription.cancel();
  }

  Future<void> enqueue(ListingDraft draft) async {
    // Save draft
    await LocalDb.instance.insertDraft(draft);

    // Create sync task
    final task = SyncTask(
      id: draft.id,
      enqueuedAt: DateTime.now(),
    );
    await LocalDb.instance.enqueueSync(task);

    await _enforceQueueCap();

    // Try to process queue immediately if online
    processQueue();
  }

  Future<void> _enforceQueueCap() async {
    var pending = await LocalDb.instance.getPendingSyncTasks(); // oldest-first
    while (pending.length > maxQueueSize) {
      final oldest = pending.first;
      final draft = await LocalDb.instance.getDraft(oldest.id);
      if (draft != null) {
        for (final path in [draft.imagePath, draft.audioPath]) {
          if (path == null) continue;
          final file = File(path);
          if (await file.exists()) await file.delete();
        }
        await LocalDb.instance.deleteDraft(oldest.id);
      }
      await LocalDb.instance.removeSyncTask(oldest.id);
      pending = pending.skip(1).toList();
      queueVersion.value++;
    }
  }

  Future<void> processQueue() async {
    if (_isProcessing) return;
    _isProcessing = true;

    try {
      final tasks = await LocalDb.instance.getPendingSyncTasks();
      final drafts = await LocalDb.instance.getAllDrafts();

      for (var task in tasks) {
        final draft = drafts.firstWhere((d) => d.id == task.id, orElse: () => throw Exception('Draft not found'));

        if (draft.imagePath != null && draft.audioPath != null) {
          final uploadImagePath = await _downscaleForUpload(draft.imagePath!);
          bool success = await ApiClient.syncDraft(
            clientId: draft.id,
            imagePath: uploadImagePath,
            audioPath: draft.audioPath!,
          );

          if (success) {
            await LocalDb.instance.removeSyncTask(task.id);
            await LocalDb.instance.updateDraftSyncStatus(draft.id, true);
            queueVersion.value++;
          } else {
            // Stop processing if we hit an error (e.g. offline)
            break;
          }
        }
      }
    } finally {
      _isProcessing = false;
    }
  }

  // Downscales to a cached sibling file so retries don't redo the work;
  // the original stays untouched for the local draft/gallery.
  Future<String> _downscaleForUpload(String imagePath) async {
    final scaledPath = '$imagePath.upload.jpg';
    final scaledFile = File(scaledPath);
    if (await scaledFile.exists()) return scaledPath;

    final original = img.decodeImage(await File(imagePath).readAsBytes());
    if (original == null) return imagePath;

    if (original.width <= uploadMaxDimension && original.height <= uploadMaxDimension) {
      return imagePath;
    }

    final resized = original.width >= original.height
        ? img.copyResize(original, width: uploadMaxDimension)
        : img.copyResize(original, height: uploadMaxDimension);

    await scaledFile.writeAsBytes(img.encodeJpg(resized, quality: 85));
    return scaledPath;
  }
}
