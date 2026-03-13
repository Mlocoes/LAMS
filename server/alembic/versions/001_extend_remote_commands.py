"""Extend remote commands for Portainer features

Revision ID: 001_portainer
Revises: previous
Create Date: 2026-03-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_portainer'
down_revision = None  # Update this with your latest revision
branch_labels = None
depends_on = None


def upgrade():
    # Extend remote_commands table
    # Check if columns exist before adding them
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check remote_commands columns
    remote_cmd_columns = [c['name'] for c in inspector.get_columns('remote_commands')]
    
    if 'parameters' not in remote_cmd_columns:
        op.add_column('remote_commands', sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Convert result column from TEXT to JSONB if it's TEXT
    if 'result' in remote_cmd_columns:
        # Check current type
        result_col = [c for c in inspector.get_columns('remote_commands') if c['name'] == 'result'][0]
        if str(result_col['type']).lower() not in ['jsonb', 'json']:
            # Alter existing column type
            op.execute('ALTER TABLE remote_commands ALTER COLUMN result TYPE JSONB USING result::jsonb')
    else:
        op.add_column('remote_commands', sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    if 'duration_ms' not in remote_cmd_columns:
        op.add_column('remote_commands', sa.Column('duration_ms', sa.Integer(), nullable=True))
    if 'retry_count' not in remote_cmd_columns:
        op.add_column('remote_commands', sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False))
    if 'max_retries' not in remote_cmd_columns:
        op.add_column('remote_commands', sa.Column('max_retries', sa.Integer(), server_default='0', nullable=False))
    
    # Extend docker_containers table for detailed info
    docker_columns = [c['name'] for c in inspector.get_columns('docker_containers')]
    
    if 'ports' not in docker_columns:
        op.add_column('docker_containers', sa.Column('ports', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    if 'volumes' not in docker_columns:
        op.add_column('docker_containers', sa.Column('volumes', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    if 'networks' not in docker_columns:
        op.add_column('docker_containers', sa.Column('networks', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    if 'labels' not in docker_columns:
        op.add_column('docker_containers', sa.Column('labels', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    if 'restart_policy' not in docker_columns:
        op.add_column('docker_containers', sa.Column('restart_policy', sa.String(64), nullable=True))
    if 'exit_code' not in docker_columns:
        op.add_column('docker_containers', sa.Column('exit_code', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('docker_containers', 'exit_code')
    op.drop_column('docker_containers', 'restart_policy')
    op.drop_column('docker_containers', 'labels')
    op.drop_column('docker_containers', 'networks')
    op.drop_column('docker_containers', 'volumes')
    op.drop_column('docker_containers', 'ports')
    
    op.drop_column('remote_commands', 'max_retries')
    op.drop_column('remote_commands', 'retry_count')
    op.drop_column('remote_commands', 'duration_ms')
    op.drop_column('remote_commands', 'result')
    op.drop_column('remote_commands', 'parameters')
