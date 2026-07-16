/// Dart model mirroring the backend BloomCard schema
library;

import 'package:flutter/foundation.dart';

/// OWID-specific chart data payload
class OwidChartData {
  final String chartType;
  final List<int> years;
  final List<double> values;
  final String unit;
  final String indicator;
  final String entity;

  OwidChartData({
    required this.chartType,
    required this.years,
    required this.values,
    required this.unit,
    required this.indicator,
    required this.entity,
  });

  factory OwidChartData.fromJson(Map<String, dynamic> json) {
    return OwidChartData(
      chartType: json['chart_type'] as String? ?? 'line',
      years: (json['years'] as List<dynamic>).map((e) => e as int).toList(),
      values: (json['values'] as List<dynamic>).map((e) => (e as num).toDouble()).toList(),
      unit: json['unit'] as String,
      indicator: json['indicator'] as String,
      entity: json['entity'] as String? ?? 'World',
    );
  }

  /// Get chart data as coordinate pairs for fl_chart
  List<ChartPoint> get dataPoints {
    return List.generate(
      years.length,
      (i) => ChartPoint(years[i].toDouble(), values[i]),
    );
  }
}

/// Generic coordinate point for chart rendering
class ChartPoint {
  final double x;
  final double y;

  ChartPoint(this.x, this.y);
}

/// Perspective metadata for the flip overlay
class PerspectiveMeta {
  // Scores are null when no analysis pipeline measured them
  // (score_provenance unset server-side). Null means "show no gauge",
  // never "assume center / 50" — the old defaults presented invented
  // values as analysis (defect D5, 2026-07-16 audit).
  final double? biasScore; // -1.0 (left) to +1.0 (right)
  final double? constructivenessScore; // 0.0 to 100.0
  final List<String> blindspotTags;
  final String? scoreProvenance; // e.g. "selva/<model>@<version>"
  final String reasonTag; // BLINDSPOT_BREAKER, DEEP_DIVE, EXPLORE, etc.

  PerspectiveMeta({
    required this.biasScore,
    required this.constructivenessScore,
    required this.blindspotTags,
    this.scoreProvenance,
    required this.reasonTag,
  });

