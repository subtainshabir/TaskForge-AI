"""update_notes_cascade_and_indexes

Revision ID: 0da979eee50b
Revises: 3a778672f513
Create Date: 2026-09-27 09:40:01.218033

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0da979eee50b'
down_revision = '3a778672f513'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing foreign keys with ondelete='SET NULL'
    op.drop_constraint('notes_project_id_fkey', 'notes', type_='foreignkey')
    op.drop_constraint('notes_task_id_fkey', 'notes', type_='foreignkey')

    # Re-create foreign keys with ondelete='CASCADE'
    op.create_foreign_key(
        'notes_project_id_fkey',
        'notes',
        'projects',
        ['project_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'notes_task_id_fkey',
        'notes',
        'tasks',
        ['task_id'],
        ['id'],
        ondelete='CASCADE',
    )

    # Add useful indexes for note queries and ordering
    op.create_index(op.f('ix_notes_created_at'), 'notes', ['created_at'], unique=False)
    op.create_index('ix_notes_user_created', 'notes', ['user_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_notes_user_created', table_name='notes')
    op.drop_index(op.f('ix_notes_created_at'), table_name='notes')

    op.drop_constraint('notes_task_id_fkey', 'notes', type_='foreignkey')
    op.drop_constraint('notes_project_id_fkey', 'notes', type_='foreignkey')

    op.create_foreign_key(
        'notes_task_id_fkey',
        'notes',
        'tasks',
        ['task_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'notes_project_id_fkey',
        'notes',
        'projects',
        ['project_id'],
        ['id'],
        ondelete='SET NULL',
    )
