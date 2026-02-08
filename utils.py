"""
Utilitários para normalização e deduplicação de dados
"""

import re
import hashlib
from typing import Dict, Optional, Any
from urllib.parse import urlparse, parse_qs


def normalizar_url(url: str) -> str:
    """
    Normaliza URL removendo parâmetros de tracking e fragmentos
    
    Args:
        url: URL original
        
    Returns:
        URL normalizada
    """
    if not url:
        return ""
    
    try:
        # Parse da URL
        parsed = urlparse(url.strip())
        
        # Remove fragmentos (#) e query parameters (?), mantém só path
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        # Remove trailing slash se não for root
        if normalized.endswith('/') and len(parsed.path) > 1:
            normalized = normalized[:-1]
            
        return normalized.lower()
    
    except Exception:
        return url.strip().lower()


def extrair_mlb_id(url: str) -> Optional[str]:
    """
    Extrai MLB ID da URL de forma robusta
    
    Args:
        url: URL do produto
        
    Returns:
        MLB ID formatado (ex: MLB1234567890) ou None
    """
    if not url:
        return None
    
    # Padrões possíveis: MLB-1234567890, MLB1234567890, /p/MLB1234567890
    patterns = [
        r'MLB[-]?(\d{8,12})',  # MLB-1234567890 ou MLB1234567890  
        r'/p/MLB(\d{8,12})',   # /p/MLB1234567890
        r'mlb[-]?(\d{8,12})',  # Case insensitive
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return f"MLB{match.group(1)}"
    
    return None


def normalizar_dados_produto(produto_raw: Dict) -> Dict[str, Any]:
    """
    Normaliza dados do produto para inserção no banco
    
    Args:
        produto_raw: Dados brutos do scraper
        
    Returns:
        Dados normalizados com chave de deduplicação
    """
    
    # Normalização básica
    produto = {
        'mlb_id': extrair_mlb_id(produto_raw.get('url_original', '')) or produto_raw.get('mlb_id'),
        'url_original': normalizar_url(produto_raw.get('url_original', '')),
        'url_curta': (produto_raw.get('url_curta') or '').strip() or None,
        'url_afiliado': (produto_raw.get('url_afiliado') or '').strip() or None,  
        'product_id': (produto_raw.get('product_id') or '').strip() or None,
        'nome': (produto_raw.get('nome') or '').strip() or None,
        'foto_url': (produto_raw.get('foto_url') or '').strip() or None,
        'preco_atual': produto_raw.get('preco_atual'),
        'preco_original': produto_raw.get('preco_original'),
        'desconto': produto_raw.get('desconto'),
        'status': produto_raw.get('status', 'ativo')
    }
    
    # Gera chave de deduplicação
    produto['chave_dedupe'] = gerar_chave_dedupe(produto)
    
    return produto


def gerar_chave_dedupe(produto: Dict) -> str:
    """
    Gera chave única para deduplicação baseada em prioridades:
    1. mlb_id (mais confiável)
    2. product_id (segundo mais confiável) 
    3. hash da URL normalizada (fallback)
    
    Args:
        produto: Dados do produto
        
    Returns:
        String única para deduplicação
    """
    
    # Prioridade 1: MLB ID
    if produto.get('mlb_id'):
        return f"mlb:{produto['mlb_id']}"
    
    # Prioridade 2: Product ID  
    if produto.get('product_id'):
        return f"pid:{produto['product_id']}"
    
    # Prioridade 3: Hash da URL normalizada
    url_norm = produto.get('url_original', '')
    if url_norm:
        url_hash = hashlib.md5(url_norm.encode('utf-8')).hexdigest()[:16]
        return f"url:{url_hash}"
    
    # Fallback: hash de dados disponíveis
    fallback_data = f"{produto.get('nome', '')}{produto.get('preco_atual', '')}"
    fallback_hash = hashlib.md5(fallback_data.encode('utf-8')).hexdigest()[:16]
    return f"fb:{fallback_hash}"


def validar_produto(produto: Dict) -> tuple[bool, str]:
    """
    Valida se produto tem dados mínimos necessários
    
    Args:
        produto: Dados do produto
        
    Returns:
        (is_valid, error_message)
    """
    
    if not produto.get('url_original'):
        return False, "URL original é obrigatória"
    
    if not produto.get('chave_dedupe'):
        return False, "Chave de deduplicação não foi gerada"
    
    # Validações opcionais mas recomendadas
    warnings = []
    if not produto.get('nome'):
        warnings.append("Nome do produto não encontrado")
    
    if not produto.get('preco_atual'):
        warnings.append("Preço atual não encontrado")
        
    if warnings:
        return True, f"⚠️ Avisos: {'; '.join(warnings)}"
    
    return True, "Produto válido"