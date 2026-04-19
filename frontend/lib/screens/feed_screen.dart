/// Main feed screen with upward scrolling and masonry grid
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';
import '../models/bloom_card.dart';
import '../providers/feed_controller.dart';
import '../widgets/owid_card.dart';
import '../widgets/aesthetic_card.dart';
import '../widgets/completion_widget.dart';
import '../theme/design_tokens.dart';

class FeedScreen extends ConsumerStatefulWidget {
  const FeedScreen({super.key});

  @override
  ConsumerState<FeedScreen> createState() => _FeedScreenState();
}

class _FeedScreenState extends ConsumerState<FeedScreen> {
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    // Load next page when scrolled to top (in reverse mode)
    if (_scrollController.position.pixels <= _scrollController.position.minScrollExtent + 200) {
      final feedState = ref.read(feedControllerProvider);
      if (!feedState.isLoading && feedState.hasNextPage && !feedState.isComplete) {
        ref.read(feedControllerProvider.notifier).loadNextPage();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final feedState = ref.watch(feedControllerProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('🌱 Bloom Scroll'),
        centerTitle: true,
        elevation: 0,
        backgroundColor: BloomColors.primaryBg,
        foregroundColor: BloomColors.inkPrimary,
        actions: [
          // Progress indicator
          if (feedState.pagination != null && !feedState.isComplete)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: Center(
                child: Text(
                  '${feedState.pagination!.totalReadToday}/${feedState.pagination!.dailyLimit}',
                  style: BloomTypography.labelMedium.copyWith(
                    color: BloomColors.inkSecondary,
                  ),
                ),
              ),
            ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref.read(feedControllerProvider.notifier).refresh();
            },
            tooltip: 'Refresh feed',
          ),
        ],
      ),
      body: _buildBody(context, feedState),
    );
  }

  Widget _buildBody(BuildContext context, FeedState feedState) {
    // Loading state (initial load)
    if (feedState.isLoading && feedState.cards.isEmpty) {
      return const Center(
        child: CircularProgressIndicator(
          color: BloomColors.growthGreen,
        ),
      );
    }

    // Error state
    if (feedState.error != null && feedState.cards.isEmpty) {
      return _buildError(context, feedState.error!);
    }

    // Empty state
    if (feedState.cards.isEmpty && !feedState.isLoading) {
      return _buildEmptyState(context);
    }

    // Feed content
    return _buildFeed(context, feedState);
  }

  Widget _buildFeed(BuildContext context, FeedState feedState) {
    return Column(
      children: [
        // Progress bar
        if (feedState.pagination != null && !feedState.isComplete)
          LinearProgressIndicator(
            value: feedState.pagination!.progress,
            backgroundColor: BloomColors.surfaceBg,
            valueColor: AlwaysStoppedAnimation<Color>(BloomColors.growthGreen),
            minHeight: 2,
          ),

        // The upward scrolling masonry grid
        Expanded(
          child: CustomScrollView(
            controller: _scrollController,
            // CRITICAL: reverse: true makes index 0 appear at the bottom
            reverse: true,
            physics: const BouncingScrollPhysics(),
            slivers: [
              // Completion widget at top (if reached limit)
              if (feedState.isComplete && feedState.completion != null)
                SliverToBoxAdapter(
                  child: CompletionWidget(
                    completion: feedState.completion!,
                  ),
                )
              else
                // End marker at top (if more pages available)
                SliverToBoxAdapter(
                  child: _buildEndMarker(context, feedState),
                ),

              // Masonry grid of cards
              SliverPadding(
                padding: const EdgeInsets.all(BloomSpacing.screenPadding),
                sliver: SliverMasonryGrid.count(
                  crossAxisCount: 2,
                  mainAxisSpacing: BloomSpacing.md,
                  crossAxisSpacing: BloomSpacing.md,
                  childCount: feedState.cards.length,
                  itemBuilder: (context, index) {
                    return _buildCardForIndex(context, feedState.cards, index);
                  },
                ),
              ),

              // Loading indicator when loading more
              if (feedState.isLoading && feedState.cards.isNotEmpty)
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.all(BloomSpacing.lg),
                    child: Center(
                      child: CircularProgressIndicator(
                        color: BloomColors.growthGreen,
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }

  /// Build appropriate card widget with "Robin Hood" layout logic
  Widget _buildCardForIndex(BuildContext context, List<BloomCard> cards, int index) {
    final card = cards[index];

    // OWID cards: Full width (span 2 columns)
    if (card.isOwid) {
      return _buildFullWidthCard(card);
    }

    // Aesthetic cards: Single column (natural masonry fit)
    if (card.isAesthetic) {
      return AestheticCard(card: card);
    }

    // Fallback for other card types
    return _buildGenericCard(context, card);
  }

  /// Wrap OWID cards to span full width
  Widget _buildFullWidthCard(BloomCard card) {
    return SizedBox(
      // This will be placed in masonry but we want it full width
      // The parent will be 1 column wide, so we just render OwidCard normally
      child: OwidCard(card: card),
    );
  }

  Widget _buildEndMarker(BuildContext context, FeedState feedState) {
    if (!feedState.hasNextPage && !feedState.isComplete) {
      return Container(
        margin: const EdgeInsets.all(BloomSpacing.lg),
        padding: const EdgeInsets.all(BloomSpacing.xl),
        decoration: BoxDecoration(
          color: BloomColors.primaryBg,
          borderRadius: BloomSpacing.cardBorderRadius,
          border: Border.all(
            color: BloomColors.inkTertiary,
            width: BloomSpacing.borderWidth,
          ),
        ),
        child: Column(
          children: [
            Icon(
              Icons.check_circle_outline,
              size: 48,
              color: BloomColors.growthGreen,
            ),
            const SizedBox(height: BloomSpacing.md),
            Text(
              'You\'ve reached the end! 🌸',
              style: BloomTypography.h3.copyWith(
                color: BloomColors.growthGreen,
              ),
            ),
            const SizedBox(height: BloomSpacing.sm),
            Text(
              'No infinite scroll here. Time for a break!',
              style: BloomTypography.bodyMedium.copyWith(
                color: BloomColors.inkSecondary,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      );
    }

    // Loading more indicator
    if (feedState.hasNextPage) {
      return Padding(
        padding: const EdgeInsets.all(BloomSpacing.lg),
        child: Center(
          child: Text(
            'Scroll up for more blooms...',
            style: BloomTypography.caption.copyWith(
              color: BloomColors.inkSecondary,
            ),
          ),
        ),
      );
    }

    return const SizedBox.shrink();
  }

  Widget _buildGenericCard(BuildContext context, BloomCard card) {
    return Card(
      margin: const EdgeInsets.all(4),
      color: BloomColors.primaryBg,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BloomSpacing.cardBorderRadius,
        side: BorderSide(
          color: BloomColors.inkTertiary,
          width: BloomSpacing.borderWidth,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(BloomSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              card.title,
              // BloomTypography defines h1/h2/h3 (no h4); use h3 as the
              // smallest heading style available.
              style: BloomTypography.h3,
            ),
            const SizedBox(height: BloomSpacing.xs),
            Chip(
              label: Text(card.sourceType),
              backgroundColor: BloomColors.surfaceBg,
              labelStyle: BloomTypography.caption,
              visualDensity: VisualDensity.compact,
            ),
            if (card.summary != null) ...[
              const SizedBox(height: BloomSpacing.sm),
              Text(
                card.summary!,
                style: BloomTypography.bodyMedium,
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.energy_savings_leaf,
            size: 64,
            color: BloomColors.inkTertiary,
          ),
          const SizedBox(height: BloomSpacing.md),
          Text(
            'No cards in the feed yet',
            style: BloomTypography.h3.copyWith(
              color: BloomColors.inkSecondary,
            ),
          ),
          const SizedBox(height: BloomSpacing.sm),
          Text(
            'Ingest some data from the backend',
            style: BloomTypography.bodyMedium.copyWith(
              color: BloomColors.inkTertiary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildError(BuildContext context, String error) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(BloomSpacing.xl),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: BloomColors.bloomRed,
            ),
            const SizedBox(height: BloomSpacing.md),
            Text(
              'Failed to load feed',
              style: BloomTypography.h3.copyWith(
                color: BloomColors.bloomRed,
              ),
            ),
            const SizedBox(height: BloomSpacing.sm),
            Text(
              error,
              style: BloomTypography.bodyMedium.copyWith(
                color: BloomColors.inkSecondary,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: BloomSpacing.lg),
            FilledButton.icon(
              onPressed: () {
                ref.read(feedControllerProvider.notifier).refresh();
              },
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
              style: FilledButton.styleFrom(
                backgroundColor: BloomColors.growthGreen,
              ),
            ),
            const SizedBox(height: BloomSpacing.sm),
            TextButton(
              onPressed: () {
                _showConnectionDialog(context);
              },
              child: const Text('Check connection settings'),
            ),
          ],
        ),
      ),
    );
  }

  void _showConnectionDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Connection Help'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Make sure the backend is running:'),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: BloomColors.surfaceBg,
                borderRadius: BloomSpacing.cardBorderRadius,
              ),
              child: Text(
                'cd backend\n./run_dev.sh',
                style: BloomTypography.bodyMedium.copyWith(
                  fontFamily: 'monospace',
                ),
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'iOS Simulator: http://localhost:8000\n'
              'Android Emulator: http://10.0.2.2:8000\n'
              'Physical Device: http://<your-ip>:8000',
              style: BloomTypography.bodySmall,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }
}
