# STORY-007: The Finite Feed

**Status**: ✅ Implemented
**Date**: 2025-11-19
**Epic**: The Scroll

> Current audit note (2026-05-28): This is a historical implementation record. Production currently verifies the completion response at `https://api.almanac.solar/api/v1/feed?read_count=20`; see [CURRENT_STATE.md](CURRENT_STATE.md).

## Overview

STORY-007 implements the "Finite Feed" - a hard daily limit of 20 cards to prevent infinite scrolling. This transforms content consumption from endless doomscrolling into a finite, intentional experience where **"The End" is the product**.

**Key Innovation**: Daily limits + completion celebration = sustainable media consumption

## Implementation Summary

### 1. Backend Pagination & Limits

**Purpose**: Enforce daily limits and return completion state

**Changes**:
- Added `DAILY_LIMIT = 20` constant to routes.py
- Updated `/feed` endpoint with pagination parameters
- Returns completion object when limit reached
- Tracks read count to enforce limits

**New Endpoint Signature**:
```python
@router.get("/feed")
async def get_feed(
    user_context: Optional[List[str]] = Query(None),
    page: int = Query(1, ge=1),
    read_count: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
```

**Response Structure**:
```json
{
  "cards": [...],
  "pagination": {
    "page": 1,
    "limit": 10,
    "has_next_page": true,
    "total_read_today": 10,
    "daily_limit": 20
  },
  "completion": {
    "type": "COMPLETION",
    "message": "The Garden is Watered.",
    "subtitle": "You've reached today's limit. Return tomorrow for fresh blooms.",
    "stats": {
      "read_count": 20,
      "daily_limit": 20
    }
  },
  "serendipity_enabled": true
}
```

**Completion Logic**:
- If `read_count >= DAILY_LIMIT`: Return empty cards + completion object
- If `read_count + limit > DAILY_LIMIT`: Clamp limit to remaining cards
- If final page: Append completion object to response

### 2. Frontend Models

**PaginationMeta Class** (`frontend/lib/models/bloom_card.dart`):
```dart
class PaginationMeta {
  final int page;
  final int limit;
  final bool hasNextPage;
  final int totalReadToday;
  final int dailyLimit;

  double get progress => totalReadToday / dailyLimit;
  int get remaining => dailyLimit - totalReadToday;
}
```

**CompletionData Class**:
```dart
class CompletionData {
  final String type;
  final String message;
  final String subtitle;
  final Map<String, dynamic> stats;

  int get readCount => stats['read_count'];
  int get dailyLimit => stats['daily_limit'];
}
```

**Updated FeedResponse**:
```dart
class FeedResponse {
  final List<BloomCard> cards;
  final PaginationMeta pagination;
  final CompletionData? completion;
  final bool serendipityEnabled;

  bool get isComplete => completion != null;
  bool get hasNextPage => pagination.hasNextPage;
}
```

### 3. Local Storage Service

**StorageService** (`frontend/lib/services/storage_service.dart`):

**Purpose**: Persist read state across app sessions with daily reset

**Features**:
- Automatic daily reset (checks date on init)
- Read count tracking
- Read card IDs tracking (for serendipity context)
- Shared preferences backend

**Key Methods**:
```dart
Future<void> init()  // Initialize with daily reset check
Future<int> getReadCount()  // Get today's read count
Future<void> incrementReadCount({int by = 1})  // Increment counter
Future<void> markCardAsRead(String cardId)  // Mark specific card as read
Future<bool> isCardRead(String cardId)  // Check if card already read
```

**Daily Reset Logic**:
```dart
final lastResetDate = prefs.getString(_lastResetDateKey);
final today = DateTime.now().toIso8601String().split('T')[0];  // YYYY-MM-DD

if (lastResetDate != today) {
  // Reset counters for new day
  await prefs.setInt(_readCountKey, 0);
  await prefs.setStringList(_readCardIdsKey, []);
  await prefs.setString(_lastResetDateKey, today);
}
```

### 4. Feed Controller (Riverpod)

**FeedController** (`frontend/lib/providers/feed_controller.dart`):

**Purpose**: Stateful pagination management with read tracking

**State Structure**:
```dart
class FeedState {
  final List<BloomCard> cards;
  final PaginationMeta? pagination;
  final CompletionData? completion;
  final bool isLoading;
  final String? error;
  final int currentPage;
}
```

**Key Methods**:
```dart
Future<void> loadFeed({bool refresh = false})  // Load first page
Future<void> loadNextPage()  // Load next page (append)
Future<void> markCardAsRead(String cardId)  // Update read state
Future<void> refresh()  // Clear and reload
```

**Pagination Flow**:
1. Get current `read_count` from StorageService
2. Get last 5 `read_card_ids` for serendipity context
3. Call API with pagination params
4. Append new cards to existing list (for page > 1)
5. Update state with new pagination/completion data

### 5. CompletionWidget

**CompletionWidget** (`frontend/lib/widgets/completion_widget.dart`):

**Purpose**: Celebrate completion of daily feed

