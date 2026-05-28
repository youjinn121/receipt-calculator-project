"""initial schema

Revision ID: fd080f64c708
Revises: 
Create Date: 2026-04-09 10:58:36.890968

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'fd080f64c708'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('receipts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('file_name', sa.String(), nullable=False),
    sa.Column('store', sa.String(), nullable=True),
    sa.Column('item_total', sa.Integer(), nullable=True),
    sa.Column('payment_total', sa.Integer(), nullable=True),
    sa.Column('receipt_discount_total', sa.Integer(), nullable=True),
    sa.Column('fee_total', sa.Integer(), nullable=True),
    sa.Column('is_valid', sa.Boolean(), nullable=False),
    sa.Column('is_total_inferred', sa.Boolean(), nullable=False),
    sa.Column('requires_user_total_confirmation', sa.Boolean(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_receipts_id'), 'receipts', ['id'], unique=False)

    op.create_table('receipt_analysis',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('receipt_id', sa.Integer(), nullable=False),
    sa.Column('guilty_pleasure_index', sa.Float(), nullable=True),
    sa.Column('home_cooking_ratio', sa.Float(), nullable=True),
    sa.Column('impulse_buy_factor', sa.Float(), nullable=True),
    sa.Column('basket_variety_score', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['receipt_id'], ['receipts.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('receipt_id')
    )
    op.create_index(op.f('ix_receipt_analysis_id'), 'receipt_analysis', ['id'], unique=False)

    op.create_table('receipt_images',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('receipt_id', sa.Integer(), nullable=False),
    sa.Column('page_no', sa.Integer(), nullable=False),
    sa.Column('file_path', sa.String(), nullable=False),
    sa.Column('ocr_json_path', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['receipt_id'], ['receipts.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_receipt_images_id'), 'receipt_images', ['id'], unique=False)

    op.create_table('receipt_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('receipt_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('normalized_name', sa.String(), nullable=True),
    sa.Column('category', sa.String(), nullable=True),
    sa.Column('category_source', sa.String(), nullable=True),
    sa.Column('code', sa.String(), nullable=True),
    sa.Column('qty', sa.Integer(), nullable=True),
    sa.Column('unit_price', sa.Integer(), nullable=True),
    sa.Column('base_price', sa.Integer(), nullable=True),
    sa.Column('discount', sa.Integer(), nullable=True),
    sa.Column('final_price', sa.Integer(), nullable=True),
    sa.Column('source_line_indices', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['receipt_id'], ['receipts.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_receipt_items_id'), 'receipt_items', ['id'], unique=False)

    op.create_table('receipt_item_categories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('receipt_item_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('category', sa.String(), nullable=False),
    sa.Column('category_source', sa.String(), nullable=True),
    sa.Column('raw_response', sa.Text(), nullable=True),
    sa.Column('use_fallback', sa.Boolean(), nullable=True),
    sa.Column('use_llm', sa.Boolean(), nullable=True),
    sa.Column('use_cache', sa.Boolean(), nullable=True),
    sa.Column('cache_hit', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['receipt_item_id'], ['receipt_items.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_receipt_item_categories_id'), 'receipt_item_categories', ['id'], unique=False)

    op.create_table('receipt_lines',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('receipt_id', sa.Integer(), nullable=False),
    sa.Column('line_idx', sa.Integer(), nullable=False),
    sa.Column('line_text', sa.Text(), nullable=False),
    sa.Column('normalized_line_text', sa.Text(), nullable=True),
    sa.Column('line_type', sa.String(), nullable=True),
    sa.Column('price_raw', sa.Integer(), nullable=True),
    sa.Column('name_raw', sa.String(), nullable=True),
    sa.Column('is_restored', sa.Boolean(), nullable=True),
    sa.Column('restore_reason', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['receipt_id'], ['receipts.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_receipt_lines_id'), 'receipt_lines', ['id'], unique=False)

    op.create_table('receipt_validation',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('receipt_id', sa.Integer(), nullable=False),
    sa.Column('checked_item_count', sa.Integer(), nullable=True),
    sa.Column('valid_item_count', sa.Integer(), nullable=True),
    sa.Column('invalid_item_count', sa.Integer(), nullable=True),
    sa.Column('total_match', sa.Boolean(), nullable=True),
    sa.Column('subtotal_segment_match', sa.Boolean(), nullable=True),
    sa.Column('categorization_rate', sa.Float(), nullable=True),
    sa.Column('error_count', sa.Integer(), nullable=True),
    sa.Column('warning_count', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['receipt_id'], ['receipts.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('receipt_id')
    )
    op.create_index(op.f('ix_receipt_validation_id'), 'receipt_validation', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_receipt_validation_id'), table_name='receipt_validation')
    op.drop_table('receipt_validation')

    op.drop_index(op.f('ix_receipt_lines_id'), table_name='receipt_lines')
    op.drop_table('receipt_lines')

    op.drop_index(op.f('ix_receipt_item_categories_id'), table_name='receipt_item_categories')
    op.drop_table('receipt_item_categories')

    op.drop_index(op.f('ix_receipt_items_id'), table_name='receipt_items')
    op.drop_table('receipt_items')

    op.drop_index(op.f('ix_receipt_images_id'), table_name='receipt_images')
    op.drop_table('receipt_images')

    op.drop_index(op.f('ix_receipt_analysis_id'), table_name='receipt_analysis')
    op.drop_table('receipt_analysis')

    op.drop_index(op.f('ix_receipts_id'), table_name='receipts')
    op.drop_table('receipts')