/// Perspective Overlay - "The Back of the Card"
library;

import 'package:flutter/material.dart';
import '../../models/bloom_card.dart';
import '../../theme/design_tokens.dart';
import 'bias_compass.dart';
import 'constructiveness_ring.dart';
import 'serendipity_tag.dart';

class PerspectiveOverlay extends StatelessWidget {
  final BloomCard card;
  final VoidCallback onClose;

  const PerspectiveOverlay({
    super.key,
    required this.card,
    required this.onClose,
  });

  @override
  Widget build(BuildContext context) {
    final meta = card.meta;

    // If no perspective metadata, show a message
    if (meta == null) {
      return _buildNoMetaCard(context);
    }

    return Container(
      decoration: BoxDecoration(
        color: BloomColors.primaryBg, // Same "paper" background
        borderRadius: BloomSpacing.cardBorderRadius,
        border: Border.all(
          color: BloomColors.inkTertiary,
          width: BloomSpacing.borderWidth,
        ),
      ),
      child: Stack(
        children: [
          // Main content
          Padding(
            padding: const EdgeInsets.all(BloomSpacing.screenPadding),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                // Header
                Row(
                  children: [
                    Icon(
                      Icons.leaderboard_outlined,
                      size: 24,
                      color: BloomColors.inkPrimary,
                    ),
                    const SizedBox(width: BloomSpacing.sm),
                    Expanded(
                      child: Text(
                        'Perspective Stats',
                        style: BloomTypography.h3,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: BloomSpacing.lg),

                // 1. Serendipity Tag (Why this card)
                SerendipityTag(meta: meta),
                const SizedBox(height: BloomSpacing.lg),

                // 2 & 3. Bias meter + constructiveness ring — only rendered
                // when a pipeline actually measured the scores. Showing
                // gauges for unmeasured cards presented fabricated values
                // as analysis (defect D5, 2026-07-16 audit).
                if (meta.hasMeasuredScores && meta.biasScore != null) ...[
                  BiasCompass(biasScore: meta.biasScore!),
                  const SizedBox(height: BloomSpacing.lg),
                ],
                if (meta.hasMeasuredScores && meta.constructivenessScore != null) ...[
                  ConstructivenessRing(score: meta.constructivenessScore!),
                  const SizedBox(height: BloomSpacing.md),
                ],
                if (!meta.hasMeasuredScores)
                  Text(
                    'Perspective analysis not yet available for this card.',
                    style: BloomTypography.caption.copyWith(
                      color: BloomColors.inkSecondary,
                    ),
                  ),

                // Blindspot tags if present
                if (meta.blindspotTags.isNotEmpty) ...[
                  const SizedBox(height: BloomSpacing.md),
                  Wrap(
                    spacing: BloomSpacing.xs,
                    runSpacing: BloomSpacing.xs,
                    children: meta.blindspotTags.map((tag) {
                      return Chip(
                        label: Text(tag.replaceAll('-', ' ')),
                        backgroundColor: BloomColors.surfaceBg,
                        labelStyle: BloomTypography.caption.copyWith(
                          color: BloomColors.inkSecondary,
                        ),
                        visualDensity: VisualDensity.compact,
                      );
                    }).toList(),
                  ),
                ],
              ],
            ),
          ),

          // Close button (top-right)
          Positioned(
            top: 8,
            right: 8,
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: onClose,
                borderRadius: BorderRadius.circular(20),
                child: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: BloomColors.surfaceBg,
                    border: Border.all(
                      color: BloomColors.inkTertiary,
                      width: 1,
                    ),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: const Icon(
                    Icons.close,
                    size: 20,
                    color: BloomColors.inkPrimary,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNoMetaCard(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: BloomColors.primaryBg,
        borderRadius: BloomSpacing.cardBorderRadius,
        border: Border.all(
          color: BloomColors.inkTertiary,
          width: BloomSpacing.borderWidth,
        ),
      ),
      padding: const EdgeInsets.all(BloomSpacing.screenPadding),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'No Perspective Data',
            style: BloomTypography.h3,
          ),
          const SizedBox(height: BloomSpacing.sm),
          Text(
            'Perspective analysis not yet available for this card.',
            style: BloomTypography.bodyMedium.copyWith(
              color: BloomColors.inkSecondary,
            ),
          ),
          const SizedBox(height: BloomSpacing.md),
          OutlinedButton.icon(
            onPressed: onClose,
            icon: const Icon(Icons.arrow_back),
            label: const Text('Back to card'),
          ),
        ],
      ),
    );
  }
}