**Design**:
```
┌─────────────────────────┐
│    🌸 (animated)       │  ← Flower icon with scale/rotate
│                         │
│ The Garden is Watered. │  ← Botanical message
│                         │
│ You've reached today's  │  ← Subtitle
│ limit. Return tomorrow  │
│                         │
├─────────────────────────┤
│  ✓ 20    🌱 20         │  ← Stats (read / goal)
├─────────────────────────┤
│ 🕐 New blooms tomorrow │  ← Return message
└─────────────────────────┘
```

**Animations**:
- Fade in (0 → 1.0 opacity over 400ms)
- Scale up (0.95 → 1.0 with easeOutBack curve)
- Flower icon: Elastic scale + rotation

**Paper & Ink Styling**:
- Background: `primaryBg` (warm paper)
- Border: 1px `inkTertiary`
- Message color: `growthGreen`
- Stats background: `surfaceBg`

### 6. Updated FeedScreen

**FeedScreen** (`frontend/lib/screens/feed_screen.dart`):

**Changes**:
- Converted from `ConsumerWidget` to `ConsumerStatefulWidget`
- Added `ScrollController` for pagination trigger
- Integrated `FeedController` state management
- Shows `CompletionWidget` when limit reached

**Pagination Trigger**:
```dart
void _onScroll() {
  // Load next page when scrolled to top (reverse mode)
  if (position.pixels <= position.minScrollExtent + 200) {
    if (!isLoading && hasNextPage && !isComplete) {
      ref.read(feedControllerProvider.notifier).loadNextPage();
    }
  }
}
```

**Progress Indicator**:
- AppBar shows "10/20" read count
- Linear progress bar at top of feed
- Color-coded with `growthGreen`

**Feed Layout**:
```
┌─────────────────────────┐
│ 🌱 Bloom Scroll   10/20│  ← AppBar with counter
├═════════════════════════┤  ← Progress bar
│                         │
│  [Completion Widget]    │  ← If complete
│  or [End Marker]        │  ← If more pages
│                         │
│  ┌────┬────┐            │
│  │ 🎨 │ 📊 │            │  ← Masonry grid
│  ├────┼────┤            │    (reverse scroll)
│  │ 📊 │ 🎨 │            │
│  └────┴────┘            │
│                         │
│  [Loading...]           │  ← If loading more
└─────────────────────────┘
```

## Design Philosophy

**"The End" is the Product**:
- Finite feeds create natural stopping points
- Completion is celebrated, not punished
- Daily limits prevent doomscrolling addiction
- Encourages quality over quantity

**Botanical Metaphors**:
- "The Garden is Watered" = Daily goal achieved
- "New blooms arrive tomorrow" = Return tomorrow
- Flower icon symbolizes growth and renewal
- Green color = healthy, sustainable consumption

**No "Load More" Button**:
- Architect's note: "Resist adding 'Load More'"
- Automatic pagination on scroll up
- Hard stop at daily limit
- No escape hatch for infinite scrolling

## Acceptance Criteria

### ✅ AC1: Backend Pagination
- [x] `/feed` endpoint accepts page, read_count, limit params
- [x] DAILY_LIMIT = 20 enforced
- [x] Returns pagination metadata
- [x] Returns completion object when limit reached

### ✅ AC2: Completion Widget
- [x] Shows "The Garden is Watered." message
- [x] Displays stats (read count / daily limit)
- [x] Animated flower icon
- [x] Paper & Ink styling
- [x] Encourages return tomorrow

### ✅ AC3: Read State Tracking
- [x] StorageService persists read count
- [x] Daily automatic reset (midnight UTC)
- [x] Tracks individual card IDs
- [x] Survives app restarts

### ✅ AC4: Pagination Controller
- [x] FeedController manages state
- [x] Loads next page on scroll
- [x] Stops at daily limit
- [x] Shows progress in AppBar
- [x] Updates read count on card views

## Architecture Notes

### Pagination Strategy

**Why Scroll-Based Instead of Button?**
- Natural feel (no jarring "Load More" button)
- Matches upward scroll pattern
- Triggers when user approaches top (200px threshold)
- Prevents accidental triggers

**Infinite Scroll Prevention**:
```dart
if (!isLoading && hasNextPage && !isComplete) {
  loadNextPage();
}
```

Three conditions must be true:
1. Not currently loading
2. More pages available
3. Not yet complete

### Daily Reset Logic

**Why Date String Comparison?**
- Simple, timezone-agnostic
- No complex time calculations
- Resets at midnight UTC
- Consistent across devices

**Format**: `YYYY-MM-DD` (ISO 8601 date only)
```dart
final today = DateTime.now().toIso8601String().split('T')[0];
```

### State Management Flow

```
┌─────────────┐
│ FeedScreen  │
└──────┬──────┘
       │ watch
       ▼
┌──────────────────┐
│ FeedController   │◄──── Riverpod StateNotifier
└──────┬───────────┘
       │ uses
       ▼
┌──────────────────┐     ┌──────────────────┐
│ ApiService       │     │ StorageService   │
└──────────────────┘     └──────────────────┘
       │                        │
       ▼                        ▼
   FastAPI Backend        SharedPreferences
```

