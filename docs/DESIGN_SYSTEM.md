# 🎨 Bloom Scroll: Design System

**"Paper & Ink"** - The Vibe

**Last audited**: 2026-05-28. Current implementation tokens live in `frontend/lib/theme/design_tokens.dart` and `frontend/lib/theme/bloom_theme.dart`.

---

## Philosophy

The UI should feel like a **printed Sunday newspaper**, not a software application.

### Core Principles
- **High Contrast**: Black ink on warm paper
- **No Shadows**: Use borders and whitespace to define hierarchy
- **Data First**: Charts are the "hero" images, not decorations
- **Botanical Metaphors**: Growth, blooming, and gardening throughout

---

## Color Palette

### The Canvas (Backgrounds)

```dart
// Warm paper tones
static const Color primaryBg = Color(0xFFFDFCF8);    // #FDFCF8 - Old Paper
static const Color surfaceBg = Color(0xFFF4F1EA);    // #F4F1EA - Card Background
static const Color skeletonBg = Color(0xFFE6E2D6);   // #E6E2D6 - Loading State
```

**Usage**:
- `primaryBg`: Main screen background
- `surfaceBg`: Cards, elevated containers, dialogs
- `skeletonBg`: Shimmer loading placeholders

### The Ink (Typography & Icons)

```dart
// Soft black tones (never pure #000)
static const Color inkPrimary = Color(0xFF1A1A1A);   // #1A1A1A - Headings, Body
static const Color inkSecondary = Color(0xFF595959); // #595959 - Metadata, Captions
static const Color inkTertiary = Color(0xFF8C8C8C);  // #8C8C8C - Disabled, Borders
```

**Usage**:
- `inkPrimary`: Headlines, body text, chart lines
- `inkSecondary`: Subtitles, timestamps, secondary information
- `inkTertiary`: Borders, disabled states, placeholder text

### The Garden (Data & Accents)

```dart
// Botanical and alert colors
static const Color bloomRed = Color(0xFFD9534F);     // #D9534F - Alerts, Touch Indicators
static const Color growthGreen = Color(0xFF2D6A4F);  // #2D6A4F - Positive, Success, Growth
static const Color chartLine = Color(0xFF1A1A1A);    // #1A1A1A - Chart strokes
static const Color chartFill = Color(0x1A2D6A4F);    // #2D6A4F @ 10% - Chart fills
```

**Usage**:
- `bloomRed`: Action buttons, touch indicators on charts, error states
- `growthGreen`: Completion messages, positive trends, serendipity tags
- `chartLine`: All chart strokes (ink color for consistency)
- `chartFill`: Chart area fills (subtle green with 10% opacity)

### Color Usage Examples

```dart
// Background hierarchy
Scaffold(
  backgroundColor: BloomColors.primaryBg,
  body: Card(
    color: BloomColors.surfaceBg,
    // ...
  ),
)

// Text hierarchy
Text('Headline', style: TextStyle(color: BloomColors.inkPrimary))
Text('Subtitle', style: TextStyle(color: BloomColors.inkSecondary))

// Borders
Container(
  decoration: BoxDecoration(
    border: Border.all(
      color: BloomColors.inkTertiary,
      width: 1,
    ),
  ),
)
```

---

## Typography

### Font Families

**Headings**: `Libre Baskerville` (Google Font)
- Weight: **Bold (700)**
- Usage: App Bar, Article Titles, Big Statistics, Card Headings
- Character: Serif, editorial, newspaper-like

**Body/UI**: `Inter` (Google Font)
- Weight: **Regular (400)** & **SemiBold (600)**
- Usage: Chart labels, buttons, body text, captions
- Character: Sans-serif, readable, modern
- **Feature**: Enable `FontFeature.tabularFigures()` for all data numbers

### Type Scale

