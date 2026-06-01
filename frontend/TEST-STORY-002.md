# Testing Guide for STORY-002

> [!IMPORTANT]
> MADFAM-ENCLII-FIRST-LEGACY-RAW v1: This document contains legacy raw infrastructure command examples.
> Routine production operations must use Enclii web, API, or CLI. Treat raw
> `kubectl`, `helm`, SSH, provider CLI/API, `docker exec`, and direct container
> access as platform bootstrap or documented break-glass only, and record any
> missing Enclii adapter gap.


## Quick Test Checklist

### ✅ Pre-flight Checks

1. **Backend is running:**
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status":"healthy"}
   ```

2. **Data is ingested:**
   ```bash
   curl http://localhost:8000/api/v1/feed
   # Should return JSON with cards array
   ```

3. **If no data, ingest some:**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/ingest/owid?dataset_key=co2_emissions"
   curl -X POST "http://localhost:8000/api/v1/ingest/owid?dataset_key=life_expectancy"
   ```

### ✅ Running the Flutter App

#### Option 1: iOS Simulator
```bash
cd frontend
flutter pub get
flutter run
# Select iOS simulator when prompted
```

#### Option 2: Android Emulator

First, update API config for Android:
```dart
// lib/services/api_config.dart
static const String baseUrl = 'http://10.0.2.2:8000';  // Android emulator
```

Then run:
```bash
cd frontend
flutter pub get
flutter run
# Select Android emulator when prompted
```

#### Option 3: Physical Device

Find your machine's IP:
```bash
# macOS/Linux
ifconfig | grep "inet " | grep -v 127.0.0.1

# Output example: inet 192.168.1.100
```

Run with environment variable:
```bash
flutter run --dart-define=API_BASE_URL=http://192.168.1.100:8000
```

## Manual Testing Scenarios

### Test 1: App Launch & Feed Load

**Steps:**
1. Launch app
2. Observe loading indicator
3. Wait for feed to load

**Expected:**
- Circular progress indicator appears
- Feed loads with OWID cards
- Info banner shows card count
- Cards display with charts (not JSON)

**Pass Criteria:**
- ✅ No error screen
- ✅ At least one OWID card visible
- ✅ Charts render correctly

---

### Test 2: Upward Scrolling

**Steps:**
1. Observe initial screen (newest content at bottom)
2. Scroll UP with finger
3. Continue scrolling to top
4. Observe end marker

**Expected:**
- Scroll direction feels "inverted"
- Older data appears when scrolling up
- "You've reached the end!" marker at top
- No infinite scroll

**Pass Criteria:**
- ✅ `reverse: true` is working
- ✅ End marker displays
- ✅ Scrolling feels intentionally different

---

### Test 3: Chart Interaction

**Steps:**
1. Find an OWID card with chart
2. Touch and hold on the line
3. Drag finger along the line
4. Release finger

**Expected:**
- Tooltip appears on touch
- Tooltip shows: "Year\nValue Unit"
- Tooltip follows finger drag
- Dot enlarges at touch point
- Tooltip disappears on release

**Pass Criteria:**
- ✅ Tooltip appears with correct data
- ✅ Interaction is smooth
- ✅ Values are formatted (K/M/B)

**Example Tooltip:**
```
2023
37.5B tonnes
```

---

### Test 4: Chart Visual Design

**Steps:**
1. Examine chart appearance
2. Check for minimalist "Tufte style"
3. Verify color scheme

**Expected:**
- Green color theme (not aggressive/stock-trading colors)
- Smooth curved lines
- Minimal grid lines (no vertical lines)
- Subtle gradient fill below line
- Clean, calm aesthetic

**Pass Criteria:**
- ✅ No vertical grid lines
- ✅ Smooth curves (not jagged)
- ✅ Green color scheme
- ✅ Feels "calm" not "aggressive"

---

### Test 5: Error Handling

**Steps:**
1. Stop backend: `docker-compose down`
2. Pull to refresh in app
3. Observe error screen
4. Tap "Check connection settings"

**Expected:**
- Error screen appears
- Red error icon
- "Failed to load feed" message
- Retry button
- Connection help dialog shows correct URLs

