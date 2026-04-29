/// API configuration
///
/// `baseUrl` is read at compile time via `String.fromEnvironment`. The
/// production value is baked into the JS bundle by the Dockerfile:
///
///     ARG API_BASE_URL=https://api.almanac.solar
///     RUN flutter build web --release \
///         --dart-define=API_BASE_URL=${API_BASE_URL}
///
/// IMPORTANT: `String.fromEnvironment` is COMPILE-TIME only. If the
/// `--dart-define` flag isn't present at `flutter build`, the compiled
/// bundle silently bakes in the `defaultValue` below — which is
/// `localhost:8000` for local dev. That has bitten almanac.solar:
/// PRs #71/#72 added the dart-define to the Dockerfile, but the
/// reusable build workflow's change-detection saw no frontend file
/// diff on a status-probe-only commit and skipped the rebuild,
/// leaving prod stuck on a bundle from before #71. Always confirm
/// the prod bundle by curling
/// `https://almanac.solar/main.dart.js | grep localhost:` — empty
/// output = correctly baked, any hits = the defaultValue leaked.
library;

class ApiConfig {
  /// Base URL for the backend API
  /// For iOS simulator: http://localhost:8000
  /// For Android emulator: http://10.0.2.2:8000
  /// For physical device: http://<your-machine-ip>:8000
  /// In prod (almanac.solar): baked to https://api.almanac.solar via
  /// Dockerfile ARG + --dart-define.
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  /// API version prefix
  static const String apiPrefix = '/api/v1';

  /// Full API URL
  static String get apiUrl => '$baseUrl$apiPrefix';

  /// Request timeout in seconds
  static const Duration timeout = Duration(seconds: 30);

  /// Enable logging for debugging
  static const bool enableLogging = true;
}
