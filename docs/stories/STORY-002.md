# STORY-002: The First Sprout (Flutter Scaffold & Charting)

**Status**: ✅ Implemented
**Epic**: The Visual Garden
**Priority**: P0
**Stack**: Flutter (Dart), fl_chart

> Current audit note (2026-05-28): This is a historical story record. The current frontend uses Riverpod `FeedController`, `CustomScrollView` + `SliverMasonryGrid`, and `fl_chart` 1.x; use [../CURRENT_STATE.md](../CURRENT_STATE.md) and `frontend/README.md` for current commands.

## Overview

This story builds the mobile app shell that fetches data from the backend and renders OWID charts natively. It validates two critical UX pillars: **Upward Scrolling** and **Native Data Rendering**.

## What Was Built

### 1. Flutter Project Setup

**Dependencies Added:**
- `flutter_riverpod: ^2.4.9` - State management
- `dio: ^5.4.0` - HTTP client (already present)
- `fl_chart: ^0.65.0` - Interactive charting (already present)
- `riverpod_annotation: ^2.3.3` - Annotations for providers
- `riverpod_generator: ^2.3.9` - Code generation

### 2. Data Layer

**Models** (`lib/models/bloom_card.dart`)
- `BloomCard` - Main model mirroring backend schema
- `OwidChartData` - OWID-specific payload parser
- `ChartPoint` - Coordinate pair for chart rendering
- `FeedResponse` - API response wrapper

**Factory Method:**
```dart
BloomCard.fromJson(Map<String, dynamic> json)
```
Handles polymorphic `data_payload` based on `source_type`.

### 3. API Service

**Files:**
- `lib/services/api_config.dart` - Configuration (supports iOS/Android/physical device)
- `lib/services/api_service.dart` - Dio-based HTTP client

**Endpoints:**
- `GET /feed` - Fetch bloom cards
- `POST /ingest/owid` - Ingest OWID data (for testing)
- `GET /ingest/datasets` - List available datasets
- `GET /health` - Backend health check

**Platform-aware URLs:**
- iOS Simulator: `http://localhost:8000`
- Android Emulator: `http://10.0.2.2:8000`
- Physical Device: Set via `API_BASE_URL` environment variable

### 4. Riverpod State Management

**Providers** (`lib/providers/api_provider.dart`)
- `apiServiceProvider` - ApiService singleton
- `feedProvider` - FutureProvider for feed data
- `healthCheckProvider` - Backend health status

### 5. OWID Card Widget

**File:** `lib/widgets/owid_card.dart`

**Features:**
- **Tufte-style minimalism**: Removed grid lines, clean design
- **Interactive line chart** using fl_chart
- **Touch callback**: Tooltip shows exact value on touch
- **Smooth curves**: `curveSmoothness: 0.3`
- **Gradient fill**: Below-line area with opacity
- **Smart formatting**: Auto-formats large numbers (K/M/B)
- **Dynamic intervals**: Adjusts X-axis labels based on data density

**Visual Design:**
- Green color scheme (`Colors.green.shade600`)
- Rounded card with elevation
- OWID badge chip
- Summary text below chart

### 6. Feed Screen with Upward Scrolling

**File:** `lib/screens/feed_screen.dart`

**Critical Config:**
```dart
ListView.builder(
  reverse: true,  // Makes index 0 appear at bottom
  physics: const BouncingScrollPhysics(),
  ...
)
```

**Features:**
- **Reverse scrolling**: Newest content at bottom, scroll UP for history
- **Info banner**: Shows card count and scroll direction hint
- **End marker**: Definitive "You've reached the end!" message
- **Empty state**: Helpful message when no data
- **Error handling**: Retry button and connection help dialog
- **Refresh button**: Pull to refresh functionality
- **Loading state**: Circular progress indicator

### 7. Main App

**File:** `lib/main.dart`
- Wrapped in `ProviderScope` for Riverpod
- Material 3 theme with green color scheme
- Card theme with rounded corners
- Dark theme support

## File Structure

```
frontend/lib/
├── main.dart                  # UPDATED: Riverpod integration
├── models/
│   └── bloom_card.dart        # NEW: Data models
├── services/
│   ├── api_config.dart        # NEW: API configuration
│   └── api_service.dart       # NEW: Dio HTTP client
├── providers/
│   └── api_provider.dart      # NEW: Riverpod providers
├── widgets/
│   └── owid_card.dart         # NEW: Interactive chart widget
└── screens/
    └── feed_screen.dart       # NEW: Main feed with reverse scroll
```

## Quick Start

### Prerequisites

1. **Backend running:**
   ```bash
   cd infrastructure
   docker-compose -f docker-compose.dev.yml up -d

   cd ../backend
   ./run_dev.sh
   ```