  factory PerspectiveMeta.fromJson(Map<String, dynamic> json) {
    return PerspectiveMeta(
      biasScore: (json['bias_score'] as num?)?.toDouble(),
      constructivenessScore: (json['constructiveness_score'] as num?)?.toDouble(),
      blindspotTags: (json['blindspot_tags'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList() ?? [],
      scoreProvenance: json['score_provenance'] as String?,
      reasonTag: json['reason_tag'] as String? ?? 'RECENT',
    );
  }

  /// Whether measured perspective scores exist for display.
  bool get hasMeasuredScores => scoreProvenance != null;

  /// Get human-readable reason text for display
  String get reasonText {
    switch (reasonTag) {
      case 'BLINDSPOT_BREAKER':
        return '🌱 Blindspot Breaker: You rarely read this perspective';
      case 'DEEP_DIVE':
        return '⚓ Deep Dive: Connected to your interests';
      case 'EXPLORE':
        return '🗺️ Explore: New territory for you';
      case 'PERSPECTIVE_SHIFT':
        return '🔄 Perspective Shift: Related but novel';
      case 'SERENDIPITY':
        return '✨ Serendipity: Discover something new';
      case 'RECENT':
      default:
        return '📰 Recent: Fresh content';
    }
  }
}

/// Main BloomCard model - polymorphic content container
class BloomCard {
  final String id;
  final String sourceType;
  final String title;
  final String? summary;
  final String originalUrl;
  final Map<String, dynamic> dataPayload;
  final PerspectiveMeta? meta; // Perspective metadata for flip overlay
  final DateTime createdAt;

  BloomCard({
    required this.id,
    required this.sourceType,
    required this.title,
    this.summary,
    required this.originalUrl,
    required this.dataPayload,
    this.meta,
    required this.createdAt,
  });

  factory BloomCard.fromJson(Map<String, dynamic> json) {
    try {
      return BloomCard(
        id: json['id'] as String? ?? 'unknown',
        sourceType: json['source_type'] as String? ?? 'UNKNOWN',
        title: json['title'] as String? ?? 'Untitled',
        summary: json['summary'] as String?,
        originalUrl: json['original_url'] as String? ?? '',
        dataPayload: json['data_payload'] as Map<String, dynamic>? ?? {},
        meta: json['meta'] != null
            ? PerspectiveMeta.fromJson(json['meta'] as Map<String, dynamic>)
            : null,
        createdAt: json['created_at'] != null
            ? DateTime.parse(json['created_at'] as String)
            : DateTime.now(),
      );
    } catch (e) {
      debugPrint('⚠️ Error parsing BloomCard from JSON: $e');
      debugPrint('   JSON: $json');
      // Return error card instead of throwing
      return BloomCard.errorCard('Failed to parse card: $e');
    }
  }

  /// Create an error card when parsing fails
  static BloomCard errorCard(String error) {
    return BloomCard(
      id: 'error-${DateTime.now().millisecondsSinceEpoch}',
      sourceType: 'ERROR',
      title: 'Error Loading Card',
      summary: error,
      originalUrl: '',
      dataPayload: {'error': error},
      meta: null,
      createdAt: DateTime.now(),
    );
  }

  // Legacy accessors for backward compatibility
  double? get biasScore => meta?.biasScore;
  double? get constructivenessScore => meta?.constructivenessScore;
  List<String>? get blindspotTags => meta?.blindspotTags;

  /// Parse OWID-specific payload
  OwidChartData? get owidData {
    if (sourceType == 'OWID') {
      try {
        return OwidChartData.fromJson(dataPayload);
      } catch (e) {
        debugPrint('Error parsing OWID data: $e');
        return null;
      }
    }
    return null;
  }

  /// Parse aesthetic-specific payload
  AestheticData? get aestheticData {
    if (sourceType == 'AESTHETIC') {
      try {
        return AestheticData.fromJson(dataPayload);
      } catch (e) {
        debugPrint('Error parsing aesthetic data: $e');
        return null;
      }
    }
    return null;
  }

  /// Check if this is an OWID card
  bool get isOwid => sourceType == 'OWID';

  /// Check if this is an aesthetic card
  bool get isAesthetic => sourceType == 'AESTHETIC';
}

/// Aesthetic-specific image data payload
class AestheticData {
  final String imageUrl;
  final double aspectRatio;
  final String dominantColor;
  final List<String> vibeTags;
  final int? arenaBlockId;

  AestheticData({
    required this.imageUrl,
    required this.aspectRatio,
    required this.dominantColor,
    required this.vibeTags,
    this.arenaBlockId,
  });

  factory AestheticData.fromJson(Map<String, dynamic> json) {
    return AestheticData(
      imageUrl: json['image_url'] as String,
      aspectRatio: (json['aspect_ratio'] as num?)?.toDouble() ?? 1.0,
      dominantColor: json['dominant_color'] as String? ?? '#808080',
      vibeTags: (json['vibe_tags'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList() ?? [],
      arenaBlockId: json['arena_block_id'] as int?,
    );
  }
}

/// Pagination metadata for finite feed (STORY-007)
class PaginationMeta {
  final int page;
  final int limit;
  final bool hasNextPage;
  final int totalReadToday;
  final int dailyLimit;

  PaginationMeta({
    required this.page,
    required this.limit,
    required this.hasNextPage,
    required this.totalReadToday,
    required this.dailyLimit,
  });

  factory PaginationMeta.fromJson(Map<String, dynamic> json) {
    return PaginationMeta(
      page: json['page'] as int,
      limit: json['limit'] as int,
      hasNextPage: json['has_next_page'] as bool,
      totalReadToday: json['total_read_today'] as int,
      dailyLimit: json['daily_limit'] as int,
    );
  }

  /// Progress as percentage (0.0 to 1.0)
  double get progress => totalReadToday / dailyLimit;

  /// Remaining cards before limit
  int get remaining => dailyLimit - totalReadToday;
}

/// Completion object when daily limit reached (STORY-007)
class CompletionData {
  final String type; // "COMPLETION"
  final String message; // "The Garden is Watered."
  final String subtitle;
  final Map<String, dynamic> stats;

  CompletionData({
    required this.type,
    required this.message,
    required this.subtitle,
    required this.stats,
  });

  factory CompletionData.fromJson(Map<String, dynamic> json) {
    return CompletionData(
      type: json['type'] as String,
      message: json['message'] as String,
      subtitle: json['subtitle'] as String,
      stats: json['stats'] as Map<String, dynamic>,
    );
  }

  /// Get read count from stats
  int get readCount => stats['read_count'] as int? ?? 0;

  /// Get daily limit from stats
  int get dailyLimit => stats['daily_limit'] as int? ?? 20;
}

/// Feed response from API
class FeedResponse {
  final List<BloomCard> cards;
  final PaginationMeta pagination;
  final CompletionData? completion; // Present when daily limit reached
  final bool serendipityEnabled;

  FeedResponse({
    required this.cards,
    required this.pagination,
    this.completion,
    required this.serendipityEnabled,
  });

  factory FeedResponse.fromJson(Map<String, dynamic> json) {
    try {
      // Parse cards, filtering out any errors
      final cardsList = (json['cards'] as List<dynamic>?) ?? [];
      final cards = cardsList
          .map((e) {
            try {
              return BloomCard.fromJson(e as Map<String, dynamic>);
            } catch (err) {
              debugPrint('⚠️ Skipping malformed card: $err');
              return null;
            }
          })
          .whereType<BloomCard>() // Filter out nulls
          .where((card) => card.sourceType != 'ERROR') // Filter out error cards
          .toList();

      return FeedResponse(
        cards: cards,
        pagination: PaginationMeta.fromJson(
          json['pagination'] as Map<String, dynamic>? ?? {},
        ),
        completion: json['completion'] != null
            ? CompletionData.fromJson(json['completion'] as Map<String, dynamic>)
            : null,
        serendipityEnabled: json['serendipity_enabled'] as bool? ?? false,
      );
    } catch (e) {
      debugPrint('❌ Error parsing FeedResponse: $e');
      // Return empty response instead of throwing
      return FeedResponse(
        cards: [],
        pagination: PaginationMeta(
          page: 1,
          limit: 10,
          hasNextPage: false,
          totalReadToday: 0,
          dailyLimit: 20,
        ),
        serendipityEnabled: false,
      );
    }
  }

  /// Check if feed is complete (reached daily limit)
  bool get isComplete => completion != null;

  /// Check if more pages available
  bool get hasNextPage => pagination.hasNextPage;
}
