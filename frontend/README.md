# Bloom Scroll Frontend

Flutter frontend for Bloom Scroll / Almanac. Last audited against code and production on 2026-05-28; see [../docs/CURRENT_STATE.md](../docs/CURRENT_STATE.md).

## Current Stack

- Flutter / Dart
- Riverpod (`StateNotifierProvider`) for feed state
- Dio for HTTP
- `fl_chart` for OWID charts
- `flutter_staggered_grid_view` for the masonry feed
- `cached_network_image` for aesthetic image cards
- `shared_preferences` for daily read-count state
- Google Fonts package for Libre Baskerville + Inter

The current app does not use BLoC or the older Clean Architecture folder layout described in earlier drafts.

## Project Structure

```text
frontend/
├── lib/
│   ├── main.dart
│   ├── models/
│   │   └── bloom_card.dart
│   ├── providers/
│   │   ├── api_provider.dart
│   │   └── feed_controller.dart
│   ├── screens/
│   │   └── feed_screen.dart
│   ├── services/
│   │   ├── api_config.dart
│   │   ├── api_service.dart
│   │   └── storage_service.dart
│   ├── theme/
│   │   ├── bloom_theme.dart
│   │   └── design_tokens.dart
│   └── widgets/
│       ├── aesthetic_card.dart
│       ├── completion_widget.dart
│       ├── error_boundary.dart
│       ├── owid_card.dart
│       └── perspective/
├── web/
├── Dockerfile
└── pubspec.yaml
```

## Features Implemented

- Upward-scrolling feed via `CustomScrollView(reverse: true)`.
- 2-column masonry grid via `SliverMasonryGrid.count`.
- OWID line charts rendered from JSON payloads.
- Aesthetic image cards with stable aspect ratio placeholders and full-screen image viewer.
- Perspective flip overlay widgets.
- Finite feed completion state with `"The Garden is Watered."`.
- Local read-count tracking with daily reset.
- Error boundary wrapper at app root.

## Local Development

Run the backend first at `http://localhost:8000`, then:

```bash
flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000
```

For mobile simulators:

- iOS simulator: `--dart-define=API_BASE_URL=http://localhost:8000`
- Android emulator: `--dart-define=API_BASE_URL=http://10.0.2.2:8000`
- Physical device: use your machine LAN IP, for example `http://192.168.1.100:8000`

## Production Build

`frontend/Dockerfile` builds Flutter web and bakes in:

```text
API_BASE_URL=https://api.almanac.solar
```

Production evidence from 2026-05-28: `https://almanac.solar/main.dart.js` contains `https://api.almanac.solar/api/v1`, so the active API base is correct. The same bundle also contains `localhost:8000` in connection-help text, so do not use a broad `grep localhost:` check as proof that the API base leaked.

## Useful Commands

```bash
flutter pub get
flutter analyze --no-fatal-infos
flutter build web --release --dart-define=API_BASE_URL=http://localhost:8000
flutter test
dart format .
```

There is no committed `frontend/test/` directory as of the current audit, so `flutter test` may only validate framework/package setup until tests are added.

## API Configuration

`lib/services/api_config.dart` reads `API_BASE_URL` at compile time:

```dart
static const String baseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://localhost:8000',
);
```

`ApiService` appends `/api/v1` for application endpoints.