```dart
// Design Tokens (frontend/lib/theme/design_tokens.dart)
class BloomTypography {
  static const String headingFont = 'Libre Baskerville';
  static const String bodyFont = 'Inter';

  // Headings (Libre Baskerville)
  static const TextStyle h1 = TextStyle(
    fontFamily: headingFont,
    fontSize: 28,
    fontWeight: FontWeight.w700,
    color: BloomColors.inkPrimary,
    height: 1.3,
  );

  static const TextStyle h2 = TextStyle(
    fontFamily: headingFont,
    fontSize: 22,
    fontWeight: FontWeight.w700,
    color: BloomColors.inkPrimary,
    height: 1.3,
  );

  static const TextStyle h3 = TextStyle(
    fontFamily: headingFont,
    fontSize: 18,
    fontWeight: FontWeight.w700,
    color: BloomColors.inkPrimary,
    height: 1.3,
  );

  // Body (Inter)
  static const TextStyle bodyLarge = TextStyle(
    fontFamily: bodyFont,
    fontSize: 16,
    fontWeight: FontWeight.w400,
    color: BloomColors.inkPrimary,
    height: 1.5,
  );

  static const TextStyle bodyMedium = TextStyle(
    fontFamily: bodyFont,
    fontSize: 14,
    fontWeight: FontWeight.w400,
    color: BloomColors.inkPrimary,
    height: 1.5,
  );

  static const TextStyle bodySmall = TextStyle(
    fontFamily: bodyFont,
    fontSize: 12,
    fontWeight: FontWeight.w400,
    color: BloomColors.inkSecondary,
    height: 1.4,
  );

  // Labels & Captions (Inter)
  static const TextStyle labelLarge = TextStyle(
    fontFamily: bodyFont,
    fontSize: 16,
    fontWeight: FontWeight.w600,
    color: BloomColors.inkPrimary,
    height: 1.2,
  );

  static const TextStyle labelMedium = TextStyle(
    fontFamily: bodyFont,
    fontSize: 14,
    fontWeight: FontWeight.w600,
    color: BloomColors.inkPrimary,
    height: 1.2,
  );

  static const TextStyle labelSmall = TextStyle(
    fontFamily: bodyFont,
    fontSize: 12,
    fontWeight: FontWeight.w600,
    color: BloomColors.inkPrimary,
    height: 1.2,
  );

  static const TextStyle caption = TextStyle(
    fontFamily: bodyFont,
    fontSize: 11,
    fontWeight: FontWeight.w400,
    color: BloomColors.inkSecondary,
    height: 1.3,
  );

  // Data display (Inter with tabular figures)
  static const TextStyle dataLarge = TextStyle(
    fontFamily: bodyFont,
    fontSize: 24,
    fontWeight: FontWeight.w600,
    color: BloomColors.inkPrimary,
    fontFeatures: [FontFeature.tabularFigures()],
  );

  static const TextStyle dataMedium = TextStyle(
    fontFamily: bodyFont,
    fontSize: 16,
    fontWeight: FontWeight.w600,
    color: BloomColors.inkPrimary,
    fontFeatures: [FontFeature.tabularFigures()],
  );

  static const TextStyle dataSmall = TextStyle(
    fontFamily: bodyFont,
    fontSize: 12,
    fontWeight: FontWeight.w400,
    color: BloomColors.inkPrimary,
    fontFeatures: [FontFeature.tabularFigures()],
  );
}
```

### Typography Usage

```dart
// Headlines
Text('The Garden is Watered', style: BloomTypography.h2)

// Body text
Text('You\'ve reached today\'s limit...', style: BloomTypography.bodyMedium)

// Data displays (with tabular figures for alignment)
Text('20', style: BloomTypography.dataLarge)
Text('10/20', style: BloomTypography.dataMedium)

// Metadata/timestamps
Text('2 hours ago', style: BloomTypography.caption)
```

---

## Layout & Spacing

### Grid System

**Base Unit**: `8px`

All spacing values are multiples of 8px for consistent rhythm.

```dart
class BloomSpacing {
  static const double xs = 4;   // 0.5 units
  static const double sm = 8;   // 1 unit
  static const double md = 16;  // 2 units
  static const double lg = 24;  // 3 units
  static const double xl = 32;  // 4 units
  static const double xxl = 48; // 6 units

  // Semantic spacing
  static const double screenPadding = 20;  // Not 16! Give it breath
  static const double cardPadding = 16;
  static const double buttonPadding = 12;
}
```

### Corner Radius

**Philosophy**: Near-sharp to mimic cut paper.

```dart
static const double cardRadius = 4;     // Subtle, paper-like
static const double buttonRadius = 4;   // Rectangular pill
static const double dialogRadius = 8;   // Slightly softer for modals

static final cardBorderRadius = BorderRadius.circular(cardRadius);
static final buttonBorderRadius = BorderRadius.circular(buttonRadius);
```

### Elevation & Shadows

**Rule**: **Do NOT use drop shadows.**

Use a `1px` border of `ink_tertiary` to define edges instead.

