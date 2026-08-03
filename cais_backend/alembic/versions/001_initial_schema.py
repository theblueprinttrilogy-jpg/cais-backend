"""Initial schema with agents, executions, tasks, and files.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure UUID extension is available (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    # Create agents table
    op.create_table(
        'agents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_active', sa.Integer, nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_agents_name', 'agents', ['name'])

    # Create agent_executions table
    op.create_table(
        'agent_executions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column('agent_id', UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('priority', sa.Integer, nullable=False, server_default='0'),
        sa.Column('input_data', JSON, nullable=True),
        sa.Column('result', JSON, nullable=True),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_foreign_key('fk_agent_executions_agent_id', 'agent_executions', 'agents', ['agent_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_agent_executions_agent_id', 'agent_executions', ['agent_id'])
    op.create_index('ix_agent_executions_status', 'agent_executions', ['status'])
    op.create_index('ix_agent_executions_agent_id_status', 'agent_executions', ['agent_id', 'status'])

    # Create agent_tasks table
    op.create_table(
        'agent_tasks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column('agent_id', UUID(as_uuid=True), nullable=False),
        sa.Column('agent_name', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('priority', sa.Integer, nullable=False, server_default='0'),
        sa.Column('input_data', JSON, nullable=True),
        sa.Column('result', JSON, nullable=True),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_foreign_key('fk_agent_tasks_agent_id', 'agent_tasks', 'agents', ['agent_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_agent_tasks_agent_id', 'agent_tasks', ['agent_id'])
    op.create_index('ix_agent_tasks_agent_name', 'agent_tasks', ['agent_name'])
    op.create_index('ix_agent_tasks_status', 'agent_tasks', ['status'])
    op.create_index('ix_agent_tasks_agent_name_status', 'agent_tasks', ['agent_name', 'status'])

    # Create files table
    op.create_table(
        'files',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('drive_file_id', sa.String(255), nullable=True),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('is_deleted', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime, nullable=True),
        sa.Column('permanently_deleted_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_files_drive_file_id', 'files', ['drive_file_id'])


def downgrade() -> None:
    # Drop tables in reverse order to respect foreign key constraints
    op.drop_table('files')
    op.drop_table('agent_tasks')
    op.drop_table('agent_executions')
    op.drop_table('agents')
    # Optionally drop the extension (commented out to avoid issues if shared)
    # op.execute("DROP EXTENSION IF EXISTS \"uuid-ossp\"")
