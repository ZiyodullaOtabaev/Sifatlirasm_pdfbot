import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../core/constants.dart';
import '../../core/theme.dart';
import '../../data/api_service.dart';
import '../app_controller.dart';
import '../common/result_sheet.dart';

enum CloudToolMode {
  pdfToWord,
  officeToPdf,
  mergePdf,
  compressPdf,
  pdfToImages,
  watermarkPdf,
}

class CloudToolScreen extends StatefulWidget {
  final AppController ctrl;
  final CloudToolMode mode;

  const CloudToolScreen({super.key, required this.ctrl, required this.mode});

  @override
  State<CloudToolScreen> createState() => _CloudToolScreenState();
}

class _CloudToolScreenState extends State<CloudToolScreen> {
  final List<PlatformFile> _files = [];
  final TextEditingController _watermarkCtrl = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _watermarkCtrl.dispose();
    super.dispose();
  }

  String get _titleKey {
    switch (widget.mode) {
      case CloudToolMode.pdfToWord:
        return 't_pdf_word';
      case CloudToolMode.officeToPdf:
        return 't_office_pdf';
      case CloudToolMode.mergePdf:
        return 't_merge_pdf';
      case CloudToolMode.compressPdf:
        return 't_compress_pdf';
      case CloudToolMode.pdfToImages:
        return 't_pdf_img';
      case CloudToolMode.watermarkPdf:
        return 't_watermark';
    }
  }

  String get _descKey => '${_titleKey}_d';

  bool get _isMulti => widget.mode == CloudToolMode.mergePdf;

  List<String> get _allowedExtensions {
    if (widget.mode == CloudToolMode.officeToPdf) {
      return AppConstants.officeExtensions;
    }
    return const ['pdf'];
  }

  Future<void> _pickFiles() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: _allowedExtensions,
      allowMultiple: _isMulti,
    );
    if (result != null && result.files.isNotEmpty) {
      setState(() {
        if (_isMulti) {
          _files.addAll(result.files.where((f) => f.path != null));
        } else {
          _files
            ..clear()
            ..addAll(result.files.where((f) => f.path != null).take(1));
        }
      });
    }
  }

  Future<void> _runConversion() async {
    if (_files.isEmpty || _busy) return;
    if (_isMulti && _files.length < 2) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(widget.ctrl.tr('pick_pdfs')), backgroundColor: AppColors.amber),
      );
      return;
    }
    if (widget.mode == CloudToolMode.watermarkPdf && _watermarkCtrl.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(widget.ctrl.tr('watermark_hint')), backgroundColor: AppColors.amber),
      );
      return;
    }

    setState(() => _busy = true);
    try {
      late String endpoint;
      late String outName;
      late String toolKey;
      Map<String, String>? fields;

      final firstStem = _files.first.name.replaceAll(RegExp(r'\.[^.]+$'), '');

      switch (widget.mode) {
        case CloudToolMode.pdfToWord:
          endpoint = '/api/v1/convert/pdf-to-word';
          outName = '$firstStem.docx';
          toolKey = 'pdf_to_word';
          break;
        case CloudToolMode.officeToPdf:
          endpoint = '/api/v1/convert/office-to-pdf';
          outName = '$firstStem.pdf';
          toolKey = 'office_to_pdf';
          break;
        case CloudToolMode.mergePdf:
          endpoint = '/api/v1/convert/merge-pdf';
          outName = 'merged_${_files.length}_files.pdf';
          toolKey = 'pdf_merge';
          break;
        case CloudToolMode.compressPdf:
          endpoint = '/api/v1/convert/compress-pdf';
          outName = 'compressed_$firstStem.pdf';
          toolKey = 'compress_pdf';
          break;
        case CloudToolMode.pdfToImages:
          endpoint = '/api/v1/convert/pdf-to-images';
          outName = '${firstStem}_images.zip';
          toolKey = 'pdf_to_img';
          break;
        case CloudToolMode.watermarkPdf:
          endpoint = '/api/v1/convert/watermark-pdf';
          outName = 'watermarked_$firstStem.pdf';
          toolKey = 'watermark_pdf';
          fields = {'text': _watermarkCtrl.text.trim()};
          break;
      }

      final res = await widget.ctrl.api.convertMultipart(
        endpoint: endpoint,
        filePaths: _files.map((e) => e.path!).toList(),
        fields: fields,
      );

      String? extraInfo;
      if (widget.mode == CloudToolMode.compressPdf) {
        final origKb = ((int.tryParse(res.headers['x-original-size'] ?? '0') ?? 0) / 1024).round();
        final compKb = ((int.tryParse(res.headers['x-compressed-size'] ?? '0') ?? 0) / 1024).round();
        final pct = res.headers['x-saved-pct'] ?? '0';
        extraInfo = '📁 $origKb KB ➡️ 📦 $compKb KB (-$pct%)';
      } else if (res.headers['x-pages'] != null) {
        extraInfo = '📄 ${res.headers['x-pages']} bet / стр. / pages';
      }

      final saved = await widget.ctrl.saveGeneratedFile(
        bytes: res.bytes,
        fileName: outName,
        toolKey: toolKey,
        metaNote: extraInfo,
      );

      if (mounted) {
        showConversionSuccessSheet(
          context: context,
          ctrl: widget.ctrl,
          savedFile: saved,
          extraSubtitle: extraInfo,
        );
      }
    } on QuotaExceededException catch (qe) {
      if (qe.updatedUser != null) widget.ctrl.updateUserSnapshot(qe.updatedUser!);
      if (mounted) {
        showQuotaLimitDialog(context: context, ctrl: widget.ctrl, message: qe.message);
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
    final pickLabel = widget.mode == CloudToolMode.officeToPdf
        ? ctrl.tr('pick_office')
        : _isMulti
            ? ctrl.tr('pick_pdfs')
            : ctrl.tr('pick_pdf');

    return Scaffold(
      appBar: AppBar(title: Text(ctrl.tr(_titleKey))),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: InkWell(
                borderRadius: BorderRadius.circular(20),
                onTap: _busy ? null : _pickFiles,
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 26, horizontal: 18),
                  child: Column(
                    children: [
                      Container(
                        width: 58,
                        height: 58,
                        decoration: BoxDecoration(
                          color: AppColors.primary.withValues(alpha: 0.14),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(Icons.upload_file_rounded, color: AppColors.primary, size: 30),
                      ),
                      const SizedBox(height: 12),
                      Text(pickLabel, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                      const SizedBox(height: 4),
                      Text(
                        ctrl.tr(_descKey),
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 12.5, color: Theme.of(context).hintColor),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            if (widget.mode == CloudToolMode.watermarkPdf) ...[
              const SizedBox(height: 14),
              TextField(
                controller: _watermarkCtrl,
                decoration: InputDecoration(
                  hintText: ctrl.tr('watermark_hint'),
                  prefixIcon: const Icon(Icons.branding_watermark_rounded),
                ),
              ),
            ],
            const SizedBox(height: 12),
            if (_isMulti && _files.length > 1)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(
                  ctrl.tr('reorder_hint'),
                  style: TextStyle(fontSize: 12, color: Theme.of(context).hintColor),
                ),
              ),
            Expanded(
              child: _isMulti
                  ? ReorderableListView.builder(
                      itemCount: _files.length,
                      onReorderItem: (oldIdx, newIdx) {
                        setState(() {
                          final item = _files.removeAt(oldIdx);
                          _files.insert(newIdx, item);
                        });
                      },
                      itemBuilder: (ctx, i) {
                        final f = _files[i];
                        return Card(
                          key: ValueKey('${f.path}_$i'),
                          margin: const EdgeInsets.only(bottom: 8),
                          child: ListTile(
                            leading: CircleAvatar(
                              backgroundColor: AppColors.cyan.withValues(alpha: 0.16),
                              child: Text('#${i + 1}', style: const TextStyle(fontWeight: FontWeight.bold)),
                            ),
                            title: Text(f.name, maxLines: 1, overflow: TextOverflow.ellipsis),
                            subtitle: Text('${(f.size / 1024).toStringAsFixed(1)} KB'),
                            trailing: IconButton(
                              icon: const Icon(Icons.close_rounded, color: AppColors.rose),
                              onPressed: () => setState(() => _files.removeAt(i)),
                            ),
                          ),
                        );
                      },
                    )
                  : ListView.builder(
                      itemCount: _files.length,
                      itemBuilder: (ctx, i) {
                        final f = _files[i];
                        return Card(
                          child: ListTile(
                            leading: const Icon(Icons.insert_drive_file_rounded, color: AppColors.primary, size: 32),
                            title: Text(f.name, maxLines: 1, overflow: TextOverflow.ellipsis),
                            subtitle: Text('${(f.size / 1024).toStringAsFixed(1)} KB'),
                            trailing: IconButton(
                              icon: const Icon(Icons.close_rounded, color: AppColors.rose),
                              onPressed: () => setState(() => _files.clear()),
                            ),
                          ),
                        );
                      },
                    ),
            ),
            SafeArea(
              top: false,
              child: ElevatedButton.icon(
                onPressed: (_files.isEmpty || _busy) ? null : _runConversion,
                icon: _busy
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2.4, color: Colors.white),
                      )
                    : const Icon(Icons.auto_awesome_rounded),
                label: Text(_busy ? ctrl.tr('converting') : ctrl.tr('convert_btn')),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
