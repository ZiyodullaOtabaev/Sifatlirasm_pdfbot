import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/constants.dart';
import '../../core/theme.dart';
import '../admin/super_admin_screen.dart';
import '../app_controller.dart';

class ProfileScreen extends StatelessWidget {
  final AppController ctrl;
  const ProfileScreen({super.key, required this.ctrl});

  Future<void> _connectTelegram(BuildContext context) async {
    try {
      final info = await ctrl.beginTelegramSync(
        onSynced: () {
          if (context.mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text(ctrl.tr('tg_connected')), backgroundColor: AppColors.emerald),
            );
          }
        },
      );
      final deepUri = Uri.parse(info['tg_deep_link']!);
      final webUri = Uri.parse(info['bot_url']!);
      if (!await launchUrl(deepUri, mode: LaunchMode.externalApplication)) {
        await launchUrl(webUri, mode: LaunchMode.externalApplication);
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString()), backgroundColor: AppColors.rose),
        );
      }
    }
  }

  void _showServerUrlDialog(BuildContext context) {
    final textCtrl = TextEditingController(text: ctrl.storage.apiBaseUrl);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Server API URL'),
        content: TextField(
          controller: textCtrl,
          decoration: const InputDecoration(hintText: 'http://92.5.105.169:8080'),
        ),
        actions: [
          TextButton(
            onPressed: () {
              ctrl.storage.setApiBaseUrl(AppConstants.defaultApiBaseUrl);
              Navigator.pop(ctx);
              ctrl.bootstrap();
            },
            child: const Text('Reset'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(minimumSize: const Size(90, 42)),
            onPressed: () async {
              await ctrl.storage.setApiBaseUrl(textCtrl.text);
              if (ctx.mounted) Navigator.pop(ctx);
              await ctrl.bootstrap();
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final u = ctrl.user;
    return Scaffold(
      appBar: AppBar(
        title: GestureDetector(
          onLongPress: () => _showServerUrlDialog(context),
          child: Text(ctrl.tr('profile_title'), style: const TextStyle(fontWeight: FontWeight.w800)),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: ctrl.refreshProfile,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(18),
                child: Row(
                  children: [
                    CircleAvatar(
                      radius: 28,
                      backgroundColor: AppColors.primary.withValues(alpha: 0.18),
                      child: Icon(
                        u.isVip ? Icons.workspace_premium_rounded : Icons.person_rounded,
                        color: u.isVip ? AppColors.amber : AppColors.primary,
                        size: 30,
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            u.firstName.isNotEmpty ? u.firstName : 'Sifatli PDF User',
                            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            'ID: ${u.userId}${u.username.isNotEmpty ? ' • @${u.username}' : ''}',
                            style: TextStyle(fontSize: 12.5, color: Theme.of(context).hintColor),
                          ),
                          const SizedBox(height: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                            decoration: BoxDecoration(
                              color: (u.isVip ? AppColors.amber : AppColors.emerald).withValues(alpha: 0.16),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(
                              u.isVip
                                  ? '💎 VIP (${u.vipUntil ?? '∞'})'
                                  : '🆓 ${ctrl.tr('free_remaining')}: ${(u.dailyLimit - u.dailyUsed).clamp(0, u.dailyLimit)}/${u.dailyLimit}',
                              style: TextStyle(
                                fontSize: 11.5,
                                fontWeight: FontWeight.w700,
                                color: u.isVip ? AppColors.amber : AppColors.emerald,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 14),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.telegram_rounded, color: Color(0xFF2AABEE), size: 28),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            u.isTelegramLinked ? '✅ ${ctrl.tr('tg_connected')}' : ctrl.tr('tg_sync_card_title'),
                            style: const TextStyle(fontSize: 15.5, fontWeight: FontWeight.w800),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      ctrl.isSyncingTelegram ? ctrl.tr('tg_waiting') : ctrl.tr('tg_sync_card_desc'),
                      style: TextStyle(fontSize: 12.8, color: Theme.of(context).hintColor, height: 1.35),
                    ),
                    if (!u.isTelegramLinked) ...[
                      const SizedBox(height: 12),
                      ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF2AABEE)),
                        onPressed: () => _connectTelegram(context),
                        icon: const Icon(Icons.link_rounded),
                        label: Text(ctrl.tr('tg_connect_btn')),
                      ),
                    ],
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            ElevatedButton.icon(
              style: ElevatedButton.styleFrom(backgroundColor: AppColors.emerald),
              onPressed: () => Share.share(u.referralUrl),
              icon: const Icon(Icons.card_giftcard_rounded),
              label: Text('${ctrl.tr('share_ref_btn')} (${u.referralCount})'),
            ),
            const SizedBox(height: 16),
            Card(
              child: Column(
                children: [
                  ListTile(
                    leading: const Icon(Icons.language_rounded, color: AppColors.primary),
                    title: Text(ctrl.tr('lang_label'), style: const TextStyle(fontWeight: FontWeight.w600)),
                    trailing: DropdownButton<String>(
                      value: ctrl.lang,
                      underline: const SizedBox.shrink(),
                      onChanged: (v) {
                        if (v != null) ctrl.setLanguage(v);
                      },
                      items: const [
                        DropdownMenuItem(value: 'uz', child: Text("🇺🇿 O'zbekcha")),
                        DropdownMenuItem(value: 'ru', child: Text('🇷🇺 Русский')),
                        DropdownMenuItem(value: 'en', child: Text('🇬🇧 English')),
                      ],
                    ),
                  ),
                  const Divider(height: 1),
                  SwitchListTile(
                    secondary: const Icon(Icons.dark_mode_rounded, color: AppColors.purple),
                    title: Text(ctrl.tr('theme_label'), style: const TextStyle(fontWeight: FontWeight.w600)),
                    value: ctrl.isDarkMode,
                    onChanged: ctrl.toggleDarkMode,
                  ),
                  const Divider(height: 1),
                  ListTile(
                    leading: const Icon(Icons.support_agent_rounded, color: AppColors.cyan),
                    title: Text(ctrl.tr('contact_admin'), style: const TextStyle(fontWeight: FontWeight.w600)),
                    trailing: const Icon(Icons.chevron_right_rounded),
                    onTap: () => launchUrl(
                      Uri.parse(AppConstants.adminTelegram),
                      mode: LaunchMode.externalApplication,
                    ),
                  ),
                  const Divider(height: 1),
                  ListTile(
                    leading: const Icon(Icons.admin_panel_settings_rounded, color: AppColors.amber),
                    title: Text(ctrl.tr('super_admin_btn'), style: const TextStyle(fontWeight: FontWeight.w700)),
                    trailing: const Icon(Icons.lock_outline_rounded, size: 19),
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => SuperAdminScreen(ctrl: ctrl)),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