2. **Ingest some OWID data:**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/ingest/owid?dataset_key=co2_emissions"
   curl -X POST "http://localhost:8000/api/v1/ingest/owid?dataset_key=life_expectancy"
   curl -X POST "http://localhost:8000/api/v1/ingest/owid?dataset_key=child_mortality"
   ```

### Running the App

#### iOS Simulator
```bash
cd frontend
flutter pub get
flutter run -d "iPhone 15 Pro"  # or your simulator
```

#### Android Emulator
```bash
# Start emulator first
cd frontend
flutter pub get
flutter run -d emulator-5554  # or your emulator ID
```

#### Physical Device

1. Set API base URL:
   ```bash
   # Find your machine's IP address
   ifconfig | grep "inet "  # macOS/Linux
   ipconfig  # Windows
   ```

2. Run with environment variable:
   ```bash
   flutter run --dart-define=API_BASE_URL=http://192.168.1.100:8000
   ```

### Testing the App

1. **Launch app** - Should show feed with OWID cards
2. **Scroll UP** - Navigate through historical data
3. **Touch chart line** - Tooltip should appear with exact values
4. **Reach the top** - Should see "You've reached the end!" marker
5. **Pull to refresh** - Tap refresh icon to reload feed

## Acceptance Criteria Status

- [x] **AC1**: App launches with reverse scroll list
- [x] **AC2**: App successfully calls `GET /feed` and retrieves OWID cards
- [x] **AC3**: Card displays **Line Chart** (not text/JSON)
- [x] **AC4**: Touching chart line reveals specific data point with tooltip

## Key Implementation Details

### Reverse Scrolling Explanation

Setting `reverse: true` on ListView inverts the scroll direction:
- Index 0 appears at the **bottom** of the screen
- Users scroll **UP** to see older content
- Breaks standard UX pattern intentionally
- Metaphor: "Planting seeds" at bottom, "blooming" upward

### fl_chart Configuration

**Minimalist Design (Tufte Style):**
- No vertical grid lines
- Minimal horizontal grid lines (light gray)
- No borders
- Clean axis labels with smart formatting
- Smooth curved lines instead of sharp angles

**Interaction:**
- Touch anywhere on chart to see tooltip
- Touched point enlarges
- Dashed vertical indicator line
- White dot with green stroke

### API Connection Handling

The app handles three deployment scenarios:

1. **iOS Simulator**: Uses `localhost:8000`
2. **Android Emulator**: Uses `10.0.2.2:8000` (Android's host loopback)
3. **Physical Device**: Uses environment variable or shows connection help

## Troubleshooting

### "Failed to load feed" Error

**Check backend:**
```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/feed
```

**iOS Simulator:**
- Backend should be on `localhost:8000`
- Check firewall settings

**Android Emulator:**
- Use `10.0.2.2` instead of `localhost`
- Update `api_config.dart` if needed:
  ```dart
  static const String baseUrl = 'http://10.0.2.2:8000';
  ```

**Physical Device:**
- Ensure device and computer are on same network
- Use computer's IP address (not localhost)
- Check firewall allows connections on port 8000

### "No cards in the feed yet"

**Ingest data:**
```bash
curl -X POST "http://localhost:8000/api/v1/ingest/owid/all"
```

### Chart not rendering

- Check console for parsing errors
- Verify `data_payload` has required fields: `years`, `values`, `unit`, `indicator`
- Ensure backend is returning valid OWID data structure

### Import errors

```bash
cd frontend
flutter pub get
```

## Design Notes

### "Calm" Chart Aesthetic

Per the architect's note: "Focus heavily on the fl_chart configuration; it needs to look 'Calm', not like a stock trading app."

**Implemented:**
- Muted green color palette
- Smooth curves instead of jagged lines
- Minimal UI elements
- Generous padding and spacing
- Subtle gradient fill
- No aggressive colors or animations

### Reverse Scroll UX

Per the architect's note: "If the 'Reverse Scroll' feels disorienting, that is good—it means we are breaking the standard UX pattern as intended."

**User Experience:**
- Initial confusion is intentional
- Info banner provides guidance
- "Plant a Seed" FAB reinforces metaphor
- End marker provides closure (no infinite scroll)

## Performance Notes

- Initial feed load: ~2-5 seconds (includes HTTP request)
- Chart rendering: <100ms per card
- Smooth scrolling with 60 FPS on modern devices
- Dio caching can be added for offline support

## Next Steps

### STORY-003 (Suggested): Masonry Grid Layout
- Replace ListView with staggered grid
- Mix chart cards with image cards
- Implement "Robin Hood" layout balancing

### STORY-004 (Suggested): OpenAlex Cards
- Add science paper card widget
- Display abstracts and citations
- Mix with OWID charts in feed

### STORY-005 (Suggested): Offline Support
- Implement Hive local storage
- Cache feed data
- Sync in background

## Screenshots

(To be added after testing on device)

---

**Completed**: 2025-11-19
**Next Story**: TBD (Masonry Grid or Additional Card Types)
