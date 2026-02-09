-- =============================================
-- SCHEMA MYSQL - ML OFERTAS (ALTERNATIVA)
-- =============================================

-- Criar database
-- CREATE DATABASE ml_ofertas_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- CREATE USER 'ml_user'@'%' IDENTIFIED BY 'sua_senha_super_segura';
-- GRANT ALL PRIVILEGES ON ml_ofertas_db.* TO 'ml_user'@'%';

USE ml_ofertas_db;

CREATE TABLE IF NOT EXISTS ml_ofertas (
    -- Identificadores
    id INT AUTO_INCREMENT PRIMARY KEY,
    mlb_id VARCHAR(50) UNIQUE,
    chave_dedupe VARCHAR(255) NOT NULL UNIQUE,
    
    -- URLs e Links  
    url_original TEXT NOT NULL,
    url_curta TEXT,
    url_afiliado TEXT,
    product_id VARCHAR(100),
    
    -- Dados do Produto
    nome TEXT,
    foto_url TEXT,
    
    -- Preços
    preco_atual DECIMAL(10,2),
    preco_original DECIMAL(10,2), 
    desconto INT,
    
    -- Metadados
    status VARCHAR(20) DEFAULT 'ativo',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Índices
    INDEX idx_mlb_id (mlb_id),
    INDEX idx_chave_dedupe (chave_dedupe),
    INDEX idx_created_at (created_at DESC),
    INDEX idx_status (status)
) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;