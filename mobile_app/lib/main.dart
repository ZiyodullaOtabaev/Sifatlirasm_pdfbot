import 'package:flutter/material.dart';

import 'core/theme.dart';
import 'data/api_service.dart';
import 'data/storage_service.dart';
import 'ui/app_controller.dart';
import 'ui/files/my_files_screen.dart';
import 'ui/home/home_screen.dart';
import 'ui/profile/profile_screen.dart';
import 'ui/vip/vip_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final storage = StorageService();
  await storage.init();
  final api = ApiService(storage);
  final ctrl = AppController(storage: storage, api: api);
  ctrl.bootstrap();
  runApp(SifatliPdfApp(ctrl: ctrl));
}

class SifatliPdfApp extends StatelessWidget {
  final AppController ctrl;
  const SifatliPdfApp({super.key, required this.ctrl});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: ctrl,
      builder: (context, _) {
        return MaterialApp(
          title: 'Sifatli PDF',
          debugShowCheckedModeBanner: false,
          theme: AppTheme.light(),
          darkTheme: AppTheme.dark(),
          themeMode: ctrl.isDarkMode ? ThemeMode.dark : ThemeMode.light,
          home: MainShell(ctrl: ctrl),
        );
      },
    );
  }
}

class MainShell extends StatelessWidget {
  final AppController ctrl;
  const MainShell({super.key, required this.ctrl});

  @override
  Widget build(BuildContext context) {
    final pages = [
      SafeArea(child: HomeScreen(ctrl: ctrl)),
      MyFilesScreen(ctrl: ctrl),
      VipScreen(ctrl: ctrl),
      ProfileScreen(ctrl: ctrl),
    ];

    return Scaffold(
      body: IndexedStack(
        index: ctrl.navIndex,
        children: pages,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: ctrl.navIndex,
        onDestinationSelected: ctrl.setNavIndex,
        destinations: [
          NavigationDestination(
            icon: const Icon(Icons.grid_view_rounded),
            label: ctrl.tr('nav_tools'),
          ),
          NavigationDestination(
            icon: Badge(
              isLabelVisible: ctrl.savedFiles.isNotEmpty,
              label: Text('${ctrl.savedFiles.length}'),
              child: const Icon(Icons.folder_copy_rounded),
            ),
            label: ctrl.tr('nav_files'),
          ),
          NavigationDestination(
            icon: const Icon(Icons.workspace_premium_rounded, color: AppColors.amber),
            label: ctrl.tr('nav_vip'),
          ),
          NavigationDestination(
            icon: const Icon(Icons.person_rounded),
            label: ctrl.tr('nav_profile'),
          ),
        ],
      ),
    );
  }
}
