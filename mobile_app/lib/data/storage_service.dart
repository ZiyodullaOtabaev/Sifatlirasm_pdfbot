import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/constants.dart';
import '../domain/models.dart';

class StorageService {
  static const _kDeviceId = 'sp_device_id';
  static const _kAuthToken = 'sp_auth_token';
  static const _kAdminToken = 'sp_admin_token';
  static const _kLang = 'sp_language';
  static const _kDarkMode = 'sp_dark_mode';
  static const _kApiBaseUrl = 'sp_api_base_url';
  static const _kSavedFiles = 'sp_saved_files_v1';

  late final SharedPreferences _prefs;

  Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
  }

  String getOrCreateDeviceId() {
    var existing = _prefs.getString(_kDeviceId);
    if (existing != null && existing.length >= 8) return existing;
    final rnd = Random.secure();
    final hex = List.generate(16, (_) => rnd.nextInt(256).toRadixString(16).padLeft(2, '0')).join();
    existing = 'sp_${Platform.operatingSystem}_$hex';
    _prefs.setString(_kDeviceId, existing);
    return existing;
  }

  String? get authToken => _prefs.getString(_kAuthToken);
  Future<void> setAuthToken(String token) => _prefs.setString(_kAuthToken, token);

  String? get adminToken => _prefs.getString(_kAdminToken);
  Future<void> setAdminToken(String? token) {
    if (token == null) return _prefs.remove(_kAdminToken);
    return _prefs.setString(_kAdminToken, token);
  }

  String get language => _prefs.getString(_kLang) ?? 'uz';
  Future<void> setLanguage(String lang) => _prefs.setString(_kLang, lang);

  bool get isDarkMode => _prefs.getBool(_kDarkMode) ?? true;
  Future<void> setDarkMode(bool dark) => _prefs.setBool(_kDarkMode, dark);

  String get apiBaseUrl => _prefs.getString(_kApiBaseUrl) ?? AppConstants.defaultApiBaseUrl;
  Future<void> setApiBaseUrl(String url) =>
      _prefs.setString(_kApiBaseUrl, url.trim().replaceAll(RegExp(r'/+$'), ''));

  List<LocalSavedFile> loadSavedFiles() {
    final raw = _prefs.getStringList(_kSavedFiles) ?? const [];
    final out = <LocalSavedFile>[];
    for (final item in raw) {
      try {
        final f = LocalSavedFile.fromJson(jsonDecode(item) as Map<String, dynamic>);
        if (File(f.path).existsSync()) {
          out.add(f);
        }
      } catch (_) {}
    }
    return out;
  }

  Future<LocalSavedFile> saveOutputBytes({
    required List<int> bytes,
    required String fileName,
    required String toolKey,
    String? metaNote,
  }) async {
    final docsDir = await getApplicationDocumentsDirectory();
    final vaultDir = Directory('${docsDir.path}/sifatli_vault');
    if (!vaultDir.existsSync()) {
      await vaultDir.create(recursive: true);
    }

    final safeName = fileName.replaceAll(RegExp(r'[\\/:*?"<>|]'), '_');
    final ts = DateTime.now().millisecondsSinceEpoch;
    final fullPath = '${vaultDir.path}/${ts}_$safeName';
    final file = File(fullPath);
    await file.writeAsBytes(bytes, flush: true);

    final entry = LocalSavedFile(
      id: ts.toString(),
      name: safeName,
      path: fullPath,
      toolKey: toolKey,
      sizeBytes: bytes.length,
      createdAtIso: DateTime.now().toIso8601String(),
      metaNote: metaNote,
    );

    final current = loadSavedFiles();
    current.insert(0, entry);
    await _persistList(current);
    return entry;
  }

  Future<void> deleteSavedFile(String id) async {
    final current = loadSavedFiles();
    final target = current.where((e) => e.id == id).toList();
    for (final t in target) {
      try {
        final f = File(t.path);
        if (f.existsSync()) await f.delete();
      } catch (_) {}
    }
    current.removeWhere((e) => e.id == id);
    await _persistList(current);
  }

  Future<void> clearAllSavedFiles() async {
    final current = loadSavedFiles();
    for (final t in current) {
      try {
        final f = File(t.path);
        if (f.existsSync()) await f.delete();
      } catch (_) {}
    }
    await _prefs.remove(_kSavedFiles);
  }

  Future<void> _persistList(List<LocalSavedFile> items) async {
    final encoded = items.take(200).map((e) => jsonEncode(e.toJson())).toList();
    await _prefs.setStringList(_kSavedFiles, encoded);
  }
}
