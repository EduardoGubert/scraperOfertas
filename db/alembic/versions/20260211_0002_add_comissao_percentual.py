"""add comissao_percentual to offers tables

Revision ID: 20260211_0002
Revises: 20260209_0001
Create Date: 2026-02-11 09:55:00
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260211_0002"
down_revision = "20260209_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE ml_ofertas ADD COLUMN IF NOT EXISTS comissao_percentual INTEGER;")
    op.execute("ALTER TABLE ml_ofertas_relampago ADD COLUMN IF NOT EXISTS comissao_percentual INTEGER;")


def downgrade() -> None:
    op.execute("ALTER TABLE ml_ofertas_relampago DROP COLUMN IF EXISTS comissao_percentual;")
    op.execute("ALTER TABLE ml_ofertas DROP COLUMN IF EXISTS comissao_percentual;")
