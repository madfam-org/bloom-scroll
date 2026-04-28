/// Bloom Scroll Theme: "Paper & Ink" Design System
///
/// Material Theme configuration using design tokens.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'design_tokens.dart';

class BloomTheme {
  BloomTheme._();

  /// Light theme (primary theme for Bloom Scroll)
  static ThemeData get lightTheme {
    return ThemeData(
      // Use Material 3
      useMaterial3: true,

      // Color Scheme
      colorScheme: ColorScheme.light(
        primary: BloomColors.growthGreen,
        onPrimary: BloomColors.primaryBg,
        secondary: BloomColors.bloomRed,
        onSecondary: BloomColors.primaryBg,
        error: BloomColors.bloomRed,
        onError: BloomColors.primaryBg,
        surface: BloomColors.primaryBg,
        onSurface: BloomColors.inkPrimary,
      ),

      // Background
      scaffoldBackgroundColor: BloomColors.primaryBg,

      // App Bar Theme
      appBarTheme: const AppBarTheme(
        backgroundColor: BloomColors.primaryBg,
        foregroundColor: BloomColors.inkPrimary,
        elevation: BloomSpacing.elevation,
        centerTitle: true,
        titleTextStyle: TextStyle(
          fontFamily: BloomTypography.headingFont,
          fontSize: 20,
          fontWeight: FontWeight.w700,
          color: BloomColors.inkPrimary,
        ),
        iconTheme: IconThemeData(
          color: BloomColors.inkPrimary,
          size: 24,
        ),
        systemOverlayStyle: SystemUiOverlayStyle(
          statusBarColor: Colors.transparent,
          statusBarIconBrightness: Brightness.dark,
          statusBarBrightness: Brightness.light,
        ),
      ),

      // Card Theme
      cardTheme: CardThemeData(
        color: BloomColors.surfaceBg,
        elevation: BloomSpacing.elevation,
        shape: RoundedRectangleBorder(
          borderRadius: BloomSpacing.cardBorderRadius,
          side: BloomSpacing.defaultBorder,
        ),
        margin: const EdgeInsets.all(BloomSpacing.xs),
      ),

      // Text Theme - Apply Google Fonts
      textTheme: _buildTextTheme(),

      // Button Themes
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: BloomColors.growthGreen,
          foregroundColor: BloomColors.primaryBg,
          elevation: BloomSpacing.elevation,
          shape: RoundedRectangleBorder(
            borderRadius: BloomSpacing.buttonBorderRadius,
          ),
          textStyle: BloomTypography.labelMedium.copyWith(
            color: BloomColors.primaryBg,
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: BloomSpacing.md,
            vertical: BloomSpacing.sm,
          ),
        ),
      ),

      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: BloomColors.growthGreen,
          foregroundColor: BloomColors.primaryBg,
          elevation: BloomSpacing.elevation,
          shape: RoundedRectangleBorder(
            borderRadius: BloomSpacing.buttonBorderRadius,
          ),
          textStyle: BloomTypography.labelMedium.copyWith(
            color: BloomColors.primaryBg,
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: BloomSpacing.md,
            vertical: BloomSpacing.sm,
          ),
        ),
      ),

      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: BloomColors.inkPrimary,
          side: BloomSpacing.defaultBorder,
          shape: RoundedRectangleBorder(
            borderRadius: BloomSpacing.buttonBorderRadius,
          ),
          textStyle: BloomTypography.labelMedium,
          padding: const EdgeInsets.symmetric(
            horizontal: BloomSpacing.md,
            vertical: BloomSpacing.sm,
          ),
        ),
      ),

      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: BloomColors.inkPrimary,
          textStyle: BloomTypography.labelMedium,
          padding: const EdgeInsets.symmetric(
            horizontal: BloomSpacing.sm,
            vertical: BloomSpacing.xs,
          ),
        ),
      ),

      // Floating Action Button
      floatingActionButtonTheme: const FloatingActionButtonThemeData(
        backgroundColor: BloomColors.growthGreen,
        foregroundColor: BloomColors.primaryBg,
        elevation: BloomSpacing.elevation,
        shape: RoundedRectangleBorder(
          borderRadius: BloomSpacing.buttonBorderRadius,
          side: BorderSide(
            color: BloomColors.inkTertiary,
            width: BloomSpacing.borderWidth,
          ),
        ),
      ),

      // Chip Theme
      chipTheme: ChipThemeData(
        backgroundColor: BloomColors.surfaceBg,
        labelStyle: BloomTypography.labelSmall,
        side: BloomSpacing.defaultBorder,
        shape: RoundedRectangleBorder(
          borderRadius: BloomSpacing.buttonBorderRadius,
        ),
        padding: const EdgeInsets.symmetric(
          horizontal: BloomSpacing.sm,
          vertical: BloomSpacing.xs,
        ),
        elevation: BloomSpacing.elevation,
      ),

      // Divider Theme
      dividerTheme: const DividerThemeData(
        color: BloomColors.inkTertiary,
        thickness: BloomSpacing.borderWidth,
        space: BloomSpacing.md,
      ),

      // Icon Theme
      iconTheme: const IconThemeData(
        color: BloomColors.inkPrimary,
        size: 24,
      ),

      // Progress Indicator Theme
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: BloomColors.growthGreen,
      ),

      // Input Decoration Theme
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: BloomColors.surfaceBg,
        border: OutlineInputBorder(
          borderRadius: BloomSpacing.buttonBorderRadius,
          borderSide: BloomSpacing.defaultBorder,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BloomSpacing.buttonBorderRadius,
          borderSide: BloomSpacing.defaultBorder,
        ),
        focusedBorder: const OutlineInputBorder(
          borderRadius: BloomSpacing.buttonBorderRadius,
          borderSide: BorderSide(
            color: BloomColors.growthGreen,
            width: BloomSpacing.borderWidth,
          ),
        ),
        errorBorder: const OutlineInputBorder(
          borderRadius: BloomSpacing.buttonBorderRadius,
          borderSide: BorderSide(
            color: BloomColors.bloomRed,
            width: BloomSpacing.borderWidth,
          ),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: BloomSpacing.md,
          vertical: BloomSpacing.sm,
        ),
        hintStyle: BloomTypography.bodyMedium.copyWith(
          color: BloomColors.inkTertiary,
        ),
      ),

      // Snackbar Theme
      snackBarTheme: SnackBarThemeData(
        backgroundColor: BloomColors.inkPrimary,
        contentTextStyle: BloomTypography.bodyMedium.copyWith(
          color: BloomColors.primaryBg,
        ),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BloomSpacing.cardBorderRadius,
        ),
      ),

      // Dialog Theme
      dialogTheme: DialogThemeData(
        backgroundColor: BloomColors.primaryBg,
        elevation: BloomSpacing.elevation,
        shape: RoundedRectangleBorder(
          borderRadius: BloomSpacing.cardBorderRadius,
          side: BloomSpacing.defaultBorder,
        ),
        titleTextStyle: BloomTypography.h3,
        contentTextStyle: BloomTypography.bodyMedium,
      ),
    );
  }

  /// System UI overlay style for the app
  static const SystemUiOverlayStyle systemUiOverlayStyle = SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.dark,
    statusBarBrightness: Brightness.light,
    systemNavigationBarColor: BloomColors.primaryBg,
    systemNavigationBarIconBrightness: Brightness.dark,
  );

  /// Build text theme with Google Fonts
  static TextTheme _buildTextTheme() {
    // Base text theme using Inter
    final baseTextTheme = GoogleFonts.interTextTheme();

    // Apply Libre Baskerville for headings, Inter for body
    return baseTextTheme.copyWith(
      // Headings - Libre Baskerville
      displayLarge: GoogleFonts.libreBaskerville(
        fontSize: 28,
        fontWeight: FontWeight.w700,
        color: BloomColors.inkPrimary,
        height: 1.3,
      ),
      displayMedium: GoogleFonts.libreBaskerville(
        fontSize: 22,
        fontWeight: FontWeight.w700,
        color: BloomColors.inkPrimary,
        height: 1.3,
      ),
      displaySmall: GoogleFonts.libreBaskerville(
        fontSize: 18,
        fontWeight: FontWeight.w700,
        color: BloomColors.inkPrimary,
        height: 1.3,
      ),
      headlineLarge: GoogleFonts.libreBaskerville(
        fontSize: 28,
        fontWeight: FontWeight.w700,
        color: BloomColors.inkPrimary,
        height: 1.3,
      ),
      headlineMedium: GoogleFonts.libreBaskerville(
        fontSize: 22,
        fontWeight: FontWeight.w700,
        color: BloomColors.inkPrimary,
        height: 1.3,
      ),
      headlineSmall: GoogleFonts.libreBaskerville(
        fontSize: 18,
        fontWeight: FontWeight.w700,
        color: BloomColors.inkPrimary,
        height: 1.3,
      ),
      titleLarge: GoogleFonts.libreBaskerville(
        fontSize: 22,
        fontWeight: FontWeight.w700,
        color: BloomColors.inkPrimary,
        height: 1.3,
      ),
      titleMedium: GoogleFonts.libreBaskerville(
        fontSize: 18,
        fontWeight: FontWeight.w700,
        color: BloomColors.inkPrimary,
        height: 1.3,
      ),
      titleSmall: GoogleFonts.inter(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: BloomColors.inkPrimary,
        height: 1.2,
      ),

      // Body - Inter
      bodyLarge: GoogleFonts.inter(
        fontSize: 16,
        fontWeight: FontWeight.w400,
        color: BloomColors.inkPrimary,
        height: 1.5,
      ),
      bodyMedium: GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w400,
        color: BloomColors.inkPrimary,
        height: 1.5,
      ),
      bodySmall: GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        color: BloomColors.inkSecondary,
        height: 1.5,
      ),

      // Labels - Inter SemiBold
      labelLarge: GoogleFonts.inter(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: BloomColors.inkPrimary,
        height: 1.2,
      ),
      labelMedium: GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        color: BloomColors.inkPrimary,
        height: 1.2,
      ),
      labelSmall: GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w600,
        color: BloomColors.inkPrimary,
        height: 1.2,
      ),
    );
  }
}
