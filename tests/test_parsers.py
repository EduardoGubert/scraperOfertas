from decimal import Decimal

from src.infrastructure.scraping.parsers import parse_coupon_card, parse_tempo_para_acabar


def test_parse_tempo_para_acabar_normalizes_spaces():
    raw = "  termina   em  01:23:45  "
    assert parse_tempo_para_acabar(raw) == "termina em 01:23:45"


def test_parse_coupon_card_percent():
    raw = {
        "nome": "Cupom Mercado",
        "desconto_texto": "35%",
        "limite_condicoes": "Minimo R$50",
        "imagem_url": "https://img",
        "url_origem": "https://www.mercadolivre.com.br/cupons",
    }
    parsed = parse_coupon_card(raw)
    assert parsed["desconto_percentual"] == 35
    assert parsed["desconto_valor"] is None


def test_parse_coupon_card_currency():
    raw = {
        "nome": "Cupom Mercado",
        "desconto_texto": "R$ 25,90",
        "limite_condicoes": "Ate 1 uso",
        "imagem_url": "https://img",
        "url_origem": "https://www.mercadolivre.com.br/cupons",
    }
    parsed = parse_coupon_card(raw)
    assert parsed["desconto_percentual"] is None
    assert parsed["desconto_valor"] == Decimal("25.90")
