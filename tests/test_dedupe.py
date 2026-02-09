from src.domain.value_objects.dedupe import build_coupon_dedupe_key, build_offer_dedupe_key, extract_mlb_id, normalize_url


def test_normalize_url_removes_query_and_fragment():
    url = "https://produto.mercadolivre.com.br/MLB-123456789?tracking=1#foo"
    assert normalize_url(url) == "https://produto.mercadolivre.com.br/mlb-123456789"


def test_extract_mlb_id_from_multiple_patterns():
    assert extract_mlb_id("https://x.com/p/MLB12345678") == "MLB12345678"
    assert extract_mlb_id("https://x.com/MLB-9876543210-aa") == "MLB9876543210"
    assert extract_mlb_id("https://x.com/no-id") is None


def test_build_offer_dedupe_priority():
    assert build_offer_dedupe_key("MLB123", None, "https://a") == "mlb:MLB123"
    assert build_offer_dedupe_key(None, "ABC-1", "https://a") == "pid:ABC-1"
    key = build_offer_dedupe_key(None, None, "https://a.com/p/1")
    assert key.startswith("url:")


def test_build_coupon_dedupe_deterministic():
    first = build_coupon_dedupe_key("https://a", "Cupom X", "20%")
    second = build_coupon_dedupe_key("https://a", "Cupom X", "20%")
    assert first == second
