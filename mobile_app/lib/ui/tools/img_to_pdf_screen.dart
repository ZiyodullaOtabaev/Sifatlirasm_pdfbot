import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;

import '../../core/theme.dart';
import '../../data/api_service.dart';
import '../app_controller.dart';
import '../common/result_sheet.dart';

class ImgToPdfScreen extends StatefulWidget {
  final AppController ctrl;
  const ImgToPdfScreen({super.key, required this.ctrl});

  @override
  State<ImgToPdfScreen> createState() => _ImgToPdfScreenState();
}

class _ImgToPdfScreenState extends State<ImgToPdfScreen> {
  final ImagePicker _picker = ImagePicker();
  final List<XFile> _images = [];
  bool _a4Fit = true;
  bool _busy = false;

  Future<void> _pickGallery() async {
    final picked = await _picker.pickMultiImage(imageQuality: 92);
    if (picked.isNotEmpty) {
      setState(() => _images.addAll(picked));
    }
  }

  Future<void> _pickCamera() async {
    final shot = await _picker.pickImage(source: ImageSource.camera, imageQuality: 92);
    if (shot != null) {
      setState(() => _images.add(shot));
    }
  }

  Future<void> _generatePdf() async {
    if (_images.isEmpty || _busy) return;
    setState(() => _busy = true);

    try {
      // Check/log quota if online; allow offline generation seamlessly if unreachable
      try {
        final updated = await widget.ctrl.api.logLocalUsage('img_pdf');
        if (updated != null) widget.ctrl.updateUserSnapshot(updated);
      } on QuotaExceededException catch (qe) {
        if (qe.updatedUser != null) widget.ctrl.updateUserSnapshot(qe.updatedUser!);
        if (mounted) {
          showQuotaLimitDialog(context: context, ctrl: widget.ctrl, message: qe.message);
        }
        return;
      } catch (_) {}

      final pdf = pw.Document();
      for (final imgFile in _images) {
        final bytes = await File(imgFile.path).readAsBytes();
        final memImg = pw.MemoryImage(bytes);

        if (_a4Fit) {
          pdf.addPage(
            pw.Page(
              pageFormat: PdfPageFormat.a4,
              margin: const pw.EdgeInsets.all(14),
              build: (_) => pw.Center(
                child: pw.Image(memImg, fit: pw.BoxFit.contain),
              ),
            ),
          );
        } else {
          pdf.addPage(
            pw.Page(
              margin: pw.EdgeInsets.zero,
              build: (_) => pw.Center(child: pw.Image(memImg, fit: pw.BoxFit.contain)),
            ),
          );
        }
      }

      final outBytes = await pdf.save();
      final saved = await widget.ctrl.saveGeneratedFile(
        bytes: outBytes,
        fileName: 'images_${_images.length}p.pdf',
        toolKey: 'img_pdf',
        metaNote: '${_images.length} pages',
      );

      if (mounted) {
        showConversionSuccessSheet(
          context: context,
          ctrl: widget.ctrl,
          savedFile: saved,
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString()), backgroundColor: AppColors.rose),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ctrl = widget.ctrl;
    return Scaffold(
      appBar: AppBar(title: Text(ctrl.tr('t_img_pdf'))),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 8),
            child: Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size.fromHeight(48),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    ),
                    onPressed: _busy ? null : _pickGallery,
                    icon: const Icon(Icons.photo_library_rounded),
                    label: Text(ctrl.tr('pick_gallery')),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size.fromHeight(48),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    ),
                    onPressed: _busy ? null : _pickCamera,
                    icon: const Icon(Icons.camera_alt_rounded),
                    label: Text(ctrl.tr('pick_camera')),
                  ),
                ),
              ],
            ),
          ),
          if (_images.isNotEmpty) ...[
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              child: Row(
                children: [
                  const Icon(Icons.drag_indicator_rounded, size: 18, color: AppColors.cyan),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      ctrl.tr('reorder_hint'),
                      style: TextStyle(fontSize: 12, color: Theme.of(context).hintColor),
                    ),
                  ),
                  ChoiceChip(
                    label: const Text('A4'),
                    selected: _a4Fit,
                    onSelected: (v) => setState(() => _a4Fit = v),
                  ),
                ],
              ),
            ),
          ],
          Expanded(
            child: _images.isEmpty
                ? Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.add_photo_alternate_rounded, size: 68, color: AppColors.primary.withValues(alpha: 0.45)),
                        const SizedBox(height: 12),
                        Text(ctrl.tr('t_img_pdf_d'), style: TextStyle(color: Theme.of(context).hintColor)),
                      ],
                    ),
                  )
                : ReorderableListView.builder(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                    itemCount: _images.length,
                    onReorderItem: (oldIdx, newIdx) {
                      setState(() {
                        final item = _images.removeAt(oldIdx);
                        _images.insert(newIdx, item);
                      });
                    },
                    itemBuilder: (ctx, idx) {
                      final img = _images[idx];
                      return Card(
                        key: ValueKey('${img.path}_$idx'),
                        margin: const EdgeInsets.only(bottom: 10),
                        child: ListTile(
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                          leading: ClipRRect(
                            borderRadius: BorderRadius.circular(10),
                            child: Image.file(
                              File(img.path),
                              width: 52,
                              height: 52,
                              fit: BoxFit.cover,
                            ),
                          ),
                          title: Text(
                            '#${idx + 1} • ${img.name}',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                          ),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              IconButton(
                                icon: const Icon(Icons.close_rounded, color: AppColors.rose),
                                onPressed: () => setState(() => _images.removeAt(idx)),
                              ),
                              const Icon(Icons.drag_handle_rounded),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
              child: ElevatedButton.icon(
                onPressed: (_images.isEmpty || _busy) ? null : _generatePdf,
                icon: _busy
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2.4, color: Colors.white),
                      )
                    : const Icon(Icons.picture_as_pdf_rounded),
                label: Text(_busy ? ctrl.tr('converting') : '${ctrl.tr('convert_btn')} (${_images.length})'),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
