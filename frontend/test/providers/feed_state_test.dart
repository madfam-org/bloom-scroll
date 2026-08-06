import 'package:bloom_scroll/models/bloom_card.dart';
import 'package:bloom_scroll/providers/feed_controller.dart';
import 'package:flutter_test/flutter_test.dart';

BloomCard _card(String id) {
  return BloomCard.fromJson({
    'id': id,
    'source_type': 'OWID',
    'title': 'Card $id',
    'original_url': 'https://example.com/$id',
    'created_at': '2026-07-16T00:00:00Z',
    'data_payload': const <String, dynamic>{},
  });
}

PaginationMeta _pagination({required bool hasNextPage}) {
  return PaginationMeta(
    page: 1,
    limit: 10,
    hasNextPage: hasNextPage,
    totalReadToday: 0,
    dailyLimit: 20,
  );
}

void main() {
  group('FeedState Mini-Bloom (PRD §4.1)', () {
    test('normal sessions follow server pagination', () {
      final state = FeedState(
        cards: [_card('a'), _card('b')],
        pagination: _pagination(hasNextPage: true),
      );
      expect(state.isMiniBloom, isFalse);
      expect(state.hasNextPage, isTrue);
    });

    test('mini session caps at sessionLimit and never paginates', () {
      final state = FeedState(
        cards: List.generate(5, (i) => _card('$i')),
        pagination: _pagination(hasNextPage: true),
        sessionLimit: 5,
      );
      expect(state.isMiniBloom, isTrue);
      expect(state.isMiniSessionDone, isTrue);
      // Even though the server advertises more pages, the mini session ends.
      expect(state.hasNextPage, isFalse);
    });

    test('mini session below the cap still shows its cards', () {
      final state = FeedState(
        cards: [_card('a'), _card('b')],
        pagination: _pagination(hasNextPage: false),
        sessionLimit: 5,
      );
      expect(state.isMiniBloom, isTrue);
      expect(state.isMiniSessionDone, isFalse);
      expect(state.hasNextPage, isFalse);
    });
  });
}