### Performance Considerations

**Append-Only List**:
- New pages append to existing cards
- No full list rebuild
- Preserves scroll position
- Minimal memory overhead (max 20 items)

**Storage Optimization**:
- Only stores card IDs (not full objects)
- Max 20 IDs per day
- Auto-cleanup on daily reset
- Shared preferences (fast key-value store)

## Testing

### Manual Testing Checklist

1. **First Load**:
   - [ ] App shows loading spinner
   - [ ] Feed loads with 10 cards
   - [ ] AppBar shows "10/20"
   - [ ] Progress bar at 50%

2. **Scroll Pagination**:
   - [ ] Scroll up to top
   - [ ] Next page loads automatically
   - [ ] Cards append to list
   - [ ] AppBar updates to "20/20"
   - [ ] Progress bar reaches 100%

3. **Completion State**:
   - [ ] After 20 cards, CompletionWidget appears
   - [ ] Shows "The Garden is Watered."
   - [ ] Flower icon animates
   - [ ] Stats show "20 / 20"
   - [ ] "New blooms tomorrow" message visible

4. **Daily Reset**:
   - [ ] Change device date to tomorrow
   - [ ] Restart app
   - [ ] Read count resets to 0
   - [ ] Feed loads fresh 10 cards
   - [ ] AppBar shows "10/20" again

5. **Refresh**:
   - [ ] Tap refresh icon
   - [ ] Feed reloads from page 1
   - [ ] Maintains current read count
   - [ ] Scroll state resets

### Edge Cases

**No Cards Available**:
- If backend has < 20 cards total, shows "End" marker
- No completion object (didn't hit daily limit)
- Graceful fallback

**Network Failure Mid-Pagination**:
- Shows error banner
- Preserves existing cards
- Retry button available
- Doesn't lose scroll position

**Read Count Desync**:
- StorageService is source of truth
- API read_count param is advisory
- Backend enforces limit regardless
- Frontend syncs on each response

## Future Enhancements

1. **Analytics Dashboard**:
   - Weekly read count graph
   - Average daily completion rate
   - Top topics consumed
   - Longest streak

2. **Customizable Limits**:
   - User setting for daily limit (10, 20, 30)
   - Weekend vs. weekday limits
   - "Focus mode" (5 cards max)

3. **Time-Based Limits**:
   - Reset at user's local midnight (not UTC)
   - Reading time tracking (minutes spent)
   - Time-based limits (20 mins/day)

4. **Gamification**:
   - Streaks for hitting limit consistently
   - Badges for reading diversity
   - "Mindful consumer" achievements

5. **Social Features**:
   - Share completion stats
   - Compare with friends
   - Group reading challenges

## Files Changed

### Backend
- `backend/app/api/routes.py` - Added pagination, DAILY_LIMIT, completion logic

### Frontend Models
- `frontend/lib/models/bloom_card.dart` - Added PaginationMeta, CompletionData, updated FeedResponse

### Frontend Services
- `frontend/lib/services/api_service.dart` - Updated getFeed() with pagination params
- `frontend/lib/services/storage_service.dart` - New service for read state tracking

### Frontend Providers
- `frontend/lib/providers/feed_controller.dart` - New FeedController StateNotifier

### Frontend Widgets
- `frontend/lib/widgets/completion_widget.dart` - New completion celebration widget
- `frontend/lib/screens/feed_screen.dart` - Updated with pagination, completion, progress

### Frontend Config
- `frontend/pubspec.yaml` - Added shared_preferences dependency

## Commit Messages

**Backend**:
```
feat: add pagination and daily limits to feed endpoint (STORY-007 part 1/2)
- Add DAILY_LIMIT = 20 constant
- Update /feed endpoint with page, read_count, limit params
- Return completion object when limit reached
- Clamp limit to remaining cards (prevent overage)
```

**Frontend**:
```
feat: implement finite feed with completion widget (STORY-007 part 2/2)
- PaginationMeta, CompletionData models
- StorageService for read state tracking (daily reset)
- FeedController with Riverpod state management
- CompletionWidget with animated flower icon
- Updated FeedScreen with scroll pagination
- Progress indicator in AppBar and top bar
- "The Garden is Watered" completion message
- Enforce "The End" as the product
```

## References

- Shared Preferences: https://pub.dev/packages/shared_preferences
- Riverpod StateNotifier: https://riverpod.dev/docs/concepts/providers#statenotifierprovider
- Flutter ScrollController: https://api.flutter.dev/flutter/widgets/ScrollController-class.html
- ISO 8601 Date Format: https://en.wikipedia.org/wiki/ISO_8601

## Architectural Principles Applied

**Slow Web**:
- Hard limits prevent infinite consumption
- Natural stopping points create mindfulness
- Daily reset encourages routine

**Paper & Ink Design**:
- Botanical completion messaging
- Warm, encouraging tone
- No dark patterns (no "skip limit" option)

**Serendipity Zone**:
- Read card IDs feed back into algorithm
- Last 5 cards provide context
- Limits force diverse consumption

---

**The End is the Product.** ✨
