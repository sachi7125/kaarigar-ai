class ListingDraft {
  final String id;
  final String? imagePath;
  final String? audioPath;
  final DateTime createdAt;
  final bool isSynced;

  ListingDraft({
    required this.id,
    this.imagePath,
    this.audioPath,
    required this.createdAt,
    this.isSynced = false,
  });

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'imagePath': imagePath,
      'audioPath': audioPath,
      'createdAt': createdAt.toIso8601String(),
      'isSynced': isSynced ? 1 : 0,
    };
  }

  factory ListingDraft.fromMap(Map<String, dynamic> map) {
    return ListingDraft(
      id: map['id'],
      imagePath: map['imagePath'],
      audioPath: map['audioPath'],
      createdAt: DateTime.parse(map['createdAt']),
      isSynced: map['isSynced'] == 1,
    );
  }
}