```dart
// ❌ WRONG
Container(
  decoration: BoxDecoration(
    boxShadow: [BoxShadow(...)],  // NO!
  ),
)

// ✅ CORRECT
Container(
  decoration: BoxDecoration(
    color: BloomColors.surfaceBg,
    border: Border.all(
      color: BloomColors.inkTertiary,
      width: 1,
    ),
    borderRadius: BloomSpacing.cardBorderRadius,
  ),
)
```

### Padding Scale

```dart
// Contextual padding
const EdgeInsets.all(BloomSpacing.screenPadding)  // Screen edges (20px)
const EdgeInsets.all(BloomSpacing.cardPadding)    // Card content (16px)
const EdgeInsets.symmetric(
  horizontal: BloomSpacing.md,
  vertical: BloomSpacing.sm,
)  // Buttons, chips
```

---

## Components

### Cards

**Style**: Paper-like with 1px border

```dart
Card(
  elevation: 0,  // NO shadows
  color: BloomColors.primaryBg,
  shape: RoundedRectangleBorder(
    borderRadius: BloomSpacing.cardBorderRadius,
    side: BorderSide(
      color: BloomColors.inkTertiary,
      width: 1,
    ),
  ),
  child: Padding(
    padding: const EdgeInsets.all(BloomSpacing.cardPadding),
    child: // ...content
  ),
)
```

### Buttons

**Primary Button**:
```dart
FilledButton(
  style: FilledButton.styleFrom(
    backgroundColor: BloomColors.growthGreen,
    foregroundColor: BloomColors.primaryBg,
    shape: RoundedRectangleBorder(
      borderRadius: BloomSpacing.buttonBorderRadius,
    ),
    padding: const EdgeInsets.symmetric(
      horizontal: BloomSpacing.lg,
      vertical: BloomSpacing.sm,
    ),
  ),
  child: Text('Refresh', style: BloomTypography.labelLarge),
)
```

**Secondary Button**:
```dart
OutlinedButton(
  style: OutlinedButton.styleFrom(
    foregroundColor: BloomColors.inkPrimary,
    side: BorderSide(color: BloomColors.inkTertiary),
    shape: RoundedRectangleBorder(
      borderRadius: BloomSpacing.buttonBorderRadius,
    ),
  ),
  child: Text('Back to card', style: BloomTypography.labelMedium),
)
```

### Icons

**Style**: Outlined (not filled)
**Size**: 24px standard, 16px for small contexts

```dart
Icon(
  Icons.info_outline,  // Use outlined variants
  size: 24,
  color: BloomColors.inkPrimary,
)
```

---

## Chart Specifics (fl_chart)

### Configuration

**Philosophy**: Tufte-style minimalism - remove all non-data ink.

```dart
class BloomChartConfig {
  // Grid settings
  static const bool showGrid = false;  // NO background grids
  static const bool showBorder = false;  // NO box around chart

  // Axis settings
  static const bool showAxisTitles = false;  // Remove X/Y labels unless critical

  // Line chart
  static const double lineWidth = 2.0;
  static const Color lineColor = BloomColors.inkPrimary;  // Draw in ink
  static final Color fillColor = BloomColors.chartFill;  // 10% green

  // Touch interaction
  static const Color touchColor = BloomColors.bloomRed;  // Red dot on touch
  static const double touchRadius = 4.0;
}
```

### Implementation

```dart
LineChart(
  LineChartData(
    gridData: FlGridData(show: false),  // No grid
    borderData: FlBorderData(show: false),  // No border
    titlesData: FlTitlesData(show: false),  // No axis labels

    lineBarsData: [
      LineChartBarData(
        spots: dataPoints,
        color: BloomChartConfig.lineColor,
        barWidth: BloomChartConfig.lineWidth,
        dotData: FlDotData(show: false),  // Hide dots except on touch
        belowBarData: BarAreaData(
          show: true,
          color: BloomChartConfig.fillColor,
        ),
      ),
    ],

    lineTouchData: LineTouchData(
      touchTooltipData: LineTouchTooltipData(
        tooltipBgColor: BloomColors.surfaceBg,
        getTooltipItems: (touchedSpots) {
          // Show red circle + value on touch
          return touchedSpots.map((spot) {
            return LineTooltipItem(
              '${spot.y.toStringAsFixed(1)}',
              BloomTypography.labelMedium,
            );
          }).toList();
        },
      ),
    ),
  ),
)
```

### Chart Types

