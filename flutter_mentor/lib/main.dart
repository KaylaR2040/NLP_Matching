import 'package:flutter/material.dart';
import 'constants/ncsu_themes.dart';
import 'screens/mentor_form_screen.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'NCSU Mentor Portal',
      themeMode: ThemeMode.light,
      theme: NCSUTheme.light,
      darkTheme: NCSUTheme.dark,
      home: const MentorFormScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}
