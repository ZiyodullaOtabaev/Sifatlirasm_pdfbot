import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme.dart';
import '../app_controller.dart';

class VipScreen extends StatefulWidget {
  final AppController ctrl;
  const VipScreen({super.key, required this.ctrl});

  @override
  State<VipScreen> createState() => _VipScreenState();
}

class _VipScreenState extends State<VipScreen> {
  final TextEditingController _promoCtrl = TextEditingController();
  final ImagePicker _picker = ImagePicker();
  int _selectedDays = 365;
  bool _busyReceipt = false;
  bool _busyPromo = false;

  @override
  void dispose() {
    _promoCtrl.dispose();
    super.dispose();
  }

  Future<void> _uploadReceipt() async {
    final img = await _picker.pickImage(source: ImageSource.gallery, imageQuality: 90);
    if (img == null) return;

    setState(() => _busyReceipt = true);
    try {
      final msg = await widget.ctrl.api.uploadVipReceipt(filePath: img.path, days: _selectedDays);
      if (mounted) {
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            title: const Icon(Icons.check_circle_rounded, color: AppColors.emerald, size: 48),
            content: Text(msg, textAlign: TextAlign.center, style: const TextStyle(fontSize: 15)),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('OK')),
            ],
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString()), backgroundColor: AppColors.rose),
        );
      }
    } finally {
      if (mounted) setState(() => _busyReceipt = false);
    }
  }

  Future<void> _applyPromo() async {
    final code = _promoCtrl.text.trim();
    if (code.isEmpty || _busyPromo) return;
    setState(() => _busyPromo = true);
    try {
      final (msg, updatedUser) = await widget.ctrl.api.redeemPromo(code);
      widget.ctrl.updateUserSnapshot(updatedUser);
      _promoCtrl.clear();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(msg), backgroundColor: AppColors.emerald),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString()), backgroundColor: AppColors.rose),
        );
      }
    } finally {
      if (mounted) setState(() => _busyPromo = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ctrl = widget.ctrl;
    final u = ctrl.user;
    final p = u.vipPrices;

    return Scaffold(
      appBar: AppBar(
        title: Text(ctrl.tr('nav_vip'), style: const TextStyle(fontWeight: FontWeight.w800)),
      ),
      body: RefreshIndicator(
        onRefresh: ctrl.refreshProfile,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                gradient: AppColors.vipGradient,
                borderRadius: BorderRadius.circular(22),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.workspace_premium_rounded, color: Colors.white, size: 32),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          u.isVip
                              ? '💎 ${ctrl.tr('vip_unlimited')} (${u.vipUntil ?? '∞'})'
                              : ctrl.tr('vip_title'),
                          style: const TextStyle(color: Colors.white, fontSize: 18.5, fontWeight: FontWeight.w800),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    ctrl.tr('vip_subtitle'),
                    style: TextStyle(color: Colors.white.withValues(alpha: 0.92), fontSize: 13.2, height: 1.35),
                  ),
                  const SizedBox(height: 14),
                  _featLine(ctrl.tr('vip_feat_1')),
                  const SizedBox(height: 6),
                  _featLine(ctrl.tr('vip_feat_2')),
                  const SizedBox(height: 6),
                  _featLine(ctrl.tr('vip_feat_3')),
                ],
              ),
            ),
            const SizedBox(height: 18),
            Row(
              children: [
                Expanded(
                  child: _PlanOptionCard(
                    title: ctrl.tr('plan_month'),
                    priceUzs: '${p.formatUzs(p.uzs30)} UZS',
                    stars: '${p.stars30} ⭐',
                    selected: _selectedDays == 30,
                    onTap: () => setState(() => _selectedDays = 30),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _PlanOptionCard(
                    title: ctrl.tr('plan_year'),
                    priceUzs: '${p.formatUzs(p.uzs365)} UZS',
                    stars: '${p.stars365} ⭐',
                    badge: ctrl.tr('best_value'),
                    selected: _selectedDays == 365,
                    onTap: () => setState(() => _selectedDays = 365),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      '💳 ${ctrl.tr('pay_by_card')}',
                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      ctrl.tr('card_instruction'),
                      style: TextStyle(fontSize: 12.8, color: Theme.of(context).hintColor, height: 1.35),
                    ),
                    const SizedBox(height: 12),
                    InkWell(
                      borderRadius: BorderRadius.circular(14),
                      onTap: () {
                        Clipboard.setData(ClipboardData(text: u.cardNumber));
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text(ctrl.tr('copied')), duration: const Duration(seconds: 1)),
                        );
                      },
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
                        decoration: BoxDecoration(
                          color: AppColors.primary.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: AppColors.primary.withValues(alpha: 0.35)),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              u.cardNumber,
                              style: const TextStyle(fontSize: 16.5, fontWeight: FontWeight.w800, letterSpacing: 1.1),
                            ),
                            const Icon(Icons.copy_rounded, size: 20, color: AppColors.primary),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 14),
                    ElevatedButton.icon(
                      onPressed: _busyReceipt ? null : _uploadReceipt,
                      icon: _busyReceipt
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2.2, color: Colors.white),
                            )
                          : const Icon(Icons.receipt_long_rounded),
                      label: Text(ctrl.tr('upload_receipt')),
                    ),
                    const SizedBox(height: 10),
                    OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(
                        minimumSize: const Size.fromHeight(48),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      ),
                      onPressed: () => launchUrl(
                        Uri.parse('https://t.me/${u.botUsername}'),
                        mode: LaunchMode.externalApplication,
                      ),
                      icon: const Icon(Icons.star_rounded, color: AppColors.amber),
                      label: Text(ctrl.tr('pay_by_stars')),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '🎟 ${ctrl.tr('promo_title')}',
                      style: const TextStyle(fontSize: 15.5, fontWeight: FontWeight.w800),
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _promoCtrl,
                            textCapitalization: TextCapitalization.characters,
                            decoration: InputDecoration(
                              hintText: ctrl.tr('promo_hint'),
                              contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        ElevatedButton(
                          style: ElevatedButton.styleFrom(minimumSize: const Size(120, 48)),
                          onPressed: _busyPromo ? null : _applyPromo,
                          child: Text(ctrl.tr('promo_apply')),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _featLine(String text) {
    return Row(
      children: [
        const Icon(Icons.check_circle_rounded, color: Colors.white, size: 17),
        const SizedBox(width: 8),
        Expanded(
          child: Text(text, style: const TextStyle(color: Colors.white, fontSize: 12.5, fontWeight: FontWeight.w600)),
        ),
      ],
    );
  }
}

class _PlanOptionCard extends StatelessWidget {
  final String title;
  final String priceUzs;
  final String stars;
  final String? badge;
  final bool selected;
  final VoidCallback onTap;

  const _PlanOptionCard({
    required this.title,
    required this.priceUzs,
    required this.stars,
    this.badge,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(18),
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          color: selected ? AppColors.amber.withValues(alpha: 0.14) : Theme.of(context).cardTheme.color,
          border: Border.all(
            color: selected ? AppColors.amber : Colors.grey.withValues(alpha: 0.25),
            width: selected ? 2.0 : 1.0,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (badge != null)
              Container(
                margin: const EdgeInsets.only(bottom: 6),
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                decoration: BoxDecoration(
                  color: AppColors.amber,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  badge!,
                  style: const TextStyle(color: Colors.black, fontSize: 9.5, fontWeight: FontWeight.w900),
                ),
              ),
            Text(title, style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            Text(priceUzs, style: const TextStyle(fontSize: 16.5, fontWeight: FontWeight.w900, color: AppColors.amber)),
            const SizedBox(height: 2),
            Text(stars, style: TextStyle(fontSize: 12, color: Theme.of(context).hintColor)),
          ],
        ),
      ),
    );
  }
}
