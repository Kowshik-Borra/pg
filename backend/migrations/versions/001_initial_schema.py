"""Initial schema baseline with 26 tables

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-11

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Ensure all models are loaded in SQLAlchemy metadata
    from app.extensions import db
    import app.models
    bind = op.get_bind()
    db.metadata.create_all(bind=bind)

def downgrade():
    pass
