"""Add store settings, gnani usage tracking, and product aliases and reorder level.

Revision ID: a3f129c58b04
Revises: e2d3530619fb
Create Date: 2026-11-10 15:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f129c58b04'
down_revision: Union[str, None] = 'e2d3530619fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # 1. Idempotently add missing columns to 'products' table
    if 'products' in existing_tables:
        product_cols = [c['name'] for c in inspector.get_columns('products')]
        if 'reorder_level' not in product_cols:
            op.add_column('products', sa.Column('reorder_level', sa.Float(), nullable=True, server_default='15.0'))
        if 'aliases' not in product_cols:
            op.add_column('products', sa.Column('aliases', sa.Text(), nullable=True))

    # 2. Idempotently add missing columns to 'sales' table
    if 'sales' in existing_tables:
        sale_cols = [c['name'] for c in inspector.get_columns('sales')]
        if 'payment_status' not in sale_cols:
            op.add_column('sales', sa.Column('payment_status', sa.String(length=30), nullable=True, server_default='PAID'))

    # 3. Create 'store_settings' table if not already present
    if 'store_settings' not in existing_tables:
        op.create_table(
            'store_settings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('shop_name', sa.String(length=150), nullable=False, server_default='TamilVoice Kirana Store'),
            sa.Column('shop_name_ta', sa.String(length=150), nullable=True),
            sa.Column('owner_name', sa.String(length=100), nullable=False, server_default='Kirana Proprietor'),
            sa.Column('phone', sa.String(length=30), nullable=False, server_default='+91 98765 43210'),
            sa.Column('whatsapp_number', sa.String(length=30), nullable=True),
            sa.Column('address', sa.Text(), nullable=True),
            sa.Column('email', sa.String(length=100), nullable=True),
            sa.Column('gstin', sa.String(length=30), nullable=True),
            sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
            sa.Column('currency_symbol', sa.String(length=10), nullable=False, server_default='₹'),
            sa.Column('preferred_language', sa.String(length=10), nullable=False, server_default='ta'),
            sa.Column('voice_preferred_language', sa.String(length=20), nullable=False, server_default='ta'),
            sa.Column('speech_speed', sa.Float(), nullable=False, server_default='1.0'),
            sa.Column('auto_speak_responses', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('low_stock_threshold_default', sa.Float(), nullable=False, server_default='5.0'),
            sa.Column('receipt_footer', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_store_settings_id'), 'store_settings', ['id'], unique=False)

    # 4. Create 'gnani_api_usage' table if not already present
    if 'gnani_api_usage' not in existing_tables:
        op.create_table(
            'gnani_api_usage',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('provider', sa.String(length=50), nullable=False, server_default='gnani'),
            sa.Column('service', sa.String(length=20), nullable=False),
            sa.Column('timestamp', sa.DateTime(), nullable=False),
            sa.Column('status_code', sa.Integer(), nullable=False, server_default='200'),
            sa.Column('success', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('duration_ms', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('input_size', sa.String(length=100), nullable=True),
            sa.Column('provider_reported_credits', sa.Float(), nullable=True),
            sa.Column('estimated_credits', sa.Float(), nullable=False, server_default='1.0'),
            sa.Column('error_category', sa.String(length=50), nullable=True),
            sa.Column('error_detail', sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_gnani_api_usage_id'), 'gnani_api_usage', ['id'], unique=False)
        op.create_index(op.f('ix_gnani_api_usage_timestamp'), 'gnani_api_usage', ['timestamp'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'gnani_api_usage' in existing_tables:
        op.drop_index(op.f('ix_gnani_api_usage_timestamp'), table_name='gnani_api_usage')
        op.drop_index(op.f('ix_gnani_api_usage_id'), table_name='gnani_api_usage')
        op.drop_table('gnani_api_usage')

    if 'store_settings' in existing_tables:
        op.drop_index(op.f('ix_store_settings_id'), table_name='store_settings')
        op.drop_table('store_settings')

    if 'sales' in existing_tables:
        sale_cols = [c['name'] for c in inspector.get_columns('sales')]
        if 'payment_status' in sale_cols:
            op.drop_column('sales', 'payment_status')

    if 'products' in existing_tables:
        product_cols = [c['name'] for c in inspector.get_columns('products')]
        if 'aliases' in product_cols:
            op.drop_column('products', 'aliases')
        if 'reorder_level' in product_cols:
            op.drop_column('products', 'reorder_level')
