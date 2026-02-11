from src.domain.entities.coupons import CouponEntity
from src.infrastructure.scraping.ml_playwright_scraper import MercadoLivrePlaywrightScraper
from src.infrastructure.scraping.parsers import parse_coupon_card


def test_build_svg_data_uri_from_svg_html():
    scraper = MercadoLivrePlaywrightScraper()
    svg_html = '<svg width="40" height="40"><rect width="40" height="40"/></svg>'

    data_uri = scraper._build_svg_data_uri(svg_html)

    assert data_uri is not None
    assert data_uri.startswith("data:image/svg+xml;utf8,")
    assert "%3Csvg%20width%3D%2240%22" in data_uri


def test_normalize_coupon_candidates_uses_svg_data_uri_when_available():
    scraper = MercadoLivrePlaywrightScraper()
    raw_cards = [
        {
            "nome": "R$ 8 OFF FESTAS",
            "desconto_texto": "R$ 8",
            "limite_condicoes": "Compra minima R$79",
            "imagem_url": None,
            "imagem_svg_html": '<svg width="40" height="40"><circle cx="20" cy="20" r="19"/></svg>',
            "imagem_data_uri": None,
            "imagem_tipo": None,
            "url_origem": "https://www.mercadolivre.com.br/cupons",
            "raw_text": "R$ 8 OFF FESTAS Compra minima R$79",
        }
    ]

    normalized = scraper._normalize_coupon_candidates(raw_cards=raw_cards, max_cupons=5)

    assert len(normalized) == 1
    assert normalized[0]["imagem_tipo"] == "svg_data_uri"
    assert normalized[0]["imagem_url"] is not None
    assert normalized[0]["imagem_url"].startswith("data:image/svg+xml;utf8,")
    assert normalized[0]["imagem_data_uri"] == normalized[0]["imagem_url"]
    assert normalized[0]["imagem_svg_html"] is not None


def test_normalize_coupon_candidates_without_svg_or_img_keeps_null_image():
    scraper = MercadoLivrePlaywrightScraper()
    raw_cards = [
        {
            "nome": "15% OFF em Casa",
            "desconto_texto": "15%",
            "limite_condicoes": "Compra minima R$129,9",
            "imagem_url": None,
            "imagem_svg_html": None,
            "imagem_data_uri": None,
            "imagem_tipo": None,
            "url_origem": "https://www.mercadolivre.com.br/cupons",
            "raw_text": "15% OFF em Casa Compra minima R$129,9",
        }
    ]

    normalized = scraper._normalize_coupon_candidates(raw_cards=raw_cards, max_cupons=5)

    assert len(normalized) == 1
    assert normalized[0]["imagem_url"] is None
    assert normalized[0]["imagem_data_uri"] is None
    assert normalized[0]["imagem_tipo"] is None


def test_parse_and_entity_preserve_svg_data_uri_payload():
    scraper = MercadoLivrePlaywrightScraper()
    raw_cards = [
        {
            "nome": "7% OFF Leva Agora!",
            "desconto_texto": "7%",
            "limite_condicoes": "Compra minima R$799",
            "imagem_svg_html": '<svg width="24" height="24"><path d="M1 1 L2 2"/></svg>',
            "url_origem": "https://www.mercadolivre.com.br/cupons",
            "raw_text": "7% OFF Leva Agora! Compra minima R$799",
        }
    ]

    normalized = scraper._normalize_coupon_candidates(raw_cards=raw_cards, max_cupons=5)
    parsed = parse_coupon_card(normalized[0])
    entity = CouponEntity.from_raw(parsed, source_url=parsed["url_origem"] or "")

    assert parsed["imagem_url"] is not None
    assert parsed["imagem_url"].startswith("data:image/svg+xml;utf8,")
    assert parsed["raw_payload"]["imagem_tipo"] == "svg_data_uri"
    assert entity.imagem_url is not None
    assert entity.imagem_url.startswith("data:image/svg+xml;utf8,")
    assert entity.raw_payload["raw_payload"]["imagem_svg_html"] is not None
