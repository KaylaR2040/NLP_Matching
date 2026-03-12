import 'package:flutter/material.dart';

/// NC State University brand colors and theme.
/// Reference: https://brand.ncsu.edu/designing-for-nc-state/color/
class NCSUColors {
  NCSUColors._();

  // ───────────────────────────────────────────────
  // Primary palette
  // ───────────────────────────────────────────────

  static const Color wolfpackRed   = Color.fromRGBO(204, 0, 0, 1);
  static const Color wolfpackBlack = Color.fromRGBO(0, 0, 0, 1);
  static const Color wolfpackWhite = Color.fromRGBO(255, 255, 255, 1);

  // ───────────────────────────────────────────────
  // Expanded palette
  // ───────────────────────────────────────────────

  static const Color reynoldsRed    = Color.fromRGBO(153, 0, 0, 1);
  static const Color pyromanFlame   = Color.fromRGBO(209, 73, 5, 1);
  static const Color huntYellow     = Color.fromRGBO(250, 200, 0, 1);
  static const Color genomicGreen   = Color.fromRGBO(111, 125, 28, 1);
  static const Color carmichaelAqua = Color.fromRGBO(0, 132, 115, 1);
  static const Color innovationBlue = Color.fromRGBO(66, 126, 147, 1);
  static const Color bioIndigo      = Color.fromRGBO(65, 86, 161, 1);

  // ───────────────────────────────────────────────
  // Wolfpack Red - tints & shades (light → dark)
  // ───────────────────────────────────────────────

  static const Color wolfpackRed100 = Color.fromRGBO(234, 21, 0, 1);
  static const Color wolfpackRed200 = Color.fromRGBO(204, 0, 0, 1); // same as wolfpackRed
  static const Color wolfpackRed300 = Color.fromRGBO(180, 0, 0, 1);
  static const Color wolfpackRed400 = Color.fromRGBO(153, 0, 0, 1); // same as reynoldsRed
  static const Color wolfpackRed500 = Color.fromRGBO(126, 0, 0, 1);
  static const Color wolfpackRed600 = Color.fromRGBO(94, 0, 0, 1);
  static const Color wolfpackRed700 = Color.fromRGBO(62, 0, 0, 1);

  // ───────────────────────────────────────────────
  // Pyroman Flame - tints & shades
  // ───────────────────────────────────────────────

  static const Color pyromanFlame100 = Color.fromRGBO(248, 168, 18, 1);
  static const Color pyromanFlame200 = Color.fromRGBO(242, 140, 13, 1);
  static const Color pyromanFlame300 = Color.fromRGBO(225, 100, 8, 1);
  static const Color pyromanFlame400 = Color.fromRGBO(209, 73, 5, 1); // same as pyromanFlame
  static const Color pyromanFlame500 = Color.fromRGBO(192, 48, 3, 1);
  static const Color pyromanFlame600 = Color.fromRGBO(169, 27, 2, 1);
  static const Color pyromanFlame700 = Color.fromRGBO(145, 14, 1, 1);

  // ───────────────────────────────────────────────
  // Hunt Yellow - tints & shades
  // ───────────────────────────────────────────────

  static const Color huntYellow100 = Color.fromRGBO(254, 248, 203, 1);
  static const Color huntYellow200 = Color.fromRGBO(253, 229, 101, 1);
  static const Color huntYellow300 = Color.fromRGBO(248, 218, 62, 1);
  static const Color huntYellow400 = Color.fromRGBO(250, 200, 0, 1); // same as huntYellow
  static const Color huntYellow500 = Color.fromRGBO(215, 167, 0, 1);
  static const Color huntYellow600 = Color.fromRGBO(184, 136, 0, 1);
  static const Color huntYellow700 = Color.fromRGBO(150, 109, 0, 1);

  // ───────────────────────────────────────────────
  // Genomic Green - tints & shades
  // ───────────────────────────────────────────────

  static const Color genomicGreen100 = Color.fromRGBO(191, 204, 70, 1);
  static const Color genomicGreen200 = Color.fromRGBO(162, 183, 41, 1);
  static const Color genomicGreen300 = Color.fromRGBO(141, 158, 43, 1);
  static const Color genomicGreen400 = Color.fromRGBO(111, 125, 28, 1); // same as genomicGreen
  static const Color genomicGreen500 = Color.fromRGBO(88, 104, 0, 1);
  static const Color genomicGreen600 = Color.fromRGBO(66, 76, 9, 1);
  static const Color genomicGreen700 = Color.fromRGBO(47, 58, 3, 1);

  // ───────────────────────────────────────────────
  // Carmichael Aqua - tints & shades
  // ───────────────────────────────────────────────

  static const Color carmichaelAqua100 = Color.fromRGBO(145, 242, 203, 1);
  static const Color carmichaelAqua200 = Color.fromRGBO(87, 218, 177, 1);
  static const Color carmichaelAqua300 = Color.fromRGBO(45, 181, 151, 1);
  static const Color carmichaelAqua400 = Color.fromRGBO(0, 132, 115, 1); // same as carmichaelAqua
  static const Color carmichaelAqua500 = Color.fromRGBO(0, 113, 109, 1);
  static const Color carmichaelAqua600 = Color.fromRGBO(0, 91, 95, 1);
  static const Color carmichaelAqua700 = Color.fromRGBO(0, 68, 76, 1);

