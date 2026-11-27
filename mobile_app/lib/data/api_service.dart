import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../domain/models.dart';
import 'storage_service.dart';

class QuotaExceededException implements Exception {
  final String message;
  final AppUser? updatedUser;
  QuotaExceededException(this.message, {this.updatedUser});
  @override
  String toString() => message;
}

class ApiException implements Exception {
  final String message;
  ApiException(this.message);
  @override
  String toString() => message;
}

class ConvertedBinaryResult {
  final List<int> bytes;
  final Map<String, String> headers;
  ConvertedBinaryResult(this.bytes, this.headers);
}

class ApiService {
  final StorageService _storage;
  ApiService(this._storage);

  String get _base => _storage.apiBaseUrl;

  Map<String, String> _authHeaders({bool jsonBody = false, bool admin = false}) {
    final tok = admin ? _storage.adminToken : _storage.authToken;
    return {
      if (tok != null && tok.isNotEmpty) 'Authorization': 'Bearer $tok',
      if (jsonBody) 'Content-Type': 'application/json',
      'Accept-Language': _storage.language,
    };
  }

  Future<AppUser> authenticateDevice() async {
    final devId = _storage.getOrCreateDeviceId();
    final uri = Uri.parse('$_base/api/v1/auth/device');
    final resp = await http
        .post(
          uri,
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'device_id': devId,
            'platform': Platform.operatingSystem,
            'device_name': 'Sifatli PDF Mobile',
            'lang': _storage.language,
          }),
        )
        .timeout(const Duration(seconds: 12));

    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    if (resp.statusCode != 200 || data['ok'] != true) {
      throw ApiException((data['error'] ?? 'Auth failed').toString());
    }
    await _storage.setAuthToken(data['token'].toString());
    return AppUser.fromJson(data['user'] as Map<String, dynamic>);
  }

  Future<AppUser> fetchMe() async {
    if (_storage.authToken == null) {
      return authenticateDevice();
    }
    final resp = await http
        .get(Uri.parse('$_base/api/v1/me'), headers: _authHeaders())
        .timeout(const Duration(seconds: 10));
    if (resp.statusCode == 401) {
      return authenticateDevice();
    }
    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    if (data['ok'] != true) {
      throw ApiException((data['error'] ?? 'Failed loading profile').toString());
    }
    return AppUser.fromJson(data['user'] as Map<String, dynamic>);
  }

  Future<AppUser> updateServerLanguage(String lang) async {
    final resp = await http
        .post(
          Uri.parse('$_base/api/v1/me/language'),
          headers: _authHeaders(jsonBody: true),
          body: jsonEncode({'language': lang}),
        )
        .timeout(const Duration(seconds: 8));
    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    return AppUser.fromJson(data['user'] as Map<String, dynamic>);
  }

  Future<Map<String, String>> startTelegramLink() async {
    final resp = await http
        .post(Uri.parse('$_base/api/v1/auth/telegram-link/start'), headers: _authHeaders())
        .timeout(const Duration(seconds: 10));
    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    if (data['ok'] != true) {
      throw ApiException((data['error'] ?? 'Could not create link').toString());
    }
    return {
      'token': data['link_token'].toString(),
      'bot_url': data['bot_url'].toString(),
      'tg_deep_link': data['tg_deep_link'].toString(),
    };
  }

  Future<AppUser?> pollTelegramLink(String linkToken) async {
    final resp = await http
        .get(
          Uri.parse('$_base/api/v1/auth/telegram-link/poll?token=$linkToken'),
          headers: _authHeaders(),
        )
        .timeout(const Duration(seconds: 8));
    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    if (data['ok'] == true && data['linked'] == true) {
      await _storage.setAuthToken(data['token'].toString());
      return AppUser.fromJson(data['user'] as Map<String, dynamic>);
    }
    return null;
  }

  Future<AppUser?> logLocalUsage(String action) async {
    final resp = await http
        .post(
          Uri.parse('$_base/api/v1/usage/log-local'),
          headers: _authHeaders(jsonBody: true),
          body: jsonEncode({'action': action}),
        )
        .timeout(const Duration(seconds: 8));
    if (resp.statusCode == 402) {
      final data = jsonDecode(resp.body) as Map<String, dynamic>;
      throw QuotaExceededException(
        (data['error'] ?? 'Daily limit reached').toString(),
        updatedUser: data['user'] != null
            ? AppUser.fromJson(data['user'] as Map<String, dynamic>)
            : null,
      );
    }
    if (resp.statusCode == 200) {
      final data = jsonDecode(resp.body) as Map<String, dynamic>;
      if (data['user'] != null) {
        return AppUser.fromJson(data['user'] as Map<String, dynamic>);
      }
    }
    return null;
  }

  Future<(String message, AppUser user)> redeemPromo(String code) async {
    final resp = await http
        .post(
          Uri.parse('$_base/api/v1/billing/promo'),
          headers: _authHeaders(jsonBody: true),
          body: jsonEncode({'code': code}),
        )
        .timeout(const Duration(seconds: 10));
    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    if (resp.statusCode != 200 || data['ok'] != true) {
      throw ApiException((data['error'] ?? 'Promo error').toString());
    }
    return (
      (data['message'] ?? 'OK').toString(),
      AppUser.fromJson(data['user'] as Map<String, dynamic>),
    );
  }

  Future<String> uploadVipReceipt({required String filePath, required int days}) async {
    final req = http.MultipartRequest('POST', Uri.parse('$_base/api/v1/billing/vip-receipt'));
    req.headers.addAll(_authHeaders());
    req.fields['days'] = days.toString();
    req.files.add(await http.MultipartFile.fromPath('file', filePath));

    final streamed = await req.send().timeout(const Duration(seconds: 45));
    final resp = await http.Response.fromStream(streamed);
    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    if (resp.statusCode != 200 || data['ok'] != true) {
      throw ApiException((data['error'] ?? 'Receipt upload failed').toString());
    }
    return (data['message'] ?? 'Sent').toString();
  }

  Future<ConvertedBinaryResult> convertMultipart({
    required String endpoint,
    required List<String> filePaths,
    Map<String, String>? fields,
  }) async {
    if (_storage.authToken == null) {
      await authenticateDevice();
    }
    final req = http.MultipartRequest('POST', Uri.parse('$_base$endpoint'));
    req.headers.addAll(_authHeaders());
    if (fields != null) req.fields.addAll(fields);
    for (int i = 0; i < filePaths.length; i++) {
      req.files.add(await http.MultipartFile.fromPath('file_$i', filePaths[i]));
    }

    final streamed = await req.send().timeout(const Duration(seconds: 120));
    final resp = await http.Response.fromStream(streamed);
    if (resp.statusCode == 402) {
      final data = jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
      throw QuotaExceededException(
        (data['error'] ?? 'Limit reached').toString(),
        updatedUser: data['user'] != null
            ? AppUser.fromJson(data['user'] as Map<String, dynamic>)
            : null,
      );
    }
    if (resp.statusCode != 200) {
      String msg = 'Conversion error (${resp.statusCode})';
      try {
        final data = jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
        msg = (data['error'] ?? msg).toString();
      } catch (_) {}
      throw ApiException(msg);
    }
    final lowerHeaders = <String, String>{};
    resp.headers.forEach((k, v) => lowerHeaders[k.toLowerCase()] = v);
    return ConvertedBinaryResult(resp.bodyBytes, lowerHeaders);
  }

  // Super Admin Methods
  Future<void> adminLogin(String password) async {
    final resp = await http
        .post(
          Uri.parse('$_base/api/v1/admin/login'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'password': password}),
        )
        .timeout(const Duration(seconds: 10));
    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    if (resp.statusCode != 200 || data['ok'] != true) {
      throw ApiException((data['error'] ?? 'Invalid password').toString());
    }
    await _storage.setAdminToken(data['admin_token'].toString());
  }

  Future<Map<String, dynamic>> fetchAdminDashboard() async {
    final resp = await http
        .get(Uri.parse('$_base/api/v1/admin/dashboard'), headers: _authHeaders(admin: true))
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode == 401 || resp.statusCode == 403) {
      await _storage.setAdminToken(null);
      throw ApiException('Session expired');
    }
    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    if (data['ok'] != true) {
      throw ApiException((data['error'] ?? 'Error').toString());
    }
    return data;
  }

  Future<void> updateAdminSettings(Map<String, dynamic> payload) async {
    final resp = await http
        .post(
          Uri.parse('$_base/api/v1/admin/settings'),
          headers: _authHeaders(jsonBody: true, admin: true),
          body: jsonEncode(payload),
        )
        .timeout(const Duration(seconds: 10));
    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    if (resp.statusCode != 200 || data['ok'] != true) {
      throw ApiException((data['error'] ?? 'Update failed').toString());
    }
  }

  Future<void> createAdminPromo({
    required String code,
    required String rewardType,
    required int rewardValue,
    required int maxUses,
  }) async {
    final resp = await http
        .post(
          Uri.parse('$_base/api/v1/admin/promo/create'),
          headers: _authHeaders(jsonBody: true, admin: true),
          body: jsonEncode({
            'code': code,
            'reward_type': rewardType,
            'reward_value': rewardValue,
            'max_uses': maxUses,
          }),
        )
        .timeout(const Duration(seconds: 10));
    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    if (resp.statusCode != 200 || data['ok'] != true) {
      throw ApiException((data['error'] ?? 'Promo create failed').toString());
    }
  }

  Future<void> grantUserVip(String query, int days) async {
    final resp = await http
        .post(
          Uri.parse('$_base/api/v1/admin/user/grant-vip'),
          headers: _authHeaders(jsonBody: true, admin: true),
          body: jsonEncode({'query': query, 'days': days}),
        )
        .timeout(const Duration(seconds: 10));
    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    if (resp.statusCode != 200 || data['ok'] != true) {
      throw ApiException((data['error'] ?? 'Failed').toString());
    }
  }
}
