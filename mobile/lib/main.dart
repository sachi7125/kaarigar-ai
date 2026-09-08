import 'package:flutter/material.dart';
import 'screens/home_screen.dart';
import 'screens/onboarding/language_screen.dart';
import 'services/artisan_session.dart';

void main() {
  runApp(const KaarigarApp());
}

class KaarigarApp extends StatelessWidget {
  const KaarigarApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'KaarigarAI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        fontFamily: 'Inter', // Assuming Inter is available or fallback
        primaryColor: const Color(0xFF4F46E5),
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF4F46E5)),
        useMaterial3: true,
      ),
      home: const _StartupGate(),
    );
  }
}

/// First run goes to language -> phone (LanguageScreen); a returning artisan
/// (already has a local artisan_id, verified or not — publish is the only
/// gate that checks verification) goes straight to Home.
class _StartupGate extends StatelessWidget {
  const _StartupGate({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<bool>(
      future: ArtisanSession.isOnboarded(),
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Scaffold(
            backgroundColor: Color(0xFFF9FAFB),
            body: Center(child: CircularProgressIndicator(color: Color(0xFF4F46E5))),
          );
        }
        return snapshot.data! ? const HomeScreen() : const LanguageScreen();
      },
    );
  }
}
