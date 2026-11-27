import 'dart:async';

import 'package:flutter/foundation.dart';

import '../core/l10n.dart';
import '../data/api_service.dart';
import '../data/storage_service.dart';
import '../domain/models.dart';

class AppController extends ChangeNotifier {
  final StorageService storage;
  final ApiService api;

  late String _lang;
  late bool _isDarkMode;
  late AppUser _user;
  List<LocalSavedFile> _savedFiles = [];
  int _navIndex = 0;
  bool _isSyncingTelegram = false;
  Timer? _tgPollTimer;

  AppController({required this.storage, required this.api}) {
    _lang = storage.language;
    _isDarkMode = storage.isDarkMode;
    _user = AppUser.guest(_lang);
    _savedFiles = storage.loadSavedFiles();
  }

  String get lang => _lang;
  bool get isDarkMode => _isDarkMode;
  AppUser get user => _user;
  List<LocalSavedFile> get savedFiles => List.unmodifiable(_savedFiles);
  int get navIndex => _navIndex;
  bool get isSyncingTelegram => _isSyncingTelegram;

  String tr(String key) => AppStrings.tr(key, _lang);

  void setNavIndex(int idx) {
    if (_navIndex == idx) return;
    _navIndex = idx;
    notifyListeners();
  }

  Future<void> bootstrap() async {
    try {
      final me = await api.fetchMe();
      _user = me;
      if (me.language.isNotEmpty && me.language != _lang) {
        _lang = me.language;
        await storage.setLanguage(_lang);
      }
      notifyListeners();
    } catch (_) {
      // Offline mode still works cleanly for local tools & My Files!
    }
  }

  Future<void> refreshProfile() async {
    try {
      _user = await api.fetchMe();
      notifyListeners();
    } catch (_) {}
  }

  void updateUserSnapshot(AppUser u) {
    _user = u;
    notifyListeners();
  }

  Future<void> setLanguage(String newLang) async {
    if (!['uz', 'ru', 'en'].contains(newLang)) return;
    _lang = newLang;
    await storage.setLanguage(newLang);
    notifyListeners();
    try {
      _user = await api.updateServerLanguage(newLang);
      notifyListeners();
    } catch (_) {}
  }

  Future<void> toggleDarkMode(bool dark) async {
    _isDarkMode = dark;
    await storage.setDarkMode(dark);
    notifyListeners();
  }

  Future<LocalSavedFile> saveGeneratedFile({
    required List<int> bytes,
    required String fileName,
    required String toolKey,
    String? metaNote,
  }) async {
    final saved = await storage.saveOutputBytes(
      bytes: bytes,
      fileName: fileName,
      toolKey: toolKey,
      metaNote: metaNote,
    );
    _savedFiles = storage.loadSavedFiles();
    notifyListeners();
    unawaited(refreshProfile());
    return saved;
  }

  Future<void> deleteFile(String id) async {
    await storage.deleteSavedFile(id);
    _savedFiles = storage.loadSavedFiles();
    notifyListeners();
  }

  Future<void> clearAllFiles() async {
    await storage.clearAllSavedFiles();
    _savedFiles = [];
    notifyListeners();
  }

  Future<Map<String, String>> beginTelegramSync({
    required VoidCallback onSynced,
  }) async {
    final linkInfo = await api.startTelegramLink();
    final token = linkInfo['token']!;
    _isSyncingTelegram = true;
    notifyListeners();

    _tgPollTimer?.cancel();
    int attempts = 0;
    _tgPollTimer = Timer.periodic(const Duration(seconds: 2), (timer) async {
      attempts++;
      if (attempts > 90) {
        timer.cancel();
        _isSyncingTelegram = false;
        notifyListeners();
        return;
      }
      try {
        final linkedUser = await api.pollTelegramLink(token);
        if (linkedUser != null) {
          timer.cancel();
          _user = linkedUser;
          if (linkedUser.language.isNotEmpty) {
            _lang = linkedUser.language;
            await storage.setLanguage(_lang);
          }
          _isSyncingTelegram = false;
          notifyListeners();
          onSynced();
        }
      } catch (_) {}
    });

    return linkInfo;
  }

  @override
  void dispose() {
    _tgPollTimer?.cancel();
    super.dispose();
  }
}
