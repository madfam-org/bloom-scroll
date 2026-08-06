/// Feed controller for pagination and read state (STORY-007)
library;

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/bloom_card.dart';
import '../services/api_service.dart';
import '../services/storage_service.dart';
import 'api_provider.dart';

/// Feed state
class FeedState {
  final List<BloomCard> cards;
  final PaginationMeta? pagination;
  final CompletionData? completion;
  final bool isLoading;
  final String? error;
  final int currentPage;

  /// Mini-Bloom mode (PRD §4.1): a deliberately tiny session. When set,
  /// the session is capped at this many cards and never paginates.
  final int? sessionLimit;

  FeedState({
    this.cards = const [],
    this.pagination,
    this.completion,
    this.isLoading = false,
    this.error,
    this.currentPage = 1,
    this.sessionLimit,
  });

  FeedState copyWith({
    List<BloomCard>? cards,
    PaginationMeta? pagination,
    CompletionData? completion,
    bool? isLoading,
    String? error,
    int? currentPage,
  }) {
    return FeedState(
      cards: cards ?? this.cards,
      pagination: pagination ?? this.pagination,
      completion: completion ?? this.completion,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      currentPage: currentPage ?? this.currentPage,
      sessionLimit: sessionLimit,
    );
  }

  bool get isComplete => completion != null;
  bool get isMiniBloom => sessionLimit != null;
  bool get isMiniSessionDone =>
      sessionLimit != null && cards.length >= sessionLimit!;
  bool get hasNextPage {
    if (isMiniSessionDone) return false;
    return pagination?.hasNextPage ?? false;
  }
}

/// Feed controller with pagination and read state
class FeedController extends StateNotifier<FeedState> {
  final ApiService _apiService;
  final StorageService _storageService;

  FeedController(this._apiService, this._storageService) : super(FeedState()) {
    _init();
  }

  Future<void> _init() async {
    await _storageService.init();
    await loadFeed();
  }

  /// Load feed (first page or refresh). A non-null [sessionLimit] starts
  /// a Mini-Bloom session capped at that many cards (PRD §4.1).
  Future<void> loadFeed({bool refresh = false, int? sessionLimit}) async {
    if (state.isLoading) return;

    state = FeedState(
      cards: state.cards,
      pagination: state.pagination,
      isLoading: true,
      currentPage: state.currentPage,
      sessionLimit: sessionLimit,
    );

    try {
      // Get current read count from storage
      final readCount = await _storageService.getReadCount();
      final readCardIds = await _storageService.getReadCardIds();

      // Fetch first page. Everything already read today is excluded so the
      // server can never hand back duplicates (defect D2, 2026-07-16 audit).
      final response = await _apiService.getFeed(
        page: 1,
        readCount: readCount,
        limit: sessionLimit ?? 10,
        userContext: readCardIds.length > 5 ? readCardIds.sublist(readCardIds.length - 5) : readCardIds,
        excludeIds: readCardIds,
      );

      state = FeedState(
        cards: sessionLimit != null
            ? response.cards.take(sessionLimit).toList()
            : response.cards,
        pagination: response.pagination,
        completion: response.completion,
        isLoading: false,
        currentPage: 1,
        sessionLimit: sessionLimit,
      );
    } catch (e) {
      debugPrint('Error loading feed: $e');
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Load next page (pagination). Mini-Bloom sessions never paginate.
  Future<void> loadNextPage() async {
    if (state.isLoading || !state.hasNextPage || state.isComplete) return;
    if (state.isMiniBloom) return;

    state = state.copyWith(isLoading: true);

    try {
      final readCount = await _storageService.getReadCount();
      final readCardIds = await _storageService.getReadCardIds();

      // Exclude both cards read today and cards already on screen but not
      // yet read, so the next page is guaranteed fresh (defect D2).
      final excludeIds = <String>{
        ...readCardIds,
        ...state.cards.map((card) => card.id),
      }.toList();

      final response = await _apiService.getFeed(
        page: state.currentPage + 1,
        readCount: readCount,
        limit: 10,
        userContext: readCardIds.length > 5 ? readCardIds.sublist(readCardIds.length - 5) : readCardIds,
        excludeIds: excludeIds,
      );

      // Append new cards, dropping anything the server still duplicated
      // (defensive: old servers ignore exclude_ids).
      final knownIds = state.cards.map((card) => card.id).toSet();
      final freshCards =
          response.cards.where((card) => !knownIds.contains(card.id)).toList();

      state = FeedState(
        cards: [...state.cards, ...freshCards],
        pagination: response.pagination,
        completion: response.completion,
        isLoading: false,
        currentPage: state.currentPage + 1,
      );
    } catch (e) {
      debugPrint('Error loading next page: $e');
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Mark a card as read (updates local storage)
  Future<void> markCardAsRead(String cardId) async {
    await _storageService.markCardAsRead(cardId);

    // Update pagination metadata with new read count
    final newReadCount = await _storageService.getReadCount();
    if (state.pagination != null) {
      final updatedPagination = PaginationMeta(
        page: state.pagination!.page,
        limit: state.pagination!.limit,
        hasNextPage: newReadCount < state.pagination!.dailyLimit,
        totalReadToday: newReadCount,
        dailyLimit: state.pagination!.dailyLimit,
      );

      state = state.copyWith(pagination: updatedPagination);
    }
  }

  /// Refresh feed (clear and reload)
  Future<void> refresh() async {
    await loadFeed(refresh: true, sessionLimit: state.sessionLimit);
  }

  /// Start a Mini-Bloom session: 5 cards, one sitting, no pagination.
  Future<void> startMiniBloom() async {
    await loadFeed(refresh: true, sessionLimit: 5);
  }

  /// Return to the regular finite feed.
  Future<void> exitMiniBloom() async {
    await loadFeed(refresh: true);
  }
}

/// Storage service provider
final storageServiceProvider = Provider<StorageService>((ref) {
  return StorageService();
});

/// Feed controller provider
final feedControllerProvider = StateNotifierProvider<FeedController, FeedState>((ref) {
  final apiService = ref.watch(apiServiceProvider);
  final storageService = ref.watch(storageServiceProvider);
  return FeedController(apiService, storageService);
});
