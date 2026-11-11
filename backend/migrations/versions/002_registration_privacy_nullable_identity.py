"""Make tenant id proof fields nullable for registration privacy

Revision ID: 002_privacy_nullable_identity
Revises: 001_initial_schema
Create Date: 2026-11-11

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_privacy_nullable_identity'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None

def upgrade():
    # Alter tenants table to allow nulls for deprecated identity proof fields
    with op.batch_alter_table('tenants', schema=None) as batch_op:
        batch_op.alter_column('id_proof_type',
                              existing_type=sa.String(length=50),
                              nullable=True)
        batch_op.alter_column('id_proof_number_masked',
                              existing_type=sa.String(length=50),
                              nullable=True)

def downgrade():
    with op.batch_alter_table('tenants', schema=None) as batch_op:
        batch_op.alter_column('id_proof_type',
                              existing_type=sa.String(length=50),
                              nullable=False)
        batch_op.alter_column('id_proof_number_masked',
                              existing_type=sa.String(length=50),
                              nullable=False)

