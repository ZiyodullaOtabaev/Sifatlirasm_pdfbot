import 'package:flutter/material.dart';

import '../../core/theme.dart';
import '../app_controller.dart';
import '../tools/cloud_tool_screen.dart';
import '../tools/img_to_pdf_screen.dart';
import '../tools/text_to_pdf_screen.dart';

class HomeScreen extends StatelessWidget {
  final AppController ctrl;
  const HomeScreen({super.key, required this.ctrl});

  @override
  Widget build(BuildContext context) {
    final u = ctrl.user;
    return RefreshIndicator(
      onRefresh: ctrl.refreshProfile,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
        children: [
          _buildTopBar(context),
          const SizedBox(height: 16),
          _buildHeroBanner(context, u.isVip, u.dailyUsed, u.dailyLimit, u.bonusBalance),
          const SizedBox(height: 22),
          Padding(
            padding: const EdgeInsets.only(left: 4, bottom: 12),
            child: Text(
              ctrl.tr('section_tools').toUpperCase(),
              style: TextStyle(
                fontSize: 12.5,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.0,
                color: Theme.of(context).hintColor,
              ),
            ),
          ),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.06,
            children: [
              _ToolCard(
                title: ctrl.tr('t_img_pdf'),
                desc: ctrl.tr('t_img_pdf_d'),
                badge: ctrl.tr('badge_offline'),
                icon: Icons.photo_library_rounded,
                accent: AppColors.primary,
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => ImgToPdfScreen(ctrl: ctrl)),
                ),
              ),
              _ToolCard(
                title: ctrl.tr('t_text_pdf'),
                desc: ctrl.tr('t_text_pdf_d'),
                badge: ctrl.tr('badge_offline'),
                icon: Icons.article_rounded,
                accent: AppColors.emerald,
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => TextToPdfScreen(ctrl: ctrl)),
                ),
              ),
              _ToolCard(
                title: ctrl.tr('t_pdf_word'),
                desc: ctrl.tr('t_pdf_word_d'),
                badge: ctrl.tr('badge_smart'),
                icon: Icons.description_rounded,
                accent: const Color(0xFF3B82F6),
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => CloudToolScreen(ctrl: ctrl, mode: CloudToolMode.pdfToWord),
                  ),
                ),
              ),
              _ToolCard(
                title: ctrl.tr('t_office_pdf'),
                desc: ctrl.tr('t_office_pdf_d'),
                badge: ctrl.tr('badge_popular'),
                icon: Icons.slideshow_rounded,
                accent: AppColors.amber,
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => CloudToolScreen(ctrl: ctrl, mode: CloudToolMode.officeToPdf),
                  ),
                ),
              ),
              _ToolCard(
                title: ctrl.tr('t_merge_pdf'),
                desc: ctrl.tr('t_merge_pdf_d'),
                icon: Icons.merge_type_rounded,
                accent: AppColors.cyan,
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => CloudToolScreen(ctrl: ctrl, mode: CloudToolMode.mergePdf),
                  ),
                ),
              ),
              _ToolCard(
                title: ctrl.tr('t_compress_pdf'),
                desc: ctrl.tr('t_compress_pdf_d'),
                icon: Icons.compress_rounded,
                accent: AppColors.purple,
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => CloudToolScreen(ctrl: ctrl, mode: CloudToolMode.compressPdf),
                  ),
                ),
              ),
              _ToolCard(
                title: ctrl.tr('t_pdf_img'),
                desc: ctrl.tr('t_pdf_img_d'),
                icon: Icons.burst_mode_rounded,
                accent: AppColors.rose,
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => CloudToolScreen(ctrl: ctrl, mode: CloudToolMode.pdfToImages),
                  ),
                ),
              ),
              _ToolCard(
                title: ctrl.tr('t_watermark'),
                desc: ctrl.tr('t_watermark_d'),
                icon: Icons.branding_watermark_rounded,
                accent: const Color(0xFF0EA5E9),
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => CloudToolScreen(ctrl: ctrl, mode: CloudToolMode.watermarkPdf),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildTopBar(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            gradient: AppColors.heroGradient,
            borderRadius: BorderRadius.circular(13),
            boxShadow: [
              BoxShadow(
                color: AppColors.primary.withValues(alpha: 0.35),
                blurRadius: 14,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: const Icon(Icons.picture_as_pdf_rounded, color: Colors.white, size: 24),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                ctrl.tr('app_title'),
                style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w800, letterSpacing: -0.3),
              ),
              Text(
                ctrl.tr('app_subtitle'),
                style: const TextStyle(fontSize: 12, color: AppColors.cyan, fontWeight: FontWeight.w600),
              ),
            ],
          ),
        ),
        PopupMenuButton<String>(
          onSelected: ctrl.setLanguage,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          itemBuilder: (_) => const [
            PopupMenuItem(value: 'uz', child: Text("🇺🇿 O'zbekcha")),
            PopupMenuItem(value: 'ru', child: Text('🇷🇺 Русский')),
            PopupMenuItem(value: 'en', child: Text('🇬🇧 English')),
          ],
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
            decoration: BoxDecoration(
              color: AppColors.primary.withValues(alpha: 0.14),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppColors.primary.withValues(alpha: 0.35)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  ctrl.lang == 'ru' ? '🇷🇺 RU' : ctrl.lang == 'en' ? '🇬🇧 EN' : '🇺🇿 UZ',
                  style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700),
                ),
                const SizedBox(width: 4),
                const Icon(Icons.keyboard_arrow_down_rounded, size: 16),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildHeroBanner(
    BuildContext context,
    bool isVip,
    int dailyUsed,
    int dailyLimit,
    int bonus,
  ) {
    final freeLeft = dailyLimit == 0 ? '∞' : '${(dailyLimit - dailyUsed).clamp(0, dailyLimit)}/$dailyLimit';
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: AppColors.heroGradient,
        borderRadius: BorderRadius.circular(22),
        boxShadow: [
          BoxShadow(
            color: AppColors.primary.withValues(alpha: 0.32),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              ctrl.tr('hero_badge'),
              style: const TextStyle(color: Colors.white, fontSize: 10.5, fontWeight: FontWeight.w800, letterSpacing: 0.6),
            ),
          ),
          const SizedBox(height: 10),
          Text(
            ctrl.tr('hero_title'),
            style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 6),
          Text(
            ctrl.tr('hero_desc'),
            style: TextStyle(color: Colors.white.withValues(alpha: 0.88), fontSize: 12.8, height: 1.35),
          ),
          const SizedBox(height: 14),
          InkWell(
            onTap: () => ctrl.setNavIndex(2),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.26),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  Icon(
                    isVip ? Icons.workspace_premium_rounded : Icons.bolt_rounded,
                    color: AppColors.amber,
                    size: 19,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      isVip
                          ? '💎 ${ctrl.tr('vip_unlimited')}'
                          : '${ctrl.tr('free_remaining')}: $freeLeft${bonus > 0 ? '  •  +$bonus ${ctrl.tr('bonus_uses')}' : ''}',
                      style: const TextStyle(color: Colors.white, fontSize: 12.5, fontWeight: FontWeight.w700),
                    ),
                  ),
                  const Icon(Icons.arrow_forward_ios_rounded, color: Colors.white70, size: 13),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ToolCard extends StatelessWidget {
  final String title;
  final String desc;
  final String? badge;
  final IconData icon;
  final Color accent;
  final VoidCallback onTap;

  const _ToolCard({
    required this.title,
    required this.desc,
    this.badge,
    required this.icon,
    required this.accent,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    width: 42,
                    height: 42,
                    decoration: BoxDecoration(
                      color: accent.withValues(alpha: 0.16),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(icon, color: accent, size: 23),
                  ),
                  if (badge != null)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                      decoration: BoxDecoration(
                        color: accent.withValues(alpha: 0.14),
                        borderRadius: BorderRadius.circular(7),
                      ),
                      child: Text(
                        badge!,
                        style: TextStyle(color: accent, fontSize: 10, fontWeight: FontWeight.w800),
                      ),
                    ),
                ],
              ),
              const Spacer(),
              Text(
                title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 4),
              Text(
                desc,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 11.5, color: Theme.of(context).hintColor, height: 1.25),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
