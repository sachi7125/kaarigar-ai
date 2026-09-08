class SyncTask {
  final String id; // Matches ListingDraft id
  final DateTime enqueuedAt;
  final int retryCount;

  SyncTask({
    required this.id,
    required this.enqueuedAt,
    this.retryCount = 0,
  });

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'enqueuedAt': enqueuedAt.toIso8601String(),
      'retryCount': retryCount,
    };
  }

  factory SyncTask.fromMap(Map<String, dynamic> map) {
    return SyncTask(
      id: map['id'],
      enqueuedAt: DateTime.parse(map['enqueuedAt']),
      retryCount: map['retryCount'],
    );
  }
}
