"""add_task_activities_table

Revision ID: 724642fd2a1b
Revises: 8911fd2dd5f2
Create Date: 2026-09-23 23:36:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '724642fd2a1b'
down_revision = '8911fd2dd5f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'task_activities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('activity_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_task_activities_task_id', 'task_activities', ['task_id'], unique=False)
    op.create_index('ix_task_activities_user_id', 'task_activities', ['user_id'], unique=False)
    op.create_index('ix_task_activities_activity_type', 'task_activities', ['activity_type'], unique=False)
    op.create_index('ix_task_activities_created_at', 'task_activities', ['created_at'], unique=False)
    op.create_index('ix_task_activities_task_created', 'task_activities', ['task_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_task_activities_task_created', table_name='task_activities')
    op.drop_index('ix_task_activities_created_at', table_name='task_activities')
    op.drop_index('ix_task_activities_activity_type', table_name='task_activities')
    op.drop_index('ix_task_activities_user_id', table_name='task_activities')
    op.drop_index('ix_task_activities_task_id', table_name='task_activities')
    op.drop_table('task_activities')
