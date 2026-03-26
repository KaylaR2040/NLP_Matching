import 'package:flutter_test/flutter_test.dart';

import 'package:flutter_userforms/main.dart';

void main() {
  testWidgets('app shows the loading screen on startup', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const MyApp());
    await tester.pumpAndSettle();

    expect(find.byType(MyApp), findsOneWidget);
  });
}
