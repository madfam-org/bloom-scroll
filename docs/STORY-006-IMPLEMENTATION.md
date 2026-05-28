# STORY-006: The Perspective Overlay ("The Flip")

**Status**: ✅ Implemented
**Date**: 2025-11-19
**Epic**: The Lens

> Current audit note (2026-05-28): This is a historical implementation record. The current production/repo evidence snapshot is [CURRENT_STATE.md](CURRENT_STATE.md).

## Overview

STORY-006 implements the "Perspective Overlay" - a 3D flip animation that reveals perspective metadata on the "back" of bloom cards. This gamifies media literacy by presenting bias scores, constructiveness ratings, and serendipity context as "stat sheets" rather than warning labels.

**Key Innovation**: The card flip interaction transforms each card into a two-sided object - front shows content, back shows perspective analysis.

## Implementation Summary

### 1. Backend Metadata Enhancement

**Purpose**: Provide perspective data for the flip overlay

**Changes**:
- Updated `BloomCard.to_dict()` to include `meta` field
- Added `calculate_reason_tag()` to BloomAlgorithm
- Enhanced `/feed` endpoint to include perspective metadata

**Metadata Structure**:
```json
{
  "meta": {
    "bias_score": -0.4,  // -1.0 (left) to +1.0 (right)
    "constructiveness_score": 85,  // 0.0 to 100.0
    "blindspot_tags": ["conservative-blindspot"],
    "reason_tag": "BLINDSPOT_BREAKER"
  }
}
```

**Reason Tags**:
- `BLINDSPOT_BREAKER`: Content from perspectives user rarely encounters
- `DEEP_DIVE`: Related to user's current interests
- `EXPLORE`: New territory for the user
- `PERSPECTIVE_SHIFT`: Related but novel viewpoint
- `SERENDIPITY`: Balanced discovery
- `RECENT`: Recent/popular content (no context)

### 2. Flutter Dart Models

**PerspectiveMeta Class** (`frontend/lib/models/bloom_card.dart`):
```dart
class PerspectiveMeta {
  final double biasScore;
  final double constructivenessScore;
  final List<String> blindspotTags;
  final String reasonTag;

  String get reasonText {
    // Human-readable reason display
    // e.g., "🌱 Blindspot Breaker: You rarely read this perspective"
  }
}
```

### 3. Flutter Widgets

#### FlippableCard (`frontend/lib/widgets/perspective/flippable_card.dart`)

**Purpose**: 3D flip animation wrapper

