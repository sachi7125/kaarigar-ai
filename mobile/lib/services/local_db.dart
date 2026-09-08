// SQLite: drafts, past listings, synced offers. (Day 3)

import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import '../models/listing_draft.dart';
import '../models/sync_task.dart';

class LocalDb {
  static final LocalDb instance = LocalDb._init();
  static Database? _database;

  LocalDb._init();

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDB('kaarigar.db');
    return _database!;
  }

  Future<Database> _initDB(String filePath) async {
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, filePath);

    return await openDatabase(
      path,
      version: 2,
      onCreate: _createDB,
      onUpgrade: _upgradeDB,
    );
  }

  Future _createDB(Database db, int version) async {
    await db.execute('''
      CREATE TABLE drafts (
        id TEXT PRIMARY KEY,
        imagePath TEXT,
        audioPath TEXT,
        createdAt TEXT NOT NULL,
        isSynced INTEGER NOT NULL
      )
    ''');

    await db.execute('''
      CREATE TABLE sync_queue (
        id TEXT PRIMARY KEY,
        enqueuedAt TEXT NOT NULL,
        retryCount INTEGER NOT NULL
      )
    ''');

    await _createSettingsTable(db);
  }

  Future _upgradeDB(Database db, int oldVersion, int newVersion) async {
    if (oldVersion < 2) {
      await _createSettingsTable(db);
    }
  }

  Future<void> _createSettingsTable(Database db) async {
    // Generic key/value store — onboarding state (Day 5: artisan_id, phone,
    // language, verified) so first-run doesn't repeat, without pulling in a
    // separate shared_preferences dependency for one small table.
    await db.execute('''
      CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
      )
    ''');
  }

  // --- Drafts ---
  Future<void> insertDraft(ListingDraft draft) async {
    final db = await instance.database;
    await db.insert('drafts', draft.toMap(), conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<List<ListingDraft>> getAllDrafts() async {
    final db = await instance.database;
    final result = await db.query('drafts', orderBy: 'createdAt DESC');
    return result.map((json) => ListingDraft.fromMap(json)).toList();
  }

  Future<ListingDraft?> getDraft(String id) async {
    final db = await instance.database;
    final result = await db.query('drafts', where: 'id = ?', whereArgs: [id]);
    if (result.isEmpty) return null;
    return ListingDraft.fromMap(result.first);
  }

  Future<void> deleteDraft(String id) async {
    final db = await instance.database;
    await db.delete('drafts', where: 'id = ?', whereArgs: [id]);
  }


  Future<void> updateDraftSyncStatus(String id, bool isSynced) async {
    final db = await instance.database;
    await db.update(
      'drafts',
      {'isSynced': isSynced ? 1 : 0},
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  // --- Sync Queue ---
  Future<void> enqueueSync(SyncTask task) async {
    final db = await instance.database;
    await db.insert('sync_queue', task.toMap(), conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<List<SyncTask>> getPendingSyncTasks() async {
    final db = await instance.database;
    final result = await db.query('sync_queue', orderBy: 'enqueuedAt ASC');
    return result.map((json) => SyncTask.fromMap(json)).toList();
  }

  Future<void> removeSyncTask(String id) async {
    final db = await instance.database;
    await db.delete('sync_queue', where: 'id = ?', whereArgs: [id]);
  }

  Future<int> getSyncQueueLength() async {
    final db = await instance.database;
    final result = await db.rawQuery('SELECT COUNT(*) AS count FROM sync_queue');
    return Sqflite.firstIntValue(result) ?? 0;
  }

  // --- Settings (onboarding state) ---
  Future<void> setSetting(String key, String value) async {
    final db = await instance.database;
    await db.insert('settings', {'key': key, 'value': value},
        conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<String?> getSetting(String key) async {
    final db = await instance.database;
    final result = await db.query('settings', where: 'key = ?', whereArgs: [key]);
    return result.isEmpty ? null : result.first['value'] as String?;
  }
}
