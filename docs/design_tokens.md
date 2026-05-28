# Bloom Scroll: Design System ("Paper & Ink")

**Last audited**: 2026-05-28. This compact token sheet matches the implementation in `frontend/lib/theme/design_tokens.dart`; the fuller guide is [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md).

## 1. Core Philosophy
The UI should feel like a printed Sunday newspaper, not a software application.
* **High Contrast:** Black ink on warm paper.
* **No Shadows:** Use borders and whitespace to define hierarchy.
* **Data First:** Charts are the "hero" images, not decorations.

## 2. Color Palette

### The Canvas (Backgrounds)
* `primary_bg`: `#FDFCF8` (Warm Off-White / "Old Paper")
* `surface_bg`: `#F4F1EA` (Slightly darker paper for cards/containers)
* `skeleton_bg`: `#E6E2D6` (For loading states - warm gray, not blue-gray)

### The Ink (Typography & Icons)
* `ink_primary`: `#1A1A1A` (Soft Black - rarely use pure #000)
* `ink_secondary`: `#595959` (Graphite - for metadata/subtitles)
* `ink_tertiary`: `#8C8C8C` (Stone - for disabled states/borders)

### The Garden (Data & Accents)
* `bloom_red`: `#D9534F` (Muted Coral - for "Action" or "Alerts")
* `growth_green`: `#2D6A4F` (Botanical Green - for positive trends/serendipity)
* `chart_line`: `#1A1A1A` (Charts should be drawn in Ink)
* `chart_fill`: `#2D6A4F` (With 10% Opacity)

## 3. Typography
* **Headings:** `Libre Baskerville` (Google Font)
    * *Weight:* Bold (700)
    * *Usage:* App Bar, Article Titles, Big Statistics.
* **Body/UI:** `Inter` (Google Font)
    * *Weight:* Regular (400) & SemiBold (600)
    * *Usage:* Chart labels, buttons, summary text.
    * *Feature:* Enable `FontFeature.tabularFigures()` for all data numbers.

## 4. Layout & Spacing
* **Grid Unit:** 8px
* **Padding:** Standard screen padding is `20px` (not 16px - give it breath).
* **Corner Radius:**
    * Cards: `4px` (Subtle, near-sharp to mimic cut paper).
    * Buttons: `0px` (Rectangular pill) or `4px`.
* **Elevation:** 0.
    * *Rule:* Do not use drop shadows. Use a `1px` border of `ink_tertiary` to define edges if necessary.

## 5. Chart Specifics (fl_chart Config)
* **Grid Lines:** `false` (Remove background grids completely).
* **Axis Titles:** `false` (Remove X/Y labels unless critical).
* **Border:** `false` (No box around the chart).
* **Touch:** Show a `CircleAvatar` of `bloom_red` only when the user touches the line.
