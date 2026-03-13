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
    op.add_column('remote_commands', sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('remote_commands', sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('remote_commands', sa.Column('duration_ms', sa.Integer(), nullable=True))
    op.add_column('remote_commands', sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('remote_commands', sa.Column('max_retries', sa.Integer(), server_default='0', nullable=False))
    
    # Extend docker_containers table for detailed info
    op.add_column('docker_containers', sa.Column('ports', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('docker_containers', sa.Column('volumes', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('docker_containers', sa.Column('networks', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('docker_containers', sa.Column('labels', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('docker_containers', sa.Column('restart_policy', sa.String(64), nullable=True))
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
