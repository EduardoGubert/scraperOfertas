from src.infrastructure.scraping.ml_playwright_scraper import MercadoLivrePlaywrightScraper


def test_normalize_coupon_candidates_dedup_and_limit():
    scraper = MercadoLivrePlaywrightScraper()
    raw_cards = [
        {
            "nome": "Cupom Pet Shop",
            "desconto_texto": "15%",
            "limite_condicoes": "minimo R$ 50",
            "imagem_url": "https://img/pet.jpg",
            "url_origem": "https://www.mercadolivre.com.br/cupons/pet",
            "raw_text": "Cupom Pet Shop 15% minimo R$ 50",
        },
        {
            "nome": "Cupom Pet Shop",
            "desconto_texto": "15%",
            "limite_condicoes": "minimo R$ 50",
            "imagem_url": "https://img/pet.jpg",
            "url_origem": "https://www.mercadolivre.com.br/cupons/pet",
            "raw_text": "Cupom Pet Shop 15% minimo R$ 50",
        },
        {
            "nome": "Cupom Casa",
            "desconto_texto": "R$ 20,00",
            "limite_condicoes": "ate 1 uso",
            "imagem_url": "https://img/casa.jpg",
            "url_origem": "https://www.mercadolivre.com.br/cupons/casa",
            "raw_text": "Cupom Casa R$ 20,00 ate 1 uso",
        },
    ]

    normalized = scraper._normalize_coupon_candidates(raw_cards=raw_cards, max_cupons=2)

    assert len(normalized) == 2
    assert normalized[0]["nome"] == "Cupom Pet Shop"
    assert normalized[1]["nome"] == "Cupom Casa"


def test_normalize_coupon_candidates_fills_missing_fields_from_raw_text():
    scraper = MercadoLivrePlaywrightScraper()
    raw_cards = [
        {
            "nome": "",
            "desconto_texto": None,
            "limite_condicoes": None,
            "imagem_url": None,
            "url_origem": "https://www.mercadolivre.com.br/cupons/teste",
            "raw_text": "Super cupom mercado 10% valido ate hoje",
        }
    ]

    normalized = scraper._normalize_coupon_candidates(raw_cards=raw_cards, max_cupons=5)

    assert len(normalized) == 1
    assert normalized[0]["desconto_texto"] == "10%"
    assert normalized[0]["nome"].startswith("Super cupom mercado")
