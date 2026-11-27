import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sifatli_pdf/data/api_service.dart';
import 'package:sifatli_pdf/data/storage_service.dart';
import 'package:sifatli_pdf/main.dart';
import 'package:sifatli_pdf/ui/app_controller.dart';

void main() {
  testWidgets('Sifatli PDF app renders 3-language navigation and tools', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});
    final storage = StorageService();
    await storage.init();
    final ctrl = AppController(storage: storage, api: ApiService(storage));

    await tester.pumpWidget(SifatliPdfApp(ctrl: ctrl));
    expect(find.text('Sifatli PDF'), findsOneWidget);
    expect(find.text('Rasm → PDF'), findsOneWidget);

    await ctrl.setLanguage('ru');
    await tester.pump();
    expect(find.text('Фото → PDF'), findsOneWidget);

    await ctrl.setLanguage('en');
    await tester.pump();
    expect(find.text('Image → PDF'), findsOneWidget);
  });
}
