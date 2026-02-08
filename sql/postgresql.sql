-- =============================================
-- SCHEMA POSTGRESQL - ML OFERTAS
-- =============================================

-- Criar database (execute como superuser)
-- CREATE DATABASE ml_ofertas_db OWNER ml_user;

-- Criar usuário (execute como superuser)
-- CREATE USER ml_user WITH PASSWORD 'sua_senha_super_segura';
-- GRANT ALL PRIVILEGES ON DATABASE ml_ofertas_db TO ml_user;

-- =============================================
-- TABELA PRINCIPAL
-- =============================================

CREATE TABLE IF NOT EXISTS ml_ofertas (
    -- Identificadores
    id SERIAL PRIMARY KEY,
    mlb_id VARCHAR(50) UNIQUE,                    -- MLB1234567890 (quando disponível)
    chave_dedupe VARCHAR(255) NOT NULL UNIQUE,    -- Chave de deduplicação robusta
    
    -- URLs e Links
    url_original TEXT NOT NULL,                   -- URL original do produto
    url_curta TEXT,                              -- Link encurtado do ML (/sec/xxxx)
    url_afiliado TEXT,                           -- Link completo de afiliado
    product_id VARCHAR(100),                     -- ID do produto para compartilhamento
    
    -- Dados do Produto  
    nome TEXT,                                   -- Nome/título do produto
    foto_url TEXT,                               -- URL da imagem principal
    
    -- Preços (DECIMAL para precisão monetária)
    preco_atual DECIMAL(10,2),                   -- Preço atual com desconto
    preco_original DECIMAL(10,2),                -- Preço original (antes desconto)
    desconto INTEGER,                            -- Percentual de desconto (0-100)
    
    -- Metadados
    status VARCHAR(20) DEFAULT 'ativo',          -- ativo, inativo, erro
    created_at TIMESTAMP DEFAULT NOW(),          -- Data de criação
    updated_at TIMESTAMP DEFAULT NOW()           -- Data de última atualização
);

-- =============================================
-- ÍNDICES PARA PERFORMANCE
-- =============================================

-- Busca por MLB ID (comum)
CREATE INDEX IF NOT EXISTS idx_ml_ofertas_mlb_id 
ON ml_ofertas(mlb_id) 
WHERE mlb_id IS NOT NULL;

-- Busca por chave de deduplicação (crítico)
CREATE INDEX IF NOT EXISTS idx_ml_ofertas_chave_dedupe 
ON ml_ofertas(chave_dedupe);

-- Ordenação por data (relatórios)
CREATE INDEX IF NOT EXISTS idx_ml_ofertas_created_at 
ON ml_ofertas(created_at DESC);

-- Busca por status (filtragem)
CREATE INDEX IF NOT EXISTS idx_ml_ofertas_status 
ON ml_ofertas(status);

-- Produtos com link de afiliado (analytics)
CREATE INDEX IF NOT EXISTS idx_ml_ofertas_com_link 
ON ml_ofertas(url_curta) 
WHERE url_curta IS NOT NULL;

-- =============================================
-- TRIGGERS (OPCIONAL - AUTO UPDATE timestamp)
-- =============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_ml_ofertas_updated_at 
    BEFORE UPDATE ON ml_ofertas 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================
-- VIEWS ÚTEIS (OPCIONAL)
-- =============================================

-- View de produtos com link de afiliado
CREATE OR REPLACE VIEW vw_produtos_afiliados AS
SELECT 
    id, mlb_id, nome, preco_atual, desconto,
    url_curta, created_at
FROM ml_ofertas 
WHERE url_curta IS NOT NULL 
  AND status = 'ativo'
ORDER BY created_at DESC;

-- View de estatísticas diárias
CREATE OR REPLACE VIEW vw_stats_diarias AS
SELECT 
    created_at::date as data,
    COUNT(*) as total_produtos,
    COUNT(url_curta) as com_link,
    COUNT(*) - COUNT(url_curta) as sem_link,
    ROUND(AVG(preco_atual), 2) as preco_medio,
    ROUND(AVG(desconto), 1) as desconto_medio
FROM ml_ofertas 
GROUP BY created_at::date
ORDER BY data DESC;

-- =============================================
-- DADOS DE TESTE (OPCIONAL - REMOVER EM PROD)
-- =============================================

/*
INSERT INTO ml_ofertas (mlb_id, url_original, nome, preco_atual, chave_dedupe) VALUES 
('MLB1234567890', 'https://produto.mercadolivre.com.br/MLB-1234567890-produto-teste', 'Produto de Teste', 29.90, 'mlb:MLB1234567890');
*/

-- =============================================
-- GRANTS de PERMISSÃO
-- =============================================

GRANT SELECT, INSERT, UPDATE, DELETE ON ml_ofertas TO ml_user;
GRANT USAGE, SELECT ON SEQUENCE ml_ofertas_id_seq TO ml_user;
GRANT SELECT ON vw_produtos_afiliados, vw_stats_diarias TO ml_user;