  // ───────────────────────────────────────────────
  // Innovation Blue - tints & shades
  // ───────────────────────────────────────────────

  static const Color innovationBlue100 = Color.fromRGBO(128, 195, 212, 1);
  static const Color innovationBlue200 = Color.fromRGBO(111, 178, 197, 1);
  static const Color innovationBlue300 = Color.fromRGBO(89, 155, 175, 1);
  static const Color innovationBlue400 = Color.fromRGBO(66, 126, 147, 1); // same as innovationBlue
  static const Color innovationBlue500 = Color.fromRGBO(45, 99, 122, 1);
  static const Color innovationBlue600 = Color.fromRGBO(29, 75, 97, 1);
  static const Color innovationBlue700 = Color.fromRGBO(18, 57, 77, 1);

  // ───────────────────────────────────────────────
  // Bio-Indigo - tints & shades
  // ───────────────────────────────────────────────

  static const Color bioIndigo100 = Color.fromRGBO(132, 160, 220, 1);
  static const Color bioIndigo200 = Color.fromRGBO(114, 139, 207, 1);
  static const Color bioIndigo300 = Color.fromRGBO(91, 115, 187, 1);
  static const Color bioIndigo400 = Color.fromRGBO(65, 86, 161, 1); // same as bioIndigo
  static const Color bioIndigo500 = Color.fromRGBO(52, 72, 145, 1);
  static const Color bioIndigo600 = Color.fromRGBO(36, 52, 123, 1);
  static const Color bioIndigo700 = Color.fromRGBO(25, 38, 104, 1);

  // ───────────────────────────────────────────────
  // Wolfpack Black - tints (light grays → black)
  // ───────────────────────────────────────────────

  static const Color wolfpackBlack100 = Color.fromRGBO(242, 242, 242, 1);
  static const Color wolfpackBlack200 = Color.fromRGBO(204, 204, 204, 1);
  static const Color wolfpackBlack300 = Color.fromRGBO(178, 178, 178, 1);
  static const Color wolfpackBlack400 = Color.fromRGBO(128, 128, 128, 1);
  static const Color wolfpackBlack500 = Color.fromRGBO(77, 77, 77, 1);
  static const Color wolfpackBlack600 = Color.fromRGBO(51, 51, 51, 1);
  static const Color wolfpackBlack700 = Color.fromRGBO(0, 0, 0, 1); // same as wolfpackBlack
}


class NCSUTheme {
  NCSUTheme._();

  static const Color wolfpackRedSwatch = Color.fromRGBO(204, 0, 0, 1);


  /// Light theme 
  static ThemeData get light {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: ColorScheme.fromSeed(
        seedColor: NCSUColors.wolfpackRed,
        primary: NCSUColors.wolfpackRed,
        onPrimary: NCSUColors.wolfpackWhite,
        secondary: NCSUColors.reynoldsRed,
        onSecondary: NCSUColors.wolfpackWhite,
        error: NCSUColors.pyromanFlame,
        surface: NCSUColors.wolfpackWhite,
        onSurface: NCSUColors.wolfpackBlack600,
      ),
      scaffoldBackgroundColor: NCSUColors.wolfpackBlack100,
      appBarTheme: const AppBarTheme(
        backgroundColor: NCSUColors.wolfpackRed,
        foregroundColor: NCSUColors.wolfpackWhite,
        elevation: 2,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: NCSUColors.wolfpackRed,
          foregroundColor: NCSUColors.wolfpackWhite,
        ),
      ),
      chipTheme: ChipThemeData(
        selectedColor: NCSUColors.wolfpackRed.withAlpha(40),
        checkmarkColor: NCSUColors.wolfpackRed,
      ),
      sliderTheme: const SliderThemeData(
        activeTrackColor: NCSUColors.wolfpackRed,
        thumbColor: NCSUColors.wolfpackRed,
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: NCSUColors.wolfpackRed,
      ),
    );
  }


  /// Dark theme 
  static ThemeData get dark {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: ColorScheme.fromSeed(
        seedColor: NCSUColors.wolfpackRed,
        brightness: Brightness.dark,
        primary: NCSUColors.wolfpackRed100,
        onPrimary: NCSUColors.wolfpackBlack,
        secondary: NCSUColors.reynoldsRed,
        onSecondary: NCSUColors.wolfpackWhite,
        error: NCSUColors.pyromanFlame100,
        surface: NCSUColors.wolfpackBlack600,
        onSurface: NCSUColors.wolfpackBlack100,
      ),
      scaffoldBackgroundColor: NCSUColors.wolfpackBlack700,
      appBarTheme: const AppBarTheme(
        backgroundColor: NCSUColors.wolfpackBlack600,
        foregroundColor: NCSUColors.wolfpackWhite,
        elevation: 2,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: NCSUColors.wolfpackRed,
          foregroundColor: NCSUColors.wolfpackWhite,
        ),
      ),
      chipTheme: ChipThemeData(
        selectedColor: NCSUColors.wolfpackRed.withAlpha(60),
        checkmarkColor: NCSUColors.wolfpackRed100,
      ),
      sliderTheme: const SliderThemeData(
        activeTrackColor: NCSUColors.wolfpackRed100,
        thumbColor: NCSUColors.wolfpackRed100,
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: NCSUColors.wolfpackRed100,
      ),
    );
  }
}
