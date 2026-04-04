"""Full schema: missing user columns, availability, booking, order tables

Revision ID: a1b2c3d4e5f6
Revises: 8ec4d0d099ac
Create Date: 2025-06-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '8ec4d0d099ac'
branch_labels = None
depends_on = None


def upgrade():
    # ── Add missing columns to user table ──────────────────────────────────
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('role', sa.String(length=20), nullable=False, server_default='client'))
        batch_op.add_column(sa.Column('session_credits', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('mentoring_credits', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('verification_token', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('reset_token', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('reset_token_expiry', sa.DateTime(), nullable=True))

    # ── Create availability table (may already exist on some instances) ────
    conn = op.get_bind()
    existing_tables = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table'")
    ).scalars().all()

    if 'availability' not in existing_tables:
        op.create_table(
            'availability',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('interviewer_id', sa.Integer(), nullable=False),
            sa.Column('date', sa.Date(), nullable=False),
            sa.Column('start_time', sa.String(length=5), nullable=False),
            sa.Column('end_time', sa.String(length=5), nullable=False),
            sa.Column('is_booked', sa.Boolean(), nullable=True),
            sa.ForeignKeyConstraint(['interviewer_id'], ['user.id']),
            sa.PrimaryKeyConstraint('id'),
        )

    if 'booking' not in existing_tables:
        op.create_table(
            'booking',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('client_id', sa.Integer(), nullable=False),
            sa.Column('interviewer_id', sa.Integer(), nullable=False),
            sa.Column('availability_id', sa.Integer(), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=True),
            sa.Column('session_type', sa.String(length=50), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['availability_id'], ['availability.id']),
            sa.ForeignKeyConstraint(['client_id'], ['user.id']),
            sa.ForeignKeyConstraint(['interviewer_id'], ['user.id']),
            sa.PrimaryKeyConstraint('id'),
        )

    # ── Create order table ──────────────────────────────────────────────────
    op.create_table(
        'order',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('stripe_session_id', sa.String(length=200), nullable=False),
        sa.Column('plan', sa.String(length=50), nullable=False),
        sa.Column('session_credits_granted', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('mentoring_credits_granted', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stripe_session_id'),
    )


def downgrade():
    op.drop_table('order')
    op.drop_table('booking')
    op.drop_table('availability')
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('reset_token_expiry')
        batch_op.drop_column('reset_token')
        batch_op.drop_column('verification_token')
        batch_op.drop_column('is_verified')
        batch_op.drop_column('created_at')
        batch_op.drop_column('mentoring_credits')
        batch_op.drop_column('session_credits')
        batch_op.drop_column('role')
