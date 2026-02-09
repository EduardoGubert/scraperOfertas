from decimal import Decimal

from src.domain.entities.coupons import CouponEntity
from src.domain.entities.offers import OfferEntity


def test_offer_entity_from_raw_generates_dedupe_and_numbers():
    raw = {
        "url_original": "https://produto.mercadolivre.com.br/MLB-123456789-item",
        "preco_atual": "19.90",
        "preco_original": "39.90",
        "desconto": "50",
        "nome": "Produto Teste",
    }
    entity = OfferEntity.from_raw(raw)
    assert entity.mlb_id == "MLB123456789"
    assert entity.preco_atual == Decimal("19.90")
    assert entity.preco_original == Decimal("39.90")
    assert entity.desconto == 50
    assert entity.chave_dedupe == "mlb:MLB123456789"
    assert entity.minimal_required() is True


def test_coupon_entity_from_raw_generates_dedupe():
    raw = {
        "nome": "Cupom Casa",
        "desconto_texto": "20%",
        "desconto_percentual": 20,
        "desconto_valor": None,
        "limite_condicoes": "Minimo R$100",
        "imagem_url": "https://img",
        "url_origem": "https://www.mercadolivre.com.br/cupons",
    }
    entity = CouponEntity.from_raw(raw, source_url=raw["url_origem"])
    assert entity.chave_dedupe.startswith("coupon:")
    assert entity.minimal_required() is True
