"""Add pgvector index and user_interactions table

Revision ID: 002
Revises: 001
Create Date: 2025-11-19 02:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: str | None = '001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Add HNSW index for vector similarity search and create user_interactions table.

    HNSW (Hierarchical Navigable Small Worlds) is an efficient algorithm for
    approximate nearest neighbor search in high-dimensional spaces.
    """

    # Create HNSW index on embedding column for fast vector similarity search
    # Using cosine distance as the metric (1 - cosine_similarity)
    # m=16: number of connections per layer (higher = more accurate, slower build)
    # ef_construction=64: size of dynamic candidate list (higher = more accurate, slower build)
    op.execute("""
        CREATE INDEX ix_bloom_cards_embedding_hnsw
        ON bloom_cards
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """)

    # Create user_interactions table for tracking user engagement
    op.create_table(
        'user_interactions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False, comment='User identifier (can be session ID)'),
        sa.Column('card_id', UUID(as_uuid=True), nullable=False, comment='BloomCard ID'),
        sa.Column('action', sa.String(50), nullable=False, comment='view, read, skip, save'),
        sa.Column('dwell_time', sa.Integer(), nullable=True, comment='Time spent on card in seconds'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
    )

    # Create indexes for efficient user interaction queries
    op.create_index('ix_user_interactions_user_id', 'user_interactions', ['user_id'])
    op.create_index('ix_user_interactions_card_id', 'user_interactions', ['card_id'])
    op.create_index('ix_user_interactions_created_at', 'user_interactions', ['created_at'])

    # Composite index for user context queries (recent interactions by user)
    op.create_index(
        'ix_user_interactions_user_created',
        'user_interactions',
        ['user_id', 'created_at']
    )


def downgrade() -> None:
    """Drop user_interactions table and pgvector index."""

    # Drop user_interactions table and its indexes
    op.drop_index('ix_user_interactions_user_created', table_name='user_interactions')
    op.drop_index('ix_user_interactions_created_at', table_name='user_interactions')
    op.drop_index('ix_user_interactions_card_id', table_name='user_interactions')
    op.drop_index('ix_user_interactions_user_id', table_name='user_interactions')
    op.drop_table('user_interactions')

    # Drop HNSW index
    op.drop_index('ix_bloom_cards_embedding_hnsw', table_name='bloom_cards')