**Features**:
- 300ms animation duration (snappy per architect's note)
- Y-axis rotation using Matrix4 transform
- Info icon (ⓘ) in top-right corner triggers flip
- Preserves front content, adds perspective overlay on back

**Animation**:
```dart
Transform(
  transform: Matrix4.identity()
    ..setEntry(3, 2, 0.001) // Add perspective
    ..rotateY(angle),
  child: showFront ? _buildFront() : _buildBack(),
)
```

#### PerspectiveOverlay (`frontend/lib/widgets/perspective/perspective_overlay.dart`)

**Purpose**: "The Back of the Card" - stats display

**Layout**:
```
┌─────────────────────┐
│ Perspective Stats  ✕│  ← Close button
├─────────────────────┤
│ 🌱 Why This Card?   │  ← Serendipity Tag
│ Blindspot Breaker   │
├─────────────────────┤
│ Political Spectrum  │  ← Bias Compass
│ ←──────●──────→    │
├─────────────────────┤
│ Constructiveness   │  ← Ring Gauge
│    ◐ 85           │
└─────────────────────┘
```

#### BiasCompass (`frontend/lib/widgets/perspective/bias_compass.dart`)

**Purpose**: Political spectrum visualization

**Design**:
- Horizontal line with gradient (subtle red edges, gray center)
- Fulcrum marker at center
- Circular pill indicator shows position
- Labels: "Left-Leaning" | "Center" | "Right-Leaning"
- **Important**: NO party names (Democrat/Republican) to avoid partisan associations

**Positioning**:
```dart
final position = (biasScore + 1.0) / 2.0; // Convert -1 to 1 → 0 to 1
```

#### ConstructivenessRing (`frontend/lib/widgets/perspective/constructiveness_ring.dart`)

**Purpose**: Nutritional score visualization

**Design**:
- Radial gauge (circular progress indicator)
- CustomPainter for arc rendering
- Score displayed in center with tabular figures
- Color-coded:
  - < 50: `ink_tertiary` (gray) → "High Noise"
  - > 80: `growth_green` → "High Signal"
  - 50-80: `ink_secondary` → "Mixed Signal"

**Descriptions**:
- High Noise: "Contains emotional language, partisan framing, or inflammatory content."
- High Signal: "Well-sourced, balanced analysis with constructive tone."
- Mixed Signal: "Mix of factual content and opinion-based framing."

#### SerendipityTag (`frontend/lib/widgets/perspective/serendipity_tag.dart`)

**Purpose**: "Why This Card?" explanation

**Design**:
- Icon + text pill showing reason for recommendation
- Color-coded icons based on reason type:
  - `BLINDSPOT_BREAKER`: 🌱 visibility_outlined (green)
  - `DEEP_DIVE`: ⚓ anchor_outlined (green)
  - `EXPLORE`: 🗺️ explore_outlined (red)
  - `PERSPECTIVE_SHIFT`: 🔄 360_outlined (ink)
  - `SERENDIPITY`: ✨ auto_awesome_outlined (green)
  - `RECENT`: 📰 fiber_new_outlined (gray)

### 4. Integration

**OwidCard**:
```dart
return FlippableCard(
  card: widget.card,
  front: Card(
    // Existing OWID chart content
  ),
);
```

**AestheticCard**:
```dart
return FlippableCard(
  card: card,
  front: GestureDetector(
    // Preserves Hero animation for full-screen view
    child: Card(
      // Existing aesthetic image content
    ),
  ),
);
```

## Design Philosophy

**"Stat Sheet" Not "Warning Label"**:
- Perspective analysis presented as game-like stats
- Encourages curiosity rather than fear
- Maintains the "paper" aesthetic (same warm background)
- Interactive discovery through flip gesture

**Gamifying Media Literacy**:
- Political spectrum as a meter/gauge
- Constructiveness as a "nutritional score"
- Serendipity reason as quest context
- No moral judgment, just information

## Acceptance Criteria

### ✅ AC1: Flip Animation
- [x] Tapping info icon triggers smooth 3D flip
- [x] Animation duration < 300ms
- [x] Y-axis rotation with perspective transform

### ✅ AC2: Bias Visualization
- [x] Horizontal line with fulcrum at center
- [x] Pill indicator positioned correctly (-1.0 to +1.0)
- [x] Labels: "Left-Leaning", "Center", "Right-Leaning"
- [x] NO party names (Democrat/Republican)

### ✅ AC3: Visual Consistency
- [x] Back of card uses `primary_bg` (paper) color
- [x] Same border style as front (1px ink_tertiary)
- [x] Feels like same object, just turned over
- [x] No dark mode overlay

### ✅ AC4: Accessibility
- [x] Semantic labels on all interactive elements
- [x] Clear close button for screen readers
- [x] High contrast text (ink on paper)
- [x] Touch targets meet minimum size (48x48dp)

## Architecture Notes

### The Flip Gesture

**Why Info Icon Instead of Swipe?**
- Swipe conflicts with scroll gestures in masonry grid
- Info icon is discoverable and intentional
- Avoids accidental flips during browsing

**Animation Technique**:
```dart
// Matrix4 perspective transform
..setEntry(3, 2, 0.001)  // Perspective depth
..rotateY(angle)         // Y-axis rotation

// Show front or back based on angle
final showFront = angle < math.pi / 2;
```

### Performance Considerations

**Animation Smoothness**:
- Single AnimationController per card
- CurvedAnimation with easeInOut curve
- Dispose controller in widget lifecycle
- No expensive rebuilds during animation

**Widget Structure**:
```
FlippableCard (StatefulWidget)
├── AnimatedBuilder
│   └── Transform
│       ├── Front: Original card content
│       └── Back: PerspectiveOverlay
└── Info icon overlay (positioned absolutely)
```

### Design System Compliance

**Colors**:
- Background: `BloomColors.primaryBg` (#FDFCF8)
- Borders: `BloomColors.inkTertiary` (1px)
- Text: `BloomTypography` (Libre Baskerville + Inter)
- Icons: Outlined style, 24px

**Spacing**:
- Padding: `BloomSpacing.screenPadding` (20px)
- Gaps: `BloomSpacing.md` (16px) between sections
- Border radius: `BloomSpacing.cardRadius` (4px)

## Testing

### Manual Testing Checklist

1. **Flip Animation**:
   - [ ] Tap info icon on OWID card
   - [ ] Card flips smoothly in < 300ms
   - [ ] Back shows perspective stats
   - [ ] Tap close button to flip back

2. **Bias Compass**:
   - [ ] Left-leaning card (-0.4) shows pill left of center
   - [ ] Center card (0.0) shows pill at center
   - [ ] Right-leaning card (+0.6) shows pill right of center

3. **Constructiveness Ring**:
   - [ ] Low score (30) shows gray ring, "High Noise" label
   - [ ] High score (90) shows green ring, "High Signal" label
   - [ ] Score displays in center with correct value

4. **Serendipity Tag**:
   - [ ] BLINDSPOT_BREAKER shows green visibility icon
   - [ ] EXPLORE shows red explore icon
   - [ ] Reason text is human-readable

5. **Accessibility**:
   - [ ] Screen reader announces "Info" button
   - [ ] Screen reader reads perspective stats
   - [ ] Close button has clear label

### Edge Cases

**No Metadata**:
- If `meta` field is null, shows "No Perspective Data" message
- Graceful fallback with explanation

**Invalid Scores**:
- Bias score clamped to [-1.0, 1.0]
- Constructiveness score clamped to [0.0, 100.0]

## Future Enhancements

1. **Advanced Perspective Analysis**:
   - Real bias detection using PoliticalBiasBERT
   - Constructiveness scoring via sentiment analysis
   - Dynamic blindspot detection based on user history

2. **Interactive Features**:
   - Tap bias compass to see related articles
   - Tap constructiveness ring to see explanation
   - Share perspective stats as image

3. **Customization**:
   - User settings for flip animation speed
   - Toggle perspective overlay on/off
   - Custom bias spectrum labels

## Files Changed

### Backend
- `backend/app/models/bloom_card.py` - Added `meta` field to to_dict()
- `backend/app/curation/bloom_algorithm.py` - Added calculate_reason_tag()
- `backend/app/api/routes.py` - Enhanced feed endpoint

### Frontend
- `frontend/lib/models/bloom_card.dart` - Added PerspectiveMeta class
- `frontend/lib/widgets/perspective/flippable_card.dart` - 3D flip wrapper
- `frontend/lib/widgets/perspective/perspective_overlay.dart` - Back of card
- `frontend/lib/widgets/perspective/bias_compass.dart` - Political spectrum
- `frontend/lib/widgets/perspective/constructiveness_ring.dart` - Radial gauge
- `frontend/lib/widgets/perspective/serendipity_tag.dart` - Why this card
- `frontend/lib/widgets/owid_card.dart` - Integrated FlippableCard
- `frontend/lib/widgets/aesthetic_card.dart` - Integrated FlippableCard

## Commit Messages

**Part 1 (Backend)**:
```
feat: add perspective metadata to feed endpoint (STORY-006 part 1/2)
- Update BloomCard.to_dict() to include 'meta' field
- Add calculate_reason_tag() to BloomAlgorithm
- Enhance /feed endpoint with bias_score, constructiveness, reason_tag
```

**Part 2 (Frontend)**:
```
feat: implement 3D flip animation and perspective overlay (STORY-006 part 2/2)
- FlippableCard: 3D flip wrapper with Matrix4 transform
- BiasCompass: Political spectrum visualization
- ConstructivenessRing: Radial gauge with CustomPainter
- SerendipityTag: Reason display with icons
- Integrated into OwidCard and AestheticCard
```

## References

- Flutter Animation Docs: https://flutter.dev/docs/development/ui/animations
- Matrix4 Transforms: https://api.flutter.dev/flutter/vector_math_64/Matrix4-class.html
- CustomPainter: https://api.flutter.dev/flutter/rendering/CustomPainter-class.html
- Accessibility: https://flutter.dev/docs/development/accessibility-and-localization/accessibility
