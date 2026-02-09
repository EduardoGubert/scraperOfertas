"""core schema for ofertas, ofertas_relampago and cupons

Revision ID: 20260209_0001
Revises:
Create Date: 2026-02-09 00:00:01
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260209_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ml_ofertas (
            id SERIAL PRIMARY KEY,
            mlb_id VARCHAR(50),
            chave_dedupe VARCHAR(255) NOT NULL,
            url_original TEXT NOT NULL,
            url_curta TEXT,
            url_afiliado TEXT,
            product_id VARCHAR(100),
            nome TEXT,
            foto_url TEXT,
            preco_atual DECIMAL(12,2),
            preco_original DECIMAL(12,2),
            desconto INTEGER,
            status VARCHAR(20) DEFAULT 'ativo',
            enviado_whatsapp BOOLEAN DEFAULT false,
            enviado_whatsapp_at TIMESTAMPTZ,
            sent_to_whatsapp BOOLEAN DEFAULT false,
            sent_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT timezone('America/Sao_Paulo', now()),
            updated_at TIMESTAMPTZ DEFAULT timezone('America/Sao_Paulo', now())
        );
        """
    )

    op.execute("ALTER TABLE ml_ofertas ADD COLUMN IF NOT EXISTS enviado_whatsapp BOOLEAN DEFAULT false;")
    op.execute("ALTER TABLE ml_ofertas ADD COLUMN IF NOT EXISTS enviado_whatsapp_at TIMESTAMPTZ;")
    op.execute("ALTER TABLE ml_ofertas ADD COLUMN IF NOT EXISTS sent_to_whatsapp BOOLEAN DEFAULT false;")
    op.execute("ALTER TABLE ml_ofertas ADD COLUMN IF NOT EXISTS sent_at TIMESTAMPTZ;")
    op.execute(
        """
        ALTER TABLE ml_ofertas
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT timezone('America/Sao_Paulo', now());
        """
    )
    op.execute(
        """
        ALTER TABLE ml_ofertas
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT timezone('America/Sao_Paulo', now());
        """
    )

    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_ml_ofertas_chave_dedupe ON ml_ofertas(chave_dedupe);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ml_ofertas_mlb_id ON ml_ofertas(mlb_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ml_ofertas_created_at ON ml_ofertas(created_at DESC);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ml_ofertas_relampago (
            LIKE ml_ofertas INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES
        );
        """
    )
    op.execute("ALTER TABLE ml_ofertas_relampago ADD COLUMN IF NOT EXISTS tempo_para_acabar TEXT;")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_ml_ofertas_relampago_chave_dedupe
        ON ml_ofertas_relampago(chave_dedupe);
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_ml_ofertas_relampago_mlb_id ON ml_ofertas_relampago(mlb_id);")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ml_ofertas_relampago_created_at
        ON ml_ofertas_relampago(created_at DESC);
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ml_cupons (
            id SERIAL PRIMARY KEY,
            nome TEXT,
            desconto_texto TEXT,
            desconto_percentual INTEGER,
            desconto_valor DECIMAL(12,2),
            limite_condicoes TEXT,
            imagem_url TEXT,
            url_origem TEXT NOT NULL,
            status VARCHAR(20) DEFAULT 'ativo',
            sent_to_whatsapp BOOLEAN DEFAULT false,
            sent_at TIMESTAMPTZ,
            chave_dedupe VARCHAR(255) NOT NULL,
            raw_payload JSONB,
            created_at TIMESTAMPTZ DEFAULT timezone('America/Sao_Paulo', now()),
            updated_at TIMESTAMPTZ DEFAULT timezone('America/Sao_Paulo', now())
        );
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_ml_cupons_chave_dedupe ON ml_cupons(chave_dedupe);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ml_cupons_created_at ON ml_cupons(created_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ml_cupons_status ON ml_cupons(status);")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
        BEGIN
            NEW.updated_at = timezone('America/Sao_Paulo', now());
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_ml_ofertas_updated_at') THEN
                CREATE TRIGGER trg_ml_ofertas_updated_at
                BEFORE UPDATE ON ml_ofertas
                FOR EACH ROW
                EXECUTE FUNCTION set_updated_at();
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_ml_ofertas_relampago_updated_at') THEN
                CREATE TRIGGER trg_ml_ofertas_relampago_updated_at
                BEFORE UPDATE ON ml_ofertas_relampago
                FOR EACH ROW
                EXECUTE FUNCTION set_updated_at();
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_ml_cupons_updated_at') THEN
                CREATE TRIGGER trg_ml_cupons_updated_at
                BEFORE UPDATE ON ml_cupons
                FOR EACH ROW
                EXECUTE FUNCTION set_updated_at();
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ml_cupons;")
    op.execute("DROP TABLE IF EXISTS ml_ofertas_relampago;")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")
