import 'package:flutter/material.dart';

class NCSUColors {
  static const Color wolfpackRed = Color.fromRGBO(204, 0, 0, 1);
  static const Color reynoldsRed = Color.fromRGBO(153, 0, 0, 1);
  static const Color wolfpackBlack = Color.fromRGBO(0, 0, 0, 1);
  static const Color wolfpackWhite = Color.fromRGBO(255, 255, 255, 1);
  static const Color bioIndigo = Color.fromRGBO(65, 86, 161, 1);
  static const Color innovationBlue = Color.fromRGBO(66, 126, 147, 1);
}

class NCSUTheme {
  static ThemeData get light {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: NCSUColors.wolfpackRed,
        primary: NCSUColors.wolfpackRed,
        onPrimary: NCSUColors.wolfpackWhite,
        surface: const Color(0xFFF7F7F7),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: NCSUColors.wolfpackRed,
        foregroundColor: NCSUColors.wolfpackWhite,
        centerTitle: false,
      ),
      scaffoldBackgroundColor: const Color(0xFFF4F4F4),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: NCSUColors.wolfpackRed,
          foregroundColor: NCSUColors.wolfpackWhite,
          minimumSize: const Size(140, 44),
        ),
      ),
      cardTheme: CardThemeData(
        color: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        elevation: 1,
      ),
    );
  }
}
