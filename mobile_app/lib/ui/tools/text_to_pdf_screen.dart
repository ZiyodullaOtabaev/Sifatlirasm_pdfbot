import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;

import '../../core/theme.dart';
import '../../data/api_service.dart';
import '../app_controller.dart';
import '../common/result_sheet.dart';

class TextToPdfScreen extends StatefulWidget {
  final AppController ctrl;
  const TextToPdfScreen({super.key, required this.ctrl});

  @override
  State<TextToPdfScreen> createState() => _TextToPdfScreenState();
}

class _TextToPdfScreenState extends State<TextToPdfScreen> {
  final TextEditingController _titleCtrl = TextEditingController();
  final TextEditingController _textCtrl = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _titleCtrl.dispose();
    _textCtrl.dispose();
    super.dispose();
  }

  Future<void> _generate() async {
    final text = _textCtrl.text.trim();
    final title = _titleCtrl.text.trim();
    if (text.isEmpty || _busy) return;

    setState(() => _busy = true);
    try {
      List<int>? pdfBytes;

      // Primary: Server DejaVuSans generator (100% Cyrillic + Uzbek + Latin Unicode support)
      try {
        if (widget.ctrl.storage.authToken == null) {
          await widget.ctrl.api.authenticateDevice();
        }
        final resp = await http
            .post(
              Uri.parse('${widget.ctrl.storage.apiBaseUrl}/api/v1/convert/text-to-pdf'),
              headers: {
                'Authorization': 'Bearer ${widget.ctrl.storage.authToken}',
                'Content-Type': 'application/json',
              },
              body: jsonEncode({'title': title, 'text': text}),
            )
            .timeout(const Duration(seconds: 20));

        if (resp.statusCode == 402) {
          final d = jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
          throw QuotaExceededException((d['error'] ?? 'Limit').toString());
        } else if (resp.statusCode == 200) {
          pdfBytes = resp.bodyBytes;
        }
      } on QuotaExceededException {
        rethrow;
      } catch (_) {
        // Offline fallback using local dart pdf package
      }

      if (pdfBytes == null) {
        final doc = pw.Document();
        doc.addPage(
          pw.MultiPage(
            pageFormat: PdfPageFormat.a4,
            margin: const pw.EdgeInsets.all(42),
            build: (_) => [
              if (title.isNotEmpty) ...[
                pw.Text(title, style: pw.TextStyle(fontSize: 18, fontWeight: pw.FontWeight.bold)),
                pw.SizedBox(height: 14),
              ],
              pw.Text(text, style: const pw.TextStyle(fontSize: 12, lineSpacing: 4)),
            ],
          ),
        );
        pdfBytes = await doc.save();
      }

      final saved = await widget.ctrl.saveGeneratedFile(
        bytes: pdfBytes,
        fileName: title.isNotEmpty ? '$title.pdf' : 'text_document.pdf',
        toolKey: 'text_pdf',
      );

      if (mounted) {
        showConversionSuccessSheet(context: context, ctrl: widget.ctrl, savedFile: saved);
      }
    } on QuotaExceededException catch (qe) {
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
    return Scaffold(
      appBar: AppBar(title: Text(ctrl.tr('t_text_pdf'))),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            TextField(
              controller: _titleCtrl,
              decoration: InputDecoration(
                hintText: ctrl.tr('doc_title_hint'),
                prefixIcon: const Icon(Icons.title_rounded),
              ),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: TextField(
                controller: _textCtrl,
                maxLines: null,
                expands: true,
                textAlignVertical: TextAlignVertical.top,
                decoration: InputDecoration(
                  hintText: ctrl.tr('doc_text_hint'),
                  contentPadding: const EdgeInsets.all(16),
                ),
              ),
            ),
            const SizedBox(height: 14),
            SafeArea(
              top: false,
              child: ElevatedButton.icon(
                onPressed: _busy ? null : _generate,
                icon: _busy
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2.4, color: Colors.white),
                      )
                    : const Icon(Icons.picture_as_pdf_rounded),
                label: Text(_busy ? ctrl.tr('converting') : ctrl.tr('convert_btn')),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
