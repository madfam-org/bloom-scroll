"""Add score_provenance to bloom_cards and null out unmeasured scores

Perspective scores (bias_score, constructiveness_score, blindspot_tags) were
being presented to users even when no analysis pipeline produced them — the
2026-04-20 production seed rows carried hand-written values (defect D5,
2026-07-16 audit). This migration adds a provenance marker; the API only
emits scores when provenance is set, and this migration clears legacy scores
that have no provenance so fabricated values cannot resurface.

Revision ID: 003
Revises: 002
Create Date: 2026-07-16 01:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import context, op

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: str | None = '002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add score_provenance column and clear unmeasured legacy scores."""
    # Existence guard: adopted pre-alembic databases replay this migration
    # (see app/core/migrations.py) and may already carry the column when it
    # was added out-of-band. Offline mode (--sql) emits the full DDL.
    column_exists = False
    if not context.is_offline_mode():
        columns = sa.inspect(op.get_bind()).get_columns('bloom_cards')
        column_exists = any(c['name'] == 'score_provenance' for c in columns)

    if not column_exists:
        op.add_column(
            'bloom_cards',
            sa.Column(
                'score_provenance',
                sa.String(100),
                nullable=True,
                comment=(
                    'Which pipeline produced bias/constructiveness/blindspot '
                    'values, e.g. selva/<model>@<version>. NULL means the scores '
                    'were not machine-measured and must not be presented to users.'
                ),
            ),
        )

    # Every pre-existing score predates any scoring pipeline, so none of them
    # were measured: clear them rather than grandfathering fabricated values.
    op.execute(
        "UPDATE bloom_cards "
        "SET bias_score = NULL, constructiveness_score = NULL, blindspot_tags = NULL "
        "WHERE score_provenance IS NULL"
    )


def downgrade() -> None:
    """Drop score_provenance column (cleared legacy scores are not restored)."""
    op.drop_column('bloom_cards', 'score_provenance')
