import 'package:flutter/material.dart';

import '../../core/theme.dart';
import '../app_controller.dart';

class SuperAdminScreen extends StatefulWidget {
  final AppController ctrl;
  const SuperAdminScreen({super.key, required this.ctrl});

  @override
  State<SuperAdminScreen> createState() => _SuperAdminScreenState();
}

class _SuperAdminScreenState extends State<SuperAdminScreen> {
  final TextEditingController _passCtrl = TextEditingController();
  final TextEditingController _vipUserCtrl = TextEditingController();
  final TextEditingController _promoCodeCtrl = TextEditingController();
  final TextEditingController _promoValCtrl = TextEditingController(text: '5');

  Map<String, dynamic>? _dash;
  bool _loading = false;
  bool _obscure = true;

  @override
  void initState() {
    super.initState();
    if (widget.ctrl.storage.adminToken != null) {
      _loadDashboard();
    }
  }

  @override
  void dispose() {
    _passCtrl.dispose();
    _vipUserCtrl.dispose();
    _promoCodeCtrl.dispose();
    _promoValCtrl.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    setState(() => _loading = true);
    try {
      await widget.ctrl.api.adminLogin(_passCtrl.text);
      _passCtrl.clear();
      await _loadDashboard();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString()), backgroundColor: AppColors.rose),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _loadDashboard() async {
    setState(() => _loading = true);
    try {
      final d = await widget.ctrl.api.fetchAdminDashboard();
      if (mounted) setState(() => _dash = d);
    } catch (_) {
      if (mounted) setState(() => _dash = null);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _editSettingDialog(String key, String label, String current) async {
    final c = TextEditingController(text: current);
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(label),
        content: TextField(controller: c),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(minimumSize: const Size(90, 42)),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Save'),
          ),
        ],
      ),
    );
    if (ok == true) {
      await widget.ctrl.api.updateAdminSettings({key: c.text.trim()});
      await _loadDashboard();
    }
  }

  @override
  Widget build(BuildContext context) {
    final authed = widget.ctrl.storage.adminToken != null && _dash != null;
    return Scaffold(
      appBar: AppBar(
        title: const Text('🛠 Super Admin Center', style: TextStyle(fontWeight: FontWeight.w800)),
        actions: [
          if (authed)
            IconButton(
              icon: const Icon(Icons.logout_rounded),
              onPressed: () async {
                await widget.ctrl.storage.setAdminToken(null);
                setState(() => _dash = null);
              },
            ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : !authed
              ? _buildLogin()
              : _buildDashboard(),
    );
  }

  Widget _buildLogin() {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.shield_rounded, size: 64, color: AppColors.amber),
          const SizedBox(height: 16),
          const Text(
            'Super Admin Kirish',
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 20),
          TextField(
            controller: _passCtrl,
            obscureText: _obscure,
            decoration: InputDecoration(
              hintText: 'Super Admin paroli',
              prefixIcon: const Icon(Icons.key_rounded),
              suffixIcon: IconButton(
                icon: Icon(_obscure ? Icons.visibility_rounded : Icons.visibility_off_rounded),
                onPressed: () => setState(() => _obscure = !_obscure),
              ),
            ),
          ),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: _login,
            child: const Text('Kirish / Login'),
          ),
        ],
      ),
    );
  }

  Widget _buildDashboard() {
    final s = (_dash!['summary'] as Map<String, dynamic>?) ?? {};
    final fin = (_dash!['finance'] as Map<String, dynamic>?) ?? {};
    final totFin = (fin['total'] as Map<String, dynamic>?) ?? {};
    final settings = (_dash!['settings'] as Map<String, dynamic>?) ?? {};
    final mobileDevs = _dash!['mobile_devices'] ?? 0;
    final maint = settings['maintenance_mode']?.toString() == '1';

    return RefreshIndicator(
      onRefresh: _loadDashboard,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 10,
            crossAxisSpacing: 10,
            childAspectRatio: 1.65,
            children: [
              _statTile('👥 Jami Users', '${s['total_users'] ?? 0}', AppColors.primary),
              _statTile('📱 Mobil Qurilmalar', '$mobileDevs', AppColors.cyan),
              _statTile('💎 Aktiv VIP', '${s['active_vip'] ?? 0}', AppColors.amber),
              _statTile('⚡ 24s Aktiv / Ishlar', '${s['active_24h'] ?? 0} / ${s['uses_today'] ?? 0}', AppColors.emerald),
              _statTile('💰 Tushum (UZS)', '${totFin['uzs'] ?? 0}', AppColors.emerald),
              _statTile('⭐ Tushum (Stars)', '${totFin['stars'] ?? 0}', AppColors.purple),
            ],
          ),
          const SizedBox(height: 18),
          Card(
            child: Column(
              children: [
                SwitchListTile(
                  title: const Text('🔧 Texnik ishlar rejimi (Maintenance)', style: TextStyle(fontWeight: FontWeight.w700)),
                  value: maint,
                  onChanged: (v) async {
                    await widget.ctrl.api.updateAdminSettings({'maintenance_mode': v ? '1' : '0'});
                    await _loadDashboard();
                  },
                ),
                const Divider(height: 1),
                ListTile(
                  title: const Text('Kunlik bepul limit'),
                  trailing: Text('${settings['daily_free_limit'] ?? '5'} ta ✏️', style: const TextStyle(fontWeight: FontWeight.bold)),
                  onTap: () => _editSettingDialog('daily_free_limit', 'Kunlik bepul limit', '${settings['daily_free_limit'] ?? '5'}'),
                ),
                const Divider(height: 1),
                ListTile(
                  title: const Text('1 Oylik VIP narxi (UZS)'),
                  trailing: Text('${settings['vip_30_uzs'] ?? '9000'} ✏️', style: const TextStyle(fontWeight: FontWeight.bold)),
                  onTap: () => _editSettingDialog('vip_30_uzs', '1 Oylik VIP (UZS)', '${settings['vip_30_uzs'] ?? '9000'}'),
                ),
                const Divider(height: 1),
                ListTile(
                  title: const Text('1 Yillik VIP narxi (UZS)'),
                  trailing: Text('${settings['vip_365_uzs'] ?? '29000'} ✏️', style: const TextStyle(fontWeight: FontWeight.bold)),
                  onTap: () => _editSettingDialog('vip_365_uzs', '1 Yillik VIP (UZS)', '${settings['vip_365_uzs'] ?? '29000'}'),
                ),
                const Divider(height: 1),
                ListTile(
                  title: const Text('Karta raqami'),
                  trailing: Text('${settings['card_number'] ?? ''} ✏️', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                  onTap: () => _editSettingDialog('card_number', 'Karta raqami', '${settings['card_number'] ?? ''}'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text('💎 Foydalanuvchiga VIP Berish', style: TextStyle(fontWeight: FontWeight.w800)),
                  const SizedBox(height: 10),
                  TextField(
                    controller: _vipUserCtrl,
                    decoration: const InputDecoration(hintText: 'User ID yoki @username'),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: ElevatedButton(
                          onPressed: () async {
                            if (_vipUserCtrl.text.trim().isEmpty) return;
                            await widget.ctrl.api.grantUserVip(_vipUserCtrl.text.trim(), 30);
                            _vipUserCtrl.clear();
                            await _loadDashboard();
                            if (mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('+30 kun VIP berildi!'), backgroundColor: AppColors.emerald),
                              );
                            }
                          },
                          child: const Text('+30 kun VIP'),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: ElevatedButton(
                          style: ElevatedButton.styleFrom(backgroundColor: AppColors.amber, foregroundColor: Colors.black),
                          onPressed: () async {
                            if (_vipUserCtrl.text.trim().isEmpty) return;
                            await widget.ctrl.api.grantUserVip(_vipUserCtrl.text.trim(), 365);
                            _vipUserCtrl.clear();
                            await _loadDashboard();
                            if (mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('+365 kun VIP berildi!'), backgroundColor: AppColors.emerald),
                              );
                            }
                          },
                          child: const Text('+365 kun VIP'),
                        ),
                      ),
                    ],
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
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text('🎟 Yangi Promokod Yaratish (+Bonus)', style: TextStyle(fontWeight: FontWeight.w800)),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        flex: 2,
                        child: TextField(
                          controller: _promoCodeCtrl,
                          textCapitalization: TextCapitalization.characters,
                          decoration: const InputDecoration(hintText: 'KOD (masalan BONUS10)'),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: TextField(
                          controller: _promoValCtrl,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(hintText: 'Miqdor'),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  ElevatedButton(
                    onPressed: () async {
                      final code = _promoCodeCtrl.text.trim();
                      final val = int.tryParse(_promoValCtrl.text.trim()) ?? 5;
                      if (code.isEmpty) return;
                      await widget.ctrl.api.createAdminPromo(
                        code: code,
                        rewardType: 'bonus_uses',
                        rewardValue: val,
                        maxUses: 100,
                      );
                      _promoCodeCtrl.clear();
                      await _loadDashboard();
                    },
                    child: const Text('Promokod yaratish'),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _statTile(String label, String val, Color c) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(label, style: const TextStyle(fontSize: 11.5)),
            const SizedBox(height: 6),
            Text(
              val,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: c),
            ),
          ],
        ),
      ),
    );
  }
}