**Pass Criteria:**
- ✅ Error screen displays
- ✅ Retry button works
- ✅ Connection help shows platform-specific URLs

---

### Test 6: Empty State

**Steps:**
1. Clear database: `docker exec -it bloom-postgres psql -U postgres -d bloom_scroll -c "DELETE FROM bloom_cards;"`
2. Refresh app

**Expected:**
- Empty state screen
- Leaf icon
- "No cards in the feed yet" message
- Helpful text

**Pass Criteria:**
- ✅ Empty state displays
- ✅ No crash
- ✅ Helpful message shown

---

### Test 7: Refresh Functionality

**Steps:**
1. Ingest new data (backend)
2. Tap refresh icon in app bar
3. Observe loading
4. Check if new card appears

**Expected:**
- Loading indicator appears
- Feed reloads
- New data visible

**Pass Criteria:**
- ✅ Refresh works
- ✅ New data appears
- ✅ No duplicate cards

---

## Automated Test (Optional)

Create `frontend/test/widget_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:bloom_scroll/main.dart';

void main() {
  testWidgets('App launches without crashing', (WidgetTester tester) async {
    await tester.pumpWidget(const BloomScrollApp());
    expect(find.text('🌱 Bloom Scroll'), findsOneWidget);
  });
}
```

Run:
```bash
cd frontend
flutter test
```

## Acceptance Criteria Validation

### AC1: App launches with reverse scroll list
**Test:** Launch app, observe scroll direction
**Command:** `flutter run`
**Verification:** Items appear with index 0 at bottom

### AC2: App calls GET /feed successfully
**Test:** Check Dio logs in debug console
**Command:** Watch debug console during app launch
**Verification:** See HTTP GET request to `/api/v1/feed`

### AC3: Card displays Line Chart (not text/JSON)
**Test:** Visual inspection of OWID cards
**Command:** Scroll through feed
**Verification:** See fl_chart LineChart widget, not Text widget

### AC4: Touching chart reveals data point
**Test:** Touch and drag on chart line
**Command:** Use finger/cursor on chart
**Verification:** Tooltip appears with "Year\nValue Unit" format

---

## Common Issues & Solutions

### Issue: "Connection refused"

**iOS Simulator:**
```dart
// Ensure api_config.dart has:
static const String baseUrl = 'http://localhost:8000';
```

**Android Emulator:**
```dart
// Change to:
static const String baseUrl = 'http://10.0.2.2:8000';
```

### Issue: "No cards in feed"

```bash
# Ingest data
curl -X POST "http://localhost:8000/api/v1/ingest/owid/all"
```

### Issue: Chart not interactive

- Check `lineTouchData.enabled: true` in owid_card.dart
- Verify device touch is working
- Try on different device/simulator

### Issue: Scroll feels normal (not reversed)

- Check ListView.builder has `reverse: true`
- Restart app (hot reload might not update)

### Issue: Import errors

```bash
cd frontend
flutter clean
flutter pub get
flutter run
```

---

## Performance Validation

### Load Time
- Initial feed load: <5 seconds (with network)
- Chart render: <100ms per card

### Smoothness
- 60 FPS scrolling
- No jank on chart interaction

### Memory
- <200MB RAM usage for 20 cards

Run Flutter DevTools to check:
```bash
flutter pub global activate devtools
flutter pub global run devtools
```

---

## Sign-off Checklist

Before marking STORY-002 as complete:

- [ ] All 4 acceptance criteria passed
- [ ] Tested on iOS simulator
- [ ] Tested on Android emulator
- [ ] Chart interaction works smoothly
- [ ] Reverse scroll feels intentional
- [ ] Visual design is "calm" (Tufte style)
- [ ] Error handling works
- [ ] No console errors or warnings
- [ ] Code follows Dart/Flutter best practices
- [ ] Documentation is complete

---

**Tester**: _________________
**Date**: _________________
**Platform Tested**: iOS ☐  Android ☐  Both ☐
**Status**: Pass ☐  Fail ☐  Needs Revision ☐
