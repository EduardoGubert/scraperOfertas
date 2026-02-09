-- =============================================
-- PostgreSQL schema reference (legacy/manual)
-- Primary path now: Alembic migrations
--   alembic upgrade head
-- =============================================

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

CREATE UNIQUE INDEX IF NOT EXISTS uq_ml_ofertas_chave_dedupe ON ml_ofertas(chave_dedupe);
CREATE INDEX IF NOT EXISTS idx_ml_ofertas_mlb_id ON ml_ofertas(mlb_id);
CREATE INDEX IF NOT EXISTS idx_ml_ofertas_created_at ON ml_ofertas(created_at DESC);

CREATE TABLE IF NOT EXISTS ml_ofertas_relampago (
    LIKE ml_ofertas INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES
);
ALTER TABLE ml_ofertas_relampago ADD COLUMN IF NOT EXISTS tempo_para_acabar TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ml_ofertas_relampago_chave_dedupe ON ml_ofertas_relampago(chave_dedupe);
CREATE INDEX IF NOT EXISTS idx_ml_ofertas_relampago_mlb_id ON ml_ofertas_relampago(mlb_id);
CREATE INDEX IF NOT EXISTS idx_ml_ofertas_relampago_created_at ON ml_ofertas_relampago(created_at DESC);

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

CREATE UNIQUE INDEX IF NOT EXISTS uq_ml_cupons_chave_dedupe ON ml_cupons(chave_dedupe);
CREATE INDEX IF NOT EXISTS idx_ml_cupons_created_at ON ml_cupons(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ml_cupons_status ON ml_cupons(status);
