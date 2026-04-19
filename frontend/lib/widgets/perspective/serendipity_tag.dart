/// Serendipity Tag - "Why This Card?" explanation
library;

import 'package:flutter/material.dart';
import '../../models/bloom_card.dart';
import '../../theme/design_tokens.dart';

class SerendipityTag extends StatelessWidget {
  final PerspectiveMeta meta;

  const SerendipityTag({
    super.key,
    required this.meta,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(BloomSpacing.md),
      decoration: BoxDecoration(
        color: BloomColors.surfaceBg,
        borderRadius: BloomSpacing.cardBorderRadius,
        border: Border.all(
          color: BloomColors.inkTertiary,
          width: BloomSpacing.borderWidth,
        ),
      ),
      child: Row(
        children: [
          // Icon based on reason tag
          _getIconForReason(meta.reasonTag),
          const SizedBox(width: BloomSpacing.sm),

          // Reason text
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Why This Card?',
                  style: BloomTypography.caption,
                ),
                const SizedBox(height: 2),
                Text(
                  meta.reasonText,
                  style: BloomTypography.bodyMedium.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _getIconForReason(String reasonTag) {
    IconData iconData;
    Color iconColor;

    switch (reasonTag) {
      case 'BLINDSPOT_BREAKER':
        iconData = Icons.visibility_outlined;
        iconColor = BloomColors.growthGreen;
        break;
      case 'DEEP_DIVE':
        iconData = Icons.anchor_outlined;
        iconColor = BloomColors.growthGreen;
        break;
      case 'EXPLORE':
        iconData = Icons.explore_outlined;
        iconColor = BloomColors.bloomRed;
        break;
      case 'PERSPECTIVE_SHIFT':
        // Icons.360_outlined is invalid Dart (identifier can't start with
        // a digit). The Material icon is exposed as `threesixty_outlined`.
        iconData = Icons.threesixty_outlined;
        iconColor = BloomColors.inkPrimary;
        break;
      case 'SERENDIPITY':
        iconData = Icons.auto_awesome_outlined;
        iconColor = BloomColors.growthGreen;
        break;
      case 'RECENT':
      default:
        iconData = Icons.fiber_new_outlined;
        iconColor = BloomColors.inkSecondary;
    }

    return Container(
      padding: const EdgeInsets.all(BloomSpacing.sm),
      decoration: BoxDecoration(
        color: iconColor.withOpacity(0.1),
        shape: BoxShape.circle,
      ),
      child: Icon(
        iconData,
        size: 24,
        color: iconColor,
      ),
    );
  }
}
