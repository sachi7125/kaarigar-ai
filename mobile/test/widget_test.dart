import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:kaarigar/main.dart';

void main() {
  setUpAll(() {
    // The test VM has no platform channel for sqflite; back it with the
    // FFI implementation so HomeScreen's local-db read in initState works.
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });

  testWidgets('App launches to the home screen', (WidgetTester tester) async {
    await tester.pumpWidget(const KaarigarApp());
    await tester.pump();

    expect(find.text('KaarigarAI'), findsOneWidget);
    expect(find.text('No listings yet'), findsOneWidget);
    expect(find.byIcon(Icons.camera_alt), findsOneWidget);
  });
}
