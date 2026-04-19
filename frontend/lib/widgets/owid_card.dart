/// OWID Card Widget - Renders interactive charts from Our World in Data
library;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import '../models/bloom_card.dart';
import '../theme/design_tokens.dart';
import 'perspective/flippable_card.dart';

class OwidCard extends StatefulWidget {
  final BloomCard card;

  const OwidCard({
    super.key,
    required this.card,
  });

  @override
  State<OwidCard> createState() => _OwidCardState();
}

class _OwidCardState extends State<OwidCard> {
  int? _touchedIndex;

  @override
  Widget build(BuildContext context) {
    final owidData = widget.card.owidData;
    if (owidData == null) {
      return _buildErrorCard('Invalid OWID data');
    }

    final dataPoints = owidData.dataPoints;
    if (dataPoints.isEmpty) {
      return _buildErrorCard('No data available');
    }

    return FlippableCard(
      card: widget.card,
      front: Card(
        margin: const EdgeInsets.all(BloomSpacing.xs),
        child: Padding(
          padding: const EdgeInsets.all(BloomSpacing.screenPadding),
          child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Title (Libre Baskerville headings)
            Text(
              widget.card.title,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: BloomSpacing.xs),

            // Source badge
            Chip(
              label: const Text('OWID'),
              backgroundColor: BloomColors.surfaceBg,
              labelStyle: BloomTypography.caption.copyWith(
                color: BloomColors.growthGreen,
              ),
              visualDensity: VisualDensity.compact,
            ),

            const SizedBox(height: BloomSpacing.screenPadding),

            // Chart
            SizedBox(
              height: 200,
              child: _buildChart(dataPoints, owidData),
            ),

            const SizedBox(height: BloomSpacing.md),

            // Summary info (Inter body text)
            if (widget.card.summary != null)
              Text(
                widget.card.summary!,
                style: BloomTypography.bodyMedium.copyWith(
                  color: BloomColors.inkSecondary,
                ),
              ),
          ],
        ),
      ),
    ),
    );
  }

  Widget _buildChart(List<ChartPoint> dataPoints, OwidChartData owidData) {
    return LineChart(
      LineChartData(
        // Grid and borders - "Paper & Ink" design (no grids, no borders)
        gridData: FlGridData(show: BloomChartConfig.showGrid),
        borderData: FlBorderData(show: BloomChartConfig.showBorder),

        // Titles - Minimal axis labels (Tufte style + Paper & Ink)
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 50,
              getTitlesWidget: (value, meta) {
                return Text(
                  _formatValue(value, owidData.unit),
                  style: BloomTypography.dataSmall.copyWith(
                    color: BloomColors.inkTertiary,
                  ),
                );
              },
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 30,
              interval: _calculateInterval(owidData.years),
              getTitlesWidget: (value, meta) {
                return Padding(
                  padding: const EdgeInsets.only(top: BloomSpacing.sm),
                  child: Text(
                    value.toInt().toString(),
                    style: BloomTypography.dataSmall.copyWith(
                      color: BloomColors.inkTertiary,
                    ),
                  ),
                );
              },
            ),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
        ),

        // The actual line - Drawn in "Ink" color per design tokens
        lineBarsData: [
          LineChartBarData(
            spots: dataPoints
                .map((point) => FlSpot(point.x, point.y))
                .toList(),
            isCurved: true,
            curveSmoothness: 0.3,
            color: BloomChartConfig.lineColor,
            barWidth: BloomChartConfig.lineWidth,
            isStrokeCapRound: true,
            dotData: FlDotData(
              show: true,
              getDotPainter: (spot, percent, barData, index) {
                return FlDotCirclePainter(
                  radius: index == _touchedIndex
                      ? BloomChartConfig.touchSpotRadius
                      : 3,
                  color: BloomColors.primaryBg,
                  strokeWidth: 2,
                  strokeColor: BloomChartConfig.lineColor,
                );
              },
            ),
            belowBarData: BarAreaData(
              show: true,
              color: BloomChartConfig.fillColor, // Growth green with 10% opacity
            ),
          ),
        ],

        // Touch interaction
        lineTouchData: LineTouchData(
          enabled: true,
          touchCallback: (FlTouchEvent event, LineTouchResponse? touchResponse) {
            if (touchResponse == null || touchResponse.lineBarSpots == null) {
              setState(() {
                _touchedIndex = null;
              });
              return;
            }

            setState(() {
              _touchedIndex = touchResponse.lineBarSpots!.first.spotIndex;
            });
          },
          getTouchedSpotIndicator: (LineChartBarData barData, List<int> spotIndexes) {
            return spotIndexes.map((index) {
              return TouchedSpotIndicatorData(
                FlLine(
                  color: BloomChartConfig.touchColor, // bloom_red
                  strokeWidth: 2,
                  dashArray: [5, 5],
                ),
                FlDotData(
                  getDotPainter: (spot, percent, barData, index) {
                    return FlDotCirclePainter(
                      radius: BloomChartConfig.touchSpotRadius,
                      color: BloomColors.primaryBg,
                      strokeWidth: 3,
                      strokeColor: BloomChartConfig.touchColor,
                    );
                  },
                ),
              );
            }).toList();
          },
          touchTooltipData: LineTouchTooltipData(
            // fl_chart ^0.65.0 (pinned in pubspec.yaml) uses tooltipBgColor;
            // getTooltipColor was introduced in 0.66.0.
            tooltipBgColor: BloomChartConfig.touchColor,
            tooltipRoundedRadius: BloomSpacing.cardRadius,
            tooltipPadding: const EdgeInsets.symmetric(
              horizontal: BloomSpacing.sm,
              vertical: BloomSpacing.xs,
            ),
            getTooltipItems: (List<LineBarSpot> touchedSpots) {
              return touchedSpots.map((LineBarSpot touchedSpot) {
                final year = touchedSpot.x.toInt();
                final value = touchedSpot.y;
                return LineTooltipItem(
                  '$year\n${_formatValue(value, owidData.unit)}',
                  BloomTypography.dataMedium.copyWith(
                    color: BloomColors.primaryBg,
                  ),
                );
              }).toList();
            },
          ),
        ),
      ),
    );
  }

  Widget _buildErrorCard(String message) {
    return Card(
      margin: const EdgeInsets.all(BloomSpacing.xs),
      child: Padding(
        padding: const EdgeInsets.all(BloomSpacing.screenPadding),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              widget.card.title,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: BloomSpacing.sm),
            Text(
              message,
              style: BloomTypography.bodyMedium.copyWith(
                color: BloomColors.bloomRed,
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _formatValue(double value, String unit) {
    if (value >= 1e9) {
      return '${(value / 1e9).toStringAsFixed(1)}B $unit';
    } else if (value >= 1e6) {
      return '${(value / 1e6).toStringAsFixed(1)}M $unit';
    } else if (value >= 1e3) {
      return '${(value / 1e3).toStringAsFixed(1)}K $unit';
    } else {
      return '${value.toStringAsFixed(1)} $unit';
    }
  }

  double _calculateInterval(List<int> years) {
    if (years.length <= 5) return 1;
    if (years.length <= 10) return 2;
    if (years.length <= 20) return 5;
    return 10;
  }
}
