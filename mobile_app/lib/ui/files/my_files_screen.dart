import 'package:flutter/material.dart';
import 'package:open_filex/open_filex.dart';
import 'package:share_plus/share_plus.dart';

import '../../core/theme.dart';
import '../../domain/models.dart';
import '../app_controller.dart';
import '../common/result_sheet.dart';

class MyFilesScreen extends StatelessWidget {
  final AppController ctrl;
  const MyFilesScreen({super.key, required this.ctrl});

  IconData _iconFor(LocalSavedFile f) {
    if (f.isPdf) return Icons.picture_as_pdf_rounded;
    if (f.isDocx) return Icons.description_rounded;
    if (f.isZip) return Icons.folder_zip_rounded;
    return Icons.insert_drive_file_rounded;
  }

  Color _colorFor(LocalSavedFile f) {
    if (f.isPdf) return AppColors.rose;
    if (f.isDocx) return const Color(0xFF3B82F6);
    if (f.isZip) return AppColors.amber;
    return AppColors.primary;
  }

  void _openItem(BuildContext context, LocalSavedFile f) {
    if (f.isPdf) {
      Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => InAppPdfViewerScreen(file: f, ctrl: ctrl)),
      );
    } else if (f.isZip) {
      Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => ZipImagesPreviewScreen(zipFile: f, ctrl: ctrl)),
      );
    } else {
      OpenFilex.open(f.path);
    }
  }

  @override
  Widget build(BuildContext context) {
    final files = ctrl.savedFiles;
    return Scaffold(
      appBar: AppBar(
        title: Text(ctrl.tr('files_title'), style: const TextStyle(fontWeight: FontWeight.w800)),
        actions: [
          if (files.isNotEmpty)
            TextButton.icon(
              onPressed: () => ctrl.clearAllFiles(),
              icon: const Icon(Icons.delete_sweep_rounded, color: AppColors.rose, size: 20),
              label: Text(ctrl.tr('clear_all'), style: const TextStyle(color: AppColors.rose)),
            ),
        ],
      ),
      body: files.isEmpty
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.folder_open_rounded, size: 72, color: AppColors.primary.withValues(alpha: 0.4)),
                    const SizedBox(height: 14),
                    Text(
                      ctrl.tr('files_empty'),
                      textAlign: TextAlign.center,
                      style: TextStyle(fontSize: 14.5, color: Theme.of(context).hintColor, height: 1.4),
                    ),
                  ],
                ),
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
              itemCount: files.length,
              itemBuilder: (ctx, i) {
                final f = files[i];
                final clr = _colorFor(f);
                return Card(
                  margin: const EdgeInsets.only(bottom: 10),
                  child: ListTile(
                    onTap: () => _openItem(context, f),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                    leading: Container(
                      width: 46,
                      height: 46,
                      decoration: BoxDecoration(
                        color: clr.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(_iconFor(f), color: clr, size: 25),
                    ),
                    title: Text(
                      f.name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14.5),
                    ),
                    subtitle: Text(
                      '${f.formattedSize}${f.metaNote != null ? ' • ${f.metaNote}' : ''}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 12),
                    ),
                    trailing: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        IconButton(
                          icon: const Icon(Icons.share_rounded, size: 20, color: AppColors.emerald),
                          onPressed: () => Share.shareXFiles([XFile(f.path)], text: f.name),
                        ),
                        IconButton(
                          icon: const Icon(Icons.delete_outline_rounded, size: 20, color: AppColors.rose),
                          onPressed: () => ctrl.deleteFile(f.id),
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
