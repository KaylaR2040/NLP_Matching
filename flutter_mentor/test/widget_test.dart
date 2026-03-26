import 'package:flutter_test/flutter_test.dart';

import 'package:flutter_mentor/main.dart';

void main() {
  testWidgets('mentor app boots', (WidgetTester tester) async {
    await tester.pumpWidget(const MyApp());
    await tester.pumpAndSettle();

    expect(find.byType(MyApp), findsOneWidget);
  });
}
