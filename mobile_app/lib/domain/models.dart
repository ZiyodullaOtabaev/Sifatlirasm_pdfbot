class VipPrices {
  final int uzs30;
  final int uzs365;
  final int stars30;
  final int stars365;

  const VipPrices({
    this.uzs30 = 9000,
    this.uzs365 = 29000,
    this.stars30 = 50,
    this.stars365 = 150,
  });

  factory VipPrices.fromJson(Map<String, dynamic>? json) {
    if (json == null) return const VipPrices();
    return VipPrices(
      uzs30: (json['uzs_30'] as num?)?.toInt() ?? 9000,
      uzs365: (json['uzs_365'] as num?)?.toInt() ?? 29000,
      stars30: (json['stars_30'] as num?)?.toInt() ?? 50,
      stars365: (json['stars_365'] as num?)?.toInt() ?? 150,
    );
  }

  String formatUzs(int val) {
    final s = val.toString();
    final buf = StringBuffer();
    for (int i = 0; i < s.length; i++) {
      if (i > 0 && (s.length - i) % 3 == 0) buf.write(' ');
      buf.write(s[i]);
    }
    return buf.toString();
  }
}

class AppUser {
  final int userId;
  final bool isTelegramLinked;
  final String username;
  final String firstName;
  final String language;
  final bool isVip;
  final bool isAdmin;
  final String? vipUntil;
  final int dailyUsed;
  final int dailyLimit;
  final int bonusBalance;
  final int remainingAvailable;
  final int usesCount;
  final int referralCount;
  final String referralUrl;
  final String botUsername;
  final VipPrices vipPrices;
  final String cardNumber;
  final bool maintenanceMode;

  const AppUser({
    required this.userId,
    required this.isTelegramLinked,
    required this.username,
    required this.firstName,
    required this.language,
    required this.isVip,
    required this.isAdmin,
    this.vipUntil,
    required this.dailyUsed,
    required this.dailyLimit,
    required this.bonusBalance,
    required this.remainingAvailable,
    required this.usesCount,
    required this.referralCount,
    required this.referralUrl,
    required this.botUsername,
    required this.vipPrices,
    required this.cardNumber,
    required this.maintenanceMode,
  });

  factory AppUser.guest(String lang) => AppUser(
        userId: 0,
        isTelegramLinked: false,
        username: '',
        firstName: 'Guest',
        language: lang,
        isVip: false,
        isAdmin: false,
        vipUntil: null,
        dailyUsed: 0,
        dailyLimit: 5,
        bonusBalance: 0,
        remainingAvailable: 5,
        usesCount: 0,
        referralCount: 0,
        referralUrl: 'https://t.me/sifatlirasm_pdfbot',
        botUsername: 'sifatlirasm_pdfbot',
        vipPrices: const VipPrices(),
        cardNumber: '5614682914822756',
        maintenanceMode: false,
      );

  factory AppUser.fromJson(Map<String, dynamic> j) => AppUser(
        userId: (j['user_id'] as num?)?.toInt() ?? 0,
        isTelegramLinked: j['is_telegram_linked'] == true,
        username: (j['username'] ?? '').toString(),
        firstName: (j['first_name'] ?? '').toString(),
        language: (j['language'] ?? 'uz').toString(),
        isVip: j['is_vip'] == true,
        isAdmin: j['is_admin'] == true,
        vipUntil: j['vip_until']?.toString(),
        dailyUsed: (j['daily_used'] as num?)?.toInt() ?? 0,
        dailyLimit: (j['daily_limit'] as num?)?.toInt() ?? 5,
        bonusBalance: (j['bonus_balance'] as num?)?.toInt() ?? 0,
        remainingAvailable: (j['remaining_available'] as num?)?.toInt() ?? 5,
        usesCount: (j['uses_count'] as num?)?.toInt() ?? 0,
        referralCount: (j['referral_count'] as num?)?.toInt() ?? 0,
        referralUrl: (j['referral_url'] ?? 'https://t.me/sifatlirasm_pdfbot').toString(),
        botUsername: (j['bot_username'] ?? 'sifatlirasm_pdfbot').toString(),
        vipPrices: VipPrices.fromJson(j['vip_prices'] as Map<String, dynamic>?),
        cardNumber: (j['card_number'] ?? '').toString(),
        maintenanceMode: j['maintenance_mode'] == true,
      );
}

class LocalSavedFile {
  final String id;
  final String name;
  final String path;
  final String toolKey;
  final int sizeBytes;
  final String createdAtIso;
  final String? metaNote;

  const LocalSavedFile({
    required this.id,
    required this.name,
    required this.path,
    required this.toolKey,
    required this.sizeBytes,
    required this.createdAtIso,
    this.metaNote,
  });

  bool get isPdf => path.toLowerCase().endsWith('.pdf');
  bool get isDocx => path.toLowerCase().endsWith('.docx');
  bool get isZip => path.toLowerCase().endsWith('.zip');

  String get formattedSize {
    if (sizeBytes < 1024) return '$sizeBytes B';
    if (sizeBytes < 1024 * 1024) {
      return '${(sizeBytes / 1024).toStringAsFixed(1)} KB';
    }
    return '${(sizeBytes / (1024 * 1024)).toStringAsFixed(2)} MB';
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'path': path,
        'toolKey': toolKey,
        'sizeBytes': sizeBytes,
        'createdAtIso': createdAtIso,
        'metaNote': metaNote,
      };

  factory LocalSavedFile.fromJson(Map<String, dynamic> j) => LocalSavedFile(
        id: (j['id'] ?? '').toString(),
        name: (j['name'] ?? 'document').toString(),
        path: (j['path'] ?? '').toString(),
        toolKey: (j['toolKey'] ?? '').toString(),
        sizeBytes: (j['sizeBytes'] as num?)?.toInt() ?? 0,
        createdAtIso: (j['createdAtIso'] ?? '').toString(),
        metaNote: j['metaNote']?.toString(),
      );
}
