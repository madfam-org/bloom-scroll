import 'package:bloom_scroll/models/bloom_card.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('BloomCard', () {
    test('parses perspective metadata and OWID payloads', () {
      final card = BloomCard.fromJson({
        'id': 'card-1',
        'source_type': 'OWID',
        'title': 'Life expectancy rises',
        'summary': 'A compact data story.',
        'original_url': 'https://example.com/life-expectancy',
        'created_at': '2026-05-28T12:00:00Z',
        'data_payload': {
          'chart_type': 'line',
          'years': [2020, 2021],
          'values': [72.4, 73],
          'unit': 'years',
          'indicator': 'Life expectancy',
          'entity': 'World',
        },
        'meta': {
          'bias_score': 0.25,
          'constructiveness_score': 88,
          'blindspot_tags': ['global-south'],
          'reason_tag': 'PERSPECTIVE_SHIFT',
        },
      });

      expect(card.isOwid, isTrue);
      expect(card.meta?.constructivenessScore, 88);
      // No score_provenance -> gauges must not render (defect D5).
      expect(card.meta?.hasMeasuredScores, isFalse);
      expect(card.blindspotTags, ['global-south']);
      expect(card.owidData?.dataPoints.first.x, 2020);
      expect(card.owidData?.dataPoints.last.y, 73);
      expect(card.meta?.reasonText, contains('Perspective Shift'));
    });

    test('null scores stay null and provenance flags measured cards', () {
      final unmeasured = PerspectiveMeta.fromJson({
        'bias_score': null,
        'constructiveness_score': null,
        'blindspot_tags': [],
        'score_provenance': null,
        'reason_tag': 'RECENT',
      });
      expect(unmeasured.biasScore, isNull);
      expect(unmeasured.constructivenessScore, isNull);
      expect(unmeasured.hasMeasuredScores, isFalse);

      final measured = PerspectiveMeta.fromJson({
        'bias_score': 0.25,
        'constructiveness_score': 88,
        'blindspot_tags': ['climate'],
        'score_provenance': 'selva/test-model@1',
        'reason_tag': 'EXPLORE',
      });
      expect(measured.biasScore, 0.25);
      expect(measured.hasMeasuredScores, isTrue);
      expect(measured.scoreProvenance, 'selva/test-model@1');
    });

    test('returns safe defaults for sparse aesthetic payloads', () {
      final card = BloomCard.fromJson({
        'id': 'card-2',
        'source_type': 'AESTHETIC',
        'title': 'Solar interface study',
        'original_url': 'https://example.com/image',
        'created_at': '2026-05-28T12:00:00Z',
        'data_payload': {
          'image_url': 'https://example.com/image.jpg',
        },
      });

      expect(card.isAesthetic, isTrue);
      expect(card.aestheticData?.aspectRatio, 1.0);
      expect(card.aestheticData?.dominantColor, '#808080');
      expect(card.aestheticData?.vibeTags, isEmpty);
    });
  });

  group('FeedResponse', () {
    test('parses finite-feed completion and filters malformed cards', () {
      final response = FeedResponse.fromJson({
        'cards': [
          {
            'id': 'card-1',
            'source_type': 'OWID',
            'title': 'Valid card',
            'original_url': 'https://example.com/card',
            'created_at': '2026-05-28T12:00:00Z',
            'data_payload': <String, dynamic>{},
          },
          {
            'id': 'card-2',
            'source_type': 'OWID',
            'title': 'Malformed card',
            'original_url': 'https://example.com/bad-card',
            'created_at': 'not-a-date',
            'data_payload': <String, dynamic>{},
          },
        ],
        'pagination': {
          'page': 2,
          'limit': 10,
          'has_next_page': false,
          'total_read_today': 20,
          'daily_limit': 20,
        },
        'completion': {
          'type': 'COMPLETION',
          'message': 'The Garden is Watered.',
          'subtitle': 'Return tomorrow for fresh blooms.',
          'stats': {
            'read_count': 20,
            'daily_limit': 20,
          },
        },
        'serendipity_enabled': true,
      });

      expect(response.cards, hasLength(1));
      expect(response.cards.single.title, 'Valid card');
      expect(response.isComplete, isTrue);
      expect(response.hasNextPage, isFalse);
      expect(response.completion?.readCount, 20);
      expect(response.pagination.progress, 1.0);
      expect(response.pagination.remaining, 0);
      expect(response.serendipityEnabled, isTrue);
    });

    test('falls back to an empty terminal response when pagination is malformed', () {
      final response = FeedResponse.fromJson({
        'cards': [],
        'pagination': <String, dynamic>{},
      });

      expect(response.cards, isEmpty);
      expect(response.hasNextPage, isFalse);
      expect(response.pagination.dailyLimit, 20);
    });
  });
}
