import 'dart:io';

import 'package:archive/archive.dart';
import 'package:flutter/material.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';
import 'package:printing/printing.dart';
import 'package:share_plus/share_plus.dart';

import '../../core/theme.dart';
import '../../domain/models.dart';
import '../app_controller.dart';

class InAppPdfViewerScreen extends StatelessWidget {
  final LocalSavedFile file;
  final AppController ctrl;

  const InAppPdfViewerScreen({super.key, required this.file, required this.ctrl});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(file.name, style: const TextStyle(fontSize: 16)),
        actions: [
          IconButton(
            icon: const Icon(Icons.share_rounded),
            onPressed: () => Share.shareXFiles([XFile(file.path)], text: file.name),
          ),
          IconButton(
            icon: const Icon(Icons.open_in_new_rounded),
            onPressed: () => OpenFilex.open(file.path),
          ),
        ],
      ),
      body: PdfPreview(
        build: (_) => File(file.path).readAsBytes(),
        canChangeOrientation: false,
        canChangePageFormat: false,
        canDebug: false,
        pdfFileName: file.name,
      ),
    );
  }
}

class ZipImagesPreviewScreen extends StatefulWidget {
  final LocalSavedFile zipFile;
  final AppController ctrl;

  const ZipImagesPreviewScreen({super.key, required this.zipFile, required this.ctrl});

  @override
  State<ZipImagesPreviewScreen> createState() => _ZipImagesPreviewScreenState();
}

class _ZipImagesPreviewScreenState extends State<ZipImagesPreviewScreen> {
  List<File> _extracted = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _unpack();
  }

  Future<void> _unpack() async {
    try {
      final bytes = await File(widget.zipFile.path).readAsBytes();
      final archive = ZipDecoder().decodeBytes(bytes);
      final tmp = await getTemporaryDirectory();
      final outDir = Directory('${tmp.path}/zip_${widget.zipFile.id}');
      if (!outDir.existsSync()) await outDir.create(recursive: true);

      final list = <File>[];
      for (final item in archive) {
        if (item.isFile && item.content != null) {
          final f = File('${outDir.path}/${item.name}');
          await f.writeAsBytes(item.content as List<int>);
          list.add(f);
        }
      }
      if (mounted) {
        setState(() {
          _extracted = list;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('${widget.zipFile.name} (${_extracted.length})'),
        actions: [
          IconButton(
            icon: const Icon(Icons.folder_zip_rounded),
            tooltip: widget.ctrl.tr('share_file'),
            onPressed: () => Share.shareXFiles([XFile(widget.zipFile.path)]),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : GridView.builder(
              padding: const EdgeInsets.all(14),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
                childAspectRatio: 0.72,
              ),
              itemCount: _extracted.length,
              itemBuilder: (ctx, i) {
                final img = _extracted[i];
                return GestureDetector(
                  onTap: () => Share.shareXFiles([XFile(img.path)]),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(14),
                    child: Stack(
                      fit: StackFit.expand,
                      children: [
                        Image.file(img, fit: BoxFit.cover),
                        Positioned(
                          top: 8,
                          left: 8,
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: Colors.black87,
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(
                              '#${i + 1}',
                              style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                            ),
                          ),
                        ),
                        Positioned(
                          bottom: 8,
                          right: 8,
                          child: CircleAvatar(
                            radius: 16,
                            backgroundColor: AppColors.primary,
                            child: const Icon(Icons.share_rounded, size: 16, color: Colors.white),
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
    );
  }
}

void showConversionSuccessSheet({
  required BuildContext context,
  required AppController ctrl,
  required LocalSavedFile savedFile,
  String? extraSubtitle,
}) {
  showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(26)),
    ),
    builder: (ctx) {
      return Padding(
        padding: const EdgeInsets.fromLTRB(22, 20, 22, 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 44,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey.withValues(alpha: 0.4),
                borderRadius: BorderRadius.circular(4),
              ),
            ),
            const SizedBox(height: 18),
            Container(
              width: 64,
              height: 64,
              decoration: BoxDecoration(
                color: AppColors.emerald.withValues(alpha: 0.16),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.check_circle_rounded, color: AppColors.emerald, size: 38),
            ),
            const SizedBox(height: 14),
            Text(
              ctrl.tr('ready_title'),
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 6),
            Text(
              '${savedFile.name} • ${savedFile.formattedSize}',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 13.5, color: Theme.of(ctx).hintColor),
            ),
            if (extraSubtitle != null && extraSubtitle.isNotEmpty) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  extraSubtitle,
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                ),
              ),
            ],
            const SizedBox(height: 8),
            Text(
              ctrl.tr('saved_note'),
              style: const TextStyle(fontSize: 12, color: AppColors.emerald),
            ),
            const SizedBox(height: 20),
            if (savedFile.isPdf) ...[
              ElevatedButton.icon(
                onPressed: () {
                  Navigator.pop(ctx);
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => InAppPdfViewerScreen(file: savedFile, ctrl: ctrl),
                    ),
                  );
                },
                icon: const Icon(Icons.visibility_rounded),
                label: Text(ctrl.tr('view_pdf')),
              ),
              const SizedBox(height: 10),
            ] else if (savedFile.isZip) ...[
              ElevatedButton.icon(
                onPressed: () {
                  Navigator.pop(ctx);
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => ZipImagesPreviewScreen(zipFile: savedFile, ctrl: ctrl),
                    ),
                  );
                },
                icon: const Icon(Icons.photo_library_rounded),
                label: Text(ctrl.tr('open_file')),
              ),
              const SizedBox(height: 10),
            ],
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size.fromHeight(48),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    ),
                    onPressed: () => OpenFilex.open(savedFile.path),
                    icon: const Icon(Icons.open_in_new_rounded, size: 19),
                    label: Text(ctrl.tr('open_file')),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.emerald,
                      minimumSize: const Size.fromHeight(48),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    ),
                    onPressed: () => Share.shareXFiles([XFile(savedFile.path)], text: savedFile.name),
                    icon: const Icon(Icons.share_rounded, size: 19),
                    label: Text(ctrl.tr('share_file')),
                  ),
                ),
              ],
            ),
          ],
        ),
      );
    },
  );
}

void showQuotaLimitDialog({
  required BuildContext context,
  required AppController ctrl,
  required String message,
}) {
  showDialog(
    context: context,
    builder: (ctx) => AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
      title: Row(
        children: [
          const Icon(Icons.workspace_premium_rounded, color: AppColors.amber, size: 28),
          const SizedBox(width: 8),
          Expanded(
            child: Text(ctrl.tr('limit_modal_title'), style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
      content: Text(message, style: const TextStyle(fontSize: 14.5, height: 1.4)),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(ctx),
          child: const Text('OK'),
        ),
        ElevatedButton.icon(
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.amber,
            foregroundColor: Colors.black,
            minimumSize: const Size(140, 44),
          ),
          onPressed: () {
            Navigator.pop(ctx);
            Navigator.popUntil(context, (r) => r.isFirst);
            ctrl.setNavIndex(2); // Switch to VIP tab
          },
          icon: const Icon(Icons.diamond_rounded, size: 18),
          label: Text(ctrl.tr('go_vip')),
        ),
      ],
    ),
  );
}