**Line Charts** (OWID data):
- Stroke: `inkPrimary` (2px)
- Fill: `chartFill` (10% green)
- No grid, no border
- Touch: Red circle tooltip

**Bar Charts** (Future):
- Bars: `growthGreen` or `inkPrimary`
- No background, minimal labels

---

## Animation Guidelines

### Timing

**Snappy** (<300ms): UI feedback, state changes
**Medium** (300-500ms): Page transitions, card flips
**Slow** (>500ms): Completion celebrations, onboarding

```dart
// Flip animation (STORY-006)
AnimationController(
  duration: const Duration(milliseconds: 300),  // Snappy!
  vsync: this,
)

// Completion flower animation (STORY-007)
TweenAnimationBuilder(
  duration: const Duration(milliseconds: 800),  // Celebratory
  curve: Curves.elasticOut,
  // ...
)
```

### Curves

**Ease Out**: Default for most animations
```dart
CurvedAnimation(
  parent: controller,
  curve: Curves.easeOut,
)
```

**Ease In Out**: Flip animations, reversible actions
```dart
CurvedAnimation(
  curve: Curves.easeInOut,
)
```

**Elastic Out**: Playful, celebratory (completion widget)
```dart
TweenAnimationBuilder(
  curve: Curves.elasticOut,
  // Bouncy, joyful feel
)
```

---

## Accessibility

### Color Contrast

All text meets **WCAA AA** standards:
- `inkPrimary` on `primaryBg`: 11.5:1 (AAA)
- `inkSecondary` on `primaryBg`: 7.2:1 (AA)
- `inkTertiary` on `primaryBg`: 4.6:1 (AA for large text)

### Touch Targets

**Minimum**: 48x48 dp (Material Design standard)

```dart
// Icon buttons
IconButton(
  iconSize: 24,
  constraints: BoxConstraints(
    minWidth: 48,
    minHeight: 48,
  ),
  // ...
)
```

### Semantic Labels

```dart
// Screen readers
Semantics(
  label: 'Close perspective overlay',
  child: IconButton(
    icon: Icon(Icons.close),
    onPressed: onClose,
  ),
)
```

### Font Scaling

Support system font scaling up to 200%:
```dart
// Use relative sizing, not fixed
MediaQuery.of(context).textScaleFactor
```

---

## Design Tokens Reference

### Quick Reference Table

| Token | Value | Usage |
|-------|-------|-------|
| `primaryBg` | `#FDFCF8` | Screen background |
| `surfaceBg` | `#F4F1EA` | Card background |
| `inkPrimary` | `#1A1A1A` | Body text, headlines |
| `inkSecondary` | `#595959` | Metadata, captions |
| `inkTertiary` | `#8C8C8C` | Borders, disabled |
| `bloomRed` | `#D9534F` | Alerts, touch |
| `growthGreen` | `#2D6A4F` | Success, positive |
| `screenPadding` | `20px` | Screen edges |
| `cardPadding` | `16px` | Card content |
| `cardRadius` | `4px` | Corner radius |
| `borderWidth` | `1px` | All borders |

---

## Botanical Language

### Terminology

Use gardening metaphors throughout the UI:

- **"Plant a seed"** → Add to reading list
- **"Bloom"** → Card appears in feed
- **"The Garden is Watered"** → Daily limit reached
- **"New blooms arrive tomorrow"** → Return message
- **"Blindspot Breaker"** → 🌱 Discover new perspective
- **"Serendipity"** → ✨ Unexpected connection

### Icon Mapping

- 🌱 Growth, new perspectives
- 🌸 Completion, beauty
- 🌿 Natural, organic
- ⚓ Deep dive, stability
- 🗺️ Exploration
- 🔄 Perspective shift
- ✨ Serendipity

---

## Implementation Checklist

When building new features, ensure:

- [ ] Colors from `BloomColors` class (no hardcoded hex)
- [ ] Typography from `BloomTypography` class (no inline styles)
- [ ] Spacing from `BloomSpacing` class (multiples of 8)
- [ ] No drop shadows (use 1px borders instead)
- [ ] Corner radius = 4px for cards
- [ ] Icons are outlined (not filled)
- [ ] Touch targets ≥ 48x48 dp
- [ ] Charts have no grids or borders
- [ ] Animations < 300ms for UI feedback
- [ ] Botanical language in copy

---

**Version**: 2.1
**Last Updated**: 2026-05-28
**Maintainer**: Design Team
